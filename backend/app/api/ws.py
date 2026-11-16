"""WebSocket /ws/sim (BACKEND §4): hello on connect, then tick/status/event_applied pushes.
Client may send "ping" (or {"type":"ping"}); server answers {"type":"pong"}."""

import json

import anyio  # Starlette's own concurrency layer; cooperates with its cancel scopes
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


def _is_ping(text: str) -> bool:
    if text == "ping":
        return True
    try:
        return json.loads(text).get("type") == "ping"
    except (ValueError, AttributeError):
        return False


@router.websocket("/ws/sim")
async def sim_ws(ws: WebSocket) -> None:
    await ws.accept()
    c = ws.app.state.sessions.get(ws.query_params.get("session"))
    q = c.subscribe()
    try:
        await ws.send_json({"type": "hello", "snapshot": c.snapshot().model_dump(mode="json")})
        async with anyio.create_task_group() as tg:

            async def push() -> None:
                while True:
                    await ws.send_json(await q.get())

            async def pull() -> None:
                try:
                    while True:
                        if _is_ping(await ws.receive_text()):
                            await ws.send_json({"type": "pong"})
                except WebSocketDisconnect:
                    pass
                finally:
                    tg.cancel_scope.cancel()  # client gone: stop pushing

            tg.start_soon(push)
            tg.start_soon(pull)
    except WebSocketDisconnect:
        pass
    finally:
        c.unsubscribe(q)

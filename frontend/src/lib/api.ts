import type {
  ApiError,
  Architecture,
  ControlRequest,
  ControlResponse,
  EventRequest,
  EventResponse,
  FormulaBreakdown,
  SimSnapshot,
  VisionScanResult,
} from '../types/contracts'

const BASE = import.meta.env.VITE_API_URL ?? ''

export class ApiFailure extends Error {
  readonly code: string
  constructor(code: string, message: string) {
    super(message)
    this.code = code
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    const json = !(init?.body instanceof FormData) // FormData sets its own multipart header
    res = await fetch(`${BASE}/api${path}`, {
      ...init,
      headers: json ? { 'Content-Type': 'application/json', ...init?.headers } : init?.headers,
    })
  } catch {
    throw new ApiFailure('network', 'The simulation server is unreachable.')
  }
  const body: unknown = await res.json().catch(() => null)
  if (!res.ok) {
    const err = (body as ApiError | null)?.error
    throw new ApiFailure(err?.code ?? String(res.status), err?.message ?? res.statusText)
  }
  return body as T
}

export const api = {
  health: (signal?: AbortSignal) => request<{ status: string }>('/health', { signal }),
  state: () => request<SimSnapshot>('/sim/state'),
  control: (body: ControlRequest) =>
    request<ControlResponse>('/sim/control', { method: 'POST', body: JSON.stringify(body) }),
  event: (body: EventRequest) =>
    request<EventResponse>('/sim/events', { method: 'POST', body: JSON.stringify(body) }),
  scan: (form: FormData) => request<VisionScanResult>('/vision/scan', { method: 'POST', body: form }),
  architecture: () => request<Architecture>('/meta/architecture'),
  formula: (skuId: string) =>
    request<FormulaBreakdown>(`/sim/skus/${encodeURIComponent(skuId)}/formula`),
}

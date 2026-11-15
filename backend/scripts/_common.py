import json
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
RAW = BACKEND / "data" / "raw"
SEED = BACKEND / "data" / "seed"
CORPUS = BACKEND / "data" / "rag" / "corpus"
SKU_BASE = Path(__file__).with_name("sku_base.json")
# Generic client name: no personal contact details in requests to outside services.
USER_AGENT = "ShelfSense-dev/0.1 (seed builder)"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  wrote {path.relative_to(BACKEND) if path.is_relative_to(BACKEND) else path}")

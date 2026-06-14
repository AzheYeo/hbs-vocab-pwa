from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "words.json"
INPUT_DIR = ROOT / "content_batches" / "completed"
MERGED_FILE = ROOT / "data" / "words.enriched.json"


def load_generated(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text.startswith("["):
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError(f"{path} must contain a JSON array")
        return data
    rows = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        item = json.loads(line)
        if isinstance(item, list):
            rows.extend(item)
        elif isinstance(item, dict):
            rows.append(item)
        else:
            raise ValueError(f"{path}:{line_no} is not an object or array")
    return rows


def normalize_pos_defs(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if not isinstance(item, dict):
            continue
        pos = str(item.get("pos", "")).strip()
        defs = item.get("defs")
        if isinstance(defs, str):
            defs = [defs]
        if not isinstance(defs, list):
            definition = item.get("definition")
            defs = [definition] if definition else []
        defs = [str(part).strip() for part in defs if str(part).strip()]
        if pos and defs:
            result.append({"pos": pos, "defs": defs})
    return result


def normalize_examples(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if not isinstance(item, dict):
            continue
        en = str(item.get("en", "")).strip()
        zh = str(item.get("zh", "")).strip()
        if en and zh:
            result.append({"en": en, "zh": zh})
    return result


def is_complete(item: dict[str, Any]) -> bool:
    return (
        bool(normalize_pos_defs(item.get("pos_defs")))
        and bool(str(item.get("etymology", "")).strip())
        and bool(str(item.get("formation_semantic", "")).strip())
        and 3 <= len(normalize_examples(item.get("examples"))) <= 5
    )


def main() -> None:
    payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in payload["words"]}
    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    merged_count = 0
    for path in sorted(INPUT_DIR.glob("*")):
        if path.suffix.lower() not in {".json", ".jsonl"}:
            continue
        for generated in load_generated(path):
            item_id = generated.get("id")
            if item_id not in by_id:
                continue
            target = by_id[item_id]
            pos_defs = normalize_pos_defs(generated.get("pos_defs"))
            examples = normalize_examples(generated.get("examples"))
            if pos_defs:
                target["pos_defs"] = pos_defs
            for key in ("etymology", "formation_semantic"):
                value = str(generated.get(key, "")).strip()
                if value:
                    target[key] = value
            if examples:
                target["examples"] = examples
            target["content_status"] = "complete" if is_complete(target) else "partial"
            merged_count += 1

    payload["words"] = list(by_id.values())
    payload["content_summary"] = {
        "complete": sum(1 for item in payload["words"] if item.get("content_status") == "complete"),
        "partial": sum(1 for item in payload["words"] if item.get("content_status") == "partial"),
        "needs_generation": sum(1 for item in payload["words"] if item.get("content_status") == "needs_generation"),
    }
    MERGED_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"Merged {merged_count} generated entries into {MERGED_FILE}")
    print(payload["content_summary"])


if __name__ == "__main__":
    main()

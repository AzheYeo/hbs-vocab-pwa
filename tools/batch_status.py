from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BATCH_DIR = ROOT / "content_batches"
COMPLETED_DIR = BATCH_DIR / "completed"


def count_json_entries(path: Path) -> int | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return len(data) if isinstance(data, list) else None


def main() -> None:
    batch_files = sorted(BATCH_DIR.glob("batch_*.jsonl"))
    completed = []
    missing = []
    invalid = []
    for path in batch_files:
        out = COMPLETED_DIR / f"{path.stem}.json"
        if not out.exists():
            missing.append(path.name)
            continue
        count = count_json_entries(out)
        if count is None:
            invalid.append(out.name)
        else:
            completed.append((out.name, count))

    print(f"total_batches: {len(batch_files)}")
    print(f"completed_batches: {len(completed)}")
    print(f"missing_batches: {len(missing)}")
    print(f"invalid_batches: {len(invalid)}")
    if completed:
        print("completed_tail:")
        for name, count in completed[-10:]:
            print(f"- {name}: {count}")
    if missing:
        print("missing_head:")
        for name in missing[:30]:
            print(f"- {name}")
    if invalid:
        print("invalid:")
        for name in invalid[:30]:
            print(f"- {name}")


if __name__ == "__main__":
    main()

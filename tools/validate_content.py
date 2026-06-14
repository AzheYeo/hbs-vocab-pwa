from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "words.json"
MAX_SAMPLE_ISSUES = 20


def is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_pos_defs(item: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    pos_defs = item.get("pos_defs")

    if not isinstance(pos_defs, list) or not pos_defs:
        return ["pos_defs must be a non-empty array"]

    for index, entry in enumerate(pos_defs, start=1):
        prefix = f"pos_defs[{index}]"
        if not isinstance(entry, dict):
            issues.append(f"{prefix} must be an object")
            continue

        if not is_nonempty_string(entry.get("pos")):
            issues.append(f"{prefix}.pos must be a non-empty string")

        defs = entry.get("defs")
        if not isinstance(defs, list):
            issues.append(f"{prefix}.defs must be an array")
        elif not defs:
            issues.append(f"{prefix}.defs must not be empty")
        else:
            for def_index, definition in enumerate(defs, start=1):
                if not is_nonempty_string(definition):
                    issues.append(f"{prefix}.defs[{def_index}] must be a non-empty string")

    return issues


def validate_examples(item: dict[str, Any]) -> list[str]:
    examples = item.get("examples")

    if not isinstance(examples, list):
        return ["examples must be an array with 3-5 items"]

    if not 3 <= len(examples) <= 5:
        return [f"examples must contain 3-5 items, found {len(examples)}"]

    return []


def validate_word(item: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    issues.extend(validate_pos_defs(item))
    issues.extend(validate_examples(item))

    if not is_nonempty_string(item.get("etymology")):
        issues.append("etymology must be non-empty")

    if not is_nonempty_string(item.get("formation_semantic")):
        issues.append("formation_semantic must be non-empty")

    return issues


def load_words() -> list[dict[str, Any]]:
    payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    words = payload.get("words") if isinstance(payload, dict) else payload

    if not isinstance(words, list):
        raise ValueError("words.json must contain a top-level words array or be an array")

    invalid_items = [index for index, item in enumerate(words, start=1) if not isinstance(item, dict)]
    if invalid_items:
        first = invalid_items[0]
        raise ValueError(f"words[{first}] must be an object")

    return words


def describe_word(item: dict[str, Any], fallback_index: int) -> str:
    word_id = item.get("id") or f"#{fallback_index}"
    word = item.get("word") or "<missing word>"
    return f"{word_id} ({word})"


def main() -> None:
    words = load_words()

    complete_count = 0
    sample_issues: list[str] = []

    for index, item in enumerate(words, start=1):
        issues = validate_word(item)
        if issues:
            if len(sample_issues) < MAX_SAMPLE_ISSUES:
                sample_issues.append(f"{describe_word(item, index)}: {'; '.join(issues)}")
        else:
            complete_count += 1

    total = len(words)
    needs_generation = total - complete_count

    print(f"total: {total}")
    print(f"complete: {complete_count}")
    print(f"needs_generation: {needs_generation}")
    print(f"sample_issues_first_{MAX_SAMPLE_ISSUES}:")

    if sample_issues:
        for issue in sample_issues:
            print(f"- {issue}")
    else:
        print("- none")


if __name__ == "__main__":
    main()

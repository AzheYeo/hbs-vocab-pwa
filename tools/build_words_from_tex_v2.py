#!/usr/bin/env python3
"""Build PWA data directly from the generated v2 LaTeX modules."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_DIR = REPO_ROOT / "tex" / "modules"
CSV_FILE = REPO_ROOT / "data" / "红宝书_考研英语词汇_完整词表.csv"
OUT_FILE = REPO_ROOT / "mobile_pwa" / "data" / "words.json"

FIELDS = ("释义", "词源", "构词", "例句")
POS_RE = re.compile(r"(adj|adv|prep|conj|pron|num|interj|vt|vi|n|v)\.", re.I)


def module_kind(filename: str) -> str:
    if filename.startswith("bikaoci"):
        return "必考词"
    if filename.startswith("jichuci"):
        return "基础词"
    return "超纲词"


def module_order(path: Path) -> tuple[int, int]:
    name = path.stem
    group = 0 if name.startswith("bikaoci") else 1 if name.startswith("jichuci") else 2
    match = re.search(r"unit_(\d+)", name)
    return group, int(match.group(1)) if match else 999


def source_from_csv(source: str) -> str:
    if source.startswith("必考词Unit_"):
        return f"bikaoci_unit_{int(source.rsplit('_', 1)[1]):02d}.tex"
    if source.startswith("基础词Unit_"):
        return f"jichuci_unit_{int(source.rsplit('_', 1)[1]):02d}.tex"
    if source == "超纲词":
        return "chaogangci.tex"
    return source


def load_csv_meta() -> dict[tuple[str, str], dict[str, object]]:
    meta: dict[tuple[str, str], dict[str, object]] = {}
    if not CSV_FILE.exists():
        return meta
    with CSV_FILE.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            word = row.get("单词", "").strip()
            source = source_from_csv(row.get("来源", ""))
            meta[(source, word)] = {
                "order": {
                    "global": int(row["序号"]) if row.get("序号", "").isdigit() else None,
                    "unit": int(row["单元内序号"]) if row.get("单元内序号", "").isdigit() else None,
                    "pdf_page": int(row["PDF页码"]) if row.get("PDF页码", "").isdigit() else None,
                },
                "source_meta": {
                    "csv_source": row.get("数据来源表", ""),
                    "tex_source": source,
                    "image_file": row.get("图片文件", ""),
                    "ocr_text": row.get("原始识别文本", ""),
                    "ocr_confidence": row.get("识别置信度", ""),
                },
            }
    return meta


def read_braced(text: str, open_brace: int) -> tuple[str, int]:
    depth = 0
    out: list[str] = []
    i = open_brace
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            out.append(ch)
            i += 1
            out.append(text[i])
        elif ch == "{":
            depth += 1
            if depth > 1:
                out.append(ch)
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return "".join(out), i + 1
            out.append(ch)
        else:
            out.append(ch)
        i += 1
    raise ValueError("unclosed brace")


def strip_latex(value: str) -> str:
    value = value.replace("\n", " ")
    value = re.sub(r"\\EntryField\{[^{}]*\}", " ", value)
    value = re.sub(r"\\(?:textit|textbf|emph)\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\(?:begingroup|endgroup|par|small|EntryRule)\b", " ", value)
    value = re.sub(r"\\color\{gray\}", " ", value)
    value = re.sub(r"\\textcolor\{gray\}\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\begin\{[^{}]+\}(?:\[[^\]]*\])?", " ", value)
    value = re.sub(r"\\end\{[^{}]+\}", " ", value)
    value = re.sub(r"\\[a-zA-Z]+\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\([#$%&_{}])", r"\1", value)
    value = value.replace("``", '"').replace("''", '"')
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def extract_fields(body: str) -> dict[str, str]:
    locations: list[tuple[int, str, int]] = []
    for field in FIELDS:
        token = rf"\EntryField{{{field}}}"
        for match in re.finditer(re.escape(token), body):
            locations.append((match.start(), field, match.end()))
        legacy = rf"\textbf{{【{field}】}}"
        for match in re.finditer(re.escape(legacy), body):
            locations.append((match.start(), field, match.end()))
    locations.sort()
    result: dict[str, str] = {}
    for i, (start, field, content_start) in enumerate(locations):
        end = locations[i + 1][0] if i + 1 < len(locations) else len(body)
        result[field] = body[content_start:end].strip()
    return result


def split_pos_defs(definition: str) -> list[dict[str, object]]:
    text = strip_latex(definition).strip(" ;；。")
    matches = list(POS_RE.finditer(text))
    if not text:
        return []
    if not matches:
        return [{"pos": "", "defs": [text]}]
    result: list[dict[str, object]] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        defs_text = text[start:end].strip(" ;；,，")
        defs = [part.strip(" ;；,，") for part in re.split(r"[；;]", defs_text) if part.strip(" ;；,，")]
        if defs:
            result.append({"pos": match.group(0), "defs": defs})
    return result or [{"pos": "", "defs": [text]}]


def parse_examples(raw: str) -> list[dict[str, str]]:
    match = re.search(r"\\begin\{enumerate\}(?:\[[^\]]*\])?(.*?)\\end\{enumerate\}", raw, flags=re.S)
    text = match.group(1) if match else raw
    examples: list[dict[str, str]] = []
    for chunk in re.split(r"(?m)\s*\\item\s+", text):
        chunk = chunk.strip()
        if not chunk:
            continue
        zh = ""
        zh_match = re.search(
            r"\\begingroup\\small\\color\{gray\}(.*?)\\par\\endgroup|\\textcolor\{gray\}\{([^{}]*)\}",
            chunk,
            flags=re.S,
        )
        if zh_match:
            zh = strip_latex(zh_match.group(1) or zh_match.group(2) or "")
            en = chunk[: zh_match.start()]
        else:
            en = chunk
        en = strip_latex(en)
        if en:
            examples.append({"en": en, "zh": zh})
    return examples


def iter_entries(text: str) -> list[tuple[str, str]]:
    entries: list[tuple[int, str, int]] = []
    for match in re.finditer(r"\\EntryWord\{", text):
        word, after = read_braced(text, match.end() - 1)
        entries.append((match.start(), strip_latex(word), after))
    if not entries:
        for match in re.finditer(r"\\item\[\s*\\textbf\{", text):
            word, after = read_braced(text, match.end() - 1)
            close = text.find("]", after)
            entries.append((match.start(), strip_latex(word), close + 1))
    result: list[tuple[str, str]] = []
    for index, (start, word, body_start) in enumerate(entries):
        end = entries[index + 1][0] if index + 1 < len(entries) else len(text)
        result.append((word, text[body_start:end]))
    return result


def parse_module(path: Path, csv_meta: dict[tuple[str, str], dict[str, object]]) -> list[dict[str, object]]:
    text = path.read_text(encoding="utf-8")
    chapter = re.search(r"\\chapter\*?\{([^{}]+)\}", text)
    module = strip_latex(chapter.group(1)) if chapter else path.stem
    kind = module_kind(path.name)
    words: list[dict[str, object]] = []
    for index, (word, body) in enumerate(iter_entries(text), start=1):
        fields = extract_fields(body)
        meta = csv_meta.get((path.name, word), {})
        examples = parse_examples(fields.get("例句", ""))
        entry: dict[str, object] = {
            "id": f"{path.stem}:{index}",
            "word": word,
            "module": module,
            "kind": kind,
            "source": path.name,
            "pos_defs": split_pos_defs(fields.get("释义", "")),
            "etymology": strip_latex(fields.get("词源", "")),
            "formation_semantic": strip_latex(fields.get("构词", "")),
            "examples": examples,
            "content_status": "complete" if fields.get("词源") and fields.get("构词") and len(examples) >= 3 else "partial",
        }
        if meta.get("order"):
            entry["order"] = meta["order"]
        if meta.get("source_meta"):
            entry["source_meta"] = meta["source_meta"]
        words.append(entry)
    return words


def main() -> None:
    csv_meta = load_csv_meta()
    all_words: list[dict[str, object]] = []
    for path in sorted(MODULE_DIR.glob("*.tex"), key=module_order):
        all_words.extend(parse_module(path, csv_meta))

    modules: dict[str, dict[str, object]] = {}
    for item in all_words:
        module = str(item["module"])
        modules.setdefault(module, {"name": module, "kind": item["kind"], "count": 0})
        modules[module]["count"] += 1

    complete = sum(1 for item in all_words if item["content_status"] == "complete")
    payload = {
        "version": 3,
        "schema": "hbs-vocab-etymology-v2-tex",
        "source": "tex/modules",
        "total": len(all_words),
        "content_summary": {
            "complete": complete,
            "partial": len(all_words) - complete,
        },
        "modules": list(modules.values()),
        "words": all_words,
    }
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"words: {len(all_words)}")
    print(f"complete: {complete}")
    print(f"output: {OUT_FILE}")


if __name__ == "__main__":
    main()

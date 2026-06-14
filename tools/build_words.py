from __future__ import annotations

import json
import re
import csv
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_DIR = REPO_ROOT / "tex" / "modules"
CSV_FILE = REPO_ROOT / "data" / "红宝书_考研英语词汇_完整词表.csv"
OUT_FILE = REPO_ROOT / "mobile_pwa" / "data" / "words.json"

FIELD_MAP = {
    "FieldEtym": "etymology",
    "FieldForm": "formation",
    "FieldSem": "semantic",
    "FieldMem": "memory",
    "FieldEx": "example",
    "FieldTrans": "translation",
}

POS_ALIASES = {
    "n": "n.",
    "v": "v.",
    "vt": "v.",
    "vi": "v.",
    "adj": "adj.",
    "adv": "adv.",
    "adu": "adv.",
    "prep": "prep.",
    "conj": "conj.",
    "pron": "pron.",
    "num": "num.",
    "interj": "interj.",
}


def read_braced(text: str, open_brace: int) -> tuple[str, int]:
    depth = 0
    out: list[str] = []
    i = open_brace
    while i < len(text):
        ch = text[i]
        if ch == "{":
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
    raise ValueError("Unclosed brace")


def strip_latex(value: str) -> str:
    value = value.replace("\n", " ")
    value = re.sub(r"\\text(?:it|bf|sl|emph)\{([^{}]*)\}", r"\1", value)
    value = value.replace(r"$\to$", "→")
    value = value.replace(r"$\leftrightarrow$", "↔")
    value = value.replace(r"$\approx$", "≈")
    value = value.replace(r"\%", "%")
    value = value.replace(r"\$", "$")
    value = value.replace(r"\'e", "é")
    value = value.replace(r"\aa", "å")
    value = value.replace(r"\ae{}", "ae")
    value = value.replace(r"\ae", "ae")
    value = value.replace(r"\=o", "o")
    value = value.replace(r"\=e", "e")
    value = value.replace(r"\u{e}", "e")
    value = value.replace(r"\c{c}", "c")
    value = value.replace(r"\v{C}", "C")
    value = re.sub(r"\\[a-zA-Z]+\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\([#$%&_{}])", r"\1", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def module_source_from_csv(source: str) -> str:
    if source.startswith("必考词Unit_"):
        number = int(source.rsplit("_", 1)[1])
        return f"bikaoci_unit_{number:02d}.tex"
    if source.startswith("基础词Unit_"):
        number = int(source.rsplit("_", 1)[1])
        return f"jichuci_unit_{number:02d}.tex"
    if source == "超纲词":
        return "chaogangci.tex"
    return source


def normalize_pos(pos: str) -> str:
    key = pos.lower().strip(". ")
    return POS_ALIASES.get(key, f"{key}.")


def clean_definition(value: str) -> str:
    value = value.strip()
    value = value.strip("；;，,。. ")
    value = value.replace(".....", "...")
    value = value.replace("....", "...")
    value = re.sub(r"\s+", " ", value)
    return value


def parse_ocr_pos_defs(word: str, raw: str) -> list[dict[str, object]]:
    if not raw:
        return []
    text = raw.strip()
    if text.lower().startswith(word.lower()):
        text = text[len(word):]
    text = re.sub(r"^[\[/【].*?[\]」】］]", "", text)
    text = text.replace("／", "/").replace("；", ";")
    text = text.replace("（常力", "").replace("（u）", "").replace("（c）", "")
    pattern = re.compile(r"(adj|adv|adu|prep|conj|pron|num|interj|vt|vi|n|v)\.?", re.I)
    matches = list(pattern.finditer(text))
    result: list[dict[str, object]] = []
    for i, match in enumerate(matches):
        pos = normalize_pos(match.group(1))
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        definition = clean_definition(text[start:end].strip("/ "))
        if not definition:
            continue
        definition = definition.replace("/", "；")
        defs = [clean_definition(part) for part in re.split(r"[;；]", definition) if clean_definition(part)]
        if defs:
            result.append({"pos": pos, "defs": defs, "source": "ocr"})
    return result


def load_csv_meta() -> dict[tuple[str, str], dict[str, object]]:
    meta: dict[tuple[str, str], dict[str, object]] = {}
    if not CSV_FILE.exists():
        return meta
    with CSV_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            source_file = module_source_from_csv(row.get("来源", ""))
            word = row.get("单词", "").strip()
            raw = row.get("原始识别文本", "").strip()
            meta[(source_file, word)] = {
                "order": {
                    "global": int(row["序号"]) if row.get("序号", "").isdigit() else None,
                    "unit": int(row["单元内序号"]) if row.get("单元内序号", "").isdigit() else None,
                    "pdf_page": int(row["PDF页码"]) if row.get("PDF页码", "").isdigit() else None,
                },
                "source_meta": {
                    "csv_source": row.get("数据来源表", ""),
                    "tex_source": source_file,
                    "image_file": row.get("图片文件", ""),
                    "ocr_text": raw,
                    "ocr_confidence": row.get("识别置信度", ""),
                },
                "pos_defs": parse_ocr_pos_defs(word, raw),
            }
    return meta


def module_kind(filename: str) -> str:
    if filename.startswith("bikaoci"):
        return "必考词"
    if filename.startswith("jichuci"):
        return "基础词"
    return "超纲词"


def module_order(path: Path) -> tuple[int, int]:
    name = path.stem
    if name.startswith("bikaoci"):
        group = 0
    elif name.startswith("jichuci"):
        group = 1
    else:
        group = 2
    m = re.search(r"unit_(\d+)", name)
    return group, int(m.group(1)) if m else 999


def parse_module(path: Path, csv_meta: dict[tuple[str, str], dict[str, object]]) -> list[dict[str, object]]:
    text = path.read_text(encoding="utf-8")
    chapter = re.search(r"\\chapter\*?\{([^{}]+)\}", text)
    module = chapter.group(1) if chapter else path.stem
    kind = module_kind(path.name)
    words: list[dict[str, object]] = []
    pos = 0
    while True:
        start = text.find(r"\begin{wordentry}", pos)
        if start < 0:
            break
        word_start = text.find("{", start + len(r"\begin{wordentry}"))
        word, after_word = read_braced(text, word_start)
        end = text.find(r"\end{wordentry}", after_word)
        if end < 0:
            break
        body = text[after_word:end]
        entry: dict[str, object] = {
            "id": f"{path.stem}:{len(words) + 1}",
            "word": strip_latex(word),
            "module": module,
            "kind": kind,
            "source": path.name,
        }
        row_meta = csv_meta.get((path.name, str(entry["word"])), {})
        if row_meta.get("order"):
            entry["order"] = row_meta["order"]
        if row_meta.get("source_meta"):
            entry["source_meta"] = row_meta["source_meta"]
        cursor = 0
        while cursor < len(body):
            found = None
            for macro in FIELD_MAP:
                idx = body.find("\\" + macro + "{", cursor)
                if idx >= 0 and (found is None or idx < found[0]):
                    found = (idx, macro)
            if found is None:
                break
            idx, macro = found
            open_brace = body.find("{", idx)
            content, cursor = read_braced(body, open_brace)
            entry[FIELD_MAP[macro]] = strip_latex(content)
        entry["pos_defs"] = row_meta.get("pos_defs", [])
        entry["formation_semantic"] = " ".join(
            str(entry.get(key, "")).strip()
            for key in ("formation", "semantic")
            if str(entry.get(key, "")).strip()
        )
        if entry.get("example") or entry.get("translation"):
            entry["examples"] = [
                {
                    "en": entry.get("example", ""),
                    "zh": entry.get("translation", ""),
                }
            ]
        else:
            entry["examples"] = []
        entry["content_status"] = "needs_generation"
        if entry["pos_defs"]:
            entry["content_status"] = "partial"
        words.append(entry)
        pos = end + len(r"\end{wordentry}")
    return words


def main() -> None:
    all_words: list[dict[str, object]] = []
    csv_meta = load_csv_meta()
    for path in sorted(MODULE_DIR.glob("*.tex"), key=module_order):
        all_words.extend(parse_module(path, csv_meta))
    modules: dict[str, dict[str, object]] = {}
    for item in all_words:
        module = str(item["module"])
        modules.setdefault(
            module,
            {
                "name": module,
                "kind": item["kind"],
                "count": 0,
            },
        )
        modules[module]["count"] = int(modules[module]["count"]) + 1
    payload = {
        "version": 2,
        "title": "红宝书考研英语词汇：词源学解释",
        "schema": {
            "pos_defs": [{"pos": "n./v./adj./adv.", "definition": "中文释义"}],
            "etymology": "词源解释",
            "formation_semantic": "构词 + 语义演变",
            "examples": [{"en": "English sentence.", "zh": "中文翻译。"}],
        },
        "count": len(all_words),
        "modules": list(modules.values()),
        "words": all_words,
    }
    OUT_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"Wrote {len(all_words)} words to {OUT_FILE}")


if __name__ == "__main__":
    main()

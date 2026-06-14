#!/usr/bin/env python3
"""Sync rewritten LaTeX modules to mobile_pwa word card format.

Parses the new v2 LaTeX format:
  \\item[\\textbf{WORD}]
  \\textbf{【释义】} POS and Chinese definitions
  \\textbf{【词源】} Etymology
  \\textbf{【构词】} Formation + semantics
  \\textbf{【例句】} Numbered examples with translations

Outputs: mobile_pwa/data/words.enriched.json
"""

from __future__ import annotations

import json
import re
import csv
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_DIR = REPO_ROOT / "tex" / "modules"
CSV_FILE = REPO_ROOT / "data" / "红宝书_考研英语词汇_完整词表.csv"
OUT_FILE = REPO_ROOT / "mobile_pwa" / "data" / "words.enriched.json"


def strip_latex(value: str) -> str:
    """Remove LaTeX markup from a string."""
    value = value.replace("\n", " ")
    # Remove italic/bold/emphasis
    value = re.sub(r"\\text(?:it|bf|sl|emph)\{([^{}]*)\}", r"\1", value)
    # Remove textbackslash
    value = value.replace("\\textbackslash{}", "\\")
    # Remove textasciitilde
    value = value.replace("\\textasciitilde{}", "~")
    # Remove textasciicircum
    value = value.replace("\\textasciicircum{}", "^")
    # Remove escaped special chars
    value = value.replace("\\#", "#")
    value = value.replace("\\$", "$")
    value = value.replace("\\%", "%")
    value = value.replace("\\&", "&")
    value = value.replace("\\_", "_")
    value = value.replace("\\{", "{")
    value = value.replace("\\}", "}")
    # Remove \hspace{}, \vspace{}, \hrulefill
    value = re.sub(r"\\hspace\{[^}]*\}", "", value)
    value = re.sub(r"\\vspace\{[^}]*\}", "", value)
    value = re.sub(r"\\hrulefill", "", value)
    # Remove \textcolor{gray}{...}
    value = re.sub(r"\\textcolor\{gray\}\{([^{}]*)\}", r"\1", value)
    # Remove other LaTeX commands
    value = re.sub(r"\\[a-zA-Z]+\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\([#$%&_{}])", r"\1", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def parse_pos_defs(text: str) -> list[dict]:
    """Parse POS and definitions from 释义 text like 'v. 辐射；散发；流露'"""
    if not text:
        return []

    result = []
    # Split by common POS abbreviations
    # Pattern: POS abbreviation followed by definitions
    pos_pattern = re.compile(
        r'(n\.|v\.|adj\.|adv\.|prep\.|conj\.|pron\.|num\.|interj\.|vt\.|vi\.|a\.)'
    )

    parts = pos_pattern.split(text)
    # parts will be like ['', 'v.', ' 辐射；散发；流露 ', 'n.', ' 物体；目标']
    i = 0
    while i < len(parts):
        part = parts[i].strip()
        if pos_pattern.match(part):
            pos = part.rstrip(".")
            if pos in ("a", "a."):
                pos = "adj"
            if pos in ("vt", "vi"):
                pos = "v"
            defs_text = parts[i + 1] if i + 1 < len(parts) else ""
            defs = [d.strip() for d in re.split(r'[；;，,/／]', defs_text) if d.strip()]
            result.append({"pos": f"{pos}.", "defs": defs})
            i += 2
        else:
            i += 1

    # Fallback: if no structured POS found, just split by common patterns
    if not result and text.strip():
        result.append({"pos": "", "defs": [d.strip() for d in re.split(r'[；;，]', text) if d.strip()]})

    return result


def parse_examples(text: str) -> list[dict]:
    """Parse example sentences from LaTeX enumerate environment.

    Expected format:
      \\item English sentence
      \\hspace{1em}\\textcolor{gray}{Chinese translation}
    """
    if not text:
        return []

    examples = []
    # Find all \item ... patterns
    # Each example is: \item English\n\hspace{1em}\textcolor{gray}{Chinese}
    items = re.split(r'\\item\s+', text)
    for item in items:
        item = item.strip()
        if not item:
            continue
        # Split by \hspace...\textcolor{gray}{
        en_part = re.sub(r'\s*\\hspace\{[^}]*\}.*$', '', item, flags=re.DOTALL).strip()
        zh_match = re.search(r'\\textcolor\{gray\}\{([^{}]*)\}', item)
        zh_part = zh_match.group(1) if zh_match else ""

        if en_part:
            examples.append({
                "en": strip_latex(en_part),
                "zh": strip_latex(zh_part),
            })

    return examples


def parse_module_v2(path: Path, csv_words: dict) -> list[dict]:
    """Parse a v2 format LaTeX module file."""
    text = path.read_text(encoding="utf-8")

    # Get chapter title
    chapter = re.search(r'\\chapter\{([^{}]+)\}', text)
    module_name = strip_latex(chapter.group(1)) if chapter else path.stem

    # Determine kind
    if path.name.startswith("bikaoci"):
        kind = "必考词"
    elif path.name.startswith("jichuci"):
        kind = "基础词"
    else:
        kind = "超纲词"

    words = []
    # Split by \item[\textbf{...}] to get individual word entries
    entries = re.split(r'\\item\[\\textbf\{([^{}]+)\}\]', text)
    # entries[0] is preamble, then alternating: word, content, word, content...

    word_index = 0
    for i in range(1, len(entries), 2):
        if i + 1 > len(entries):
            break
        word = strip_latex(entries[i])
        content = entries[i + 1] if i + 1 < len(entries) else ""

        entry = {
            "id": f"{path.stem}:{word_index + 1}",
            "word": word,
            "module": module_name,
            "kind": kind,
            "source": path.name,
        }

        # Look up CSV metadata
        csv_key = word.lower()
        if csv_key in csv_words:
            csv_entry = csv_words[csv_key]
            entry["order"] = csv_entry.get("order", {})
            if csv_entry.get("source_meta"):
                entry["source_meta"] = csv_entry["source_meta"]

        # Parse sections
        # 【释义】
        pos_match = re.search(r'\\textbf\{【释义】\}\s*(.+?)(?=\\textbf\{【|$)', content, re.DOTALL)
        pos_text = pos_match.group(1).strip() if pos_match else ""
        entry["pos_defs"] = parse_pos_defs(strip_latex(pos_text))

        # 【词源】
        etym_match = re.search(r'\\textbf\{【词源】\}\s*(.+?)(?=\\textbf\{【|$)', content, re.DOTALL)
        entry["etymology"] = strip_latex(etym_match.group(1)) if etym_match else ""

        # 【构词】
        form_match = re.search(r'\\textbf\{【构词】\}\s*(.+?)(?=\\textbf\{【例句】|$)', content, re.DOTALL)
        entry["formation_semantic"] = strip_latex(form_match.group(1)) if form_match else ""

        # 【例句】
        ex_match = re.search(r'\\textbf\{【例句】\}\s*(.+?)(?=\\vspace|\\hrulefill|$)', content, re.DOTALL)
        ex_text = ex_match.group(1) if ex_match else ""
        entry["examples"] = parse_examples(ex_text)

        words.append(entry)
        word_index += 1

    return words


def load_csv_words() -> dict:
    """Load CSV data indexed by lowercase word."""
    words = {}
    if not CSV_FILE.exists():
        return words

    with CSV_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            word = row.get("单词", "").strip()
            if not word:
                continue
            seq = int(row["序号"]) if row.get("序号", "").isdigit() else None
            unit_seq = int(row["单元内序号"]) if row.get("单元内序号", "").isdigit() else None
            pdf_page = int(row["PDF页码"]) if row.get("PDF页码", "").isdigit() else None

            words[word.lower()] = {
                "order": {
                    "global": seq,
                    "unit": unit_seq,
                    "pdf_page": pdf_page,
                },
                "source_meta": {
                    "csv_source": row.get("数据来源表", ""),
                    "source_module": row.get("来源", ""),
                    "ocr_text": row.get("原始识别文本", ""),
                    "ocr_confidence": row.get("识别置信度", ""),
                },
            }
    return words


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


def main() -> None:
    print("Loading CSV metadata...")
    csv_words = load_csv_words()
    print(f"  Loaded {len(csv_words)} words from CSV")

    print("\nParsing LaTeX modules...")
    all_words = []
    tex_files = sorted(MODULE_DIR.glob("*.tex"), key=module_order)

    if not tex_files:
        print("  ERROR: No .tex module files found!")
        return

    for path in tex_files:
        count = len(all_words)
        words = parse_module_v2(path, csv_words)
        all_words.extend(words)
        print(f"  {path.name}: {len(words)} words")

    # Build module summary
    modules = {}
    for item in all_words:
        mod_name = str(item["module"])
        if mod_name not in modules:
            modules[mod_name] = {
                "name": mod_name,
                "kind": item["kind"],
                "count": 0,
            }
        modules[mod_name]["count"] += 1

    # Build output
    payload = {
        "version": 3,
        "title": "红宝书考研英语词汇：词源学解释",
        "count": len(all_words),
        "modules": list(modules.values()),
        "words": all_words,
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"\nWrote {len(all_words)} words to {OUT_FILE}")

    # Validate
    missing_etymology = sum(1 for w in all_words if not w.get("etymology"))
    missing_examples = sum(1 for w in all_words if not w.get("examples"))
    print(f"  Missing etymology: {missing_etymology}")
    print(f"  Missing examples: {missing_examples}")


if __name__ == "__main__":
    main()

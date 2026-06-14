from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "words.json"
OUT_DIR = ROOT / "content_batches"


SYSTEM_PROMPT = """你是考研英语词汇内容编辑，任务是把一个词条改写成适合移动端背诵的结构化 JSON。

必须只输出 JSON，不要 Markdown，不要解释。

字段要求：
{
  "id": "原 id",
  "word": "原单词",
  "pos_defs": [
    {"pos": "词性缩写，如 v./n./adj.", "defs": ["中文释义，按考研常见义项"]}
  ],
  "etymology": "词源解释，解释来源、核心词根、历史演变，中文为主，必要处保留英文/拉丁词形",
  "formation_semantic": "构词 + 语义：说明前缀/词根/后缀，并串联现代义项如何从核心义发展出来",
  "examples": [
    {"en": "考研/学术语境英文例句", "zh": "自然中文翻译"}
  ]
}

例句数量规则：
- 如果中文释义只有 1 个主要义项，给 3 个例句。
- 如果有 2 个主要义项，给 4 个例句。
- 如果有 3 个或更多主要义项，给 5 个例句。
- 每条例句必须覆盖一个真实义项；多个义项时要尽量覆盖不同义项。

质量规则：
- 中文释义要简洁、准确、对标考研，不要生造罕见义项。
- 词源不要编造不确定来源；不确定时写“可能源自/词源不确定”，但仍给可记忆的核心线索。
- 例句不要过长，优先教育、科研、社会、经济、环境、文化等考研常见语境。
- 翻译要忠实，不要机器腔。
- 不要使用 LaTeX 命令。
"""


def main(batch_size: int = 40) -> None:
    payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    words = payload["words"]
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "system_prompt.txt").write_text(SYSTEM_PROMPT, encoding="utf-8")

    manifest = []
    for batch_index, start in enumerate(range(0, len(words), batch_size), start=1):
        batch = words[start : start + batch_size]
        path = OUT_DIR / f"batch_{batch_index:04d}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for item in batch:
                request = {
                    "id": item["id"],
                    "word": item["word"],
                    "module": item["module"],
                    "kind": item["kind"],
                    "existing": {
                        "etymology": item.get("etymology", ""),
                        "formation": item.get("formation", ""),
                        "semantic": item.get("semantic", ""),
                        "memory": item.get("memory", ""),
                        "example": item.get("example", ""),
                        "translation": item.get("translation", ""),
                        "pos_defs": item.get("pos_defs", []),
                    },
                }
                f.write(json.dumps(request, ensure_ascii=False) + "\n")
        manifest.append({"file": path.name, "count": len(batch)})

    (OUT_DIR / "manifest.json").write_text(
        json.dumps({"batch_size": batch_size, "batches": manifest}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(manifest)} batches to {OUT_DIR}")


if __name__ == "__main__":
    main()

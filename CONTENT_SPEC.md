# 词条内容标准

本文档定义 `mobile_pwa` 新词条内容的目标结构、质量规则和批量生成提示词。现有数据可逐步迁移；新增或重生成内容应优先遵守本标准。

## 目标

每个词条应让学习者同时获得四类信息：

- 词性和中文释义：明确考试常见义项，避免只有笼统中文翻译。
- 词源：说明来源语言、原始形式和核心意象。
- 构词与语义演变：把词根词缀拆解和现代义项联系起来。
- 例句：覆盖主要释义，并给出自然中文译文。

## JSON 字段

单个词条建议使用以下字段：

```json
{
  "id": "bikaoci_unit_01:1",
  "word": "radiate",
  "module": "必考词 Unit 1",
  "kind": "必考词",
  "source": "bikaoci_unit_01.tex",
  "pos_defs": [
    {
      "pos": "v.",
      "defs": ["辐射；放射", "散发；流露", "从中心向外扩散"]
    }
  ],
  "etymology": "源自拉丁语 radiare（发出光线），其词根 radius 本义为“光线、辐射线”。英语继承了“向外发出光线或能量”的核心意象。",
  "formation_semantic": "radi- 表示“光线、辐射线”，-ate 是动词后缀，表示“使……”。词义从“发出光线”扩展为物理意义上的“辐射”，再引申为信息、热量、情绪等“向外散发”。",
  "examples": [
    {
      "en": "The reactor is designed to prevent harmful particles from radiating into the environment.",
      "zh": "该反应堆的设计旨在防止有害粒子辐射到环境中。"
    },
    {
      "en": "Confidence seemed to radiate from her as she explained the research findings.",
      "zh": "当她解释研究发现时，自信似乎从她身上自然流露出来。"
    },
    {
      "en": "Several roads radiate from the old square to different parts of the city.",
      "zh": "几条道路从老广场向城市不同区域辐射开去。"
    }
  ]
}
```

### 字段说明

- `id`: 稳定唯一标识，建议沿用模块和序号格式。
- `word`: 词头。保留必要的英美拼写提示，如 `hono(u)r`。
- `module`: 所属单元，如 `必考词 Unit 1`。
- `kind`: 词表类型，如 `必考词`、`基础词`、`超纲词`。
- `source`: 原始来源文件名，便于追溯。
- `pos_defs`: 词性和中文释义数组。
- `etymology`: 词源说明，突出来源和核心意象。
- `formation_semantic`: 构词拆解和语义演变合并说明。
- `examples`: 英文例句和中文译文数组，数量为 3-5 条。

## pos_defs 规则

`pos_defs` 是数组，每项对应一个词性：

```json
{
  "pos": "n.",
  "defs": ["目标；目的", "物体；对象"]
}
```

规则：

- `pos` 使用常见缩写：`n.`、`v.`、`adj.`、`adv.`、`prep.`、`conj.`、`pron.`、`num.`、`interj.`。
- 一个词有多个主要词性时，按考研常见程度排序。
- `defs` 使用中文短语，不写完整解释句。
- 每个词性下保留 1-4 个高频义项，优先覆盖考研阅读和翻译常见义。
- 多义词要区分含义，不把无关义项压成一个笼统翻译。
- 派生词或专业义可收录，但不得挤掉核心义。

## etymology 规则

`etymology` 负责说明“这个词从哪里来”：

- 说明来源语言和关键原形，如拉丁语、希腊语、古法语、中古英语。
- 给出原形的大意，使用中文括注。
- 解释核心意象，如“投掷”“捆绑”“光线”“边界”。
- 不确定的词源要明确写“可能”“通常认为”，避免绝对化。
- 不要堆砌冷僻音变细节；服务记忆和理解即可。

## formation_semantic 规则

`formation_semantic` 负责说明“它怎么组成、怎么变成现代义”：

- 先拆构词：前缀、词根、后缀及其含义。
- 再讲语义链：原始具体义 -> 抽象义 -> 现代常见义。
- 同根词可少量列举，用于帮助辨析。
- 避免机械拆错。若词形不是透明构词，应说明“现代英语中可联想为……，但历史上并非直接由……构成”。
- 语言应简洁，一般 1-3 句。

## examples 规则

`examples` 是数组，每项包含：

```json
{
  "en": "A fair evaluation system must be based on objective criteria.",
  "zh": "公平的评价体系必须基于客观标准。"
}
```

数量规则：

- 1 个主要释义：3 条例句。
- 2 个主要释义：3-4 条例句，至少覆盖每个释义。
- 3 个及以上主要释义：4-5 条例句，优先覆盖高频义。
- 词性差异明显时，每个主要词性至少 1 条。

质量规则：

- 英文例句应自然、现代、考试友好，长度建议 10-22 个词。
- 例句优先使用学术、社会、科技、教育、经济、法律、文化等考研常见语境。
- 译文应忠实自然，不逐词硬译。
- 例句必须体现目标词的具体义项，不能只是泛泛出现。
- 避免敏感、暴力、低俗或过强政治立场的内容。
- 不使用专有名人、真实品牌或过时新闻作为必要理解条件。

## 整体质量规则

- JSON 必须可解析，不允许尾逗号、注释或未转义引号。
- 所有字符串使用中文全角标点时保持一致；英文例句使用英文标点。
- 同一个词条内部不要自相矛盾，例如词源说“投掷”，构词却解释为“看见”。
- 不编造明确词源。拿不准时写成保守表述。
- 不把记忆法写进 `etymology`；如后续需要记忆字段，应单独增加 `memory`。
- 内容以考研英语学习为目标，不追求百科式全面。
- 避免 AI 腔套话，如“在现代社会中具有重要意义”，除非例句确实需要。
- 生成后至少抽查：字段完整性、例句数量、词性覆盖、中文释义是否贴合英文例句。

## 批量生成提示词模板

可将以下模板用于分批生成或补全词条。批量时建议每批 20-50 个词，降低格式错误率。

```text
你是一名考研英语词汇内容编辑。请为下面的英文单词生成结构化 JSON 词条。

任务要求：
1. 每个词条必须包含字段：id, word, module, kind, source, pos_defs, etymology, formation_semantic, examples。
2. pos_defs 是数组；每项包含 pos 和 defs。pos 使用 n./v./adj./adv. 等缩写，defs 是中文释义数组。
3. etymology 用中文说明词源来源、原始形式和核心意象；不确定时使用保守表述。
4. formation_semantic 用中文说明构词拆解和语义演变，把词根词缀与现代义联系起来。
5. examples 是数组，每项包含 en 和 zh。例句数量 3-5 条：
   - 1 个主要释义给 3 条；
   - 2 个主要释义给 3-4 条；
   - 3 个及以上主要释义给 4-5 条。
6. 例句要覆盖主要词性和高频义项，英文自然，中文译文忠实。
7. 只输出 JSON 数组，不输出解释、Markdown 或额外文本。

输入词表：
[
  {
    "id": "bikaoci_unit_01:1",
    "word": "radiate",
    "module": "必考词 Unit 1",
    "kind": "必考词",
    "source": "bikaoci_unit_01.tex"
  }
]
```

## JSON 示例

```json
[
  {
    "id": "bikaoci_unit_01:4",
    "word": "object",
    "module": "必考词 Unit 1",
    "kind": "必考词",
    "source": "bikaoci_unit_01.tex",
    "pos_defs": [
      {
        "pos": "n.",
        "defs": ["物体；对象", "目标；目的"]
      },
      {
        "pos": "v.",
        "defs": ["反对；不赞成"]
      }
    ],
    "etymology": "源自拉丁语 objectum（投在面前的东西），由 ob-（朝向、对着）和 iacere（投掷）构成，经古法语进入英语。",
    "formation_semantic": "ob- 表示“朝向、对着”，ject- 表示“投掷”。“被投在面前的东西”发展出名词义“物体、对象”；“把意见投向对面”则引申为动词义“反对”。",
    "examples": [
      {
        "en": "The museum displayed a small object found during the archaeological excavation.",
        "zh": "博物馆展出了一件在考古发掘中发现的小物件。"
      },
      {
        "en": "The main object of the policy is to reduce inequality in education.",
        "zh": "这项政策的主要目标是减少教育不平等。"
      },
      {
        "en": "Several committee members objected to the proposal because it lacked financial details.",
        "zh": "几名委员会成员反对该提案，因为它缺少财务细节。"
      },
      {
        "en": "Parents may object if schools collect personal data without clear consent.",
        "zh": "如果学校未经明确同意就收集个人数据，家长可能会反对。"
      }
    ]
  }
]
```


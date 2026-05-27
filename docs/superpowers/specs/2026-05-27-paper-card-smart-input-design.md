# paper-card 智能输入 + 语言支持

## 问题

paper-card 当前只接受 `folder_slug` 作为输入，要求 `metadata.yaml` 和 `paper.md` 已存在。用户实际场景中可能给出论文标题、DOI、arXiv 链接、本地 PDF 路径等。每次都要手动跑 paper-search → paper-acquire 才能做卡片，体验断裂。

## 目标

1. paper-card 接受多种输入格式，自动检测类型并补全前置条件
2. 卡片输出语言可控，默认跟随用户对话语言

## 输入类型检测

```
用户输入
  │
  ├─ $PAPERS_DIR/{input}/metadata.yaml 存在？
  │   → 已导入论文，直接检查 paper.md 并生成卡片
  │
  ├─ 本地文件存在且以 .pdf 结尾？
  │   → 本地 PDF 路径，走"本地 PDF 处理流程"
  │
  └─ 其他（标题/DOI/arXiv ID/URL）
      → 委托 paper-import，然后生成卡片
```

### 检测优先级

1. **folder_slug**：先检查 `$PAPERS_DIR/{input}/metadata.yaml` 是否存在。存在则直接进入卡片生成。不需要模式匹配 — 目录存在即为有效 slug。
2. **本地 PDF**：检查输入是否为本地存在的 `.pdf` 文件（`Path(input).suffix == '.pdf' and Path(input).is_file()`）。
3. **论文引用**：其他所有输入视为论文引用（标题/DOI/arXiv ID/URL），委托 paper-import 处理。

## 本地 PDF 处理流程

用户给本地 PDF（如 `~/Downloads/paper.pdf`）时，不能直接走 paper-import（它会重新搜索+下载）。需要拆分步骤：

1. **pdf-to-md**：调 `pdf-to-md` 把 PDF 转成 markdown，输出到 PDF 同目录
2. **paper-search**：用 PDF 文件名或用户提供的上下文信息解析论文身份，生成 `metadata.yaml`
3. **组织目录**：在 `$PAPERS_DIR/{folder_slug}/` 下创建标准目录结构，复制（不移动）PDF 和 markdown 到 `paper/` 子目录。保留用户原始文件不动。
4. **生成卡片**

### paper-search 解析策略

本地 PDF 没有现成的搜索结果，需要从有限信息推断：
- 从 PDF 文件名提取关键词（如 `2301.13688.pdf` → arXiv ID，`attention_is_all_you_need.pdf` → 标题）
- 如果文件名无法推断，询问用户补充信息（标题/DOI/arXiv ID）
- 拿到身份信息后，正常调 paper-search 生成 metadata.yaml

## 委托 paper-import

非 folder_slug、非本地 PDF 的输入（标题/DOI/arXiv/URL），paper-card 指示 agent：

1. 调用 paper-import skill，传入用户的论文引用
2. paper-import 完成 search → acquire 后，获得 folder_slug
3. paper-card 继续用该 folder_slug 生成卡片

这在 SKILL.md 中以自然语言指令实现，不需要代码。

## 语言支持

### `--lang` 选项

- `--lang zh`：中文
- `--lang en`：英文
- 未指定时：跟随用户对话语言（agent 从用户的自然语言推断：用户用中文提问则输出中文，用英文则输出英文）

### 语言规则

| 内容 | 语言 |
|---|---|
| frontmatter: title / authors / venue / url / code | 原文（不翻译） |
| frontmatter: tags / builds_on / contrasts_with / verdict / status | 跟随 --lang |
| Section headers (## Problem, ## Method, ...) | 跟随 --lang |
| 分析正文 | 跟随 --lang，技术术语保持英文原文 |

### 术语保持英文的原则

以下内容即使在中文卡片中也不翻译：
- 方法名：Transformer、BERT、GAT、Geom-GCN
- 数据集：CIFAR-10、ImageNet、OGB
- 指标：mAP、BLEU、F1、AUC
- 架构组件：attention head、MLP、GNN layer
- 专有名词：arXiv、Semantic Scholar、OpenReview

### 模板处理

模板文件保持英文不变。agent 在生成卡片时根据 `--lang` 指令翻译 section headers 和正文内容。不需要为每种语言维护模板副本。

## SKILL.md 变更

### argument-hint

```
-argument-hint: "<folder_slug>"
+argument-hint: "<论文引用 | folder_slug | PDF路径> [--lang zh|en]"
```

### 前置条件部分

替换为"输入处理"部分：

```markdown
## Input Handling

### 输入类型检测

按以下优先级检测输入类型：

1. **已导入论文**（folder_slug）：检查 `$PAPERS_DIR/{input}/metadata.yaml` 是否存在。
   存在 → 检查 paper.md → 生成卡片。
2. **本地 PDF**：输入是本地 `.pdf` 文件路径。
   → 调 pdf-to-md 转 markdown → paper-search 解析身份 → 组织目录 → 生成卡片。
3. **论文引用**（标题/DOI/arXiv/URL）：其他所有输入。
   → 委托 paper-import 完成 search+acquire → 用生成的 folder_slug → 生成卡片。
```

### Workflow 部分

在现有 Step 1 前插入 Step 0：

```markdown
### Step 0: Input Resolution

检测输入类型并确保前置条件满足（详见 Input Handling）。

完成后，以下文件必须存在：
- `$PAPERS_DIR/{folder_slug}/metadata.yaml`
- `$PAPERS_DIR/{folder_slug}/paper/paper.md`
```

### 语言指令

在 Workflow 末尾添加：

```markdown
### Language

卡片输出语言由 `--lang` 参数决定。未指定时跟随用户对话语言。

语言规则：
- 元数据字段（title/authors/venue/url/code）保持原文，不翻译
- Section headers、分析正文、tags、verdict 跟随 --lang
- 技术术语（方法名、数据集名、指标名）保持英文原文
```

## 不变的部分

- 双 subagent 并行提取（Structure Extractor + Evaluation Extractor）
- card.md（快速概览）和 card-deep.md（深度分析）双模板
- 综合规则：事实取保守、判断取平均、限制合并去重
- 模板文件内容（英文模板保持不变）
- subagent reference 文件内容

## 影响范围

- `skills/paper-card/SKILL.md`：主要改动
- `skills/paper-card/evals/evals.json`：新增输入类型和语言相关的 eval case
- 其他 skill 文件：不改动

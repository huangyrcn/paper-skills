# Subagent 1: Structure Extractor

Extract factual, verifiable content from a research paper. Output structured JSON.

## Task

Read the full paper markdown and extract the following structure. Be precise — use exact numbers, exact method names, exact dataset names from the paper. Do not speculate or add your own opinions.

## Output Schema

Return a single JSON object:

```json
{
  "tldr": "一句话: 做了什么 + 为什么值得读 (≤2 lines)",
  "problem": {
    "task": "具体任务描述",
    "input_output": "Input → Output",
    "setting": "实验设定/假设条件",
    "why_matters": "为什么这个问题重要"
  },
  "motivation": {
    "previous_methods": "之前的方法通常怎么做",
    "weakness": "它们的弱点",
    "key_insight": "本文的关键洞察"
  },
  "method": {
    "core_idea": "一句话核心思想",
    "pipeline": "整体流程描述",
    "key_modules": [
      {"name": "模块名", "description": "做什么"}
    ],
    "diff_from_baseline": "与最近 baseline 的关键差异"
  },
  "objective": {
    "type": "optimization | mechanism | theoretical_result",
    "description": "优化目标/系统机制/理论结果",
    "equations": ["关键公式或算法，用文字描述"],
    "components": [
      {"name": "项/模块名", "guarantee": "保证或鼓励什么"}
    ]
  },
  "experiments": {
    "datasets": ["数据集名称"],
    "baselines": ["baseline 方法名"],
    "metrics": ["评估指标"],
    "key_results": [
      {"metric": "指标名", "value": "具体数字", "setting": "在什么条件下"}
    ],
    "ablation_findings": ["消融实验揭示了什么"],
    "sensitivity": "对超参/条件的敏感性分析"
  },
  "tags": ["领域", "子方向", "方法关键词"],
  "builds_on": ["直接引用/建立在其上的方法"],
  "contrasts_with": ["对比/竞争的方法"]
}
```

## Rules

1. **Exact numbers**: Always include specific percentages, scores, or values from the paper
2. **No judgment**: Do not assess novelty, soundness, or quality — that's the other subagent's job
3. **Faithful extraction**: If the paper doesn't explicitly state something, omit it rather than infer
4. **Key modules**: Limit to the 2-4 most important components
5. **Tags**: 3-6 tags covering domain, subfield, and method type

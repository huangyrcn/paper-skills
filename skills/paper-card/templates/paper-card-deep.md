---
aliases: ["{{论文完整标题}}"]
authors: "{{第一作者 et al.}}"
year: {{YYYY}}
venue: "{{会议/期刊 + track}}"
url: "{{arxiv / doi}}"
code: "{{github / project page — 论文中未提及则填 null}}"
tags: ["领域", "子方向", "方法关键词 — 与输出语言一致，技术术语保持英文"]
status: skim
date_added: {{YYYY-MM-DD}}
builds_on: []
contrasts_with: []
superseded_by: []
novelty: 0
soundness: 0
reproducibility: 0
relevance: 0
verdict: ""
---

<!--
  填写说明: frontmatter 的 novelty / soundness / reproducibility / relevance /
  verdict 必须填入实际评分（不要留 0 或空字符串）。
  这些值来自你在 ## 10. My Evaluation 中的评分，两边必须一致。
-->

<!--
╔══════════════════════════════════════════════════════════════╗
║  提取指引 — 在填充本模板前阅读以下规则                         ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  忠实性: 只提取论文中明确陈述或直接暗示的内容。                  ║
║  不要引入外部知识。论文没提到的信息用 null 或省略。              ║
║                                                              ║
║  语言: section 正文使用 --lang 指定的语言（默认跟随用户语言）。  ║
║  每个 section 只用一种语言，不要中英文重复。                    ║
║  技术术语（方法名、数据集、指标）保持英文。                     ║
║                                                              ║
║  信息密度: 每个要点用完整的句子，不要过度压缩。                 ║
║  读者应该不需要回看论文就能理解你说的内容。                     ║
║                                                              ║
║  公式: 所有数学公式用 LaTeX（$..$ 行内，$$...$$ 独立行）。     ║
║  不要用代码块或纯文本来写公式。                                ║
║                                                              ║
║  格式: 复制模板的 section 标题（含编号和注释），                 ║
║  保留 > [!tldr] / > [!success] 等 callout 语法。              ║
║                                                              ║
║  注释: 模板中的 <!-- ... --> 注释块仅用于指导提取，             ║
║  不要出现在最终输出中。填充完内容后删除这些注释。               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
-->

## 1. TL;DR

> [!tldr]
> 做了什么 + 为什么值得读。不超过两行。

## 2. Main Claim & Verification

作者主张 vs 你读完的判定，放在一起便于对照。

- **Claim**: 作者最核心的主张是什么（不是方法，是主张）
- **Evidence**: 作者用什么来支撑
- **Is the evidence enough?** yes | partially | no — 一句话理由

**真正证明了**:
1. 
2. 

**没有证明 / 回避了**:
1. 
2. 

## 3. Problem

- **Task**: 具体任务描述
- **Input → Output**: 
- **Setting / Assumption**: 实验设定或理论假设
- **Why this problem matters**: 

## 4. Motivation

- **Previous methods usually**: 
- **Their weakness**: 
- **Key insight of this paper**: 

## 5. Method

<!--
  这是"方法拆解"，不是"方法摘要"。目标读者：对 ML 有基础但不专攻该方向的人。
  
  在讲具体模块之前，先用 2-3 句话建立背景框架：
  - 这个方法属于什么范式？（如 GNN 的 message passing、seq2seq 的 encoder-decoder）
  - 如果使用了已知范式，用该范式的标准结构来定位本方法的创新点。
    例：message passing 范式有三个阶段——message（邻居发什么）、
    aggregate（怎么合并）、update（怎么更新自身）。
    说明本方法在哪一个阶段做了不同的设计。
  - 对读者可能熟悉的概念做桥接，但要讲清结构性差异，不要只贴标签。
    不能只说"类似 X"——要指出"和 X 的关键区别是什么"。
  - 明确哪些是借来的、哪些是新的。
    例："标准组件（message passing 框架、线性变换、softmax）沿用已有设计；
    本文核心贡献是 attention 打分函数 e_ij 及其在图拓扑上的 masked 应用。"

  每个模块用四步结构：
  1. 直觉：一句非技术语言解释这个模块要解决什么问题
     例："GCN 给所有邻居相同权重，但实际中不同邻居的重要性不同"
  2. 公式：LaTeX 展示具体计算。符号首次出现时用文字定义。
     - 如果是多层架构，公式必须带层级上标：$\vec{h}_i^{(l)}$, $\mathbf{W}^{(l)}$
     - 激活函数首次出现时说明具体是什么（如 ELU、ReLU），不要只写 σ
     - 例："输入节点特征 $\vec{h}_i$（维度为 F 的向量），乘以可学习的变换矩阵 $\mathbf{W}$..."
  3. 例子：用具体数字走一遍计算，必须算到最后一步得出数值结果
     不要中途停下（如"得到原始分数 e_ij"但不给出具体数字）。
     如果模块有多个并行子组件（如 multi-head、multiple branches），
     每个子组件都必须有完整的参数和至少一步计算推导——不能只给第一个算完、后面直接跳到结果。
  4. 设计动机：为什么这样而不那样，对比其他选择
     - 桥接概念时要讲清结构性差异，不要只贴标签。
       不能只说"类似 X"就完事——要点出"和 X 的关键区别是什么"。
     - 避免未定义的抽象术语（如"子空间"），如必须使用则给出具体含义。
  
  图特有的关键细节：
  - self-loop：说明节点是否对自己计算 attention（通常是，要明确写出）
  - 有向 vs 无向：attention 是否对称
  
  符号规范：
  - 公式用 LaTeX，不用代码块或纯文本
  - 拼接符号 || 首次出现时解释
  - 非标准激活函数（如 LeakyReLU）首次出现时简要解释：
    "LeakyReLU（允许小负值通过，斜率 0.2，而非像 ReLU 直接截断为 0）"
  
  结构要求：
  - Pipeline 应包含 skip connections、attention dropout 等影响模型行为的组件，
    不要把它们放在单独的杂项段落。如果它们只在某些架构变体中使用，注明适用范围。
-->

- **Core idea**(一句话): 
- **Pipeline**: 用 → 连接各步骤的整体流程（包含 skip connections、dropout 等影响行为的组件）
- **Context**: 这个方法属于什么范式？用读者熟悉的概念做桥接（2-3 句）。明确哪些是借来的、哪些是新的。
- **Key modules**:
  1. 模块名:
     - 直觉: 一句话解释要解决的问题
     - 公式: LaTeX，多层用层级上标，激活函数说明具体是什么
     - 例子: 具体数值走一遍，必须算到最后一步
     - 设计动机: 为什么这样设计
  2. 
  3. 
- **与最近 baseline 的差异**: 

## 6. Objective / Mechanism / Formula

- **Optimization objective / system mechanism / theoretical result**: 
- **Important equation / algorithm / theorem**: 
- **What each component guarantees or encourages**:
  - Term / Module A:
  - Term / Module B:

## 7. Why It Should Work

作者的逻辑链:

> Because ..., the model can ..., which improves ...

- **Convincing part**: 
- **Weak / questionable part**: 

## 8. Experiments

- **Datasets / setup**: 
- **Baselines**: 
- **Metrics**: 
- **最有说服力的结果**: 具体数字 + 在什么指标上
- **Ablation 揭示了什么**: 
- **Sensitivity / case study**: 

## 9. Limitations

- **作者承认的**: 
- **我看出来的**: 实验缺哪类、假设何时崩、scale 是否敏感

## 10. My Evaluation

<!--
  评分锚定（1-5 星）：
  Novelty:    3=已有技术的新组合  4=子领域内新范式  5=开创新方向
  Soundness:  3=实验支撑但有缺口  4=严谨证明+全面实验  5=数学证明无实验缺口
  Reproducibility: 3=论文细节足够复现但无代码  4=官方代码或超详细方法  5=代码+数据+完整配置
  论文没提到代码可用性时，仅基于方法描述的详细程度评分（通常 2-3）。
  大多数论文 novelty 和 soundness 在 2-3 之间。
-->

- Novelty: ★☆☆☆☆ — 一句话理由
- Soundness: ★☆☆☆☆ — 一句话理由
- Reproducibility: ★☆☆☆☆ — 一句话理由
- Relevance to my work: ★☆☆☆☆ — 怎么相关

## 11. Takeaway & Inspiration

- **能直接搬的**: idea / 实验设计 / baseline / 数据集 / 代码
- **想追问的实验**: 
- **如果我来做,会怎么改**: 
- **可能延伸出的 research idea**: 

## 12. Open Questions

- [ ] 
- [ ] 

## 13. Follow-up

- **后续工作**: 
- **被反驳 / 推翻**: 
- **我自己是否引用过**: no
- **必读前置文献**: 

## 14. Final Verdict

<!--
  选一个，不犹豫：
  - Worth reading deeply: 主张有强证据支撑，或方法新颖且验证充分
  - Useful baseline: 扎实但不改变你对问题的思考方式
  - Interesting idea but weak proof: 思路好但证据不足（实验少/缺对比/未解释的问题）
  - Not very relevant: 边际贡献或离读者兴趣太远
-->

> [!success] Verdict
> Worth reading deeply | Useful baseline | Interesting idea but weak proof | Not very relevant

一句话理由:

## 15. Implementation Notes（可选，打算复现时再填）

- **Backbone / framework**: 
- **Key hyperparameters**: 
- **Training tricks**: 
- **Data preprocessing**: 
- **Code quality**: 
- **Reproduction difficulty**: easy | medium | hard
- **坑 / 不公平的对比**: 

## 16. 摘录（原文片段，严格区分于上面所有判断）

> "..."  — p.{{x}}

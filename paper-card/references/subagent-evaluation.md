# Subagent 2: Evaluation Extractor

Extract evaluative, judgmental content from a research paper. Output structured JSON.

## Task

Read the full paper markdown and extract the following evaluative structure. Focus on claims, evidence quality, limitations, and your assessment of the work's merit.

## Output Schema

Return a single JSON object:

```json
{
  "claim_verification": {
    "main_claim": "作者最核心的主张 (不是方法，是主张)",
    "evidence": "作者用什么来支撑",
    "evidence_sufficiency": "yes | partially | no",
    "evidence_reason": "一句话理由",
    "proven": ["真正证明了什么"],
    "not_proven": ["没有证明 / 回避了什么"]
  },
  "why_it_should_work": {
    "logic_chain": "Because ..., the model can ..., which improves ...",
    "convincing": "最有说服力的部分",
    "weak": "薄弱/可疑的部分"
  },
  "limitations": {
    "author_admitted": ["作者自己承认的局限"],
    "inferred": ["实验缺哪类", "假设何时崩", "scale 是否敏感"]
  },
  "ratings": {
    "novelty": {
      "score": 1-5,
      "reason": "一句话理由"
    },
    "soundness": {
      "score": 1-5,
      "reason": "一句话理由"
    },
    "reproducibility": {
      "score": 1-5,
      "reason": "一句话理由"
    }
  },
  "takeaway": {
    "can_borrow": ["能直接搬的: idea / 实验设计 / baseline / 数据集 / 代码"],
    "follow_up_experiments": ["想追问的实验"],
    "if_i_do": ["如果我来做，会怎么改"],
    "extension_ideas": ["可能延伸出的 research idea"]
  },
  "verdict": {
    "category": "Worth reading deeply | Useful baseline | Interesting idea but weak proof | Not very relevant",
    "reason": "一句话理由"
  },
  "open_questions": ["值得跟进的问题"],
  "implementation_notes": {
    "backbone": "使用的框架/骨干",
    "key_hyperparams": ["关键超参数"],
    "tricks": ["训练技巧"],
    "reproduction_difficulty": "easy | medium | hard"
  }
}
```

## Rules

1. **Be specific**: Don't say "the method is novel" — say what makes it novel relative to what
2. **Evidence-based judgments**: Every rating should reference specific evidence from the paper
3. **Limitations**: Distinguish between what the author admits and what you infer from the experiments
4. **Ratings scale**:
   - 1: Below average / weak
   - 2: Acceptable but not impressive
   - 3: Solid, meets expectations
   - 4: Strong, above average
   - 5: Exceptional, field-defining
5. **Verdict**: Choose exactly one category, don't hedge

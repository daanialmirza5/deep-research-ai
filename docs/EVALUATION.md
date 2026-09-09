# Deep-Research-AI — Evaluation & Benchmark Harness

This document outlines the reproducible quantitative evaluation methodology used to measure agentic research quality, retrieval relevance, citation correctness, and hallucination reduction.

---

## 1. Motivation

Agentic research systems must be evaluated on empirical rigor rather than subjective reading. The evaluation harness in `ai/evaluation/` provides deterministic, zero-cost offline benchmarking across five core metrics:

1. **Citation Precision**: Proportion of inline markers (`[1]`, `[2]`) in the draft that resolve to valid, existing URLs in the ground-truth metadata.
2. **Citation Recall**: Fraction of retrieved evidence documents that are actually cited in the synthesized report.
3. **Retrieval Relevance**: Proportion of retrieved knowledge chunks containing domain target keywords.
4. **Hallucination Rate**: Proportion of key fact assertions contradicted or ungrounded against source findings.
5. **Task Completion**: Complete lifecycle synthesis across Planning, Retrieval, Fact-Checking, Citation Resolution, and Quality Scoring.

---

## 2. Benchmark Dataset

Located in `ai/evaluation/benchmark_dataset.py`, the dataset spans technical domains:
- **`bench-01`**: Distributed Consensus & Leader Election in Raft (`Distributed Systems`)
- **`bench-02`**: Physics-Informed Neural Networks & PDE Loss Formulation (`Scientific ML`)
- **`bench-03`**: Hybrid Sparse-Dense Retrieval & Reciprocal Rank Fusion (`Information Retrieval / NLP`)

---

## 3. Running the Benchmark

Execute the evaluation harness directly via Python:

```bash
python -m unittest ai/tests/test_evaluation_harness.py
```

Or run programmatic evaluations inside custom scripts:

```python
from ai.evaluation import EvaluationHarness, generate_evaluation_markdown_report

harness = EvaluationHarness()
results = harness.run_all()
report = generate_evaluation_markdown_report(results)
print(report)
```

"""Evaluation package for deep-research-ai."""
from ai.evaluation.benchmark_dataset import BENCHMARK_DATASET, BenchmarkItem
from ai.evaluation.harness import BenchmarkResult, EvaluationHarness, generate_evaluation_markdown_report
from ai.evaluation.metrics import (
    calculate_citation_precision,
    calculate_citation_recall,
    calculate_hallucination_rate,
    calculate_retrieval_relevance,
    calculate_task_completion,
    extract_inline_citation_indices,
)

__all__ = [
    "BENCHMARK_DATASET",
    "BenchmarkItem",
    "BenchmarkResult",
    "EvaluationHarness",
    "calculate_citation_precision",
    "calculate_citation_recall",
    "calculate_hallucination_rate",
    "calculate_retrieval_relevance",
    "calculate_task_completion",
    "extract_inline_citation_indices",
    "generate_evaluation_markdown_report",
]

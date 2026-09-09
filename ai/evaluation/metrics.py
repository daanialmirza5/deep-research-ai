"""Quantitative evaluation metrics for agentic research pipelines.

Provides reproducible measurement functions for citation precision, citation recall,
retrieval relevance, claim verification / hallucination rates, and task completion.
"""
from __future__ import annotations

import re
from typing import Any


_CITATION_PATTERN = re.compile(r"\[(\d+)\]")


def extract_inline_citation_indices(text: str) -> list[int]:
    """Extracts all [1], [2], etc. citation markers from a generated draft."""
    if not text:
        return []
    matches = _CITATION_PATTERN.findall(text)
    return [int(m) for m in matches]


def calculate_citation_precision(
    draft_report: str,
    citations: list[dict[str, Any]],
    valid_source_urls: list[str] | set[str] | None = None,
) -> float:
    """Calculates the proportion of inline citation markers in the text that resolve
    to valid, non-empty, existing citation references in the metadata.
    
    If valid_source_urls is supplied, also verifies that the citation URL is a verified source.
    """
    indices = extract_inline_citation_indices(draft_report)
    if not indices:
        return 0.0

    valid_url_set = set(valid_source_urls) if valid_source_urls else None
    valid_count = 0

    for idx in indices:
        # 1-indexed citation markers mapping to 0-indexed citations list
        list_idx = idx - 1
        if 0 <= list_idx < len(citations):
            cite = citations[list_idx]
            url = cite.get("url") or ""
            if url:
                if valid_url_set is None or url in valid_url_set:
                    valid_count += 1

    return round(valid_count / len(indices), 4)


def calculate_citation_recall(
    draft_report: str,
    total_findings_count: int,
) -> float:
    """Calculates what fraction of retrieved research findings were cited in the report."""
    if total_findings_count <= 0:
        return 0.0

    unique_indices = set(extract_inline_citation_indices(draft_report))
    # Count how many unique finding indices between 1 and total_findings_count were cited
    cited_count = len([i for i in unique_indices if 1 <= i <= total_findings_count])
    return round(cited_count / total_findings_count, 4)


def calculate_retrieval_relevance(
    retrieved_chunks: list[dict[str, Any]],
    query_keywords: list[str],
) -> float:
    """Calculates the proportion of retrieved chunks containing at least one target keyword."""
    if not retrieved_chunks:
        return 0.0

    relevant_count = 0
    keywords_lower = [k.lower() for k in query_keywords if k]
    if not keywords_lower:
        return 1.0

    for chunk in retrieved_chunks:
        text = (chunk.get("chunk_text") or chunk.get("snippet") or "").lower()
        if any(k in text for k in keywords_lower):
            relevant_count += 1

    return round(relevant_count / len(retrieved_chunks), 4)


def calculate_hallucination_rate(
    fact_check_issues: list[dict[str, Any]] | list[str],
    total_claims_count: int,
) -> float:
    """Calculates the percentage of claims that were flagged as ungrounded or contradicted."""
    if total_claims_count <= 0:
        return 0.0

    issue_count = len(fact_check_issues)
    return round(min(1.0, issue_count / total_claims_count), 4)


def calculate_task_completion(state: dict[str, Any]) -> dict[str, Any]:
    """Evaluates whether all expected artifacts were synthesized in the state machine."""
    required_stages = [
        ("plan", bool(state.get("plan"))),
        ("research_findings", len(state.get("research_findings", [])) > 0),
        ("draft_report", bool(state.get("draft_report"))),
        ("citations", len(state.get("citations", [])) > 0),
        ("quality_score", state.get("quality_score") is not None),
    ]

    completed_stages = [name for name, ok in required_stages if ok]
    score = round(len(completed_stages) / len(required_stages), 4)

    return {
        "completion_rate": score,
        "is_complete": score == 1.0,
        "completed_stages": completed_stages,
        "missing_stages": [name for name, ok in required_stages if not ok],
    }

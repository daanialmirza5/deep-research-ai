"""Curated benchmark evaluation dataset for agentic research pipelines.

Contains diverse domain topics with expected keywords, reference source URLs,
and key fact assertions for testing retrieval relevance and citation precision.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BenchmarkItem:
    query_id: str
    query: str
    category: str
    target_keywords: list[str]
    reference_urls: list[str]
    key_assertions: list[str]
    mock_findings: list[dict[str, str]] = field(default_factory=list)


BENCHMARK_DATASET: list[BenchmarkItem] = [
    BenchmarkItem(
        query_id="bench-01",
        query="What are the core consensus phases and leader election rules in the Raft protocol?",
        category="Distributed Systems",
        target_keywords=["raft", "consensus", "leader election", "log replication", "heartbeat", "term"],
        reference_urls=[
            "https://raft.github.io/raft.pdf",
            "https://en.wikipedia.org/wiki/Raft_(algorithm)",
        ],
        key_assertions=[
            "Raft uses randomized election timeouts to prevent split votes.",
            "Log entries only flow in one direction from the leader to followers.",
        ],
        mock_findings=[
            {
                "source": "arxiv",
                "title": "In Search of an Understandable Consensus Algorithm",
                "url": "https://raft.github.io/raft.pdf",
                "snippet": "Raft is a consensus algorithm designed for understandability. It separates key elements like leader election, log replication, and safety.",
            },
            {
                "source": "wikipedia",
                "title": "Raft consensus",
                "url": "https://en.wikipedia.org/wiki/Raft_(algorithm)",
                "snippet": "Leader election in Raft begins when a follower transitions to candidate state after an election timeout.",
            },
        ],
    ),
    BenchmarkItem(
        query_id="bench-02",
        query="How do Physics-Informed Neural Networks (PINNs) incorporate partial differential equations into loss functions?",
        category="Scientific ML",
        target_keywords=["pinn", "physics-informed", "loss function", "residual", "automatic differentiation", "navier-stokes"],
        reference_urls=[
            "https://arxiv.org/abs/1711.10561",
            "https://en.wikipedia.org/wiki/Physics-informed_neural_networks",
        ],
        key_assertions=[
            "PINNs compute PDE residuals using automatic differentiation.",
            "The composite loss combines boundary/initial conditions with the physics residual.",
        ],
        mock_findings=[
            {
                "source": "arxiv",
                "title": "Physics-informed neural networks: A deep learning framework",
                "url": "https://arxiv.org/abs/1711.10561",
                "snippet": "PINNs integrate physics laws described by nonlinear PDEs into the loss function via automatic differentiation.",
            },
        ],
    ),
    BenchmarkItem(
        query_id="bench-03",
        query="Explain hybrid sparse-dense retrieval fusion in modern RAG systems.",
        category="Information Retrieval / NLP",
        target_keywords=["hybrid search", "sparse", "dense", "bm25", "reciprocal rank fusion", "cross-encoder"],
        reference_urls=[
            "https://arxiv.org/abs/0905.2810",
            "https://qdrant.tech/articles/hybrid-search/",
        ],
        key_assertions=[
            "Reciprocal Rank Fusion (RRF) combines ranked lists without requiring score normalization.",
            "Cross-encoders perform fine-grained joint query-document attention.",
        ],
        mock_findings=[
            {
                "source": "web",
                "title": "Hybrid Search Explained",
                "url": "https://qdrant.tech/articles/hybrid-search/",
                "snippet": "Hybrid search combines dense vector similarity with sparse BM25 keyword matching using Reciprocal Rank Fusion.",
            },
        ],
    ),
]

"""Unit tests for the deep-research-ai evaluation harness and metrics.

Compatible with both standard library unittest and pytest.
"""
import unittest

from ai.evaluation import (
    BENCHMARK_DATASET,
    EvaluationHarness,
    calculate_citation_precision,
    calculate_citation_recall,
    calculate_hallucination_rate,
    calculate_retrieval_relevance,
    calculate_task_completion,
    extract_inline_citation_indices,
    generate_evaluation_markdown_report,
)


class TestEvaluationHarness(unittest.TestCase):
    def test_extract_inline_citations(self):
        text = "Raft uses randomized election timeouts [1] and log replication [2]. [1] is key."
        indices = extract_inline_citation_indices(text)
        self.assertEqual(indices, [1, 2, 1])

    def test_citation_precision_calculation(self):
        draft = "According to [1] and [2], the system is fast. [3] is also cited."
        citations = [
            {"title": "Paper 1", "url": "https://example.com/1"},
            {"title": "Paper 2", "url": "https://example.com/2"},
        ]
        # [1] and [2] are valid; [3] is out of bounds
        score = calculate_citation_precision(draft, citations)
        self.assertAlmostEqual(score, 0.6667, places=3)

    def test_citation_precision_with_ground_truth_urls(self):
        draft = "Statement with reference [1]."
        citations = [{"title": "Phishing Source", "url": "https://unverified.com"}]
        verified_urls = ["https://arxiv.org/123", "https://official.org"]
        
        score = calculate_citation_precision(draft, citations, valid_source_urls=verified_urls)
        self.assertEqual(score, 0.0)

    def test_citation_recall_calculation(self):
        draft = "Summary mentions [1] and [3]."
        score = calculate_citation_recall(draft, total_findings_count=4)
        # Cited 2 out of 4 total findings
        self.assertEqual(score, 0.5)

    def test_retrieval_relevance_calculation(self):
        chunks = [
            {"chunk_text": "Distributed consensus using the Raft algorithm."},
            {"chunk_text": "Generic unrelated text about cooking."},
            {"chunk_text": "Leader election heartbeat mechanism in distributed nodes."},
        ]
        keywords = ["raft", "consensus", "leader election"]
        relevance = calculate_retrieval_relevance(chunks, keywords)
        # 2 out of 3 chunks match
        self.assertAlmostEqual(relevance, 0.6667, places=3)

    def test_hallucination_rate_calculation(self):
        self.assertEqual(calculate_hallucination_rate([], total_claims_count=5), 0.0)
        issues = [{"claim": "Fabricated fact", "issue": "No ground truth support"}]
        self.assertEqual(calculate_hallucination_rate(issues, total_claims_count=4), 0.25)

    def test_task_completion_evaluation(self):
        complete_state = {
            "plan": "1. Search\n2. Synthesize",
            "research_findings": [{"source": "web", "title": "A", "url": "https://a.com"}],
            "draft_report": "Full draft report text",
            "citations": [{"source_type": "web", "title": "A", "url": "https://a.com"}],
            "quality_score": 0.95,
        }
        res = calculate_task_completion(complete_state)
        self.assertTrue(res["is_complete"])
        self.assertEqual(res["completion_rate"], 1.0)

    def test_evaluation_harness_end_to_end(self):
        harness = EvaluationHarness()
        results = harness.run_all()
        
        self.assertEqual(len(results), len(BENCHMARK_DATASET))
        for r in results:
            self.assertGreaterEqual(r.retrieval_relevance, 0.0)
            self.assertGreaterEqual(r.citation_precision, 0.0)
            self.assertEqual(r.completion_rate, 1.0)
            self.assertGreaterEqual(r.duration_ms, 0.0)

        report = generate_evaluation_markdown_report(results)
        self.assertIn("Quantitative Evaluation Benchmark", report)
        self.assertIn("bench-01", report)
        self.assertIn("bench-02", report)
        self.assertIn("bench-03", report)


if __name__ == "__main__":
    unittest.main()

"""Unit tests verifying comparative agent evaluation experiments."""

import unittest
from ai.evaluation.benchmark_dataset import BENCHMARK_DATASET
from ai.evaluation.harness import EvaluationHarness, AgentVariant


class TestComparativeExperiment(unittest.TestCase):
    """Verifies baseline vs improved agent comparison metrics and invariant properties."""

    def setUp(self):
        self.harness = EvaluationHarness()

    def test_comparative_experiment_execution(self):
        summary = self.harness.run_comparative_experiment()

        self.assertGreater(len(summary.results), 0)
        # Improved agent must outperform naive baseline on core grounding dimensions
        self.assertGreaterEqual(summary.improved_avg_precision, summary.baseline_avg_precision)
        self.assertGreaterEqual(summary.improved_avg_recall, summary.baseline_avg_recall)
        self.assertGreaterEqual(summary.improved_avg_relevance, summary.baseline_avg_relevance)
        self.assertGreaterEqual(summary.improved_avg_completion, summary.baseline_avg_completion)
        self.assertLessEqual(summary.improved_avg_hallucination, summary.baseline_avg_hallucination)

    def test_agent_variant_results_structure(self):
        results = self.harness.run_all()
        self.assertEqual(len(results), len(BENCHMARK_DATASET))
        for r in results:
            self.assertEqual(r.variant, AgentVariant.IMPROVED_DEEP_RESEARCH)
            self.assertGreater(r.retrieval_relevance, 0.5)
            self.assertEqual(r.completion_rate, 1.0)


if __name__ == "__main__":
    unittest.main()

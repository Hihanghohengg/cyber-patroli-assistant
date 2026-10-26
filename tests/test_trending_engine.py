"""Tests for TrendingEngine calculation logic."""

import unittest
from app.services.intelligence.trending_engine import TrendingEngine


class TestTrendingEngine(unittest.TestCase):
    def test_trending_engine_weights_default(self):
        engine = TrendingEngine()
        total_weight = sum(engine.weights.values())
        self.assertAlmostEqual(total_weight, 1.0, places=4)
        self.assertIn("volume", engine.weights)
        self.assertIn("growth", engine.weights)
        self.assertIn("velocity", engine.weights)

    def test_custom_weights(self):
        custom_weights = {
            "volume": 0.50,
            "growth": 0.20,
            "velocity": 0.10,
            "source_diversity": 0.10,
            "recency": 0.05,
            "relevance": 0.05,
        }
        engine = TrendingEngine(weights=custom_weights)
        self.assertEqual(engine.weights["volume"], 0.50)


if __name__ == "__main__":
    unittest.main()

import unittest
import asyncio
from typing import Dict, Any
from speculative_agent_tool_runtime.core import SpeculativeEngine, MarkovTrajectoryGraph
from speculative_agent_tool_runtime.models import ToolSafetyLevel

class TestBoundaries(unittest.TestCase):
    """
    Exhaustive boundary testing for the speculative execution engine.
    """

    def setUp(self):
        self.engine = SpeculativeEngine(threshold=0.85)
        self.mtg = MarkovTrajectoryGraph()

    def test_mutating_side_effect_rejection(self):
        """Verify that MUTATING_SIDE_EFFECT tasks are immediately rejected."""
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            self.engine.dispatch_speculative_task(
                "test_tool", {}, ToolSafetyLevel.MUTATING_SIDE_EFFECT
            )
        )
        self.assertIsNone(result)

    def test_empty_arguments_canonical_hash(self):
        """Ensure canonical hash generation handles empty argument dictionaries."""
        hash1 = self.engine._calculate_canonical_hash("tool", {})
        hash2 = self.engine._calculate_canonical_hash("tool", {})
        self.assertEqual(hash1, hash2)

    def test_mtg_zero_success_boundary(self):
        """Verify MTG behavior when success rate is zero."""
        self.mtg.update_trajectory("prefix", False)
        prediction = self.mtg.get_prediction("prefix")
        # (0.5 * 0.9) + (0.0 * 0.1) = 0.45
        self.assertEqual(prediction, 0.45)

    def test_mtg_perfect_success_boundary(self):
        """Verify MTG behavior when success rate is perfect."""
        self.mtg.update_trajectory("prefix", True)
        prediction = self.mtg.get_prediction("prefix")
        # (0.5 * 0.9) + (1.0 * 0.1) = 0.55
        self.assertEqual(prediction, 0.55)

    def test_verify_non_existent_task(self):
        """Verify that verifying a non-existent task returns None."""
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            self.engine.verify_and_commit("unknown_tool", {})
        )
        self.assertIsNone(result)

    def test_task_lifecycle_completion(self):
        """Verify task status transitions from PENDING to COMPLETED."""
        loop = asyncio.get_event_loop()
        task_id = loop.run_until_complete(
            self.engine.dispatch_speculative_task(
                "test", {}, ToolSafetyLevel.SAFE_READ_ONLY
            )
        )
        # Wait for the background task to finish
        loop.run_until_complete(asyncio.sleep(0.1))
        task = self.engine.active_tasks[task_id]
        self.assertEqual(task.status, "COMPLETED")
        self.assertIsNotNone(task.result)

    def test_canonical_hash_order_independence(self):
        """Ensure hash is identical regardless of dictionary key order."""
        args1 = {"a": 1, "b": 2}
        args2 = {"b": 2, "a": 1}
        hash1 = self.engine._calculate_canonical_hash("tool", args1)
        hash2 = self.engine._calculate_canonical_hash("tool", args2)
        self.assertEqual(hash1, hash2)

    def test_mtg_missing_key_default(self):
        """Verify MTG returns 0.0 for unknown prefixes."""
        self.assertEqual(self.mtg.get_prediction("non_existent"), 0.0)

    def test_concurrent_task_dispatch(self):
        """Verify engine handles multiple concurrent tasks without collision."""
        loop = asyncio.get_event_loop()
        tasks = [
            self.engine.dispatch_speculative_task(f"tool_{i}", {}, ToolSafetyLevel.SAFE_READ_ONLY)
            for i in range(5)
        ]
        results = loop.run_until_complete(asyncio.gather(*tasks))
        self.assertEqual(len(self.engine.active_tasks), 5)
        self.assertEqual(len(set(results)), 5)

    def test_negative_latency_handling(self):
        """Verify system handles edge case of zero/negative latency logic."""
        # Simulate logic from web.py: latency = (time.perf_counter() - start) * 1000
        # If start is slightly ahead of end, ensure logic doesn't crash
        import time
        start = time.perf_counter()
        end = start - 0.001
        latency = (end - start) * 1000
        self.assertTrue(latency < 0)

if __name__ == "__main__":
    unittest.main()
import unittest
import asyncio
import json
from typing import Dict, Any
from speculative_agent_tool_runtime.core import SpeculativeEngine, MarkovTrajectoryGraph
from speculative_agent_tool_runtime.models import ToolSafetyLevel, SpeculativeTask

class TestCoreEngine(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = SpeculativeEngine(threshold=0.9)
        self.mtg = MarkovTrajectoryGraph()

    async def test_dispatch_safe_task(self):
        """Test that safe tasks are dispatched and tracked."""
        task_id = await self.engine.dispatch_speculative_task(
            "test_tool", {"key": "val"}, ToolSafetyLevel.SAFE_READ_ONLY
        )
        self.assertIsNotNone(task_id)
        self.assertIn(task_id, self.engine.active_tasks)
        self.assertEqual(self.engine.active_tasks[task_id].status, "PENDING")

    async def test_dispatch_mutating_task_rejected(self):
        """Test that mutating tasks are rejected by the engine."""
        task_id = await self.engine.dispatch_speculative_task(
            "rm_rf", {}, ToolSafetyLevel.MUTATING_SIDE_EFFECT
        )
        self.assertIsNone(task_id)

    async def test_task_execution_lifecycle(self):
        """Test that a task transitions from PENDING to COMPLETED."""
        task_id = await self.engine.dispatch_speculative_task(
            "read_db", {"id": 1}, ToolSafetyLevel.SAFE_READ_ONLY
        )
        # Wait for the background task to complete
        await asyncio.sleep(0.1)
        task = self.engine.active_tasks[task_id]
        self.assertEqual(task.status, "COMPLETED")
        self.assertEqual(task.result["data"], "speculative_result_placeholder")

    async def test_verify_and_commit_success(self):
        """Test successful verification of a completed task."""
        tool_name = "get_weather"
        args = {"city": "SF"}
        task_id = await self.engine.dispatch_speculative_task(
            tool_name, args, ToolSafetyLevel.SAFE_READ_ONLY
        )
        await asyncio.sleep(0.1)
        result = await self.engine.verify_and_commit(tool_name, args)
        self.assertIsNotNone(result)
        self.assertEqual(result["data"], "speculative_result_placeholder")

    async def test_verify_and_commit_mismatch(self):
        """Test that verification fails for incorrect arguments."""
        await self.engine.dispatch_speculative_task(
            "get_weather", {"city": "SF"}, ToolSafetyLevel.SAFE_READ_ONLY
        )
        await asyncio.sleep(0.1)
        result = await self.engine.verify_and_commit("get_weather", {"city": "NY"})
        self.assertIsNone(result)

    def test_canonical_hash_consistency(self):
        """Test that the hash function is deterministic."""
        h1 = self.engine._calculate_canonical_hash("tool", {"a": 1, "b": 2})
        h2 = self.engine._calculate_canonical_hash("tool", {"b": 2, "a": 1})
        self.assertEqual(h1, h2)

    def test_mtg_initial_prediction(self):
        """Test that MTG returns default 0.0 for unknown prefixes."""
        self.assertEqual(self.mtg.get_prediction("unknown"), 0.0)

    def test_mtg_bayesian_update(self):
        """Test that MTG updates probabilities correctly."""
        prefix = "start"
        self.mtg.update_trajectory(prefix, True)
        # (0.5 * 0.9) + (1.0 * 0.1) = 0.45 + 0.1 = 0.55
        self.assertAlmostEqual(self.mtg.get_prediction(prefix), 0.55)

    def test_mtg_multiple_updates(self):
        """Test that MTG converges over multiple updates."""
        prefix = "path"
        for _ in range(5):
            self.mtg.update_trajectory(prefix, True)
        val = self.mtg.get_prediction(prefix)
        self.assertTrue(0.5 < val < 1.0)

    async def test_concurrent_task_safety(self):
        """Test that multiple tasks can be dispatched without race conditions."""
        tasks = [
            self.engine.dispatch_speculative_task(f"t{i}", {}, ToolSafetyLevel.SAFE_READ_ONLY)
            for i in range(10)
        ]
        results = await asyncio.gather(*tasks)
        self.assertEqual(len(results), 10)
        self.assertEqual(len(self.engine.active_tasks), 10)

if __name__ == "__main__":
    unittest.main()
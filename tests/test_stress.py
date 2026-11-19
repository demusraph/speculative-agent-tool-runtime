import unittest
import asyncio
import time
import json
from typing import List
from fastapi.testclient import TestClient
from speculative_agent_tool_runtime.core import SpeculativeEngine, MarkovTrajectoryGraph
from speculative_agent_tool_runtime.models import ToolSafetyLevel
from speculative_agent_tool_runtime.web import app

class TestSpeculativeStress(unittest.TestCase):
    """
    High-performance stress tests for the Speculative Agent Tool Runtime.
    """

    def setUp(self):
        self.engine = SpeculativeEngine(threshold=0.85)
        self.client = TestClient(app)

    def test_engine_concurrency_throughput(self):
        """Test high-volume concurrent task dispatching."""
        async def run_stress():
            tasks = [
                self.engine.dispatch_speculative_task(
                    f"tool_{i}", {"arg": i}, ToolSafetyLevel.SAFE_READ_ONLY
                ) for i in range(100)
            ]
            return await asyncio.gather(*tasks)

        results = asyncio.run(run_stress())
        self.assertEqual(len(results), 100)
        self.assertTrue(all(isinstance(r, str) for r in results))
        self.assertEqual(len(self.engine.active_tasks), 100)

    def test_markov_graph_convergence(self):
        """Test trajectory prediction stability under load."""
        mtg = MarkovTrajectoryGraph()
        # Simulate 1000 updates
        for i in range(1000):
            mtg.update_trajectory("path_a", success=(i % 2 == 0))
        
        prediction = mtg.get_prediction("path_a")
        self.assertGreaterEqual(prediction, 0.0)
        self.assertLessEqual(prediction, 1.0)

    def test_api_endpoint_load(self):
        """Test FastAPI endpoint responsiveness under rapid requests."""
        payloads = [
            {"tool_name": f"test_tool_{i}", "input_args": {"val": i}, "status": "success"}
            for i in range(50)
        ]
        
        for p in payloads:
            response = self.client.post("/api/execute", json=p)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "ok")

    def test_speculative_verification_integrity(self):
        """Test verification logic against completed tasks."""
        async def verify_flow():
            tool_name = "db_query"
            args = {"query": "SELECT * FROM users"}
            
            task_id = await self.engine.dispatch_speculative_task(
                tool_name, args, ToolSafetyLevel.SAFE_READ_ONLY
            )
            
            # Wait for background task to complete
            await asyncio.sleep(0.2)
            
            result = await self.engine.verify_and_commit(tool_name, args)
            self.assertIsNotNone(result)
            self.assertEqual(result["data"], "speculative_result_placeholder")

        asyncio.run(verify_flow())

    def test_safety_constraint_enforcement(self):
        """Ensure MUTATING_SIDE_EFFECT tasks are rejected immediately."""
        async def check_safety():
            task_id = await self.engine.dispatch_speculative_task(
                "delete_all", {}, ToolSafetyLevel.MUTATING_SIDE_EFFECT
            )
            self.assertIsNone(task_id)
            self.assertEqual(len(self.engine.active_tasks), 0)

        asyncio.run(check_safety())

if __name__ == "__main__":
    unittest.main()
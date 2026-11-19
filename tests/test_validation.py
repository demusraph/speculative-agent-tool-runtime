import unittest
import uuid
from pydantic import ValidationError
from speculative_agent_tool_runtime.models import SpeculativeTask, ToolSafetyLevel, TrajectoryNode
from speculative_agent_tool_runtime.core import SpeculativeEngine, MarkovTrajectoryGraph

class TestValidation(unittest.TestCase):
    """Exhaustive validation suite for speculative-agent-tool-runtime."""

    def test_speculative_task_valid_creation(self):
        """Test successful instantiation of SpeculativeTask with valid data."""
        task = SpeculativeTask(
            tool_name="search_engine",
            arguments={"query": "AI trends"},
            safety_level=ToolSafetyLevel.SAFE_READ_ONLY
        )
        self.assertIsInstance(task.task_id, str)
        self.assertEqual(task.tool_name, "search_engine")
        self.assertEqual(task.status, "PENDING")

    def test_speculative_task_invalid_safety_level(self):
        """Test Pydantic validation error for invalid safety level enum."""
        with self.assertRaises(ValidationError):
            SpeculativeTask(
                tool_name="test",
                arguments={},
                safety_level="INVALID_LEVEL"
            )

    def test_speculative_task_invalid_status(self):
        """Test Pydantic validation error for invalid status literal."""
        with self.assertRaises(ValidationError):
            SpeculativeTask(
                tool_name="test",
                arguments={},
                safety_level=ToolSafetyLevel.SAFE_READ_ONLY,
                status="INVALID_STATUS"
            )

    def test_trajectory_node_type_enforcement(self):
        """Test TrajectoryNode type enforcement for confidence field."""
        node = TrajectoryNode(prefix="test", predicted_tool="tool", confidence=0.95)
        self.assertEqual(node.confidence, 0.95)
        with self.assertRaises(ValidationError):
            TrajectoryNode(prefix="test", predicted_tool="tool", confidence="not_a_float")

    def test_engine_canonical_hash_consistency(self):
        """Test that canonical hash generation is deterministic."""
        engine = SpeculativeEngine()
        hash1 = engine._calculate_canonical_hash("tool", {"a": 1, "b": 2})
        hash2 = engine._calculate_canonical_hash("tool", {"b": 2, "a": 1})
        self.assertEqual(hash1, hash2)

    def test_engine_safety_constraint_blocking(self):
        """Test that MUTATING_SIDE_EFFECT tasks are rejected by the engine."""
        import asyncio
        engine = SpeculativeEngine()
        
        async def run_check():
            result = await engine.dispatch_speculative_task(
                "delete_all", {}, ToolSafetyLevel.MUTATING_SIDE_EFFECT
            )
            self.assertIsNone(result)
            
        asyncio.run(run_check())

    def test_markov_graph_bounds(self):
        """Test MarkovTrajectoryGraph prediction bounds."""
        mtg = MarkovTrajectoryGraph()
        # Initial state should be 0.0 if not present
        self.assertEqual(mtg.get_prediction("unknown"), 0.0)
        
        mtg.update_trajectory("test", True)
        val = mtg.get_prediction("test")
        self.assertTrue(0.0 <= val <= 1.0)

    def test_task_id_uniqueness(self):
        """Test that tasks receive unique UUIDs by default."""
        task1 = SpeculativeTask(tool_name="t1", arguments={}, safety_level=ToolSafetyLevel.SAFE_READ_ONLY)
        task2 = SpeculativeTask(tool_name="t2", arguments={}, safety_level=ToolSafetyLevel.SAFE_READ_ONLY)
        self.assertNotEqual(task1.task_id, task2.task_id)

    def test_missing_required_fields(self):
        """Test Pydantic validation for missing required fields."""
        with self.assertRaises(ValidationError):
            # Missing tool_name and arguments
            SpeculativeTask(safety_level=ToolSafetyLevel.SAFE_READ_ONLY)

    def test_engine_task_lifecycle_state(self):
        """Test that engine correctly transitions task status."""
        import asyncio
        engine = SpeculativeEngine()
        task = SpeculativeTask(
            tool_name="test", 
            arguments={}, 
            safety_level=ToolSafetyLevel.SAFE_READ_ONLY
        )
        
        async def run_lifecycle():
            await engine._execute_task(task)
            self.assertEqual(task.status, "COMPLETED")
            self.assertIsNotNone(task.result)
            
        asyncio.run(run_lifecycle())

if __name__ == "__main__":
    unittest.main()
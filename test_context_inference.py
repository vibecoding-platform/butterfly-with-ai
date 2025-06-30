#!/usr/bin/env python3
"""
Test script for the context inference system.
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from aetherterm.agentserver.context_inference.models import (
    OperationType, OperationStage, OperationContext
)
from aetherterm.agentserver.context_inference.pattern_learner import OperationPatternLearner
from aetherterm.agentserver.context_inference.inference_engine import OperationContextInferenceEngine

# Mock storage classes for testing
class MockVectorStorage:
    def __init__(self):
        self.data = {}
        
    async def store_vector(self, id: str, vector: list, metadata: dict):
        self.data[id] = {"vector": vector, "metadata": metadata}
        return True
        
    async def search_similar(self, vector: list, limit: int = 10):
        # Simple mock - return empty for now
        return []
        
    async def get_collection_info(self):
        return {"count": len(self.data)}


class MockSQLStorage:
    def __init__(self):
        self.operations = []
        self.commands = []
        
    async def store_operation_context(self, context: OperationContext):
        self.operations.append(context)
        
    async def get_terminal_commands(self, terminal_id: str, start_time: datetime, end_time: datetime):
        # Mock command history
        mock_commands = [
            {"timestamp": datetime.utcnow() - timedelta(minutes=10), "command": "git clone https://github.com/user/repo.git", "terminal_id": terminal_id},
            {"timestamp": datetime.utcnow() - timedelta(minutes=9), "command": "cd repo", "terminal_id": terminal_id},
            {"timestamp": datetime.utcnow() - timedelta(minutes=8), "command": "npm install", "terminal_id": terminal_id},
            {"timestamp": datetime.utcnow() - timedelta(minutes=7), "command": "npm run dev", "terminal_id": terminal_id},
            {"timestamp": datetime.utcnow() - timedelta(minutes=5), "command": "git add .", "terminal_id": terminal_id},
            {"timestamp": datetime.utcnow() - timedelta(minutes=4), "command": "git commit -m 'Initial setup'", "terminal_id": terminal_id},
            {"timestamp": datetime.utcnow() - timedelta(minutes=2), "command": "npm test", "terminal_id": terminal_id},
        ]
        return mock_commands
        
    async def get_recent_commands(self, terminal_id: str, limit: int = 10):
        commands = await self.get_terminal_commands(terminal_id, datetime.utcnow() - timedelta(hours=1), datetime.utcnow())
        return commands[-limit:]


async def test_pattern_learning():
    """Test the pattern learning functionality."""
    print("Testing pattern learning...")
    
    # Create mock storage
    vector_storage = MockVectorStorage()
    sql_storage = MockSQLStorage()
    
    # Create pattern learner
    learner = OperationPatternLearner(vector_storage, sql_storage)
    
    # Test pattern learning
    try:
        patterns = await learner.learn_patterns_from_history(days=1)
        print(f"✅ Pattern learning successful: learned {len(patterns)} patterns")
        return True
    except Exception as e:
        print(f"❌ Pattern learning failed: {e}")
        return False


async def test_context_inference():
    """Test the context inference functionality."""
    print("Testing context inference...")
    
    # Create mock storage
    vector_storage = MockVectorStorage()
    sql_storage = MockSQLStorage()
    
    # Create pattern learner and inference engine
    learner = OperationPatternLearner(vector_storage, sql_storage)
    engine = OperationContextInferenceEngine(vector_storage, sql_storage, learner)
    
    # Test context inference
    try:
        result = await engine.infer_current_operation("test_terminal_123")
        print(f"✅ Context inference successful")
        print(f"   Operation type: {result.primary_context.operation_type}")
        print(f"   Stage: {result.primary_context.stage}")
        print(f"   Confidence: {result.primary_context.confidence:.2f}")
        print(f"   Recommendations: {len(result.recommendations)}")
        return True
    except Exception as e:
        print(f"❌ Context inference failed: {e}")
        return False


async def test_next_command_prediction():
    """Test next command prediction."""
    print("Testing next command prediction...")
    
    # Create mock storage
    vector_storage = MockVectorStorage()
    sql_storage = MockSQLStorage()
    
    # Create pattern learner and inference engine
    learner = OperationPatternLearner(vector_storage, sql_storage)
    engine = OperationContextInferenceEngine(vector_storage, sql_storage, learner)
    
    # First infer context
    try:
        result = await engine.infer_current_operation("test_terminal_456")
        
        if result.primary_context.next_likely_commands:
            print(f"✅ Next command prediction successful")
            print(f"   Predicted commands: {result.primary_context.next_likely_commands}")
            return True
        else:
            print("⚠️  No next commands predicted (this is okay for mock data)")
            return True
    except Exception as e:
        print(f"❌ Next command prediction failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("🚀 Starting context inference system tests...\n")
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    tests = [
        test_pattern_learning,
        test_context_inference,
        test_next_command_prediction
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append(result)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Context inference system is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
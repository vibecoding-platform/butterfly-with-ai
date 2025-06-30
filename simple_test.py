#!/usr/bin/env python3
"""
Simple test for the context inference models without dependencies.
"""

import sys
import os
from datetime import datetime
from enum import Enum

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Test just the models
try:
    from aetherterm.agentserver.context_inference.models import (
        OperationType, OperationStage, OperationContext, OperationPattern, 
        ContextInferenceResult, TeamOperationContext
    )
    print("✅ Successfully imported context inference models")
    
    # Test enum values
    print(f"   Operation types: {[t.value for t in OperationType]}")
    print(f"   Operation stages: {[s.value for s in OperationStage]}")
    
    # Test creating an operation context
    context = OperationContext(
        terminal_id="test123",
        operation_type=OperationType.DEVELOPMENT,
        stage=OperationStage.IN_PROGRESS,
        confidence=0.85,
        start_time=datetime.utcnow(),
        progress_percentage=0.6,
        command_sequence=["git clone repo", "cd repo", "npm install"],
        next_likely_commands=["npm run dev", "npm test"],
        risk_factors=["No significant risks detected"],
        suggested_actions=["Continue with testing phase"]
    )
    
    print(f"✅ Successfully created OperationContext:")
    print(f"   Terminal: {context.terminal_id}")
    print(f"   Type: {context.operation_type}")
    print(f"   Stage: {context.stage}")
    print(f"   Confidence: {context.confidence}")
    
    # Test creating inference result
    result = ContextInferenceResult(
        terminal_id="test123",
        timestamp=datetime.utcnow(),
        primary_context=context,
        overall_confidence=0.85,
        reasoning=["Recent git and npm commands suggest development workflow"],
        recommendations=["Run tests before committing"],
        warnings=["No warnings detected"]
    )
    
    print(f"✅ Successfully created ContextInferenceResult")
    print(f"   Overall confidence: {result.overall_confidence}")
    print(f"   Recommendations: {len(result.recommendations)}")
    
    print("\n🎉 All model tests passed! Core context inference types are working correctly.")
    
except Exception as e:
    print(f"❌ Error testing models: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
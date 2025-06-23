#!/usr/bin/env python3
"""
Test script for AetherTerm optional dependencies
Verifies that the system works correctly with various dependency combinations
"""

import sys
import importlib
import logging
from typing import Dict, List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def test_import(module_name: str) -> Tuple[bool, str]:
    """Test if a module can be imported."""
    try:
        importlib.import_module(module_name)
        return True, "✅ Available"
    except ImportError as e:
        return False, f"❌ Missing: {e}"


def test_core_functionality():
    """Test core AetherTerm functionality."""
    print("\n" + "="*50)
    print("🔧 TESTING CORE FUNCTIONALITY")
    print("="*50)
    
    core_modules = [
        "aetherterm.agentserver.server",
        "aetherterm.agentserver.socket_handlers", 
        "aetherterm.agentserver.routes",
        "aetherterm.agentserver.containers",
        "aetherterm.agentserver.telemetry",
    ]
    
    all_passed = True
    for module in core_modules:
        success, message = test_import(module)
        print(f"{module}: {message}")
        if not success:
            all_passed = False
    
    return all_passed


def test_ai_functionality():
    """Test AI-related functionality."""
    print("\n" + "="*50)
    print("🤖 TESTING AI FUNCTIONALITY")
    print("="*50)
    
    # Test AI service availability
    try:
        from aetherterm.agentserver.ai_services import get_ai_service, _AI_AVAILABLE, _MISSING_DEPENDENCIES
        
        ai_service = get_ai_service()
        service_type = ai_service.__class__.__name__
        
        print(f"AI Available: {'✅ Yes' if _AI_AVAILABLE else '❌ No'}")
        print(f"Missing Dependencies: {_MISSING_DEPENDENCIES if _MISSING_DEPENDENCIES else '✅ None'}")
        print(f"AI Service Type: {service_type}")
        
        # Test AI service availability check
        import asyncio
        is_available = asyncio.run(ai_service.is_available())
        print(f"AI Service Available: {'✅ Yes' if is_available else '❌ No'}")
        
        return _AI_AVAILABLE and not _MISSING_DEPENDENCIES
        
    except Exception as e:
        print(f"❌ Error testing AI functionality: {e}")
        return False


def test_langchain_functionality():
    """Test LangChain-related functionality."""
    print("\n" + "="*50)
    print("🦜 TESTING LANGCHAIN FUNCTIONALITY")
    print("="*50)
    
    try:
        from aetherterm import langchain
        
        is_available = langchain.is_langchain_available()
        missing_deps = langchain.get_missing_dependencies()
        
        print(f"LangChain Available: {'✅ Yes' if is_available else '❌ No'}")
        print(f"Missing Dependencies: {missing_deps if missing_deps else '✅ None'}")
        
        # Test individual LangChain modules
        langchain_modules = [
            "langchain",
            "langchain_openai",
            "langchain_anthropic",
            "langchain_community",
        ]
        
        for module in langchain_modules:
            success, message = test_import(module)
            print(f"{module}: {message}")
        
        return is_available
        
    except Exception as e:
        print(f"❌ Error testing LangChain functionality: {e}")
        return False


def test_optional_dependencies():
    """Test various optional dependencies."""
    print("\n" + "="*50)
    print("📦 TESTING OPTIONAL DEPENDENCIES")
    print("="*50)
    
    optional_deps = {
        "Data Processing": [
            "numpy",
            "pandas",
        ],
        "Vector Databases": [
            "chromadb",
            "faiss",
        ],
        "ML Libraries": [
            "torch",
            "transformers",
            "scikit-learn",
            "sentence_transformers",
        ],
        "Database Support": [
            "redis",
            "sqlalchemy",
            "psycopg2",
            "asyncpg",
        ],
        "Development Tools": [
            "ruff",
            "mypy",
            "pytest",
        ]
    }
    
    results = {}
    for category, modules in optional_deps.items():
        print(f"\n📋 {category}:")
        category_results = []
        for module in modules:
            success, message = test_import(module)
            print(f"  {module}: {message}")
            category_results.append(success)
        results[category] = category_results
    
    return results


def test_server_startup():
    """Test that the server can start without errors."""
    print("\n" + "="*50)
    print("🚀 TESTING SERVER STARTUP")
    print("="*50)
    
    try:
        # Test server creation without actually starting it
        from aetherterm.agentserver.server import create_app
        
        print("Creating ASGI app...")
        app, sio, container, config = create_app(
            host="localhost",
            port=57575,
            debug=True,
            unsecure=True,
        )
        
        print("✅ ASGI app created successfully")
        print(f"   App type: {type(app)}")
        print(f"   Socket.IO server: {type(sio)}")
        print(f"   Container: {type(container)}")
        
        # Test AI service initialization
        from aetherterm.agentserver.ai_services import get_ai_service
        ai_service = get_ai_service()
        print(f"   AI Service: {ai_service.__class__.__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during server startup test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_socket_handlers():
    """Test that socket handlers work correctly."""
    print("\n" + "="*50)
    print("🔌 TESTING SOCKET HANDLERS")
    print("="*50)
    
    try:
        from aetherterm.agentserver import socket_handlers
        
        # Test that handlers can be imported
        handlers = [
            "connect",
            "disconnect", 
            "create_terminal",
            "terminal_resize",
            "ai_chat_message",
            "workspace_sync_request",
        ]
        
        for handler_name in handlers:
            if hasattr(socket_handlers, handler_name):
                handler = getattr(socket_handlers, handler_name)
                print(f"✅ {handler_name}: Available")
            else:
                print(f"❌ {handler_name}: Not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing socket handlers: {e}")
        return False


def main():
    """Main test function."""
    print("🧪 AetherTerm Optional Dependencies Test")
    print("="*60)
    
    # Run all tests
    test_results = {}
    
    test_results["Core"] = test_core_functionality()
    test_results["AI"] = test_ai_functionality()
    test_results["LangChain"] = test_langchain_functionality()
    optional_results = test_optional_dependencies()
    test_results["Server Startup"] = test_server_startup()
    test_results["Socket Handlers"] = test_socket_handlers()
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    print("\n🔧 Core Functionality:")
    for test_name, passed in test_results.items():
        if test_name not in ["AI", "LangChain"]:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {test_name}: {status}")
    
    print("\n🤖 AI/ML Functionality:")
    ai_status = "✅ PASS" if test_results["AI"] else "❌ FAIL"
    langchain_status = "✅ PASS" if test_results["LangChain"] else "❌ FAIL"
    print(f"  AI Services: {ai_status}")
    print(f"  LangChain: {langchain_status}")
    
    print("\n📦 Optional Dependencies:")
    for category, results in optional_results.items():
        available_count = sum(results)
        total_count = len(results)
        percentage = (available_count / total_count) * 100 if total_count > 0 else 0
        print(f"  {category}: {available_count}/{total_count} ({percentage:.0f}%)")
    
    # Overall assessment
    core_passed = all(
        test_results[key] for key in test_results 
        if key not in ["AI", "LangChain"]
    )
    
    print("\n🎯 Overall Assessment:")
    if core_passed:
        print("✅ Core functionality is working correctly")
        
        if test_results["AI"] and test_results["LangChain"]:
            print("✅ Full AI/ML functionality is available")
            print("🎉 Complete AetherTerm installation detected")
        elif test_results["AI"] or test_results["LangChain"]:
            print("⚠️ Partial AI functionality is available")
            print("💡 Consider installing additional AI dependencies with: uv sync --extra ai")
        else:
            print("ℹ️ Running in lightweight mode (no AI dependencies)")
            print("💡 To enable AI features, install with: uv sync --extra ai")
    else:
        print("❌ Core functionality has issues")
        print("🔧 Please check your installation")
    
    # Installation recommendations
    print("\n💡 Installation Recommendations:")
    
    if not core_passed:
        print("   uv sync  # Fix core installation")
    elif not any([test_results["AI"], test_results["LangChain"]]):
        print("   uv sync --extra ai       # Add AI functionality")
        print("   uv sync --extra langchain # Add LangChain only")
    elif test_results["LangChain"] and not test_results["AI"]:
        print("   uv sync --extra ai       # Add full AI functionality")
    
    # Exit with appropriate code
    if core_passed:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
OpenHands Demo Server

A simple mock server to demonstrate AetherTerm's OpenHands integration
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn
from pydantic import BaseModel

app = FastAPI(title="OpenHands Demo API", version="1.0.0")

# Mock data storage
conversations: Dict[str, Dict] = {}
agents = [
    {"id": "coding-agent", "name": "Coding Assistant", "description": "Expert in software development"},
    {"id": "debug-agent", "name": "Debug Assistant", "description": "Specializes in debugging and troubleshooting"},
    {"id": "review-agent", "name": "Code Reviewer", "description": "Provides code review and suggestions"}
]

class ConversationRequest(BaseModel):
    message: str
    agent_id: str = "coding-agent"

class ExecuteRequest(BaseModel):
    instruction: str
    workspace_dir: str = "/workspace"

@app.get("/")
async def root():
    return {"message": "OpenHands Demo Server", "version": "1.0.0"}

@app.get("/api")
async def api_root():
    return {"api": "OpenHands Demo API", "endpoints": ["/agents", "/conversations", "/execute"]}

@app.get("/api/agents")
async def get_agents():
    return {"agents": agents}

@app.post("/api/conversations")
async def create_conversation(req: ConversationRequest):
    conversation_id = str(uuid.uuid4())
    conversation = {
        "id": conversation_id,
        "agent_id": req.agent_id,
        "created_at": datetime.now().isoformat(),
        "status": "active",
        "messages": [
            {
                "id": str(uuid.uuid4()),
                "role": "user",
                "content": req.message,
                "timestamp": datetime.now().isoformat()
            }
        ]
    }
    conversations[conversation_id] = conversation
    return {"conversation": conversation}

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"conversation": conversations[conversation_id]}

@app.post("/api/conversations/{conversation_id}/messages")
async def add_message(conversation_id: str, req: ConversationRequest):
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation = conversations[conversation_id]
    message = {
        "id": str(uuid.uuid4()),
        "role": "user", 
        "content": req.message,
        "timestamp": datetime.now().isoformat()
    }
    conversation["messages"].append(message)
    
    # Generate AI response
    ai_response = {
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "content": f"I'll help you with: {req.message}. Let me analyze this task and provide a solution.",
        "timestamp": datetime.now().isoformat()
    }
    conversation["messages"].append(ai_response)
    
    return {"message": ai_response}

@app.post("/api/execute")
async def execute_task(req: ExecuteRequest):
    task_id = str(uuid.uuid4())
    task = {
        "id": task_id,
        "instruction": req.instruction,
        "workspace_dir": req.workspace_dir,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "progress": 0
    }
    
    return {"task": task}

@app.get("/api/tasks/{task_id}/stream")
async def stream_task_output(task_id: str):
    """Stream task execution output"""
    
    async def generate_stream():
        # Simulate task execution with progress updates
        steps = [
            "Analyzing task requirements...",
            "Setting up workspace...", 
            "Executing code analysis...",
            "Generating solution...",
            "Running tests...",
            "Finalizing implementation...",
            "Task completed successfully!"
        ]
        
        for i, step in enumerate(steps):
            progress = int((i + 1) / len(steps) * 100)
            
            # Progress update
            yield f"data: {json.dumps({
                'type': 'progress',
                'data': {
                    'iteration': i + 1,
                    'total_iterations': len(steps),
                    'step': step,
                    'progress': progress
                }
            })}\n\n"
            
            # Action
            yield f"data: {json.dumps({
                'type': 'action',
                'data': {
                    'action': step,
                    'timestamp': datetime.now().isoformat()
                }
            })}\n\n"
            
            # Observation
            yield f"data: {json.dumps({
                'type': 'observation', 
                'data': {
                    'content': f'Step {i+1} completed: {step}',
                    'timestamp': datetime.now().isoformat()
                }
            })}\n\n"
            
            await asyncio.sleep(2)  # Simulate work
            
        # Completion
        yield f"data: {json.dumps({
            'type': 'completion',
            'data': {
                'success': True,
                'message': 'Task completed successfully!',
                'timestamp': datetime.now().isoformat()
            }
        })}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.get("/api/workspace/files")
async def get_workspace_files():
    # Mock file listing
    files = {
        "src/main.py": {"size": 1234, "modified": datetime.now().isoformat()},
        "src/utils.py": {"size": 567, "modified": datetime.now().isoformat()},
        "tests/test_main.py": {"size": 890, "modified": datetime.now().isoformat()},
        "README.md": {"size": 445, "modified": datetime.now().isoformat()},
        "requirements.txt": {"size": 123, "modified": datetime.now().isoformat()}
    }
    
    return {"files": files, "file_count": len(files)}

if __name__ == "__main__":
    print("🤖 Starting OpenHands Demo Server...")
    print("📡 API endpoint: http://localhost:3000")
    print("📖 API docs: http://localhost:3000/docs")
    print("🔄 Ready for AetherTerm OpenHands integration demo!")
    
    uvicorn.run(app, host="0.0.0.0", port=3000, log_level="info")
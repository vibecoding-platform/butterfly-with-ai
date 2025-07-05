"""
AI Service - Infrastructure Layer

Simplified AI service for chat and log search functionality only.
Supports multiple providers: mock, anthropic, lmstudio.
"""

import asyncio
import logging
import re
import aiohttp
import json
from typing import Any, Dict, List, Optional

log = logging.getLogger("aetherterm.infrastructure.ai")


class AIService:
    """Simplified AI service for chat and log search."""

    def __init__(
        self,
        provider: str = "mock",
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet",
        lmstudio_url: str = "http://localhost:1234",
    ):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.lmstudio_url = lmstudio_url

    async def is_available(self) -> bool:
        """Check if AI service is available."""
        if self.provider == "mock":
            return True
        if self.provider == "anthropic":
            return bool(self.api_key)
        if self.provider == "lmstudio":
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.lmstudio_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                        return response.status == 200
            except Exception as e:
                log.warning(f"LMStudio health check failed: {e}")
                return False
        return False

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        terminal_context: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ):
        """Generate chat completion for terminal assistance."""
        if self.provider == "mock":
            # Mock response for testing
            last_message = messages[-1].get("content", "") if messages else ""
            
            # Provide contextual responses based on the message
            if "error" in last_message.lower():
                response = "I can help you troubleshoot this error. Can you provide more details about what you were trying to do?"
            elif "command" in last_message.lower():
                response = "I can help you with terminal commands. What specific task are you trying to accomplish?"
            elif "log" in last_message.lower():
                response = "I can help you analyze logs. You can use the log search feature to find specific entries."
            else:
                response = f"I understand you're asking about: {last_message[:50]}... How can I assist you with your terminal work?"
            
            if stream:
                for chunk in response.split():
                    yield chunk + " "
                    await asyncio.sleep(0.05)
            else:
                yield response
        elif self.provider == "lmstudio":
            # LMStudio implementation
            async for chunk in self._lmstudio_completion(messages, terminal_context, stream):
                yield chunk
        else:
            # Real implementation would call external API
            raise NotImplementedError(f"Provider {self.provider} not implemented")

    async def search_logs(
        self,
        query: str,
        logs: List[Dict[str, Any]],
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search logs using AI-enhanced matching."""
        if not query or not logs:
            return []
        
        # Simple implementation - can be enhanced with actual AI
        query_lower = query.lower()
        matched_logs = []
        
        for log_entry in logs:
            content = log_entry.get("content", "").lower()
            category = log_entry.get("category", "").lower()
            
            # Basic fuzzy matching
            if (query_lower in content or 
                query_lower in category or
                any(word in content for word in query_lower.split())):
                
                # Calculate relevance score
                score = 0
                if query_lower in content:
                    score += 10
                if query_lower in category:
                    score += 5
                
                log_entry_with_score = {**log_entry, "relevance_score": score}
                matched_logs.append(log_entry_with_score)
        
        # Sort by relevance and return top results
        matched_logs.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return matched_logs[:limit]

    async def suggest_search_terms(self, partial_query: str) -> List[str]:
        """Suggest search terms based on partial input."""
        # Simple suggestions - can be enhanced with AI
        common_terms = [
            "error", "warning", "info", "success", "failed", "completed",
            "connection", "timeout", "permission", "not found", "syntax",
            "command", "process", "system", "network", "database"
        ]
        
        if not partial_query:
            return common_terms[:5]
        
        query_lower = partial_query.lower()
        suggestions = [term for term in common_terms if query_lower in term or term.startswith(query_lower)]
        
        return suggestions[:5]

    async def _lmstudio_completion(
        self,
        messages: List[Dict[str, str]],
        terminal_context: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ):
        """Handle LMStudio API completion."""
        try:
            # Prepare system prompt with terminal context
            system_prompt = "You are a helpful terminal assistant that helps users with command-line tasks, troubleshooting, and system administration."
            if terminal_context:
                context_info = []
                if "current_directory" in terminal_context:
                    context_info.append(f"Current directory: {terminal_context['current_directory']}")
                if "recent_commands" in terminal_context:
                    context_info.append(f"Recent commands: {', '.join(terminal_context['recent_commands'][-3:])}")
                if context_info:
                    system_prompt += f"\n\nContext: {'; '.join(context_info)}"

            # Convert messages to LMStudio format
            formatted_messages = [{"role": "system", "content": system_prompt}]
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                formatted_messages.append({"role": role, "content": content})

            # Prepare request payload
            payload = {
                "model": self.model if self.model else "default",
                "messages": formatted_messages,
                "temperature": 0.7,
                "max_tokens": 1000,
                "stream": stream
            }

            async with aiohttp.ClientSession() as session:
                url = f"{self.lmstudio_url}/v1/chat/completions"
                
                async with session.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        log.error(f"LMStudio API error: {response.status} - {error_text}")
                        yield "Sorry, I'm having trouble connecting to the AI service right now."
                        return

                    if stream:
                        # Handle streaming response
                        async for line in response.content:
                            line = line.decode('utf-8').strip()
                            if line.startswith('data: '):
                                data = line[6:]  # Remove 'data: ' prefix
                                if data == '[DONE]':
                                    break
                                try:
                                    chunk_data = json.loads(data)
                                    delta = chunk_data.get('choices', [{}])[0].get('delta', {})
                                    if 'content' in delta:
                                        yield delta['content']
                                except json.JSONDecodeError:
                                    continue
                    else:
                        # Handle non-streaming response
                        result = await response.json()
                        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                        if content:
                            yield content
                        else:
                            yield "I couldn't generate a response. Please try again."

        except asyncio.TimeoutError:
            log.error("LMStudio API timeout")
            yield "The AI service is taking too long to respond. Please try again."
        except Exception as e:
            log.error(f"LMStudio API error: {e}")
            yield f"Error communicating with AI service: {str(e)}"

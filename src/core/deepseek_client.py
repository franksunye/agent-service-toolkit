"""
Simplified DeepSeek HTTP Client
Direct HTTP integration with DeepSeek API for SQL Agent
"""
import json
import logging
import requests
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.outputs import ChatGeneration, ChatResult

from core.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class DeepSeekResponse:
    """DeepSeek API response wrapper"""
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    usage: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None


class DeepSeekHTTPClient:
    """Simplified HTTP client for DeepSeek API"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.DEEPSEEK_API_KEY.get_secret_value() if settings.DEEPSEEK_API_KEY else None
        self.base_url = base_url or "https://api.deepseek.com"
        
        if not self.api_key:
            raise ValueError("DeepSeek API key is required")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _convert_messages(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """Convert LangChain messages to DeepSeek API format"""
        converted = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                converted.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                converted.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, SystemMessage):
                converted.append({"role": "system", "content": msg.content})
            else:
                # Fallback for other message types
                converted.append({"role": "user", "content": str(msg.content)})
        return converted
    
    def chat_completion(
        self,
        messages: List[BaseMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.5,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> DeepSeekResponse:
        """Send chat completion request to DeepSeek API"""
        logger.info(f"🤖 DeepSeek API call: {len(messages)} messages, tools={bool(tools)}")

        data = {
            "model": "deepseek-chat",
            "messages": self._convert_messages(messages),
            "temperature": temperature,
            "stream": stream
        }
        
        if max_tokens:
            data["max_tokens"] = max_tokens
        
        if tools:
            data["tools"] = tools
            data["tool_choice"] = "auto"
        
        try:
            logger.debug(f"📤 Sending request to DeepSeek API: {len(str(data))} chars")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data,
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"❌ DeepSeek API error: {response.status_code} - {response.text}")
                raise Exception(f"DeepSeek API error: {response.status_code} - {response.text}")

            result = response.json()
            choice = result['choices'][0]
            message = choice['message']

            logger.info(f"✅ DeepSeek API response: {choice.get('finish_reason')}, content_length={len(message.get('content', ''))}")
            if message.get('tool_calls'):
                logger.info(f"🔧 Tool calls returned: {len(message.get('tool_calls', []))}")

            return DeepSeekResponse(
                content=message.get('content', ''),
                tool_calls=message.get('tool_calls'),
                usage=result.get('usage'),
                finish_reason=choice.get('finish_reason')
            )

        except Exception as e:
            logger.error(f"❌ DeepSeek API request failed: {e}")
            raise Exception(f"DeepSeek API request failed: {e}")


class DeepSeekChatModel(BaseChatModel):
    """LangChain-compatible DeepSeek chat model"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize client after super().__init__
        object.__setattr__(self, '_client', DeepSeekHTTPClient())

    @property
    def client(self) -> DeepSeekHTTPClient:
        return self._client

    @property
    def _llm_type(self) -> str:
        return "deepseek-chat"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate chat completion"""

        # Extract tools if provided, or use bound tools
        tools = kwargs.get('tools') or getattr(self, '_bound_tools', None)
        temperature = kwargs.get('temperature', 0.5)
        max_tokens = kwargs.get('max_tokens')

        if tools:
            logger.info(f"🔧 Using {len(tools)} tools for generation")

        response = self.client.chat_completion(
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Create AI message from response
        ai_message = AIMessage(
            content=response.content,
            additional_kwargs={
                'tool_calls': response.tool_calls,
                'usage': response.usage,
                'finish_reason': response.finish_reason
            }
        )

        # Add tool calls if present
        if response.tool_calls:
            ai_message.tool_calls = response.tool_calls

        generation = ChatGeneration(message=ai_message)
        return ChatResult(generations=[generation])

    def bind_tools(self, tools):
        """Bind tools to the model for function calling"""
        logger.info(f"🔧 Binding {len(tools)} tools to DeepSeek model")

        # Convert LangChain tools to OpenAI/DeepSeek format
        converted_tools = []
        for tool in tools:
            if hasattr(tool, 'name') and hasattr(tool, 'description'):
                # Extract tool schema
                tool_schema = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": getattr(tool, 'args_schema', {})
                    }
                }

                # If tool has args_schema, convert it to JSON schema
                if hasattr(tool, 'args_schema') and tool.args_schema:
                    try:
                        # Get the schema from the Pydantic model
                        if hasattr(tool.args_schema, 'model_json_schema'):
                            tool_schema["function"]["parameters"] = tool.args_schema.model_json_schema()
                        elif hasattr(tool.args_schema, 'schema'):
                            tool_schema["function"]["parameters"] = tool.args_schema.schema()
                        else:
                            # Fallback to empty parameters
                            tool_schema["function"]["parameters"] = {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                    except Exception as e:
                        logger.warning(f"⚠️ Could not extract schema for tool {tool.name}: {e}")
                        tool_schema["function"]["parameters"] = {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                else:
                    # Default empty parameters
                    tool_schema["function"]["parameters"] = {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }

                converted_tools.append(tool_schema)
                logger.info(f"✅ Converted tool: {tool.name}")

        # Create a new instance with tools bound
        bound_model = DeepSeekChatModel()
        bound_model._bound_tools = converted_tools
        logger.info(f"🔗 Created bound model with {len(converted_tools)} tools")
        return bound_model

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {"model": "deepseek-chat"}


# Global instance for easy access
_deepseek_client = None

def get_deepseek_client() -> DeepSeekHTTPClient:
    """Get global DeepSeek client instance"""
    global _deepseek_client
    if _deepseek_client is None:
        _deepseek_client = DeepSeekHTTPClient()
    return _deepseek_client

def get_deepseek_model() -> DeepSeekChatModel:
    """Get DeepSeek LangChain-compatible model"""
    return DeepSeekChatModel()

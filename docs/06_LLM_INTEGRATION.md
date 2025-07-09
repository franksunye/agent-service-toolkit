# 🧠 LLM集成技术详细设计文档

## 🎯 概述

本文档详细描述Agent Service Toolkit中LLM模型的集成技术，包括多模型支持、工具调用机制、自定义DeepSeek客户端实现等核心技术。

## 🏗️ LLM抽象架构

### 统一模型接口

```python
# src/core/llm.py
from typing import TypeAlias
from langchain_core.language_models.chat_models import BaseChatModel

# 支持的模型类型
ModelT: TypeAlias = (
    DeepSeekChatModel    # 主要模型
    | ChatOpenAI         # 备用模型  
    | FakeToolModel      # 测试模型
)

@cache
def get_model(model_name: AllModelEnum) -> ModelT:
    """统一模型工厂函数"""
    # 处理字符串模型名称
    if isinstance(model_name, str):
        model_name = resolve_model_enum(model_name)
    
    # 路由到具体模型实现
    if isinstance(model_name, DeepseekModelName):
        return get_deepseek_model()
    elif isinstance(model_name, OpenAIModelName):
        return get_openai_model(model_name)
    elif isinstance(model_name, FakeModelName):
        return get_fake_model()
    else:
        raise ValueError(f"Unsupported model: {model_name}")
```

### 模型配置管理

```python
# src/schema/models.py
class DeepseekModelName(StrEnum):
    """DeepSeek模型枚举"""
    DEEPSEEK_CHAT = "deepseek-chat"
    DEEPSEEK_CODER = "deepseek-coder"

class OpenAIModelName(StrEnum):
    """OpenAI模型枚举"""
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_3_5_TURBO = "gpt-3.5-turbo"

# 模型映射表
_MODEL_TABLE = {
    DeepseekModelName.DEEPSEEK_CHAT: "deepseek-chat",
    OpenAIModelName.GPT_4O: "gpt-4o",
    OpenAIModelName.GPT_4O_MINI: "gpt-4o-mini",
    FakeModelName.FAKE: "fake",
}
```

## 🔧 DeepSeek自定义实现

### HTTP客户端实现

```python
# src/core/deepseek_client.py
class DeepSeekHTTPClient:
    """DeepSeek API的HTTP客户端"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.DEEPSEEK_API_KEY.get_secret_value()
        self.base_url = base_url or "https://api.deepseek.com"
        
        if not self.api_key:
            raise ValueError("DeepSeek API key is required")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def chat_completion(
        self,
        messages: List[BaseMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.5,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> DeepSeekResponse:
        """发送聊天完成请求"""
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
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data,
                timeout=30
            )

            if response.status_code != 200:
                raise Exception(f"DeepSeek API error: {response.status_code} - {response.text}")

            result = response.json()
            choice = result['choices'][0]
            message = choice['message']

            logger.info(f"✅ DeepSeek API response: {choice.get('finish_reason')}")
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
```

### LangChain兼容包装器

```python
class DeepSeekChatModel(BaseChatModel):
    """LangChain兼容的DeepSeek聊天模型"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, '_client', DeepSeekHTTPClient())

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
        """生成聊天完成"""
        # 提取工具和参数
        tools = kwargs.get('tools') or getattr(self, '_bound_tools', None)
        temperature = kwargs.get('temperature', 0.5)
        max_tokens = kwargs.get('max_tokens')
        
        if tools:
            logger.info(f"🔧 Using {len(tools)} tools for generation")

        response = self._client.chat_completion(
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # 创建AI消息
        ai_message = AIMessage(
            content=response.content,
            additional_kwargs={
                'tool_calls': response.tool_calls,
                'usage': response.usage,
                'finish_reason': response.finish_reason
            }
        )

        # 添加工具调用
        if response.tool_calls:
            ai_message.tool_calls = response.tool_calls

        generation = ChatGeneration(message=ai_message)
        return ChatResult(generations=[generation])
```

## 🔧 工具调用机制

### 工具绑定实现

```python
def bind_tools(self, tools):
    """绑定工具到模型以支持Function Calling"""
    logger.info(f"🔧 Binding {len(tools)} tools to DeepSeek model")
    
    # 转换LangChain工具为OpenAI/DeepSeek格式
    converted_tools = []
    for tool in tools:
        if hasattr(tool, 'name') and hasattr(tool, 'description'):
            tool_schema = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": self._extract_tool_parameters(tool)
                }
            }
            converted_tools.append(tool_schema)
            logger.info(f"✅ Converted tool: {tool.name}")
    
    # 创建绑定工具的新实例
    bound_model = DeepSeekChatModel()
    bound_model._bound_tools = converted_tools
    logger.info(f"🔗 Created bound model with {len(converted_tools)} tools")
    return bound_model

def _extract_tool_parameters(self, tool):
    """提取工具参数schema"""
    if hasattr(tool, 'args_schema') and tool.args_schema:
        try:
            if hasattr(tool.args_schema, 'model_json_schema'):
                return tool.args_schema.model_json_schema()
            elif hasattr(tool.args_schema, 'schema'):
                return tool.args_schema.schema()
        except Exception as e:
            logger.warning(f"⚠️ Could not extract schema for tool {tool.name}: {e}")
    
    # 默认空参数
    return {
        "type": "object",
        "properties": {},
        "required": []
    }
```

### Function Calling处理

```python
def process_function_calls(tool_calls: List[dict], available_tools: dict) -> List[ToolMessage]:
    """处理Function Calling结果"""
    tool_messages = []
    
    for tool_call in tool_calls:
        try:
            # 解析工具调用
            tool_name = tool_call["function"]["name"]
            tool_args = json.loads(tool_call["function"]["arguments"])
            tool_id = tool_call["id"]
            
            logger.info(f"🔧 Executing tool: {tool_name}")
            
            # 查找并执行工具
            if tool_name in available_tools:
                tool = available_tools[tool_name]
                result = tool.invoke(tool_args)
                
                # 创建工具消息
                tool_message = ToolMessage(
                    content=str(result),
                    tool_call_id=tool_id,
                    name=tool_name
                )
                tool_messages.append(tool_message)
                
                logger.info(f"✅ Tool {tool_name} executed successfully")
            else:
                error_msg = f"Unknown tool: {tool_name}"
                logger.error(f"❌ {error_msg}")
                
                tool_message = ToolMessage(
                    content=error_msg,
                    tool_call_id=tool_id,
                    name=tool_name
                )
                tool_messages.append(tool_message)
                
        except Exception as e:
            error_msg = f"Tool execution error: {e}"
            logger.error(f"❌ {error_msg}")
            
            tool_message = ToolMessage(
                content=error_msg,
                tool_call_id=tool_call.get("id", "unknown"),
                name=tool_call.get("function", {}).get("name", "unknown")
            )
            tool_messages.append(tool_message)
    
    return tool_messages
```

## 🎭 测试模型实现

### FakeToolModel设计

```python
class FakeToolModel(FakeListChatModel):
    """支持工具调用的测试模型"""
    
    def __init__(self, responses: list[str] = None):
        if responses is None:
            responses = ["This is a test response from the fake model."]
        super().__init__(responses=responses)
        self._tools = []

    def bind_tools(self, tools):
        """绑定工具并返回支持工具调用的新实例"""
        new_model = FakeToolModel(self.responses)
        new_model._tools = tools
        return new_model
    
    async def ainvoke(self, messages, config=None, **kwargs):
        """重写以生成智能的工具调用"""
        from langchain_core.messages import AIMessage
        
        # 获取最后的人类消息
        last_message = None
        for msg in reversed(messages):
            if hasattr(msg, 'content') and msg.content:
                last_message = msg.content.lower()
                break
        
        # 如果是数据库相关查询且有工具，生成工具调用
        if (last_message and 
            any(keyword in last_message for keyword in ['table', 'database', 'schema', 'query', 'sql']) and 
            self._tools):
            
            # 根据查询生成合适的工具调用
            tool_call = None
            if 'table' in last_message or 'schema' in last_message:
                for tool in self._tools:
                    if hasattr(tool, 'name') and tool.name == 'get_database_schema':
                        tool_call = {
                            "name": "get_database_schema",
                            "args": {},
                            "id": "call_get_schema_001"
                        }
                        break
            
            if tool_call:
                return AIMessage(
                    content="I'll check the database schema for you.",
                    tool_calls=[tool_call]
                )
        
        # 回退到默认行为
        return await super().ainvoke(messages, config, **kwargs)
```

## 🔄 流式响应处理

### 流式生成实现

```python
async def astream_generate(
    self,
    messages: List[BaseMessage],
    **kwargs
) -> AsyncGenerator[str, None]:
    """异步流式生成响应"""
    try:
        # 构建请求数据
        data = {
            "model": "deepseek-chat",
            "messages": self._convert_messages(messages),
            "stream": True,
            "temperature": kwargs.get('temperature', 0.5)
        }
        
        # 发送流式请求
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data
            ) as response:
                
                if response.status != 200:
                    raise Exception(f"API error: {response.status}")
                
                # 处理流式响应
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if line.startswith('data: '):
                        data_str = line[6:]  # 移除 'data: ' 前缀
                        
                        if data_str == '[DONE]':
                            break
                        
                        try:
                            chunk_data = json.loads(data_str)
                            delta = chunk_data['choices'][0]['delta']
                            
                            if 'content' in delta:
                                yield delta['content']
                                
                        except json.JSONDecodeError:
                            continue
                            
    except Exception as e:
        logger.error(f"Stream generation error: {e}")
        yield f"Error: {e}"
```

### 流式工具调用

```python
async def handle_streaming_tool_calls(
    stream: AsyncGenerator[dict, None]
) -> AsyncGenerator[Union[str, ToolMessage], None]:
    """处理流式工具调用"""
    tool_call_buffer = {}
    
    async for chunk in stream:
        if 'choices' in chunk:
            choice = chunk['choices'][0]
            delta = choice.get('delta', {})
            
            # 处理内容流
            if 'content' in delta and delta['content']:
                yield delta['content']
            
            # 处理工具调用流
            if 'tool_calls' in delta:
                for tool_call_delta in delta['tool_calls']:
                    index = tool_call_delta.get('index', 0)
                    
                    if index not in tool_call_buffer:
                        tool_call_buffer[index] = {
                            'id': '',
                            'function': {'name': '', 'arguments': ''}
                        }
                    
                    # 累积工具调用数据
                    if 'id' in tool_call_delta:
                        tool_call_buffer[index]['id'] += tool_call_delta['id']
                    
                    if 'function' in tool_call_delta:
                        func_delta = tool_call_delta['function']
                        if 'name' in func_delta:
                            tool_call_buffer[index]['function']['name'] += func_delta['name']
                        if 'arguments' in func_delta:
                            tool_call_buffer[index]['function']['arguments'] += func_delta['arguments']
            
            # 检查是否完成
            if choice.get('finish_reason') == 'tool_calls':
                # 执行累积的工具调用
                for tool_call in tool_call_buffer.values():
                    if tool_call['function']['name']:  # 确保工具名称完整
                        tool_result = await execute_tool_call(tool_call)
                        yield tool_result
```

## 📊 模型性能监控

### 调用统计

```python
from prometheus_client import Counter, Histogram

# 性能指标
MODEL_REQUESTS = Counter('llm_requests_total', 'Total LLM requests', ['model', 'status'])
MODEL_LATENCY = Histogram('llm_request_duration_seconds', 'LLM request duration', ['model'])
TOKEN_USAGE = Counter('llm_tokens_total', 'Total tokens used', ['model', 'type'])

class MonitoredModel:
    """带监控的模型包装器"""
    
    def __init__(self, model: BaseChatModel, model_name: str):
        self.model = model
        self.model_name = model_name
    
    async def ainvoke(self, messages, **kwargs):
        """监控模型调用"""
        start_time = time.time()
        
        try:
            with MODEL_LATENCY.labels(model=self.model_name).time():
                result = await self.model.ainvoke(messages, **kwargs)
            
            MODEL_REQUESTS.labels(model=self.model_name, status='success').inc()
            
            # 记录token使用量
            if hasattr(result, 'usage_metadata'):
                usage = result.usage_metadata
                TOKEN_USAGE.labels(model=self.model_name, type='input').inc(usage.get('input_tokens', 0))
                TOKEN_USAGE.labels(model=self.model_name, type='output').inc(usage.get('output_tokens', 0))
            
            return result
            
        except Exception as e:
            MODEL_REQUESTS.labels(model=self.model_name, status='error').inc()
            raise
```

### 错误处理与重试

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

class ResilientModel:
    """具有重试机制的模型包装器"""
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def ainvoke_with_retry(self, messages, **kwargs):
        """带重试的模型调用"""
        try:
            return await self.model.ainvoke(messages, **kwargs)
        except Exception as e:
            logger.warning(f"Model call failed, retrying: {e}")
            raise
    
    async def ainvoke(self, messages, **kwargs):
        """主调用方法"""
        try:
            return await self.ainvoke_with_retry(messages, **kwargs)
        except Exception as e:
            logger.error(f"Model call failed after retries: {e}")
            # 返回错误消息而不是抛出异常
            return AIMessage(content=f"抱歉，模型调用失败: {e}")
```

---

*本文档详细描述了LLM集成的核心技术实现，为模型集成和优化提供技术指导。*

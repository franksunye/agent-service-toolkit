# 🔧 后端服务详细设计文档

## 🎯 概述

本文档详细描述Agent Service Toolkit后端服务的技术实现，包括FastAPI服务架构、Agent管理系统、LLM集成、数据存储等核心组件的设计和实现。

## 🏗️ FastAPI服务架构

### 服务入口点

```python
# src/service/service.py
app = FastAPI(lifespan=lifespan)
router = APIRouter(dependencies=[Depends(verify_bearer)])

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok"}

app.include_router(router)
```

### 核心API端点

#### 1. 服务信息端点
```python
@router.get("/info")
async def info() -> ServiceMetadata:
    """获取服务元数据，包括可用Agent和模型"""
    return ServiceMetadata(
        agents=get_all_agent_info(),
        models=list(settings.AVAILABLE_MODELS),
        default_agent=DEFAULT_AGENT,
        default_model=settings.DEFAULT_MODEL,
    )
```

#### 2. Agent调用端点
```python
@router.post("/{agent_id}/invoke")
async def invoke(
    agent_id: str,
    input: ChatMessage,
    config: Annotated[RunnableConfig, Depends(get_config)]
) -> ChatMessage:
    """同步调用Agent"""
    agent = get_agent(agent_id)
    response = await agent.ainvoke({"messages": [input.to_langchain()]}, config)
    return langchain_to_chat_message(response["messages"][-1])
```

#### 3. 流式响应端点
```python
@router.post("/{agent_id}/stream")
async def stream(
    agent_id: str,
    input: ChatMessage,
    config: Annotated[RunnableConfig, Depends(get_config)]
) -> StreamingResponse:
    """流式调用Agent"""
    agent = get_agent(agent_id)
    
    async def generate():
        async for chunk in agent.astream({"messages": [input.to_langchain()]}, config):
            if "messages" in chunk:
                for message in chunk["messages"]:
                    yield f"data: {json.dumps(langchain_to_chat_message(message).model_dump())}\n\n"
    
    return StreamingResponse(generate(), media_type="text/plain")
```

### 认证与授权

#### Bearer Token认证
```python
security = HTTPBearer()

async def verify_bearer(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """验证Bearer Token"""
    if not settings.AUTH_SECRET:
        return  # 开发模式，跳过认证
    
    token = credentials.credentials
    if not verify_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
```

### 配置管理

#### 运行时配置
```python
def get_config(
    model: str = Query(default=settings.DEFAULT_MODEL),
    thread_id: str = Query(default_factory=lambda: str(uuid.uuid4())),
    user_id: str = Query(default="anonymous")
) -> RunnableConfig:
    """构建Agent运行配置"""
    return RunnableConfig(
        configurable={
            "model": model,
            "thread_id": thread_id,
            "user_id": user_id
        },
        tags=["agent-service"],
        metadata={"source": "api"}
    )
```

## 🤖 Agent管理系统

### Agent注册机制

#### Agent定义
```python
# src/agents/agents.py
@dataclass
class Agent:
    description: str
    graph: Pregel

agents: dict[str, Agent] = {
    "sql-agent": Agent(
        description="An intelligent SQL database assistant",
        graph=sql_agent
    ),
    "chatbot": Agent(
        description="A simple chatbot", 
        graph=chatbot
    ),
    # ... 更多Agent
}
```

#### Agent获取
```python
def get_agent(agent_id: str) -> Pregel:
    """根据ID获取Agent实例"""
    if agent_id not in agents:
        raise ValueError(f"Unknown agent: {agent_id}")
    return agents[agent_id].graph

def get_all_agent_info() -> list[AgentInfo]:
    """获取所有Agent信息"""
    return [
        AgentInfo(key=agent_id, description=agent.description) 
        for agent_id, agent in agents.items()
    ]
```

### Agent生命周期管理

#### 初始化
```python
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    try:
        # 初始化数据库连接
        saver = get_checkpointer()
        store = get_store()
        
        # 配置所有Agent
        agents = get_all_agent_info()
        for a in agents:
            agent = get_agent(a.key)
            agent.checkpointer = saver  # 会话记忆
            agent.store = store         # 长期存储
        
        yield
    except Exception as e:
        logger.error(f"Error during initialization: {e}")
        raise
```

## 🧠 LLM集成架构

### 模型抽象层

#### 统一模型接口
```python
# src/core/llm.py
ModelT: TypeAlias = (
    DeepSeekChatModel
    | ChatOpenAI  
    | FakeToolModel
)

@cache
def get_model(model_name: AllModelEnum) -> ModelT:
    """模型工厂函数"""
    if isinstance(model_name, DeepseekModelName):
        return get_deepseek_model()
    elif isinstance(model_name, OpenAIModelName):
        return ChatOpenAI(model=model_name.value)
    elif isinstance(model_name, FakeModelName):
        return FakeToolModel()
    else:
        raise ValueError(f"Unsupported model: {model_name}")
```

### DeepSeek集成

#### 自定义DeepSeek客户端
```python
# src/core/deepseek_client.py
class DeepSeekChatModel(BaseChatModel):
    """LangChain兼容的DeepSeek模型"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._client = DeepSeekHTTPClient()
    
    def bind_tools(self, tools):
        """绑定工具到模型"""
        converted_tools = []
        for tool in tools:
            tool_schema = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.args_schema.model_json_schema()
                }
            }
            converted_tools.append(tool_schema)
        
        bound_model = DeepSeekChatModel()
        bound_model._bound_tools = converted_tools
        return bound_model
    
    async def _generate(self, messages, **kwargs):
        """生成响应"""
        tools = kwargs.get('tools') or getattr(self, '_bound_tools', None)
        response = self._client.chat_completion(
            messages=messages,
            tools=tools,
            temperature=kwargs.get('temperature', 0.5)
        )
        
        ai_message = AIMessage(
            content=response.content,
            tool_calls=response.tool_calls
        )
        return ChatResult(generations=[ChatGeneration(message=ai_message)])
```

### 工具调用机制

#### 工具绑定
```python
def bind_tools_to_model(model: ModelT, tools: list[BaseTool]) -> ModelT:
    """将工具绑定到模型"""
    if hasattr(model, 'bind_tools'):
        return model.bind_tools(tools)
    else:
        raise ValueError(f"Model {type(model)} does not support tool binding")
```

#### Function Calling处理
```python
def process_tool_calls(tool_calls: list[dict]) -> list[ToolMessage]:
    """处理工具调用"""
    results = []
    for tool_call in tool_calls:
        tool_name = tool_call["function"]["name"]
        tool_args = json.loads(tool_call["function"]["arguments"])
        
        # 执行工具
        tool = get_tool(tool_name)
        result = tool.invoke(tool_args)
        
        # 创建工具消息
        tool_message = ToolMessage(
            content=str(result),
            tool_call_id=tool_call["id"]
        )
        results.append(tool_message)
    
    return results
```

## 💾 数据存储设计

### 会话存储

#### SQLite Checkpointer
```python
# src/memory/sqlite.py
class SqliteSaver(BaseCheckpointSaver):
    """SQLite会话存储"""
    
    def __init__(self, conn: sqlite3.Connection):
        super().__init__()
        self.conn = conn
        self._setup_tables()
    
    def _setup_tables(self):
        """创建存储表"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                thread_id TEXT,
                checkpoint_ns TEXT,
                checkpoint_id TEXT,
                parent_checkpoint_id TEXT,
                type TEXT,
                checkpoint BLOB,
                metadata BLOB,
                PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
            )
        """)
    
    async def aput(self, config: RunnableConfig, checkpoint: Checkpoint, metadata: dict):
        """保存检查点"""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_data = pickle.dumps(checkpoint)
        metadata_data = pickle.dumps(metadata)
        
        self.conn.execute("""
            INSERT OR REPLACE INTO checkpoints 
            (thread_id, checkpoint_ns, checkpoint_id, checkpoint, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (thread_id, "", checkpoint.id, checkpoint_data, metadata_data))
        self.conn.commit()
```

### 长期存储

#### Store接口实现
```python
class SqliteStore(BaseStore):
    """SQLite长期存储"""
    
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._setup_tables()
    
    def _setup_tables(self):
        """创建存储表"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS store (
                namespace TEXT,
                key TEXT,
                value BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (namespace, key)
            )
        """)
    
    async def aput(self, namespace: tuple[str, ...], key: str, value: dict):
        """存储键值对"""
        ns_str = "/".join(namespace)
        value_data = pickle.dumps(value)
        
        self.conn.execute("""
            INSERT OR REPLACE INTO store (namespace, key, value, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (ns_str, key, value_data))
        self.conn.commit()
```

## 🔧 工具系统设计

### 工具注册
```python
# src/agents/tools.py
@tool
def calculator(expression: str) -> str:
    """计算数学表达式"""
    try:
        result = eval(expression)  # 生产环境需要安全的计算器
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"

# 工具注册表
AVAILABLE_TOOLS = {
    "calculator": calculator,
    "web_search": web_search,
    "database_search": database_search,
}
```

### 工具执行
```python
def execute_tool(tool_name: str, args: dict) -> str:
    """安全执行工具"""
    if tool_name not in AVAILABLE_TOOLS:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    tool = AVAILABLE_TOOLS[tool_name]
    try:
        result = tool.invoke(args)
        return str(result)
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return f"工具执行失败: {e}"
```

## 📊 监控与日志

### 结构化日志
```python
import structlog

logger = structlog.get_logger()

async def log_agent_execution(agent_id: str, user_id: str, execution_time: float):
    """记录Agent执行日志"""
    logger.info(
        "agent_execution_completed",
        agent_id=agent_id,
        user_id=user_id,
        execution_time=execution_time,
        timestamp=datetime.utcnow().isoformat()
    )
```

### 性能监控
```python
from prometheus_client import Counter, Histogram

# 指标定义
REQUEST_COUNT = Counter('agent_requests_total', 'Total agent requests', ['agent_id', 'status'])
REQUEST_DURATION = Histogram('agent_request_duration_seconds', 'Agent request duration')

@REQUEST_DURATION.time()
async def execute_agent(agent_id: str, input_data: dict):
    """执行Agent并记录指标"""
    try:
        result = await agent.ainvoke(input_data)
        REQUEST_COUNT.labels(agent_id=agent_id, status='success').inc()
        return result
    except Exception as e:
        REQUEST_COUNT.labels(agent_id=agent_id, status='error').inc()
        raise
```

---

*本文档详细描述了后端服务的核心技术实现，为开发和维护提供技术参考。*

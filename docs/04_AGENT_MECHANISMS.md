# 🤖 Agent机制详细设计文档

## 🎯 概述

本文档详细描述Agent Service Toolkit中各种Agent的实现机制和设计模式，为Agent开发提供技术指导。

### 🤖 Agent类型总览

项目支持8种不同类型的Agent，每种都有其特定的用途和实现模式：

1. **SQL Agent** - 数据库查询和分析助手 ([详细设计](08_SQL_AGENT_DESIGN.md))
2. **Research Assistant** - 网络搜索和研究助手
3. **Simple Chatbot** - 基础对话机器人
4. **Command Agent** - LangGraph v0.3 Command功能演示
5. **Supervisor Agent** - 多Agent协调管理
6. **Interrupt Agent** - 支持人机交互中断
7. **Background Task Agent** - 后台任务处理
8. **Knowledge Base Agent** - RAG检索增强生成

> **注意**: SQL Agent的详细实现请参考 [SQL Agent详细设计文档](08_SQL_AGENT_DESIGN.md)

### 📊 Agent特性对比

| Agent类型 | 复杂度 | 工具集成 | 状态管理 | 特殊功能 | 主要用途 |
|-----------|--------|----------|----------|----------|----------|
| SQL Agent | 高 | ✅ 数据库工具 | 复杂状态 | 4阶段工作流 | 数据库查询分析 |
| Research Assistant | 中 | ✅ 搜索/计算器 | 标准状态 | 安全检查 | 网络搜索研究 |
| Simple Chatbot | 低 | ❌ 无工具 | 消息历史 | 最简实现 | 基础对话 |
| Command Agent | 中 | ❌ 无工具 | 基础状态 | Command路由 | 流程控制演示 |
| Supervisor Agent | 高 | ✅ 多Agent | 协调状态 | 多Agent管理 | 任务分发协调 |
| Interrupt Agent | 中 | ❌ 无工具 | 扩展状态 | 人机中断 | 交互式对话 |
| Background Task Agent | 中 | ❌ 无工具 | 任务状态 | 后台处理 | 异步任务管理 |
| Knowledge Base Agent | 高 | ✅ 检索工具 | 文档状态 | RAG检索 | 知识库问答 |

## 🏗️ LangGraph框架基础

### 状态图架构

```python
from langgraph.graph import StateGraph, END
from langgraph.managed import RemainingSteps

class AgentState(MessagesState, total=False):
    """Agent状态定义"""
    safety: LlamaGuardOutput          # 安全检查结果
    remaining_steps: RemainingSteps   # 剩余执行步数
    planning_result: dict             # 规划阶段结果
    database_context: dict            # 数据库上下文
```

### 基础工作流模式

```python
# 创建状态图
agent = StateGraph(AgentState)

# 添加节点
agent.add_node("guard_input", llama_guard_input)      # 输入安全检查
agent.add_node("model", acall_model)                  # 模型调用
agent.add_node("tools", ToolNode(tools))              # 工具执行
agent.add_node("block_unsafe_content", block_unsafe)  # 阻止不安全内容

# 设置入口点
agent.set_entry_point("guard_input")

# 添加条件边
agent.add_conditional_edges(
    "guard_input", 
    check_safety, 
    {"unsafe": "block_unsafe_content", "safe": "model"}
)

agent.add_conditional_edges(
    "model",
    should_continue,
    {"continue": "tools", "end": END}
)

agent.add_edge("tools", "model")
agent.add_edge("block_unsafe_content", END)
```

## 🧠 SQL Agent概览

SQL Agent是项目中最复杂的Agent，采用4阶段工作流程处理数据库查询和分析任务。

### 核心特性
- **4阶段工作流程**: Planning → Tool Execution → Reflection → Memory Storage
- **记忆系统集成**: 支持用户偏好和查询历史存储
- **安全SQL执行**: 严格的SQL注入防护和权限控制
- **智能查询分析**: 自动识别用户查询模式和偏好

### 工具集成
```python
sql_tools = [
    get_database_schema,      # 获取数据库结构
    execute_sql_query,        # 执行SQL查询
    analyze_query_results,    # 分析查询结果
    analyze_database_schema,  # 分析数据库设计
    generate_sql_query,       # 生成SQL查询
]
```

### 记忆系统
- **命名空间**: `("sql_agent", user_id)`
- **存储内容**: 用户偏好、查询历史、查询模式
- **个性化**: 基于历史提供个性化建议

> **详细实现**: 完整的SQL Agent设计和实现请参考 [SQL Agent详细设计文档](08_SQL_AGENT_DESIGN.md)

## 🔍 Research Assistant设计

### 工具集成架构
```python
# Research Assistant工具集
tools = [
    DuckDuckGoSearchResults(max_results=5),
    calculator,
    OpenWeatherMapQueryRun(api_wrapper=OpenWeatherMapAPIWrapper())
]

class AgentState(MessagesState, total=False):
    safety: LlamaGuardOutput
    remaining_steps: RemainingSteps

async def acall_model(state: AgentState, config: RunnableConfig) -> AgentState:
    """调用模型并处理安全检查"""
    m = get_model(config["configurable"].get("model", settings.DEFAULT_MODEL))
    model_runnable = wrap_model(m)
    response = await model_runnable.ainvoke(state, config)
    
    # Llama Guard安全检查
    llama_guard = LlamaGuard()
    safety_output = await llama_guard.ainvoke("Agent", state["messages"] + [response])
    
    if safety_output.safety_assessment == SafetyAssessment.UNSAFE:
        return {"messages": [format_safety_message(safety_output)], "safety": safety_output}
    
    # 检查剩余步数
    if state["remaining_steps"] < 2 and response.tool_calls:
        return {
            "messages": [
                AIMessage(
                    id=response.id,
                    content="Sorry, need more steps to process this request.",
                )
            ]
        }
    
    return {"messages": [response]}
```

### 安全检查机制
```python
async def llama_guard_input(state: AgentState, config: RunnableConfig) -> AgentState:
    """输入安全检查"""
    llama_guard = LlamaGuard()
    safety_output = await llama_guard.ainvoke("User", state["messages"])
    return {"safety": safety_output, "messages": []}

def check_safety(state: AgentState) -> Literal["unsafe", "safe"]:
    """检查安全状态"""
    safety: LlamaGuardOutput = state["safety"]
    match safety.safety_assessment:
        case SafetyAssessment.UNSAFE:
            return "unsafe"
        case _:
            return "safe"
```

## 💬 Simple Chatbot设计

### 最简化实现
```python
from langgraph.func import entrypoint

@entrypoint()
async def chatbot(
    inputs: dict[str, list[BaseMessage]],
    *,
    previous: dict[str, list[BaseMessage]],
    config: RunnableConfig,
):
    """简单聊天机器人"""
    messages = inputs["messages"]
    if previous:
        messages = previous["messages"] + messages

    model = get_model(config["configurable"].get("model", settings.DEFAULT_MODEL))
    response = await model.ainvoke(messages)
    
    return entrypoint.final(
        value={"messages": [response]}, 
        save={"messages": messages + [response]}
    )
```

## 💬 Simple Chatbot设计

### 最简化实现
Simple Chatbot是最基础的Agent，使用LangGraph的entrypoint装饰器实现简单的对话功能。

```python
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.func import entrypoint
from core import get_model, settings

@entrypoint()
async def chatbot(
    inputs: dict[str, list[BaseMessage]],
    *,
    previous: dict[str, list[BaseMessage]],
    config: RunnableConfig,
):
    """简单聊天机器人 - 直接调用LLM进行对话"""
    messages = inputs["messages"]
    if previous:
        messages = previous["messages"] + messages

    model = get_model(config["configurable"].get("model", settings.DEFAULT_MODEL))
    response = await model.ainvoke(messages)

    return entrypoint.final(
        value={"messages": [response]},
        save={"messages": messages + [response]}
    )
```

**特点**:
- 无状态管理，只保留消息历史
- 直接LLM调用，无工具集成
- 适用于基础对话场景

## 🔧 Command Agent设计

### 流程控制演示
Command Agent展示了LangGraph v0.3的Command功能，用于动态流程控制。

```python
import random
from typing import Literal
from langchain_core.messages import AIMessage
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.types import Command

class AgentState(MessagesState, total=False):
    pass

def node_a(state: AgentState) -> Command[Literal["node_b", "node_c"]]:
    """节点A - 随机选择下一个节点"""
    print("Called A")
    value = random.choice(["a", "b"])

    # Command允许同时更新状态和路由到下一个节点
    if value == "a":
        goto = "node_b"
    else:
        goto = "node_c"

    return Command(
        # 状态更新
        update={"messages": [AIMessage(content=f"Hello {value}")]},
        # 路由到下一个节点
        goto=goto,
    )

def node_b(state: AgentState):
    """节点B"""
    print("Called B")
    return {"messages": [AIMessage(content="Hello B")]}

def node_c(state: AgentState):
    """节点C"""
    print("Called C")
    return {"messages": [AIMessage(content="Hello C")]}

# 构建图
builder = StateGraph(AgentState)
builder.add_edge(START, "node_a")
builder.add_node(node_a)
builder.add_node(node_b)
builder.add_node(node_c)
# 注意：节点A、B、C之间没有边，通过Command动态路由

command_agent = builder.compile()
```

**特点**:
- 展示Command功能的动态路由
- 替代传统的条件边函数
- 同时支持状态更新和流程控制

## 🎭 Supervisor Agent设计

### 多Agent协调
Supervisor Agent使用LangGraph的create_supervisor功能，协调多个专业Agent。

```python
from langgraph.prebuilt import create_react_agent, create_supervisor

# 创建专业Agent
math_agent = create_react_agent(
    model=model,
    tools=[add, multiply],
    name="math_expert",
    prompt="You are a math expert. Always use one tool at a time.",
).with_config(tags=["skip_stream"])

research_agent = create_react_agent(
    model=model,
    tools=[web_search],
    name="research_expert",
    prompt="You are a world class researcher with access to web search. Do not do any math.",
).with_config(tags=["skip_stream"])

# 创建监督工作流
workflow = create_supervisor(
    [research_agent, math_agent],
    model=model,
    prompt=(
        "You are a team supervisor managing a research expert and a math expert. "
        "For current events, use research_agent. "
        "For math problems, use math_agent."
    ),
    add_handoff_back_messages=False,
)

langgraph_supervisor_agent = workflow.compile()
```

**特点**:
- 多Agent协调管理
- 智能任务分发
- 专业化Agent组合
- 统一的监督逻辑

## 🔄 Interrupt Agent设计

### 人机交互中断
Interrupt Agent展示了LangGraph的interrupt功能，支持人机交互中断。

```python
import logging
from datetime import datetime
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.store.base import BaseStore
from langgraph.types import interrupt
from pydantic import BaseModel, Field

class AgentState(MessagesState, total=False):
    birthdate: datetime | None

class BirthdateExtraction(BaseModel):
    birthdate: str | None = Field(
        description="The extracted birthdate in YYYY-MM-DD format"
    )
    reasoning: str = Field(
        description="Explanation of how the birthdate was extracted"
    )

async def determine_birthdate(
    state: AgentState, config: RunnableConfig, store: BaseStore
) -> AgentState:
    """确定用户生日，支持中断询问"""

    user_id = config["configurable"].get("user_id")
    namespace = (user_id,) if user_id else None

    # 检查存储中是否已有生日信息
    if namespace:
        try:
            result = await store.aget(namespace, key="birthdate")
            if result and result.value.get("birthdate"):
                birthdate_str = result.value["birthdate"]
                birthdate = datetime.fromisoformat(birthdate_str)
                return {"birthdate": birthdate, "messages": []}
        except Exception as e:
            logger.error(f"Error reading from store: {e}")

    # 尝试从对话中提取生日
    model = get_model(config["configurable"].get("model", settings.DEFAULT_MODEL))
    model_runnable = wrap_model(
        model.with_structured_output(BirthdateExtraction),
        birthdate_extraction_prompt.format()
    )
    response: BirthdateExtraction = await model_runnable.ainvoke(state, config)

    # 如果没有找到生日，中断询问用户
    if response.birthdate is None:
        birthdate_input = interrupt(f"{response.reasoning}\nPlease tell me your birthdate?")
        # 将用户输入添加到消息中，递归处理
        state["messages"].append(HumanMessage(birthdate_input))
        return await determine_birthdate(state, config, store)

    # 解析并存储生日
    try:
        birthdate = datetime.fromisoformat(response.birthdate)

        # 存储到长期记忆
        if namespace:
            await store.aput(namespace, "birthdate", {"birthdate": birthdate.isoformat()})

        return {"birthdate": birthdate, "messages": []}
    except ValueError:
        # 日期格式错误，再次中断
        birthdate_input = interrupt(
            "I couldn't understand the date format. Please provide your birthdate in YYYY-MM-DD format."
        )
        state["messages"].append(HumanMessage(birthdate_input))
        return await determine_birthdate(state, config, store)

# 构建图
agent = StateGraph(AgentState)
agent.add_node("background", background)
agent.add_node("determine_birthdate", determine_birthdate)
agent.add_node("generate_response", generate_response)

agent.set_entry_point("background")
agent.add_edge("background", "determine_birthdate")
agent.add_edge("determine_birthdate", "generate_response")
agent.add_edge("generate_response", END)

interrupt_agent = agent.compile()
```

**特点**:
- 支持人机交互中断
- 长期记忆存储用户信息
- 递归处理用户输入
- 智能信息提取和验证

## 🔄 Background Task Agent设计

### 后台任务处理
Background Task Agent展示了如何处理后台任务并实时更新状态。

```python
import asyncio
from langchain_core.messages import AIMessage
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.types import StreamWriter
from agents.bg_task_agent.task import Task

class AgentState(MessagesState, total=False):
    pass

async def bg_task(state: AgentState, writer: StreamWriter) -> AgentState:
    """执行后台任务并实时更新状态"""
    task1 = Task("Simple task 1...", writer)
    task2 = Task("Simple task 2...", writer)

    # 启动任务1
    task1.start()
    await asyncio.sleep(2)

    # 启动任务2
    task2.start()
    await asyncio.sleep(2)

    # 更新任务1状态
    task1.write_data(data={"status": "Still running..."})
    await asyncio.sleep(2)

    # 完成任务2
    task2.finish(result="error", data={"output": 42})
    await asyncio.sleep(2)

    # 完成任务1
    task1.finish(result="success", data={"output": 42})

    return {"messages": []}

# 构建图
agent = StateGraph(AgentState)
agent.add_node("model", acall_model)
agent.add_node("bg_task", bg_task)
agent.set_entry_point("bg_task")

agent.add_edge("bg_task", "model")
agent.add_edge("model", END)

bg_task_agent = agent.compile()
```

**Task类设计**:
```python
from typing import Literal
from uuid import uuid4
from langgraph.types import StreamWriter
from schema.task_data import TaskData

class Task:
    def __init__(self, task_name: str, writer: StreamWriter | None = None) -> None:
        self.name = task_name
        self.id = str(uuid4())
        self.state: Literal["new", "running", "complete"] = "new"
        self.result: Literal["success", "error"] | None = None
        self.writer = writer

    def start(self, writer: StreamWriter | None = None, data: dict = {}) -> BaseMessage:
        """启动任务"""
        self.state = "new"
        task_message = self._generate_and_dispatch_message(writer, data)
        return task_message

    def write_data(self, writer: StreamWriter | None = None, data: dict = {}) -> BaseMessage:
        """更新任务数据"""
        if self.state == "complete":
            raise ValueError("Only incomplete tasks can output data.")
        self.state = "running"
        task_message = self._generate_and_dispatch_message(writer, data)
        return task_message

    def finish(
        self,
        result: Literal["success", "error"],
        writer: StreamWriter | None = None,
        data: dict = {},
    ) -> BaseMessage:
        """完成任务"""
        self.state = "complete"
        self.result = result
        task_message = self._generate_and_dispatch_message(writer, data)
        return task_message
```

**特点**:
- 支持后台任务执行
- 实时状态更新和通知
- 任务生命周期管理
- 流式数据传输

## 📚 Knowledge Base Agent设计

### RAG检索增强生成
Knowledge Base Agent集成Amazon Bedrock Knowledge Base，提供检索增强生成功能。

```python
import logging
from typing import Any
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, MessagesState, StateGraph
from langchain_aws import BedrockRetrieve

class KnowledgeBaseState(MessagesState, total=False):
    retrieved_documents: list[dict[str, Any]]

async def retrieve_documents(state: KnowledgeBaseState, config: RunnableConfig) -> KnowledgeBaseState:
    """从知识库检索相关文档"""

    # 获取最后的人类消息作为查询
    human_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
    if not human_messages:
        return {"retrieved_documents": [], "messages": []}

    query = human_messages[-1].content

    try:
        # 初始化检索器
        retriever = get_kb_retriever()

        # 检索文档
        retrieved_docs = await retriever.ainvoke(query)

        # 创建文档摘要
        document_summaries = []
        for i, doc in enumerate(retrieved_docs, 1):
            summary = {
                "id": doc.metadata.get("id", f"doc-{i}"),
                "source": doc.metadata.get("source", "Unknown"),
                "title": doc.metadata.get("title", f"Document {i}"),
                "content": doc.page_content,
                "relevance_score": doc.metadata.get("score", 0),
            }
            document_summaries.append(summary)

        logger.info(f"Retrieved {len(document_summaries)} documents for query: {query[:50]}...")

        return {"retrieved_documents": document_summaries, "messages": []}

    except Exception as e:
        logger.error(f"Error during document retrieval: {e}")
        return {
            "retrieved_documents": [],
            "messages": [AIMessage(content=f"Sorry, I encountered an error while searching: {str(e)}")],
        }

async def generate_response(state: KnowledgeBaseState, config: RunnableConfig) -> KnowledgeBaseState:
    """基于检索到的文档生成回复"""

    retrieved_docs = state.get("retrieved_documents", [])

    if not retrieved_docs:
        return {
            "messages": [
                AIMessage(content="I couldn't find any relevant information to answer your question.")
            ]
        }

    # 构建上下文
    context_parts = []
    for doc in retrieved_docs[:5]:  # 限制使用前5个最相关的文档
        context_parts.append(f"Source: {doc['source']}\nContent: {doc['content']}\n")

    context = "\n---\n".join(context_parts)

    # 获取用户查询
    human_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
    user_query = human_messages[-1].content if human_messages else ""

    # 构建提示
    prompt = f"""Based on the following context from the knowledge base, please answer the user's question.

Context:
{context}

User Question: {user_query}

Please provide a comprehensive answer based on the retrieved information. If the context doesn't contain enough information to fully answer the question, please say so and provide what information is available."""

    # 生成回复
    model = get_model(config["configurable"].get("model", settings.DEFAULT_MODEL))
    response = await model.ainvoke([HumanMessage(content=prompt)])

    return {"messages": [response]}

def get_kb_retriever():
    """获取知识库检索器"""
    return BedrockRetrieve(
        knowledge_base_id=settings.BEDROCK_KNOWLEDGE_BASE_ID,
        region_name=settings.AWS_REGION,
        retrieval_config={"vectorSearchConfiguration": {"numberOfResults": 10}},
    )

# 构建图
kb_workflow = StateGraph(KnowledgeBaseState)
kb_workflow.add_node("retrieve", retrieve_documents)
kb_workflow.add_node("generate", generate_response)

kb_workflow.set_entry_point("retrieve")
kb_workflow.add_edge("retrieve", "generate")
kb_workflow.add_edge("generate", END)

kb_agent = kb_workflow.compile()
```

**特点**:
- 集成Amazon Bedrock Knowledge Base
- 检索增强生成(RAG)架构
- 文档相关性评分
- 上下文感知的回复生成
- 支持多种文档源

## 🎯 Agent选择指南

### 根据需求选择合适的Agent

#### 数据相关任务
- **SQL Agent**: 数据库查询、数据分析、报表生成
- **Knowledge Base Agent**: 文档检索、知识问答、信息查找

#### 研究和搜索任务
- **Research Assistant**: 网络搜索、实时信息获取、计算任务
- **Knowledge Base Agent**: 内部知识库查询、文档分析

#### 对话和交互任务
- **Simple Chatbot**: 基础对话、简单问答
- **Interrupt Agent**: 需要用户输入的交互式对话
- **Supervisor Agent**: 复杂任务的多Agent协调

#### 系统和流程任务
- **Command Agent**: 流程控制演示、条件路由
- **Background Task Agent**: 长时间运行的后台任务
- **Supervisor Agent**: 多步骤任务的协调管理

### Agent组合使用

#### 典型组合模式

1. **数据分析工作流**:
   ```
   Supervisor Agent → SQL Agent → Research Assistant
   ```
   - 监督Agent协调数据查询和外部信息补充

2. **知识问答系统**:
   ```
   Knowledge Base Agent → Research Assistant
   ```
   - 先查询内部知识库，再搜索外部信息

3. **交互式数据探索**:
   ```
   Interrupt Agent → SQL Agent
   ```
   - 通过交互收集用户需求，然后执行数据查询

## 🛠️ Agent开发最佳实践

### 记忆系统集成标准模式

#### 1. 状态定义标准
```python
class AgentState(MessagesState, total=False):
    """Agent状态定义标准模板"""
    # 基础字段
    safety: LlamaGuardOutput          # 安全检查结果
    remaining_steps: RemainingSteps   # 剩余执行步数

    # Agent特定字段
    agent_specific_data: Optional[Dict[str, Any]]

    # 记忆系统字段
    user_preferences: Optional[Dict[str, Any]]
    historical_context: Optional[str]
```

#### 2. 记忆系统集成模板
```python
async def load_agent_memory(config: RunnableConfig, store: BaseStore, agent_name: str) -> Dict[str, Any]:
    """标准记忆加载函数"""
    user_id = config["configurable"].get("user_id", "anonymous")
    namespace = (agent_name, user_id)

    try:
        preferences = await store.aget(namespace, "preferences")
        history = await store.aget(namespace, "history")

        return {
            "preferences": preferences.value if preferences else {},
            "history": history.value if history else []
        }
    except Exception as e:
        logger.error(f"Error loading {agent_name} memory: {e}")
        return {"preferences": {}, "history": []}

async def save_agent_memory(config: RunnableConfig, store: BaseStore, agent_name: str, memory_data: Dict[str, Any]):
    """标准记忆保存函数"""
    user_id = config["configurable"].get("user_id", "anonymous")
    namespace = (agent_name, user_id)

    try:
        for key, value in memory_data.items():
            await store.aput(namespace, key, value)
        logger.info(f"Saved {agent_name} memory for user {user_id}")
    except Exception as e:
        logger.error(f"Error saving {agent_name} memory: {e}")
```

#### 3. 命名空间管理原则
```python
# 标准命名空间格式: (agent_name, user_id, [optional_category])
NAMESPACE_PATTERNS = {
    "user_preferences": ("agent_name", "user_id", "preferences"),
    "interaction_history": ("agent_name", "user_id", "history"),
    "agent_specific_data": ("agent_name", "user_id", "data"),
    "shared_context": ("shared", "user_id", "context")  # 跨Agent共享
}

# 示例使用
sql_agent_namespace = ("sql_agent", user_id)
shared_namespace = ("shared", user_id)
```

### Agent状态管理统一原则

#### 1. 状态字段命名规范
```python
class StandardAgentState(MessagesState, total=False):
    # 系统级字段 - 所有Agent通用
    safety: LlamaGuardOutput
    remaining_steps: RemainingSteps

    # 功能级字段 - 特定功能Agent使用
    tool_results: List[Dict[str, Any]]      # 工具执行结果
    planning_context: Optional[str]         # 规划上下文

    # Agent级字段 - 特定Agent专用
    sql_context: Optional[str]              # SQL Agent专用
    search_results: List[Dict[str, Any]]    # Research Agent专用

    # 记忆级字段 - 记忆系统相关
    user_preferences: Optional[Dict[str, Any]]
    personalized_context: Optional[str]
```

#### 2. 状态更新模式
```python
async def update_state_safely(state: AgentState, updates: Dict[str, Any]) -> AgentState:
    """安全的状态更新函数"""
    try:
        # 验证更新字段
        valid_fields = set(AgentState.__annotations__.keys())
        invalid_fields = set(updates.keys()) - valid_fields

        if invalid_fields:
            logger.warning(f"Invalid state fields: {invalid_fields}")
            updates = {k: v for k, v in updates.items() if k in valid_fields}

        return updates
    except Exception as e:
        logger.error(f"Error updating state: {e}")
        return {}
```

### 工具调用安全实践

#### 1. 工具执行安全包装
```python
async def safe_tool_execution(tool: BaseTool, args: Dict[str, Any], context: str = "") -> Dict[str, Any]:
    """安全的工具执行包装器"""
    try:
        # 参数验证
        if hasattr(tool, 'args_schema') and tool.args_schema:
            validated_args = tool.args_schema(**args)
            result = await tool.ainvoke(validated_args.dict())
        else:
            result = await tool.ainvoke(args)

        return {
            "success": True,
            "result": result,
            "tool_name": tool.name,
            "context": context
        }
    except ValidationError as e:
        logger.error(f"Tool {tool.name} validation error: {e}")
        return {
            "success": False,
            "error": f"Parameter validation failed: {e}",
            "tool_name": tool.name
        }
    except Exception as e:
        logger.error(f"Tool {tool.name} execution error: {e}")
        return {
            "success": False,
            "error": str(e),
            "tool_name": tool.name
        }
```

#### 2. 工具权限控制
```python
def check_tool_permissions(tool_name: str, user_id: str, context: Dict[str, Any]) -> bool:
    """检查工具使用权限"""
    # 定义工具权限级别
    TOOL_PERMISSIONS = {
        "read_only": ["get_database_schema", "web_search"],
        "data_access": ["execute_sql_query", "database_search"],
        "admin_only": ["analyze_database_schema", "system_commands"]
    }

    # 检查用户权限级别
    user_level = context.get("user_level", "read_only")

    for level, tools in TOOL_PERMISSIONS.items():
        if tool_name in tools:
            return user_level in ["admin_only"] or level == user_level or level == "read_only"

    return False
```

### 错误处理和日志记录规范

#### 1. 结构化错误处理
```python
class AgentError(Exception):
    """Agent专用异常类"""
    def __init__(self, message: str, error_type: str, context: Dict[str, Any] = None):
        self.message = message
        self.error_type = error_type
        self.context = context or {}
        super().__init__(self.message)

async def handle_agent_error(error: Exception, state: AgentState, context: str = "") -> AgentState:
    """统一的Agent错误处理"""
    if isinstance(error, AgentError):
        error_message = f"Agent Error ({error.error_type}): {error.message}"
        logger.error(f"{context} - {error_message}", extra=error.context)
    else:
        error_message = f"Unexpected error: {str(error)}"
        logger.exception(f"{context} - {error_message}")

    return {
        "messages": [AIMessage(content=f"I encountered an error: {error_message}. Please try again.")]
    }
```

#### 2. 结构化日志记录
```python
import structlog

# 配置结构化日志
logger = structlog.get_logger()

async def log_agent_execution(agent_name: str, user_id: str, action: str, **kwargs):
    """记录Agent执行日志"""
    logger.info(
        "agent_execution",
        agent_name=agent_name,
        user_id=user_id,
        action=action,
        timestamp=datetime.utcnow().isoformat(),
        **kwargs
    )

# 使用示例
await log_agent_execution(
    agent_name="sql_agent",
    user_id=user_id,
    action="query_execution",
    query_type="SELECT",
    execution_time=0.5,
    success=True
)
```

### Agent间数据隔离设计原则

#### 1. 命名空间隔离策略
```python
class NamespaceManager:
    """命名空间管理器"""

    @staticmethod
    def get_agent_namespace(agent_name: str, user_id: str) -> Tuple[str, ...]:
        """获取Agent专用命名空间"""
        return (agent_name, user_id)

    @staticmethod
    def get_shared_namespace(user_id: str, category: str = "shared") -> Tuple[str, ...]:
        """获取共享命名空间"""
        return ("shared", user_id, category)

    @staticmethod
    def get_global_namespace(category: str) -> Tuple[str, ...]:
        """获取全局命名空间"""
        return ("global", category)

# 使用示例
sql_namespace = NamespaceManager.get_agent_namespace("sql_agent", user_id)
shared_namespace = NamespaceManager.get_shared_namespace(user_id, "preferences")
```

#### 2. 数据访问控制
```python
async def secure_data_access(store: BaseStore, namespace: Tuple[str, ...], key: str, user_id: str) -> Optional[Any]:
    """安全的数据访问控制"""
    # 检查命名空间权限
    if len(namespace) >= 2 and namespace[1] != user_id and namespace[0] != "global":
        logger.warning(f"Unauthorized access attempt: {user_id} -> {namespace}")
        return None

    try:
        result = await store.aget(namespace, key)
        return result.value if result else None
    except Exception as e:
        logger.error(f"Data access error: {e}")
        return None
```

### 开发新Agent的指导原则

#### 1. 确定Agent复杂度
- **简单Agent**: 使用`@entrypoint()`装饰器
- **中等复杂度**: 使用标准StateGraph + 工具集成
- **复杂Agent**: 使用多阶段工作流程 + 自定义状态

#### 2. 选择合适的状态管理
```python
# 基础状态 - 只需要消息历史
class AgentState(MessagesState, total=False):
    pass

# 扩展状态 - 需要额外信息
class AgentState(MessagesState, total=False):
    custom_field: str
    processing_status: dict
```

#### 3. 工具集成模式
```python
# 简单工具集成
tools = [tool1, tool2]
model_with_tools = model.bind_tools(tools)

# 复杂工具集成
async def tool_node(state: AgentState) -> AgentState:
    # 自定义工具执行逻辑
    pass
```

#### 4. 错误处理和恢复
```python
async def safe_node(state: AgentState) -> AgentState:
    try:
        # 节点逻辑
        pass
    except Exception as e:
        return await handle_agent_error(e, state, "node_execution")
```

---

*本文档详细描述了所有Agent的实现机制和设计模式，为Agent开发和选择提供全面指导。*

## 🔧 工具系统设计

### 工具定义标准
```python
from langchain_core.tools import tool

@tool
def calculator(expression: str) -> str:
    """计算数学表达式
    
    Args:
        expression: 要计算的数学表达式，如 "2 + 3 * 4"
    
    Returns:
        计算结果的字符串表示
    """
    try:
        # 安全的数学表达式计算
        allowed_names = {
            k: v for k, v in math.__dict__.items() 
            if not k.startswith("__")
        }
        allowed_names.update({"abs": abs, "round": round})
        
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"
```

### 工具安全执行
```python
def safe_tool_execution(tool: BaseTool, args: dict) -> str:
    """安全执行工具"""
    try:
        # 参数验证
        if hasattr(tool, 'args_schema') and tool.args_schema:
            validated_args = tool.args_schema(**args)
            result = tool.invoke(validated_args.dict())
        else:
            result = tool.invoke(args)
        
        return str(result)
    except ValidationError as e:
        return f"参数验证失败: {e}"
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return f"工具执行失败: {e}"
```

## 📊 状态管理

### 会话状态
```python
class SQLAgentState(MessagesState, total=False):
    """SQL Agent状态定义"""
    # 继承基础消息状态
    messages: list[BaseMessage]
    
    # 扩展状态字段
    safety: LlamaGuardOutput          # 安全检查结果
    remaining_steps: RemainingSteps   # 剩余步数
    planning_result: dict             # 规划结果
    database_context: dict            # 数据库上下文
    tool_results: list[dict]          # 工具执行结果
    user_preferences: dict            # 用户偏好设置
```

### 长期记忆
```python
async def store_user_preference(state: SQLAgentState, config: RunnableConfig):
    """存储用户偏好到长期记忆"""
    store = config.get("store")
    if store:
        user_id = config["configurable"]["user_id"]
        namespace = ("user_preferences", user_id)
        
        preferences = {
            "preferred_query_format": "table",
            "show_query_details": True,
            "last_interaction": datetime.utcnow().isoformat()
        }
        
        await store.aput(namespace, "sql_preferences", preferences)
```

## 🔄 错误处理与恢复

### 异常处理机制
```python
async def handle_agent_error(state: AgentState, error: Exception) -> AgentState:
    """Agent错误处理"""
    logger.error(f"Agent execution error: {error}")
    
    error_message = AIMessage(
        content=f"抱歉，处理您的请求时遇到了问题: {str(error)}。请稍后重试或换个方式提问。"
    )
    
    return {"messages": [error_message]}

# 在Agent中使用错误处理
try:
    result = await agent.ainvoke(input_data, config)
except Exception as e:
    result = await handle_agent_error(state, e)
```

---

*本文档详细描述了各种Agent的实现机制和设计模式，为Agent开发提供技术指导。*

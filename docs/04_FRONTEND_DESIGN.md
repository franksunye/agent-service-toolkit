# 🎨 前端界面详细设计文档

## 🎯 概述

本文档详细描述Agent Service Toolkit前端界面的技术实现，基于Streamlit框架构建的Web应用，提供直观的聊天界面和丰富的交互体验。

## 🏗️ Streamlit应用架构

### 应用入口点

```python
# src/streamlit_app.py
async def main() -> None:
    """主应用函数"""
    st.set_page_config(
        page_title="Agent Service Toolkit",
        page_icon="🧰",
        menu_items={},
    )
    
    # 隐藏Streamlit默认UI元素
    st.html("""
        <style>
        [data-testid="stStatusWidget"] {
            visibility: hidden;
            height: 0%;
            position: fixed;
        }
        </style>
    """)
    
    # 设置工具栏模式
    if st.get_option("client.toolbarMode") != "minimal":
        st.set_option("client.toolbarMode", "minimal")
        await asyncio.sleep(0.1)
        st.rerun()
```

### 核心组件设计

#### 1. 用户身份管理
```python
def get_or_create_user_id() -> str:
    """获取或创建用户ID"""
    # 检查session state
    if USER_ID_COOKIE in st.session_state:
        return st.session_state[USER_ID_COOKIE]
    
    # 检查URL参数
    if USER_ID_COOKIE in st.query_params:
        user_id = st.query_params[USER_ID_COOKIE]
        st.session_state[USER_ID_COOKIE] = user_id
        return user_id
    
    # 生成新的用户ID
    user_id = str(uuid.uuid4())
    st.session_state[USER_ID_COOKIE] = user_id
    st.query_params[USER_ID_COOKIE] = user_id
    return user_id
```

#### 2. Agent客户端连接
```python
def initialize_agent_client() -> AgentClient:
    """初始化Agent客户端"""
    if "agent_client" not in st.session_state:
        load_dotenv()
        agent_url = os.getenv("AGENT_URL")
        if not agent_url:
            host = os.getenv("HOST", "0.0.0.0")
            port = os.getenv("PORT", 8080)
            agent_url = f"http://{host}:{port}"
        
        try:
            with st.spinner("Connecting to agent service..."):
                st.session_state.agent_client = AgentClient(base_url=agent_url)
        except AgentClientError as e:
            st.error(f"Error connecting to agent service: {e}")
            st.stop()
    
    return st.session_state.agent_client
```

## 🎛️ 侧边栏设计

### 应用信息区域
```python
with st.sidebar:
    st.header(f"{APP_ICON} {APP_TITLE}")
    st.write("Full toolkit for running an AI agent service built with LangGraph, FastAPI and Streamlit")
```

### 功能按钮区域
```python
# 新建聊天按钮
if st.button(":material/chat: New Chat", use_container_width=True):
    st.session_state.messages = []
    st.session_state.thread_id = str(uuid.uuid4())
    st.rerun()

# 设置弹窗
with st.popover(":material/settings: Settings", use_container_width=True):
    model_idx = agent_client.info.models.index(agent_client.info.default_model)
    model = st.selectbox("LLM to use", options=agent_client.info.models, index=model_idx)
    
    agent_list = [a.key for a in agent_client.info.agents]
    agent_idx = agent_list.index(agent_client.info.default_agent)
    agent_client.agent = st.selectbox(
        "Agent to use",
        options=agent_list,
        index=agent_idx,
    )
    
    use_streaming = st.toggle("Stream results", value=True)
    st.text_input("User ID (read-only)", value=user_id, disabled=True)
```

### 分享功能
```python
@st.dialog("Share/resume chat")
def share_chat_dialog() -> None:
    """分享聊天对话框"""
    session = st.runtime.get_instance()._session_mgr.list_active_sessions()[0]
    st_base_url = urllib.parse.urlunparse([
        session.client.request.protocol, 
        session.client.request.host, 
        "", "", "", ""
    ])
    
    # 构建分享URL
    chat_url = f"{st_base_url}?thread_id={st.session_state.thread_id}&{USER_ID_COOKIE}={user_id}"
    st.markdown(f"**Chat URL:**\n```text\n{chat_url}\n```")
    st.info("Copy the above URL to share or revisit this chat")

if st.button(":material/upload: Share/resume chat", use_container_width=True):
    share_chat_dialog()
```

## 💬 聊天界面设计

### 欢迎消息系统
```python
def display_welcome_message(agent_type: str):
    """显示Agent特定的欢迎消息"""
    welcome_messages = {
        "sql-agent": """Hello! I'm an intelligent SQL database assistant with access to your SQLite database. I can help you with:

• **Database Exploration** - View table structures and relationships
• **Query Generation** - Convert your questions into SQL queries  
• **Data Analysis** - Execute queries and provide business insights
• **Schema Optimization** - Analyze and recommend database improvements

**Example queries to try:**
- "What tables are in the database?"
- "Show me all users in the Engineering department"
- "What are the total sales by user?"
- "Analyze the database schema for optimization opportunities"

Ask me anything about your database!""",
        
        "chatbot": "Hello! I'm a simple chatbot. Ask me anything!",
        
        "research-assistant": "Hello! I'm an AI-powered research assistant with web search and a calculator. Ask me anything!",
        
        "rag-assistant": """Hello! I'm an AI-powered Company Policy & HR assistant with access to AcmeTech's Employee Handbook.
        I can help you find information about benefits, remote work, time-off policies, company values, and more. Ask me anything!""",
        
        "_default": "Hello! I'm an AI agent. Ask me anything!"
    }
    
    welcome = welcome_messages.get(agent_type, welcome_messages["_default"])
    with st.chat_message("ai"):
        st.write(welcome)
```

### 消息渲染系统
```python
async def draw_messages(
    messages_agen: AsyncGenerator[ChatMessage | str, None],
    is_new: bool = False,
) -> None:
    """渲染聊天消息"""
    last_message_type = None
    st.session_state.last_message = None
    
    # 流式内容占位符
    streaming_content = ""
    streaming_placeholder = None
    
    while msg := await anext(messages_agen, None):
        # 处理流式token
        if isinstance(msg, str):
            if not streaming_placeholder:
                if last_message_type != "ai":
                    last_message_type = "ai"
                    st.session_state.last_message = st.chat_message("ai")
                with st.session_state.last_message:
                    streaming_placeholder = st.empty()
            
            streaming_content += msg
            streaming_placeholder.write(streaming_content)
            continue
        
        # 处理完整消息
        if not isinstance(msg, ChatMessage):
            st.error(f"Unexpected message type: {type(msg)}")
            st.stop()
        
        match msg.type:
            case "human":
                last_message_type = "human"
                st.chat_message("human").write(msg.content)
            
            case "ai":
                if is_new:
                    st.session_state.messages.append(msg)
                
                if last_message_type != "ai":
                    last_message_type = "ai"
                    st.session_state.last_message = st.chat_message("ai")
                
                with st.session_state.last_message:
                    if msg.content:
                        if streaming_placeholder:
                            streaming_placeholder.write(msg.content)
                            streaming_content = ""
                            streaming_placeholder = None
                        else:
                            st.write(msg.content)
                    
                    # 处理工具调用
                    if msg.tool_calls:
                        await handle_tool_calls(msg.tool_calls, messages_agen, is_new)
```

### 工具调用可视化
```python
async def handle_tool_calls(tool_calls: list, messages_agen: AsyncGenerator, is_new: bool):
    """处理和显示工具调用"""
    call_results = {}
    
    # 为每个工具调用创建状态容器
    for tool_call in tool_calls:
        status = st.status(
            f"""Tool Call: {tool_call["name"]}""",
            state="running" if is_new else "complete",
        )
        call_results[tool_call["id"]] = status
        status.write("Input:")
        status.write(tool_call["args"])
    
    # 等待工具执行结果
    for _ in range(len(call_results)):
        tool_result: ChatMessage = await anext(messages_agen)
        
        if tool_result.type != "tool":
            st.error(f"Unexpected ChatMessage type: {tool_result.type}")
            st.stop()
        
        if is_new:
            st.session_state.messages.append(tool_result)
        
        if tool_result.tool_call_id:
            status = call_results[tool_result.tool_call_id]
        
        status.write("Output:")
        with status:
            format_sql_result(tool_result.content)  # 特殊格式化SQL结果
        
        status.update(state="complete")
```

## 🎨 SQL结果格式化

### 智能结果显示
```python
def format_sql_result(content: str) -> None:
    """格式化和显示SQL查询结果"""
    try:
        result_data = json.loads(content)
        
        if isinstance(result_data, dict) and "success" in result_data:
            if result_data.get("success"):
                # 成功的查询结果
                if "results" in result_data and result_data["results"]:
                    st.write("**Query Results:**")
                    
                    results = result_data["results"]
                    if isinstance(results, list) and len(results) > 0:
                        if isinstance(results[0], dict):
                            # 表格数据
                            import pandas as pd
                            df = pd.DataFrame(results)
                            st.dataframe(df, use_container_width=True, hide_index=True)
                            
                            # 显示统计信息
                            col1, col2 = st.columns(2)
                            with col1:
                                st.caption(f"📊 **{len(results)}** rows returned")
                            with col2:
                                st.caption(f"📋 **{len(df.columns)}** columns")
                        else:
                            # 简单列表结果
                            for i, row in enumerate(results[:10]):
                                st.write(f"{i+1}. {row}")
                            if len(results) > 10:
                                st.caption(f"... and {len(results) - 10} more rows")
                
                # 显示查询元数据
                if "query" in result_data:
                    with st.expander("🔍 Query Details"):
                        st.code(result_data["query"], language="sql")
                        
                        if "row_count" in result_data or "query_type" in result_data:
                            col1, col2 = st.columns(2)
                            if "row_count" in result_data:
                                with col1:
                                    st.metric("Rows Returned", result_data["row_count"])
                            if "query_type" in result_data:
                                with col2:
                                    st.metric("Query Type", result_data["query_type"])
            
            else:
                # 错误结果
                error_msg = result_data.get('error', 'Unknown error')
                st.error(f"❌ **Query Failed**: {error_msg}")
                
                if "query" in result_data:
                    with st.expander("🔍 View Failed Query"):
                        st.code(result_data["query"], language="sql")
                
                if "error_type" in result_data:
                    st.caption(f"Error Type: {result_data['error_type']}")
        else:
            # 非SQL结果，正常显示
            st.write(content)
    
    except (json.JSONDecodeError, ImportError):
        # 非JSON或pandas不可用，显示纯文本
        st.write(content)
```

## 🔄 用户交互流程

### 消息输入处理
```python
if user_input := st.chat_input():
    """处理用户输入"""
    # 添加用户消息到历史
    messages.append(ChatMessage(type="human", content=user_input))
    st.chat_message("human").write(user_input)
    
    try:
        if use_streaming:
            # 流式响应
            stream = agent_client.astream(
                message=user_input,
                model=model,
                thread_id=st.session_state.thread_id,
                user_id=user_id,
            )
            await draw_messages(stream, is_new=True)
        else:
            # 非流式响应
            response = await agent_client.ainvoke(
                message=user_input,
                model=model,
                thread_id=st.session_state.thread_id,
                user_id=user_id,
            )
            messages.append(response)
            st.chat_message("ai").write(response.content)
        
        st.rerun()  # 清理过期容器
    except AgentClientError as e:
        st.error(f"Error generating response: {e}")
        st.stop()
```

### 反馈系统
```python
async def handle_feedback() -> None:
    """处理用户反馈"""
    if "last_feedback" not in st.session_state:
        st.session_state.last_feedback = (None, None)
    
    latest_run_id = st.session_state.messages[-1].run_id
    feedback = st.feedback("stars", key=latest_run_id)
    
    if feedback is not None and (latest_run_id, feedback) != st.session_state.last_feedback:
        # 标准化反馈分数 (0-1)
        normalized_score = (feedback + 1) / 5.0
        
        agent_client: AgentClient = st.session_state.agent_client
        try:
            await agent_client.acreate_feedback(
                run_id=latest_run_id,
                key="human-feedback-stars",
                score=normalized_score,
                kwargs={"comment": "In-line human feedback"},
            )
        except AgentClientError as e:
            st.error(f"Error recording feedback: {e}")
            st.stop()
        
        st.session_state.last_feedback = (latest_run_id, feedback)
        st.toast("Feedback recorded", icon=":material/reviews:")
```

## 📱 响应式设计

### 移动端适配
```python
# CSS样式优化
st.html("""
<style>
/* 移动端优化 */
@media (max-width: 768px) {
    .stChatMessage {
        padding: 0.5rem;
    }
    
    .stDataFrame {
        font-size: 0.8rem;
    }
    
    .stExpander {
        margin: 0.25rem 0;
    }
}

/* 深色模式支持 */
@media (prefers-color-scheme: dark) {
    .stChatMessage {
        background-color: #1e1e1e;
        border: 1px solid #333;
    }
}
</style>
""")
```

### 性能优化
```python
# 消息历史限制
MAX_MESSAGES = 100

def trim_message_history(messages: list[ChatMessage]) -> list[ChatMessage]:
    """限制消息历史长度"""
    if len(messages) > MAX_MESSAGES:
        # 保留最近的消息
        return messages[-MAX_MESSAGES:]
    return messages

# 缓存优化
@st.cache_data(ttl=300)  # 5分钟缓存
def get_agent_info():
    """缓存Agent信息"""
    return agent_client.info
```

---

*本文档详细描述了前端界面的设计和实现，为UI/UX优化提供技术参考。*

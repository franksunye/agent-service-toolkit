"""
SQL Agent - Intelligent Database Assistant
Implements 4-phase workflow: Planning → Tool Selection → Execution → Reflection
Based on PDME-PoC architecture adapted for LangGraph framework
"""
import logging
from datetime import datetime
from typing import Dict, List, Any, Literal, Optional
import json

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig, RunnableLambda, RunnableSerializable
from langchain_core.tools import BaseTool, tool
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.managed import RemainingSteps
from langgraph.prebuilt import ToolNode
from langgraph.store.base import BaseStore

from agents.llama_guard import LlamaGuard, LlamaGuardOutput, SafetyAssessment
from core import get_model, settings
from core.deepseek_client import get_deepseek_client
from core.database import get_database_client

logger = logging.getLogger(__name__)


# Memory system utilities
async def load_user_memory(config: RunnableConfig, store: BaseStore) -> Dict[str, Any]:
    """Load user preferences and query history from long-term memory"""
    user_id = config["configurable"].get("user_id", "anonymous")
    namespace = ("sql_agent", user_id)

    try:
        # Load user preferences
        preferences = await store.aget(namespace, "preferences")
        query_history = await store.aget(namespace, "query_history")
        query_patterns = await store.aget(namespace, "query_patterns")

        user_memory = {
            "preferences": preferences.value if preferences else {},
            "query_history": query_history.value if query_history else [],
            "query_patterns": query_patterns.value if query_patterns else []
        }

        logger.info(f"📚 Loaded user memory for {user_id}: {len(user_memory['query_history'])} queries")
        return user_memory

    except Exception as e:
        logger.error(f"❌ Error loading user memory: {e}")
        return {"preferences": {}, "query_history": [], "query_patterns": []}


async def save_user_memory(config: RunnableConfig, store: BaseStore, memory_data: Dict[str, Any]):
    """Save user preferences and query history to long-term memory"""
    user_id = config["configurable"].get("user_id", "anonymous")
    namespace = ("sql_agent", user_id)

    try:
        # Save preferences
        if "preferences" in memory_data:
            await store.aput(namespace, "preferences", memory_data["preferences"])

        # Save query history (keep last 50 queries)
        if "query_history" in memory_data:
            query_history = memory_data["query_history"][-50:]  # Limit history size
            await store.aput(namespace, "query_history", query_history)

        # Save query patterns
        if "query_patterns" in memory_data:
            await store.aput(namespace, "query_patterns", memory_data["query_patterns"])

        logger.info(f"💾 Saved user memory for {user_id}")

    except Exception as e:
        logger.error(f"❌ Error saving user memory: {e}")


def analyze_query_patterns(query_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Analyze user query patterns to identify common themes and preferences"""
    patterns = []

    if not query_history:
        return patterns

    # Analyze table usage frequency
    table_usage = {}
    query_types = {}

    for query_record in query_history:
        query = query_record.get("query", "").lower()

        # Extract table names (simple pattern matching)
        import re
        table_matches = re.findall(r'from\s+(\w+)', query)
        for table in table_matches:
            table_usage[table] = table_usage.get(table, 0) + 1

        # Categorize query types
        if "select" in query:
            if "group by" in query or "count" in query or "sum" in query:
                query_types["analytics"] = query_types.get("analytics", 0) + 1
            else:
                query_types["lookup"] = query_types.get("lookup", 0) + 1
        elif "insert" in query or "update" in query or "delete" in query:
            query_types["modification"] = query_types.get("modification", 0) + 1

    # Generate patterns
    if table_usage:
        most_used_table = max(table_usage, key=table_usage.get)
        patterns.append({
            "type": "frequent_table",
            "table": most_used_table,
            "usage_count": table_usage[most_used_table],
            "description": f"Frequently queries {most_used_table} table"
        })

    if query_types:
        most_common_type = max(query_types, key=query_types.get)
        patterns.append({
            "type": "query_preference",
            "preference": most_common_type,
            "count": query_types[most_common_type],
            "description": f"Prefers {most_common_type} queries"
        })

    return patterns


class SQLAgentState(MessagesState, total=False):
    """
    SQL Agent state extending MessagesState with SQL-specific fields
    """
    safety: LlamaGuardOutput
    remaining_steps: RemainingSteps

    # SQL Agent specific state
    planning_result: Optional[Dict[str, Any]]
    tool_execution_results: List[Dict[str, Any]]
    database_context: Optional[str]
    sql_query_history: List[str]
    analysis_insights: Optional[str]

    # Memory system integration
    user_preferences: Optional[Dict[str, Any]]
    query_patterns: List[Dict[str, Any]]
    personalized_context: Optional[str]


# SQL Tools Implementation
@tool
def get_database_schema() -> str:
    """
    Get the current database schema information including all tables and columns.
    This tool provides a complete overview of the database structure.
    """
    logger.info("🔍 Executing get_database_schema tool")
    try:
        db_client = get_database_client()
        logger.info(f"📊 Database client initialized: {db_client.db_path}")
        schema_info = db_client.get_schema_info()
        logger.info(f"✅ Schema info retrieved: {len(schema_info.get('tables', {}))} tables found")

        if "error" in schema_info:
            logger.error(f"❌ Error retrieving schema: {schema_info['error']}")
            return f"Error retrieving schema: {schema_info['error']}"

        # Format schema information for display
        result = f"Database Schema ({schema_info['database_type']}):\n"
        result += f"Location: {schema_info['database_path']}\n\n"

        for table_name, table_info in schema_info["tables"].items():
            result += f"Table: {table_name} ({table_info['row_count']} rows)\n"
            for column in table_info["columns"]:
                pk_marker = " PRIMARY KEY" if column["primary_key"] else ""
                null_marker = " NOT NULL" if column["not_null"] else ""
                default_marker = f" DEFAULT {column['default_value']}" if column["default_value"] else ""
                result += f"  - {column['name']} {column['type']}{pk_marker}{null_marker}{default_marker}\n"
            result += "\n"

        logger.info(f"📋 Schema formatted successfully, {len(result)} characters")
        return result

    except Exception as e:
        logger.error(f"❌ Error accessing database schema: {str(e)}")
        return f"Error accessing database schema: {str(e)}"


@tool
def execute_sql_query(sql_query: str, user_request: str = "") -> str:
    """
    Execute a SQL query safely and return the results.

    Args:
        sql_query: The SQL query to execute
        user_request: The original user request for context

    Returns:
        JSON string containing query results and metadata
    """
    try:
        db_client = get_database_client()
        result = db_client.execute_query(sql_query)

        # Add user request context
        result["user_request"] = user_request
        result["timestamp"] = datetime.now().isoformat()

        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "error_type": "EXECUTION_ERROR",
            "query": sql_query,
            "user_request": user_request,
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_result, indent=2)


@tool
def analyze_query_results(query_result: str, context: str = "") -> str:
    """
    Analyze query results and provide business insights and recommendations.
    
    Args:
        query_result: JSON string of query results
        context: Additional context about the analysis purpose
    
    Returns:
        Analysis insights and recommendations
    """
    try:
        # Parse the query result to validate it's proper JSON
        result_data = json.loads(query_result)

        # Check if the query was successful
        if not result_data.get("success", False):
            return f"Cannot analyze failed query: {result_data.get('error', 'Unknown error')}"

        # Use DeepSeek for intelligent analysis
        client = get_deepseek_client()

        analysis_prompt = f"""
        Analyze the following SQL query results and provide business insights:

        Query Results: {query_result}
        Context: {context}

        Please provide:
        1. Key findings from the data
        2. Business insights and patterns
        3. Recommendations for action
        4. Any data quality observations
        5. Statistical summary if applicable

        Keep the analysis concise but valuable.
        """

        messages = [
            HumanMessage(content=analysis_prompt)
        ]

        response = client.chat_completion(messages, temperature=0.3)
        return response.content

    except json.JSONDecodeError:
        return f"Invalid query result format: {query_result[:200]}..."
    except Exception as e:
        return f"Analysis failed: {str(e)}"


@tool
def analyze_database_schema(schema_info: str = "") -> str:
    """
    Analyze database schema and provide optimization recommendations.

    Args:
        schema_info: Optional database schema information (if empty, will fetch current schema)

    Returns:
        Schema analysis and optimization recommendations
    """
    try:
        # If no schema info provided, get current schema
        if not schema_info:
            schema_info = get_database_schema()

        client = get_deepseek_client()

        analysis_prompt = f"""
        Analyze the following database schema and provide recommendations:

        Schema: {schema_info}

        Please evaluate:
        1. Schema design quality and best practices
        2. Potential performance issues and bottlenecks
        3. Missing indexes or constraints that should be added
        4. Normalization opportunities and data redundancy
        5. Security considerations and vulnerabilities
        6. Data type optimization suggestions
        7. Relationship integrity and foreign key usage

        Provide specific, actionable recommendations with examples where appropriate.
        """

        messages = [
            HumanMessage(content=analysis_prompt)
        ]

        response = client.chat_completion(messages, temperature=0.3)
        return response.content

    except Exception as e:
        return f"Schema analysis failed: {str(e)}"


@tool
def generate_sql_query(user_request: str, schema_context: str = "") -> str:
    """
    Generate a SQL query based on user request and database schema.

    Args:
        user_request: Natural language description of what the user wants
        schema_context: Optional database schema context (if empty, will fetch current schema)

    Returns:
        Generated SQL query with explanation
    """
    try:
        # If no schema context provided, get current schema
        if not schema_context:
            schema_context = get_database_schema()

        client = get_deepseek_client()

        query_prompt = f"""
        Generate a SQL query based on the user request and database schema.

        Database Schema:
        {schema_context}

        User Request: {user_request}

        Please provide:
        1. A safe, efficient SQL query that fulfills the request
        2. Brief explanation of what the query does
        3. Any assumptions made
        4. Potential limitations or considerations

        Only generate SELECT, INSERT, UPDATE, or CREATE TABLE queries.
        Use proper SQL syntax and best practices.
        """

        messages = [
            HumanMessage(content=query_prompt)
        ]

        response = client.chat_completion(messages, temperature=0.2)
        return response.content

    except Exception as e:
        return f"Query generation failed: {str(e)}"


# Define available tools
sql_tools = [
    get_database_schema,
    execute_sql_query,
    analyze_query_results,
    analyze_database_schema,
    generate_sql_query
]

# Create tool node
tool_node = ToolNode(sql_tools)


def wrap_model(model: BaseChatModel) -> RunnableSerializable[SQLAgentState, AIMessage]:
    """Wrap model to work with SQL Agent state"""
    preprocessor = RunnableLambda(
        lambda state: state["messages"],
        name="StateModifier",
    )
    return preprocessor | model


async def planning_phase(state: SQLAgentState, config: RunnableConfig, store: BaseStore) -> SQLAgentState:
    """
    Phase 1: Planning - Analyze user intent and plan tool usage
    This is the core intelligence of the SQL Agent
    """
    logger.info("🚀 Starting planning phase")
    messages = state["messages"]
    last_message = messages[-1] if messages else None

    if not last_message:
        logger.warning("❌ No user input received in planning phase")
        return {"messages": [AIMessage(content="No user input received.")]}

    logger.info(f"📝 User request: {last_message.content}")

    # Load user memory for personalized context
    logger.info("📚 Loading user memory for personalized context")
    user_memory = await load_user_memory(config, store)

    # Get database context
    logger.info("🔍 Getting database schema for context")
    schema_info = get_database_schema.invoke({})
    logger.info(f"📊 Schema info retrieved: {len(schema_info)} characters")

    # Build personalized context
    personalized_context = ""
    if user_memory["query_history"]:
        recent_queries = user_memory["query_history"][-5:]  # Last 5 queries
        personalized_context += f"\nRecent user queries: {[q.get('description', '') for q in recent_queries]}"

    if user_memory["query_patterns"]:
        patterns = user_memory["query_patterns"]
        personalized_context += f"\nUser preferences: {[p.get('description', '') for p in patterns]}"

    # Create planning prompt with personalized context
    planning_prompt = f"""
    You are an intelligent SQL database assistant. You MUST use the available tools to answer user questions.

    Available tools:
    1. get_database_schema - Get database structure information
    2. generate_sql_query - Generate SQL queries from natural language
    3. execute_sql_query - Execute SQL queries safely
    4. analyze_query_results - Analyze query results for insights
    5. analyze_database_schema - Analyze database design and optimization

    Current database schema:
    {schema_info}

    {personalized_context}

    User request: {last_message.content}

    For the user's request "{last_message.content}", you should:
    1. If they're asking about tables/schema: Use get_database_schema
    2. If they need data queried: Use execute_sql_query with appropriate SQL
    3. If they need analysis: Use analyze_query_results or analyze_database_schema

    Consider the user's previous queries and preferences when planning your approach.

    You MUST call the appropriate tools. Do not just provide a text response.
    """

    # Get model and make planning decision
    model_name = config["configurable"].get("model", settings.DEFAULT_MODEL)
    logger.info(f"🤖 Using model: {model_name}")

    model = get_model(model_name)
    model_with_tools = model.bind_tools(sql_tools)
    logger.info(f"🔧 Model bound with {len(sql_tools)} tools")

    planning_messages = [
        SystemMessage(content=planning_prompt),
        last_message
    ]

    logger.info("💭 Invoking model for planning decision")
    response = await model_with_tools.ainvoke(planning_messages, config)

    # Debug the response
    logger.info(f"📤 Model response type: {type(response)}")
    logger.info(f"📤 Model response content: {response.content[:200]}...")
    logger.info(f"📤 Has tool_calls attribute: {hasattr(response, 'tool_calls')}")

    if hasattr(response, 'tool_calls'):
        logger.info(f"🔧 Tool calls: {response.tool_calls}")
        if response.tool_calls:
            logger.info(f"✅ {len(response.tool_calls)} tool calls generated")
        else:
            logger.warning("⚠️ tool_calls attribute exists but is empty")
    else:
        logger.error("❌ Response has no tool_calls attribute")

    # Store planning result in state
    planning_result = {
        "planned_tools": response.tool_calls if hasattr(response, 'tool_calls') else [],
        "reasoning": response.content
    }

    logger.info(f"📋 Planning result: {planning_result}")

    return {
        "messages": [response],
        "planning_result": planning_result,
        "database_context": schema_info,
        "user_preferences": user_memory["preferences"],
        "query_patterns": user_memory["query_patterns"],
        "personalized_context": personalized_context
    }


async def should_use_tools(state: SQLAgentState) -> Literal["tools", "reflection"]:
    """Determine if tools should be executed or move to reflection"""
    logger.info("🤔 Determining whether to use tools or go to reflection")

    last_message = state["messages"][-1]
    logger.info(f"📨 Last message type: {type(last_message)}")
    logger.info(f"📨 Last message content: {last_message.content[:100]}...")

    has_tool_calls_attr = hasattr(last_message, 'tool_calls')
    logger.info(f"🔧 Has tool_calls attribute: {has_tool_calls_attr}")

    if has_tool_calls_attr:
        tool_calls = last_message.tool_calls
        logger.info(f"🔧 Tool calls: {tool_calls}")
        logger.info(f"🔧 Tool calls length: {len(tool_calls) if tool_calls else 0}")

        if tool_calls:
            logger.info("✅ Going to tools node")
            return "tools"
        else:
            logger.info("⚠️ No tool calls found, going to reflection")
            return "reflection"
    else:
        logger.info("❌ No tool_calls attribute, going to reflection")
        return "reflection"


async def reflection_phase(state: SQLAgentState, config: RunnableConfig, store: BaseStore) -> SQLAgentState:
    """
    Phase 4: Reflection - Synthesize results and generate final response
    """
    messages = state["messages"]
    tool_results = state.get("tool_execution_results", [])
    
    # Create reflection prompt
    reflection_prompt = f"""
    Based on the tool execution results, provide a comprehensive response to the user's request.
    
    Tool Results Summary:
    {json.dumps(tool_results, indent=2) if tool_results else "No tool results available"}
    
    Provide:
    1. Direct answer to the user's question
    2. Key insights and findings
    3. Relevant data interpretation
    4. Actionable recommendations if applicable
    
    Make the response clear, valuable, and easy to understand.
    """
    
    model = get_model(config["configurable"].get("model", settings.DEFAULT_MODEL))
    
    reflection_messages = [
        SystemMessage(content=reflection_prompt),
        *messages
    ]
    
    response = await model.ainvoke(reflection_messages, config)

    # Save query to user memory
    await save_query_to_memory(state, config, store)

    return {"messages": [response]}


async def save_query_to_memory(state: SQLAgentState, config: RunnableConfig, store: BaseStore):
    """Save the current query and results to user memory"""
    try:
        # Extract query information from the conversation
        messages = state["messages"]
        user_query = None
        executed_queries = []

        # Find the original user query
        for msg in messages:
            if hasattr(msg, 'type') and msg.type == 'human':
                user_query = msg.content
                break

        # Extract executed SQL queries from tool results
        tool_results = state.get("tool_execution_results", [])
        for result in tool_results:
            if "query" in str(result):
                executed_queries.append(result)

        if user_query:
            # Load existing memory
            user_memory = await load_user_memory(config, store)

            # Create query record
            query_record = {
                "timestamp": datetime.now().isoformat(),
                "user_query": user_query,
                "description": user_query[:100],  # Short description
                "executed_queries": executed_queries,
                "success": len(executed_queries) > 0
            }

            # Add to query history
            query_history = user_memory["query_history"]
            query_history.append(query_record)

            # Analyze and update patterns
            query_patterns = analyze_query_patterns(query_history)

            # Update preferences based on usage
            preferences = user_memory["preferences"]
            preferences["last_interaction"] = datetime.now().isoformat()
            preferences["total_queries"] = len(query_history)

            # Save updated memory
            memory_data = {
                "preferences": preferences,
                "query_history": query_history,
                "query_patterns": query_patterns
            }

            await save_user_memory(config, store, memory_data)
            logger.info(f"💾 Saved query to user memory: {user_query[:50]}...")

    except Exception as e:
        logger.error(f"❌ Error saving query to memory: {e}")


# Build the SQL Agent graph
def create_sql_agent() -> StateGraph:
    """Create the SQL Agent StateGraph with 4-phase workflow"""
    
    workflow = StateGraph(SQLAgentState)
    
    # Add nodes
    workflow.add_node("planning", planning_phase)
    workflow.add_node("tools", tool_node)
    workflow.add_node("reflection", reflection_phase)
    
    # Add edges
    workflow.set_entry_point("planning")
    workflow.add_conditional_edges("planning", should_use_tools)
    workflow.add_edge("tools", "reflection")
    workflow.add_edge("reflection", END)
    
    return workflow


# Create the compiled SQL agent
sql_agent = create_sql_agent().compile()

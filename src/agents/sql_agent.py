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

from agents.llama_guard import LlamaGuard, LlamaGuardOutput, SafetyAssessment
from core import get_model, settings
from core.deepseek_client import get_deepseek_client
from core.database import get_database_client

logger = logging.getLogger(__name__)


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


async def planning_phase(state: SQLAgentState, config: RunnableConfig) -> SQLAgentState:
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

    # Get database context
    logger.info("🔍 Getting database schema for context")
    schema_info = get_database_schema.invoke({})
    logger.info(f"📊 Schema info retrieved: {len(schema_info)} characters")

    # Create planning prompt
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

    User request: {last_message.content}

    For the user's request "{last_message.content}", you should:
    1. If they're asking about tables/schema: Use get_database_schema
    2. If they need data queried: Use execute_sql_query with appropriate SQL
    3. If they need analysis: Use analyze_query_results or analyze_database_schema

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
        "database_context": schema_info
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


async def reflection_phase(state: SQLAgentState, config: RunnableConfig) -> SQLAgentState:
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
    
    return {"messages": [response]}


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

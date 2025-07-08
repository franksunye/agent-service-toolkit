"""
SQL Agent - Intelligent Database Assistant
Implements 4-phase workflow: Planning → Tool Selection → Execution → Reflection
Based on PDME-PoC architecture adapted for LangGraph framework
"""
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
    # TODO: Implement actual database connection
    # For now, return a sample schema
    return """
    Current Database Schema:
    
    Table: users
      - id INTEGER PRIMARY KEY
      - name TEXT NOT NULL
      - email TEXT UNIQUE
      - age INTEGER
      - created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    
    Table: orders
      - id INTEGER PRIMARY KEY
      - user_id INTEGER FOREIGN KEY REFERENCES users(id)
      - product_name TEXT NOT NULL
      - amount DECIMAL(10,2)
      - order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    
    Table: products
      - id INTEGER PRIMARY KEY
      - name TEXT NOT NULL
      - price DECIMAL(10,2)
      - category TEXT
      - stock_quantity INTEGER
    """


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
    # TODO: Implement actual SQL execution with safety checks
    # For now, return a sample result
    sample_result = {
        "success": True,
        "query": sql_query,
        "user_request": user_request,
        "results": [
            {"id": 1, "name": "John Doe", "email": "john@example.com", "age": 30},
            {"id": 2, "name": "Jane Smith", "email": "jane@example.com", "age": 25},
            {"id": 3, "name": "Bob Johnson", "email": "bob@example.com", "age": 35}
        ],
        "row_count": 3,
        "execution_time_ms": 45
    }
    return json.dumps(sample_result, indent=2)


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
        # Parse the query result
        result_data = json.loads(query_result)
        
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
        
        Keep the analysis concise but valuable.
        """
        
        messages = [
            HumanMessage(content=analysis_prompt)
        ]
        
        response = client.chat_completion(messages, temperature=0.3)
        return response.content
        
    except Exception as e:
        return f"Analysis failed: {str(e)}"


@tool
def analyze_database_schema(schema_info: str) -> str:
    """
    Analyze database schema and provide optimization recommendations.
    
    Args:
        schema_info: Database schema information
    
    Returns:
        Schema analysis and optimization recommendations
    """
    try:
        client = get_deepseek_client()
        
        analysis_prompt = f"""
        Analyze the following database schema and provide recommendations:
        
        Schema: {schema_info}
        
        Please evaluate:
        1. Schema design quality
        2. Potential performance issues
        3. Missing indexes or constraints
        4. Normalization opportunities
        5. Security considerations
        
        Provide specific, actionable recommendations.
        """
        
        messages = [
            HumanMessage(content=analysis_prompt)
        ]
        
        response = client.chat_completion(messages, temperature=0.3)
        return response.content
        
    except Exception as e:
        return f"Schema analysis failed: {str(e)}"


# Define available tools
sql_tools = [
    get_database_schema,
    execute_sql_query,
    analyze_query_results,
    analyze_database_schema
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
    messages = state["messages"]
    last_message = messages[-1] if messages else None
    
    if not last_message:
        return {"messages": [AIMessage(content="No user input received.")]}
    
    # Get database context
    schema_info = get_database_schema.invoke({})
    
    # Create planning prompt
    planning_prompt = f"""
    You are an intelligent SQL database assistant. Analyze the user's request and plan the appropriate tools to use.
    
    Available tools:
    1. get_database_schema - Get database structure information
    2. execute_sql_query - Execute SQL queries safely
    3. analyze_query_results - Analyze query results for insights
    4. analyze_database_schema - Analyze database design
    
    Current database schema:
    {schema_info}
    
    User request: {last_message.content}
    
    Plan the sequence of tools needed to fulfill this request. Consider:
    - What information do you need?
    - What SQL queries might be required?
    - Should results be analyzed for insights?
    
    Use function calling to specify the tools and their parameters.
    """
    
    # Get model and make planning decision
    model = get_model(config["configurable"].get("model", settings.DEFAULT_MODEL))
    model_with_tools = model.bind_tools(sql_tools)
    
    planning_messages = [
        SystemMessage(content=planning_prompt),
        last_message
    ]
    
    response = await model_with_tools.ainvoke(planning_messages, config)
    
    # Store planning result in state
    planning_result = {
        "planned_tools": response.tool_calls if hasattr(response, 'tool_calls') else [],
        "reasoning": response.content
    }
    
    return {
        "messages": [response],
        "planning_result": planning_result,
        "database_context": schema_info
    }


async def should_use_tools(state: SQLAgentState) -> Literal["tools", "reflection"]:
    """Determine if tools should be executed or move to reflection"""
    last_message = state["messages"][-1]
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    else:
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

#!/usr/bin/env python3
"""
Simple test to identify the SQL Agent tool calling issue
"""

import os
import sys
import asyncio
import logging

# Add src to path
sys.path.insert(0, 'src')

# Set up environment
os.environ['DEEPSEEK_API_KEY'] = 'sk-test'
os.environ['DEEPSEEK_BASE_URL'] = 'https://api.deepseek.com'

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_fake_model_tool_calling():
    """Test if fake model can generate tool calls"""
    
    print("🧪 Testing Fake Model Tool Calling")
    print("=" * 50)
    
    try:
        from langchain_community.chat_models import FakeListChatModel
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
        from langchain_core.tools import tool
        
        # Create a simple test tool
        @tool
        def test_tool(query: str) -> str:
            """A test tool that returns a simple response."""
            return f"Test tool called with: {query}"
        
        # Create fake model with tool call response
        fake_responses = [
            AIMessage(
                content="I'll use the test tool to help you.",
                tool_calls=[{
                    "name": "test_tool",
                    "args": {"query": "test query"},
                    "id": "test_call_1"
                }]
            )
        ]
        
        fake_model = FakeListChatModel(responses=fake_responses)
        model_with_tools = fake_model.bind_tools([test_tool])
        
        messages = [
            SystemMessage(content="You are a helpful assistant. Use tools when needed."),
            HumanMessage(content="Please use the test tool.")
        ]
        
        print("Invoking fake model with tools...")
        response = await model_with_tools.ainvoke(messages)
        
        print(f"Response type: {type(response)}")
        print(f"Response content: {response.content}")
        print(f"Has tool_calls: {hasattr(response, 'tool_calls')}")
        
        if hasattr(response, 'tool_calls'):
            print(f"Tool calls: {response.tool_calls}")
            if response.tool_calls:
                print("✅ Fake model successfully generated tool calls!")
            else:
                print("❌ Fake model has tool_calls attribute but it's empty")
        else:
            print("❌ Fake model response has no tool_calls attribute")
        
    except Exception as e:
        print(f"❌ Error in fake model test: {e}")
        import traceback
        traceback.print_exc()

async def test_database_tools_directly():
    """Test database tools directly without the agent"""
    
    print("\n🗄️ Testing Database Tools Directly")
    print("=" * 50)
    
    try:
        # Test database client directly
        from core.database import DatabaseClient
        
        print("Creating database client...")
        db_client = DatabaseClient()
        
        print("Testing schema retrieval...")
        schema_info = db_client.get_schema_info()
        
        if 'tables' in schema_info:
            print(f"✅ Found {len(schema_info['tables'])} tables:")
            for table_name, table_info in schema_info['tables'].items():
                print(f"  - {table_name}: {table_info['row_count']} rows")
        else:
            print(f"❌ Schema info: {schema_info}")
        
        print("\nTesting simple query...")
        result = db_client.execute_query("SELECT COUNT(*) as total FROM users")
        print(f"Query result: {result}")
        
        if result.get('success'):
            print("✅ Database operations working correctly!")
        else:
            print(f"❌ Database query failed: {result}")
        
    except Exception as e:
        print(f"❌ Error in database test: {e}")
        import traceback
        traceback.print_exc()

async def test_sql_tools_import():
    """Test importing SQL tools individually"""
    
    print("\n🔧 Testing SQL Tools Import")
    print("=" * 50)
    
    try:
        # Import tools directly from the file
        import importlib.util
        
        spec = importlib.util.spec_from_file_location("sql_agent", "src/agents/sql_agent.py")
        sql_agent_module = importlib.util.module_from_spec(spec)
        
        # Mock the problematic imports
        sys.modules['agents.llama_guard'] = type('MockModule', (), {
            'LlamaGuard': object,
            'LlamaGuardOutput': object,
            'SafetyAssessment': object
        })()
        
        sys.modules['core'] = type('MockModule', (), {
            'get_model': lambda x: None,
            'settings': type('MockSettings', (), {'DEFAULT_MODEL': 'fake'})()
        })()
        
        sys.modules['core.deepseek_client'] = type('MockModule', (), {
            'get_deepseek_client': lambda: None
        })()
        
        sys.modules['core.database'] = type('MockModule', (), {
            'get_database_client': lambda: None
        })()
        
        spec.loader.exec_module(sql_agent_module)
        
        # Test if tools are defined
        if hasattr(sql_agent_module, 'get_database_schema'):
            print("✅ get_database_schema tool found")
        
        if hasattr(sql_agent_module, 'sql_tools'):
            print(f"✅ sql_tools list found with {len(sql_agent_module.sql_tools)} tools")
            for tool in sql_agent_module.sql_tools:
                print(f"  - {tool.name}")
        
    except Exception as e:
        print(f"❌ Error importing SQL tools: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main test function"""
    print("🔍 SQL Agent Issue Diagnosis")
    print("=" * 60)
    
    await test_fake_model_tool_calling()
    await test_database_tools_directly()
    await test_sql_tools_import()
    
    print("\n📋 Summary:")
    print("1. If fake model tool calling works, the issue is in the SQL Agent's model configuration")
    print("2. If database tools work, the issue is in the LangGraph workflow")
    print("3. If SQL tools import correctly, the issue is in the planning phase logic")
    
    print("\n🏁 Diagnosis completed")

if __name__ == "__main__":
    asyncio.run(main())

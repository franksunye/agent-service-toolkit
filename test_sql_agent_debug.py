#!/usr/bin/env python3
"""
Debug script to test SQL Agent tool calling functionality
This script tests the core issue: why tools are not being called
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

async def test_sql_agent_tool_calling():
    """Test SQL Agent tool calling functionality"""
    
    print("🚀 Testing SQL Agent Tool Calling")
    print("=" * 50)
    
    try:
        # Import directly from sql_agent module to avoid agents.__init__ issues
        sys.path.insert(0, 'src/agents')
        from sql_agent import sql_agent, get_database_schema
        from langchain_core.messages import HumanMessage
        
        print("✅ Successfully imported SQL Agent")
        
        # Test 1: Direct tool invocation
        print("\n📋 Test 1: Direct tool invocation")
        schema_result = get_database_schema.invoke({})
        print(f"Schema result length: {len(schema_result)} characters")
        print(f"Schema preview: {schema_result[:200]}...")
        
        # Test 2: SQL Agent with simple query
        print("\n🤖 Test 2: SQL Agent execution")
        
        # Create test input
        test_input = {
            "messages": [HumanMessage(content="What tables are in the database?")]
        }
        
        # Create config
        config = {
            "configurable": {
                "model": "fake",  # Use fake model to avoid API calls
                "thread_id": "test-thread"
            }
        }
        
        print("Invoking SQL Agent...")
        result = await sql_agent.ainvoke(test_input, config)
        
        print(f"Result type: {type(result)}")
        print(f"Result keys: {list(result.keys())}")
        
        if "messages" in result:
            messages = result["messages"]
            print(f"Number of messages: {len(messages)}")
            
            for i, msg in enumerate(messages):
                print(f"\nMessage {i+1}:")
                print(f"  Type: {type(msg)}")
                print(f"  Content: {msg.content[:200]}...")
                if hasattr(msg, 'tool_calls'):
                    print(f"  Tool calls: {msg.tool_calls}")
        
        print("\n✅ SQL Agent test completed")
        
    except Exception as e:
        print(f"❌ Error in SQL Agent test: {e}")
        import traceback
        traceback.print_exc()

async def test_model_tool_binding():
    """Test model tool binding specifically"""
    
    print("\n🔧 Testing Model Tool Binding")
    print("=" * 50)
    
    try:
        from core.llm import get_model
        from sql_agent import sql_tools
        from langchain_core.messages import HumanMessage, SystemMessage
        
        # Get fake model
        model = get_model("fake")
        print(f"✅ Got model: {type(model)}")
        
        # Bind tools
        model_with_tools = model.bind_tools(sql_tools)
        print(f"✅ Bound {len(sql_tools)} tools to model")
        
        # Test tool calling
        messages = [
            SystemMessage(content="You are a SQL assistant. Use the get_database_schema tool to answer questions about database structure."),
            HumanMessage(content="What tables are in the database?")
        ]
        
        print("Invoking model with tools...")
        response = await model_with_tools.ainvoke(messages)
        
        print(f"Response type: {type(response)}")
        print(f"Response content: {response.content[:200]}...")
        print(f"Has tool_calls: {hasattr(response, 'tool_calls')}")
        
        if hasattr(response, 'tool_calls'):
            print(f"Tool calls: {response.tool_calls}")
        
        print("✅ Model tool binding test completed")
        
    except Exception as e:
        print(f"❌ Error in model tool binding test: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main test function"""
    print("🧪 SQL Agent Debug Test Suite")
    print("=" * 60)
    
    await test_sql_agent_tool_calling()
    await test_model_tool_binding()
    
    print("\n🏁 All tests completed")

if __name__ == "__main__":
    asyncio.run(main())

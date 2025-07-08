#!/usr/bin/env python3
"""
Test the fixed fake model with tool calling
"""

import os
import sys
import asyncio

# Add src to path
sys.path.insert(0, 'src')

# Set up environment
os.environ['DEEPSEEK_API_KEY'] = 'sk-test'
os.environ['DEEPSEEK_BASE_URL'] = 'https://api.deepseek.com'

async def test_fixed_fake_model():
    """Test the fixed fake model with tool calling"""
    
    print("🧪 Testing Fixed Fake Model")
    print("=" * 50)
    
    try:
        from core.llm import FakeToolModel
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_core.tools import tool
        
        # Create a simple test tool
        @tool
        def get_database_schema() -> str:
            """Get database schema information."""
            return "Test schema info"
        
        # Create fake model
        fake_model = FakeToolModel()
        model_with_tools = fake_model.bind_tools([get_database_schema])
        
        messages = [
            SystemMessage(content="You are a SQL assistant. Use tools when needed."),
            HumanMessage(content="What tables are in the database?")
        ]
        
        print("Invoking fixed fake model with tools...")
        response = await model_with_tools.ainvoke(messages)
        
        print(f"Response type: {type(response)}")
        print(f"Response content: {response.content}")
        print(f"Has tool_calls: {hasattr(response, 'tool_calls')}")
        
        if hasattr(response, 'tool_calls'):
            print(f"Tool calls: {response.tool_calls}")
            if response.tool_calls:
                print("✅ Fixed fake model successfully generated tool calls!")
                return True
            else:
                print("❌ Fixed fake model has tool_calls attribute but it's empty")
        else:
            print("❌ Fixed fake model response has no tool_calls attribute")
        
        return False
        
    except Exception as e:
        print(f"❌ Error in fixed fake model test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_sql_agent_with_fixed_model():
    """Test SQL Agent with the fixed model"""
    
    print("\n🤖 Testing SQL Agent with Fixed Model")
    print("=" * 50)
    
    try:
        # Import the planning phase directly
        import importlib.util
        
        # Mock the problematic imports
        sys.modules['agents.llama_guard'] = type('MockModule', (), {
            'LlamaGuard': object,
            'LlamaGuardOutput': object,
            'SafetyAssessment': object
        })()
        
        # Import the planning phase function
        spec = importlib.util.spec_from_file_location("sql_agent", "src/agents/sql_agent.py")
        sql_agent_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sql_agent_module)
        
        from langchain_core.messages import HumanMessage
        
        # Create test state
        state = {
            "messages": [HumanMessage(content="What tables are in the database?")]
        }
        
        # Create test config
        config = {
            "configurable": {
                "model": "fake"
            }
        }
        
        print("Testing planning phase...")
        result = await sql_agent_module.planning_phase(state, config)
        
        print(f"Planning result keys: {list(result.keys())}")
        
        if "messages" in result and result["messages"]:
            last_msg = result["messages"][-1]
            print(f"Last message type: {type(last_msg)}")
            print(f"Last message content: {last_msg.content}")
            
            if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                print(f"✅ Planning phase generated {len(last_msg.tool_calls)} tool calls!")
                for i, tool_call in enumerate(last_msg.tool_calls):
                    print(f"  Tool call {i+1}: {tool_call}")
                return True
            else:
                print("❌ Planning phase did not generate tool calls")
        
        return False
        
    except Exception as e:
        print(f"❌ Error in SQL Agent test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("🔧 Testing Fixed Fake Model for SQL Agent")
    print("=" * 60)
    
    model_works = await test_fixed_fake_model()
    agent_works = await test_sql_agent_with_fixed_model()
    
    print(f"\n📋 Results:")
    print(f"Fixed fake model works: {'✅' if model_works else '❌'}")
    print(f"SQL Agent planning works: {'✅' if agent_works else '❌'}")
    
    if model_works and agent_works:
        print("\n🎉 SUCCESS: The issue has been fixed!")
        print("The SQL Agent should now work correctly in Streamlit.")
    else:
        print("\n⚠️ Still investigating the issue...")
    
    print("\n🏁 Test completed")

if __name__ == "__main__":
    asyncio.run(main())

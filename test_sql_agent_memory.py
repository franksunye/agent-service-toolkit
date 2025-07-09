#!/usr/bin/env python3
"""
Test script for SQL Agent memory system integration
Verifies that the SQL Agent can store and retrieve user preferences and query history
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from langchain_core.messages import HumanMessage
from langgraph.store.memory import InMemoryStore

from agents.sql_agent import sql_agent, load_user_memory, save_user_memory, analyze_query_patterns
from core.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_memory_functions():
    """Test the memory utility functions"""
    print("🧪 Testing SQL Agent Memory Functions")
    print("=" * 50)
    
    # Create test store
    store = InMemoryStore()
    
    # Test configuration
    config = {
        "configurable": {
            "user_id": "test_user_123",
            "model": settings.DEFAULT_MODEL
        }
    }
    
    # Test 1: Load empty memory
    print("\n📚 Test 1: Loading empty user memory")
    memory = await load_user_memory(config, store)
    print(f"Empty memory: {memory}")
    assert memory["preferences"] == {}
    assert memory["query_history"] == []
    assert memory["query_patterns"] == []
    print("✅ Empty memory test passed")
    
    # Test 2: Save user memory
    print("\n💾 Test 2: Saving user memory")
    test_memory = {
        "preferences": {
            "language": "en",
            "response_style": "detailed",
            "last_interaction": datetime.now().isoformat()
        },
        "query_history": [
            {
                "timestamp": datetime.now().isoformat(),
                "user_query": "Show me all users",
                "description": "Show me all users",
                "executed_queries": [{"query": "SELECT * FROM users"}],
                "success": True
            },
            {
                "timestamp": datetime.now().isoformat(),
                "user_query": "Count users by department",
                "description": "Count users by department",
                "executed_queries": [{"query": "SELECT department, COUNT(*) FROM users GROUP BY department"}],
                "success": True
            }
        ],
        "query_patterns": []
    }
    
    await save_user_memory(config, store, test_memory)
    print("✅ Memory saved successfully")
    
    # Test 3: Load saved memory
    print("\n📖 Test 3: Loading saved user memory")
    loaded_memory = await load_user_memory(config, store)
    print(f"Loaded preferences: {loaded_memory['preferences']}")
    print(f"Loaded query history: {len(loaded_memory['query_history'])} queries")
    assert len(loaded_memory["query_history"]) == 2
    assert loaded_memory["preferences"]["language"] == "en"
    print("✅ Memory loading test passed")
    
    # Test 4: Query pattern analysis
    print("\n🔍 Test 4: Query pattern analysis")
    patterns = analyze_query_patterns(loaded_memory["query_history"])
    print(f"Detected patterns: {patterns}")
    assert len(patterns) > 0
    print("✅ Pattern analysis test passed")
    
    print("\n🎉 All memory function tests passed!")


async def test_sql_agent_with_memory():
    """Test SQL Agent with memory integration"""
    print("\n🤖 Testing SQL Agent with Memory Integration")
    print("=" * 50)
    
    # Create test store
    store = InMemoryStore()
    
    # Configure the agent with store
    sql_agent.store = store
    
    # Test configuration
    config = {
        "configurable": {
            "user_id": "test_user_456",
            "model": settings.DEFAULT_MODEL,
            "thread_id": "test_thread_123"
        }
    }
    
    # Test queries
    test_queries = [
        "What tables are in the database?",
        "Show me all users in the Engineering department",
        "Count the total number of users"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Test Query {i}: {query}")
        
        try:
            # Create input message
            input_data = {"messages": [HumanMessage(content=query)]}
            
            # Invoke the agent
            result = await sql_agent.ainvoke(input_data, config)
            
            # Check result
            if "messages" in result:
                last_message = result["messages"][-1]
                print(f"✅ Agent responded: {last_message.content[:100]}...")
            else:
                print("❌ No messages in result")
            
            # Verify memory was updated
            memory = await load_user_memory(config, store)
            print(f"📚 Query history now has {len(memory['query_history'])} entries")
            
        except Exception as e:
            print(f"❌ Error with query '{query}': {e}")
            logger.exception("Query execution failed")
    
    # Final memory check
    print("\n📊 Final Memory State:")
    final_memory = await load_user_memory(config, store)
    print(f"Total queries: {len(final_memory['query_history'])}")
    print(f"Preferences: {final_memory['preferences']}")
    print(f"Patterns: {final_memory['query_patterns']}")
    
    print("\n🎉 SQL Agent memory integration test completed!")


async def main():
    """Main test function"""
    print("🚀 Starting SQL Agent Memory System Tests")
    print("=" * 60)
    
    try:
        # Test memory functions
        await test_memory_functions()
        
        # Test SQL Agent integration
        await test_sql_agent_with_memory()
        
        print("\n" + "=" * 60)
        print("🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.exception("Test execution failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

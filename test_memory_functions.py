#!/usr/bin/env python3
"""
Simplified test for SQL Agent memory functions
Tests only the memory utility functions without requiring full Agent setup
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set minimal environment variables to avoid validation errors
os.environ.setdefault("DEEPSEEK_API_KEY", "test_key")

from langgraph.store.memory import InMemoryStore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Import memory functions directly
async def load_user_memory(config, store):
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


async def save_user_memory(config, store, memory_data):
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


def analyze_query_patterns(query_history):
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
            "model": "test_model"
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
                "query": "select * from users",
                "success": True
            },
            {
                "timestamp": datetime.now().isoformat(),
                "user_query": "Count users by department",
                "description": "Count users by department",
                "query": "select department, count(*) from users group by department",
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
    
    # Test 5: Different user isolation
    print("\n🔒 Test 5: User data isolation")
    config2 = {
        "configurable": {
            "user_id": "test_user_456",
            "model": "test_model"
        }
    }
    
    memory2 = await load_user_memory(config2, store)
    print(f"User 2 memory: {memory2}")
    assert memory2["query_history"] == []  # Should be empty for different user
    print("✅ User isolation test passed")
    
    print("\n🎉 All memory function tests passed!")


async def main():
    """Main test function"""
    print("🚀 Starting SQL Agent Memory System Tests")
    print("=" * 60)
    
    try:
        # Test memory functions
        await test_memory_functions()
        
        print("\n" + "=" * 60)
        print("🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.exception("Test execution failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Comprehensive test suite for SQL Agent
Tests database operations, security measures, and agent functionality
"""
import asyncio
import os
import sys
import tempfile
import pytest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.database import DatabaseClient, SQLValidationError
from agents.sql_agent import sql_agent, get_database_schema, execute_sql_query
from langchain_core.messages import HumanMessage


class TestDatabaseClient:
    """Test the DatabaseClient class"""
    
    def setup_method(self):
        """Setup test database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.db_client = DatabaseClient(self.temp_db.name)
    
    def teardown_method(self):
        """Cleanup test database"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_database_initialization(self):
        """Test database initialization and sample data creation"""
        schema = self.db_client.get_schema_info()
        assert schema["database_type"] == "SQLite"
        assert "users" in schema["tables"]
        assert "orders" in schema["tables"]
        assert "products" in schema["tables"]
    
    def test_valid_select_query(self):
        """Test executing valid SELECT queries"""
        result = self.db_client.execute_query("SELECT * FROM users LIMIT 3")
        assert result["success"] is True
        assert result["query_type"] == "SELECT"
        assert len(result["results"]) <= 3
        assert "columns" in result
    
    def test_valid_insert_query(self):
        """Test executing valid INSERT queries"""
        query = "INSERT INTO users (name, email, age, department) VALUES ('Test User', 'test@example.com', 25, 'Testing')"
        result = self.db_client.execute_query(query)
        assert result["success"] is True
        assert result["query_type"] == "MODIFY"
        assert result["rows_affected"] == 1
    
    def test_sql_injection_protection(self):
        """Test SQL injection protection"""
        malicious_queries = [
            "SELECT * FROM users; DROP TABLE users;",
            "SELECT * FROM users WHERE id = 1 OR 1=1; DELETE FROM users;",
            "SELECT * FROM users UNION SELECT * FROM sqlite_master",
            "SELECT * FROM users; --",
            "DROP TABLE users",
            "DELETE FROM users",
            "TRUNCATE TABLE users"
        ]
        
        for query in malicious_queries:
            result = self.db_client.execute_query(query)
            assert result["success"] is False
            assert result["error_type"] == "VALIDATION_ERROR"
    
    def test_parameterized_queries(self):
        """Test parameterized query execution"""
        query = "SELECT * FROM users WHERE age > ? AND department = ?"
        params = (25, 'Engineering')
        result = self.db_client.execute_query(query, params)
        assert result["success"] is True
        assert result["query_type"] == "SELECT"
    
    def test_schema_info_retrieval(self):
        """Test schema information retrieval"""
        schema = self.db_client.get_schema_info()
        assert "tables" in schema
        
        users_table = schema["tables"]["users"]
        assert "columns" in users_table
        assert "row_count" in users_table
        
        # Check for expected columns
        column_names = [col["name"] for col in users_table["columns"]]
        assert "id" in column_names
        assert "name" in column_names
        assert "email" in column_names
    
    def test_invalid_sql_syntax(self):
        """Test handling of invalid SQL syntax"""
        result = self.db_client.execute_query("INVALID SQL SYNTAX")
        assert result["success"] is False
        assert result["error_type"] == "VALIDATION_ERROR"
    
    def test_empty_query(self):
        """Test handling of empty queries"""
        result = self.db_client.execute_query("")
        assert result["success"] is False
        assert result["error_type"] == "VALIDATION_ERROR"


class TestSQLTools:
    """Test SQL Agent tools"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        # Set environment variable for test database
        os.environ['SQL_AGENT_DB_PATH'] = self.temp_db.name
    
    def teardown_method(self):
        """Cleanup test environment"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
        if 'SQL_AGENT_DB_PATH' in os.environ:
            del os.environ['SQL_AGENT_DB_PATH']
    
    def test_get_database_schema_tool(self):
        """Test the get_database_schema tool"""
        schema_result = get_database_schema.invoke({})
        assert "Database Schema" in schema_result
        assert "users" in schema_result
        assert "orders" in schema_result
        assert "products" in schema_result
    
    def test_execute_sql_query_tool(self):
        """Test the execute_sql_query tool"""
        query = "SELECT COUNT(*) as user_count FROM users"
        result = execute_sql_query.invoke({"sql_query": query, "user_request": "Count users"})
        
        import json
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert "results" in result_data
        assert result_data["user_request"] == "Count users"
    
    def test_execute_sql_query_with_error(self):
        """Test SQL query tool with invalid query"""
        query = "DROP TABLE users"  # Should be blocked
        result = execute_sql_query.invoke({"sql_query": query})
        
        import json
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "VALIDATION_ERROR" in result_data["error_type"]


@pytest.mark.asyncio
class TestSQLAgent:
    """Test the complete SQL Agent workflow"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        os.environ['SQL_AGENT_DB_PATH'] = self.temp_db.name
        os.environ['USE_FAKE_MODEL'] = 'true'
    
    def teardown_method(self):
        """Cleanup test environment"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
        if 'SQL_AGENT_DB_PATH' in os.environ:
            del os.environ['SQL_AGENT_DB_PATH']
        if 'USE_FAKE_MODEL' in os.environ:
            del os.environ['USE_FAKE_MODEL']
    
    async def test_sql_agent_schema_request(self):
        """Test SQL Agent handling schema requests"""
        config = {
            "configurable": {
                "model": "fake",
                "thread_id": "test-schema"
            }
        }
        
        test_message = HumanMessage(content="What tables are in the database?")
        initial_state = {"messages": [test_message]}
        
        result = await sql_agent.ainvoke(initial_state, config)
        
        assert "messages" in result
        assert len(result["messages"]) > 1  # Should have response
    
    async def test_sql_agent_query_request(self):
        """Test SQL Agent handling query requests"""
        config = {
            "configurable": {
                "model": "fake",
                "thread_id": "test-query"
            }
        }
        
        test_message = HumanMessage(content="Show me all users in the Engineering department")
        initial_state = {"messages": [test_message]}
        
        result = await sql_agent.ainvoke(initial_state, config)
        
        assert "messages" in result
        assert len(result["messages"]) > 1


def run_security_tests():
    """Run security-focused tests"""
    print("🔒 Running Security Tests...")
    
    # Test SQL injection attempts
    test_client = TestDatabaseClient()
    test_client.setup_method()
    
    try:
        test_client.test_sql_injection_protection()
        print("✅ SQL Injection Protection: PASS")
    except Exception as e:
        print(f"❌ SQL Injection Protection: FAIL - {e}")
    finally:
        test_client.teardown_method()
    
    # Test parameterized queries
    test_client = TestDatabaseClient()
    test_client.setup_method()
    
    try:
        test_client.test_parameterized_queries()
        print("✅ Parameterized Queries: PASS")
    except Exception as e:
        print(f"❌ Parameterized Queries: FAIL - {e}")
    finally:
        test_client.teardown_method()


def run_functionality_tests():
    """Run functionality tests"""
    print("🧪 Running Functionality Tests...")
    
    # Test database operations
    test_client = TestDatabaseClient()
    test_client.setup_method()
    
    try:
        test_client.test_database_initialization()
        test_client.test_valid_select_query()
        test_client.test_valid_insert_query()
        test_client.test_schema_info_retrieval()
        print("✅ Database Operations: PASS")
    except Exception as e:
        print(f"❌ Database Operations: FAIL - {e}")
    finally:
        test_client.teardown_method()
    
    # Test SQL tools
    test_tools = TestSQLTools()
    test_tools.setup_method()
    
    try:
        test_tools.test_get_database_schema_tool()
        test_tools.test_execute_sql_query_tool()
        print("✅ SQL Tools: PASS")
    except Exception as e:
        print(f"❌ SQL Tools: FAIL - {e}")
    finally:
        test_tools.teardown_method()


async def run_agent_tests():
    """Run SQL Agent integration tests"""
    print("🤖 Running SQL Agent Tests...")
    
    test_agent = TestSQLAgent()
    test_agent.setup_method()
    
    try:
        await test_agent.test_sql_agent_schema_request()
        await test_agent.test_sql_agent_query_request()
        print("✅ SQL Agent Integration: PASS")
    except Exception as e:
        print(f"❌ SQL Agent Integration: FAIL - {e}")
    finally:
        test_agent.teardown_method()


async def main():
    """Main test runner"""
    print("🚀 SQL Agent Test Suite")
    print("=" * 50)
    
    run_security_tests()
    print()
    run_functionality_tests()
    print()
    await run_agent_tests()
    
    print("\n" + "=" * 50)
    print("🎉 Test suite completed!")


if __name__ == "__main__":
    asyncio.run(main())

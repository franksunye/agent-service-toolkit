"""
Database Client for SQL Agent
Provides secure database operations with SQLite support
"""
import sqlite3
import logging
import re
import os
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass


class SQLValidationError(Exception):
    """Custom exception for SQL validation errors"""
    pass


class DatabaseClient:
    """
    Secure database client with SQLite support
    Provides connection management, query validation, and security measures
    """
    
    def __init__(self, db_path: str = "sql_agent.db"):
        self.db_path = db_path
        self.connection_timeout = 30
        self._ensure_database_exists()
        self._create_sample_tables()
    
    def _ensure_database_exists(self):
        """Ensure the database file exists and is accessible"""
        try:
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            
            # Test connection
            with self._get_connection() as conn:
                conn.execute("SELECT 1")
            
            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            raise DatabaseError(f"Failed to initialize database: {e}")
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper error handling"""
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=self.connection_timeout,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row  # Enable column access by name
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            raise DatabaseError(f"Database connection error: {e}")
        finally:
            if conn:
                conn.close()
    
    def _validate_sql_query(self, query: str) -> None:
        """
        Validate SQL query for security and safety
        Prevents dangerous operations and SQL injection attempts
        """
        if not query or not query.strip():
            raise SQLValidationError("Empty query not allowed")
        
        query_upper = query.upper().strip()
        
        # Block dangerous operations
        dangerous_keywords = [
            'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE INDEX',
            'DROP INDEX', 'PRAGMA', 'ATTACH', 'DETACH'
        ]
        
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                raise SQLValidationError(f"Operation '{keyword}' is not allowed for security reasons")
        
        # Allow only specific safe operations
        allowed_starts = ['SELECT', 'INSERT', 'UPDATE', 'CREATE TABLE', 'WITH']
        if not any(query_upper.startswith(start) for start in allowed_starts):
            raise SQLValidationError("Only SELECT, INSERT, UPDATE, CREATE TABLE, and WITH queries are allowed")
        
        # Basic SQL injection pattern detection
        injection_patterns = [
            r';\s*(DROP|DELETE|TRUNCATE)',
            r'UNION\s+SELECT',
            r'--\s*$',
            r'/\*.*\*/',
            r'xp_cmdshell',
            r'sp_executesql'
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                raise SQLValidationError(f"Potentially malicious SQL pattern detected")
        
        logger.debug(f"SQL query validated: {query[:100]}...")
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> Dict[str, Any]:
        """
        Execute a SQL query safely with validation and error handling
        
        Args:
            query: SQL query string
            params: Optional parameters for parameterized queries
            
        Returns:
            Dictionary containing query results and metadata
        """
        try:
            # Validate the query
            self._validate_sql_query(query)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Execute query with parameters if provided
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                # Handle different query types
                if query.upper().strip().startswith('SELECT') or query.upper().strip().startswith('WITH'):
                    # For SELECT queries, fetch results
                    rows = cursor.fetchall()
                    columns = [description[0] for description in cursor.description] if cursor.description else []
                    
                    # Convert rows to list of dictionaries
                    results = []
                    for row in rows:
                        results.append(dict(zip(columns, row)))
                    
                    return {
                        "success": True,
                        "query": query,
                        "results": results,
                        "row_count": len(results),
                        "columns": columns,
                        "query_type": "SELECT"
                    }
                else:
                    # For INSERT, UPDATE, CREATE TABLE queries
                    conn.commit()
                    return {
                        "success": True,
                        "query": query,
                        "rows_affected": cursor.rowcount,
                        "query_type": "MODIFY"
                    }
                    
        except SQLValidationError as e:
            logger.warning(f"SQL validation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "VALIDATION_ERROR",
                "query": query
            }
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "DATABASE_ERROR",
                "query": query
            }
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "UNKNOWN_ERROR",
                "query": query
            }
    
    def get_schema_info(self) -> Dict[str, Any]:
        """Get comprehensive database schema information"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                tables = [row[0] for row in cursor.fetchall()]
                
                schema_info = {
                    "database_type": "SQLite",
                    "database_path": self.db_path,
                    "tables": {}
                }
                
                # Get detailed info for each table
                for table in tables:
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = cursor.fetchall()
                    
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    row_count = cursor.fetchone()[0]
                    
                    schema_info["tables"][table] = {
                        "columns": [
                            {
                                "name": col[1],
                                "type": col[2],
                                "not_null": bool(col[3]),
                                "default_value": col[4],
                                "primary_key": bool(col[5])
                            }
                            for col in columns
                        ],
                        "row_count": row_count
                    }
                
                return schema_info
                
        except Exception as e:
            logger.error(f"Failed to get schema info: {e}")
            return {
                "error": str(e),
                "database_type": "SQLite",
                "database_path": self.db_path
            }
    
    def _create_sample_tables(self):
        """Create sample tables for demonstration and testing"""
        sample_tables = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                age INTEGER,
                department TEXT,
                salary DECIMAL(10,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_name TEXT NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                category TEXT,
                stock_quantity INTEGER DEFAULT 0,
                description TEXT
            )
            """
        ]
        
        sample_data = [
            "INSERT OR IGNORE INTO users (name, email, age, department, salary) VALUES ('John Doe', 'john@example.com', 30, 'Engineering', 75000)",
            "INSERT OR IGNORE INTO users (name, email, age, department, salary) VALUES ('Jane Smith', 'jane@example.com', 25, 'Marketing', 65000)",
            "INSERT OR IGNORE INTO users (name, email, age, department, salary) VALUES ('Bob Johnson', 'bob@example.com', 35, 'Sales', 70000)",
            "INSERT OR IGNORE INTO users (name, email, age, department, salary) VALUES ('Alice Brown', 'alice@example.com', 28, 'Engineering', 80000)",
            "INSERT OR IGNORE INTO users (name, email, age, department, salary) VALUES ('Charlie Wilson', 'charlie@example.com', 32, 'HR', 60000)",
            
            "INSERT OR IGNORE INTO products (name, price, category, stock_quantity, description) VALUES ('Laptop', 999.99, 'Electronics', 50, 'High-performance laptop')",
            "INSERT OR IGNORE INTO products (name, price, category, stock_quantity, description) VALUES ('Mouse', 29.99, 'Electronics', 200, 'Wireless optical mouse')",
            "INSERT OR IGNORE INTO products (name, price, category, stock_quantity, description) VALUES ('Keyboard', 79.99, 'Electronics', 150, 'Mechanical keyboard')",
            "INSERT OR IGNORE INTO products (name, price, category, stock_quantity, description) VALUES ('Monitor', 299.99, 'Electronics', 75, '24-inch LED monitor')",
            
            "INSERT OR IGNORE INTO orders (user_id, product_name, amount, status) VALUES (1, 'Laptop', 999.99, 'completed')",
            "INSERT OR IGNORE INTO orders (user_id, product_name, amount, status) VALUES (2, 'Mouse', 29.99, 'completed')",
            "INSERT OR IGNORE INTO orders (user_id, product_name, amount, status) VALUES (3, 'Keyboard', 79.99, 'pending')",
            "INSERT OR IGNORE INTO orders (user_id, product_name, amount, status) VALUES (1, 'Monitor', 299.99, 'completed')",
            "INSERT OR IGNORE INTO orders (user_id, product_name, amount, status) VALUES (4, 'Mouse', 29.99, 'shipped')"
        ]
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Create tables
                for table_sql in sample_tables:
                    cursor.execute(table_sql)
                
                # Insert sample data
                for data_sql in sample_data:
                    cursor.execute(data_sql)
                
                conn.commit()
                logger.info("Sample tables and data created successfully")
                
        except Exception as e:
            logger.error(f"Failed to create sample tables: {e}")


# Global database client instance
_db_client = None

def get_database_client() -> DatabaseClient:
    """Get global database client instance"""
    global _db_client
    if _db_client is None:
        _db_client = DatabaseClient()
    return _db_client

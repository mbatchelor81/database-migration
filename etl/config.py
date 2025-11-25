#!/usr/bin/env python3
"""
ETL Configuration Module

Manages database connections to both Supabase (PostgreSQL source) and MongoDB (target).
Provides connection pooling, error handling, and context managers for safe resource management.
"""

import os
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager
from dotenv import load_dotenv

# Supabase client
from supabase import create_client, Client
from postgrest.exceptions import APIError

# MongoDB client
from pymongo import MongoClient
from pymongo.errors import (
    ConnectionFailure,
    ServerSelectionTimeoutError,
    ConfigurationError,
    OperationFailure
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration constants
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@localhost:27017/project_management?authSource=admin")
MONGO_DB = os.getenv("MONGO_DB", "project_management")
MONGO_MAX_POOL_SIZE = int(os.getenv("MONGO_MAX_POOL_SIZE", "100"))
MONGO_MIN_POOL_SIZE = int(os.getenv("MONGO_MIN_POOL_SIZE", "10"))
MONGO_SERVER_SELECTION_TIMEOUT_MS = int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "5000"))
MONGO_CONNECT_TIMEOUT_MS = int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "10000"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Singleton clients
_supabase_client: Optional[Client] = None
_mongo_client: Optional[MongoClient] = None


def get_supabase_client() -> Client:
    """
    Get or create a Supabase client instance (singleton pattern).
    
    Returns:
        Client: Configured Supabase client instance
        
    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_KEY are not set
    """
    global _supabase_client
    
    if _supabase_client is not None:
        return _supabase_client
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        error_msg = "SUPABASE_URL and SUPABASE_KEY must be set in environment variables"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        logger.info(f"Initializing Supabase client: {SUPABASE_URL}")
        
        # Create client without options (simpler approach)
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("✓ Supabase client initialized successfully")
        return _supabase_client
        
    except Exception as e:
        error_msg = f"Failed to initialize Supabase client: {e}"
        logger.error(error_msg)
        raise Exception(error_msg) from e


def test_supabase_connection() -> bool:
    """Test Supabase connection by executing a simple query."""
    try:
        logger.info("Testing Supabase connection...")
        supabase = get_supabase_client()
        response = supabase.table("organizations").select("id", count="exact").limit(1).execute()
        count = response.count if hasattr(response, 'count') else len(response.data)
        logger.info(f"✓ Supabase connection successful (found {count} organizations)")
        return True
    except APIError as e:
        logger.error(f"✗ Supabase API error: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Supabase connection failed: {e}")
        return False


def get_mongo_client() -> MongoClient:
    """
    Get or create a MongoDB client instance with connection pooling.
    
    Returns:
        MongoClient: Configured MongoDB client instance
        
    Raises:
        ValueError: If MONGO_URI is not set
        ConnectionFailure: If connection to MongoDB fails
    """
    global _mongo_client
    
    if _mongo_client is not None:
        return _mongo_client
    
    if not MONGO_URI:
        error_msg = "MONGO_URI must be set in environment variables"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        logger.info(f"Initializing MongoDB client...")
        
        _mongo_client = MongoClient(
            MONGO_URI,
            maxPoolSize=MONGO_MAX_POOL_SIZE,
            minPoolSize=MONGO_MIN_POOL_SIZE,
            serverSelectionTimeoutMS=MONGO_SERVER_SELECTION_TIMEOUT_MS,
            connectTimeoutMS=MONGO_CONNECT_TIMEOUT_MS,
            retryWrites=True,
            retryReads=True,
            w="majority",
            readPreference="primary"
        )
        
        _mongo_client.admin.command('ping')
        logger.info(f"✓ MongoDB client initialized successfully")
        logger.info(f"  Pool size: {MONGO_MIN_POOL_SIZE}-{MONGO_MAX_POOL_SIZE}")
        logger.info(f"  Database: {MONGO_DB}")
        return _mongo_client
        
    except ConnectionFailure as e:
        error_msg = f"Failed to connect to MongoDB: {e}"
        logger.error(error_msg)
        raise ConnectionFailure(error_msg) from e
    except ServerSelectionTimeoutError as e:
        error_msg = f"MongoDB server selection timeout (is MongoDB running?): {e}"
        logger.error(error_msg)
        raise ServerSelectionTimeoutError(error_msg) from e
    except Exception as e:
        error_msg = f"Failed to initialize MongoDB client: {e}"
        logger.error(error_msg)
        raise Exception(error_msg) from e


def get_mongo_database():
    """Get the MongoDB database instance."""
    client = get_mongo_client()
    return client[MONGO_DB]


def close_mongo_client() -> None:
    """Close the MongoDB client connection."""
    global _mongo_client
    if _mongo_client is not None:
        logger.info("Closing MongoDB client connection...")
        _mongo_client.close()
        _mongo_client = None
        logger.info("✓ MongoDB client closed")


def test_mongo_connection() -> bool:
    """Test MongoDB connection by executing a ping command."""
    try:
        logger.info("Testing MongoDB connection...")
        client = get_mongo_client()
        result = client.admin.command('ping')
        
        if result.get('ok') == 1.0:
            db = get_mongo_database()
            stats = db.command('dbStats')
            logger.info(f"✓ MongoDB connection successful")
            logger.info(f"  Database: {MONGO_DB}")
            logger.info(f"  Collections: {stats.get('collections', 0)}")
            logger.info(f"  Data size: {stats.get('dataSize', 0) / 1024:.2f} KB")
            return True
        else:
            logger.error("✗ MongoDB ping failed")
            return False
    except ConnectionFailure as e:
        logger.error(f"✗ MongoDB connection failure: {e}")
        return False
    except ServerSelectionTimeoutError as e:
        logger.error(f"✗ MongoDB server selection timeout: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ MongoDB connection test failed: {e}")
        return False


@contextmanager
def MongoConnection():
    """
    Context manager for MongoDB database connection.
    
    Yields:
        Database: MongoDB database instance
    """
    db = None
    try:
        db = get_mongo_database()
        logger.debug("MongoDB connection acquired from pool")
        yield db
    except ConnectionFailure as e:
        logger.error(f"MongoDB connection failure in context: {e}")
        raise
    except Exception as e:
        logger.error(f"Error in MongoDB context: {e}")
        raise
    finally:
        if db is not None:
            logger.debug("MongoDB connection returned to pool")


@contextmanager
def SupabaseConnection():
    """
    Context manager for Supabase client.
    
    Yields:
        Client: Supabase client instance
    """
    client = None
    try:
        client = get_supabase_client()
        logger.debug("Supabase client acquired")
        yield client
    except APIError as e:
        logger.error(f"Supabase API error in context: {e}")
        raise
    except Exception as e:
        logger.error(f"Error in Supabase context: {e}")
        raise
    finally:
        if client is not None:
            logger.debug("Supabase client context closed")


def test_connections() -> Dict[str, bool]:
    """
    Test connections to both Supabase and MongoDB.
    
    Returns:
        Dict[str, bool]: Connection test results
    """
    logger.info("=" * 80)
    logger.info("TESTING DATABASE CONNECTIONS")
    logger.info("=" * 80)
    
    results = {
        "supabase": False,
        "mongodb": False,
        "all_connected": False
    }
    
    logger.info("\n1. Testing Supabase (PostgreSQL source)...")
    results["supabase"] = test_supabase_connection()
    
    logger.info("\n2. Testing MongoDB (target)...")
    results["mongodb"] = test_mongo_connection()
    
    results["all_connected"] = results["supabase"] and results["mongodb"]
    
    logger.info("\n" + "=" * 80)
    if results["all_connected"]:
        logger.info("✅ ALL CONNECTIONS SUCCESSFUL")
    else:
        logger.error("❌ CONNECTION FAILURES DETECTED")
        if not results["supabase"]:
            logger.error("  • Supabase connection failed")
        if not results["mongodb"]:
            logger.error("  • MongoDB connection failed")
    logger.info("=" * 80 + "\n")
    
    return results


def get_connection_info() -> Dict[str, Any]:
    """Get information about current connection configuration."""
    return {
        "supabase": {
            "url": SUPABASE_URL,
            "key_set": bool(SUPABASE_KEY),
            "connected": _supabase_client is not None
        },
        "mongodb": {
            "uri": MONGO_URI.split('@')[1] if '@' in MONGO_URI else MONGO_URI,
            "database": MONGO_DB,
            "pool_size": f"{MONGO_MIN_POOL_SIZE}-{MONGO_MAX_POOL_SIZE}",
            "timeout_ms": MONGO_SERVER_SELECTION_TIMEOUT_MS,
            "connected": _mongo_client is not None
        },
        "etl": {
            "batch_size": BATCH_SIZE,
            "log_level": LOG_LEVEL
        }
    }


def main():
    """Main function for testing connections."""
    results = test_connections()
    
    logger.info("\nConnection Configuration:")
    info = get_connection_info()
    
    logger.info("\nSupabase:")
    logger.info(f"  URL: {info['supabase']['url']}")
    logger.info(f"  Key set: {info['supabase']['key_set']}")
    logger.info(f"  Connected: {info['supabase']['connected']}")
    
    logger.info("\nMongoDB:")
    logger.info(f"  URI: {info['mongodb']['uri']}")
    logger.info(f"  Database: {info['mongodb']['database']}")
    logger.info(f"  Pool size: {info['mongodb']['pool_size']}")
    logger.info(f"  Timeout: {info['mongodb']['timeout_ms']}ms")
    logger.info(f"  Connected: {info['mongodb']['connected']}")
    
    logger.info("\nETL Settings:")
    logger.info(f"  Batch size: {info['etl']['batch_size']}")
    logger.info(f"  Log level: {info['etl']['log_level']}")
    
    close_mongo_client()
    exit(0 if results["all_connected"] else 1)


if __name__ == "__main__":
    main()

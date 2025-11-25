#!/usr/bin/env python3
"""
Test script for ETL configuration module.
Demonstrates usage of connection functions and context managers.
"""

from config import (
    get_supabase_client,
    get_mongo_client,
    get_mongo_database,
    MongoConnection,
    SupabaseConnection,
    test_connections,
    get_connection_info
)


def test_direct_connections():
    """Test direct connection functions."""
    print("\n" + "=" * 80)
    print("TEST 1: Direct Connection Functions")
    print("=" * 80)
    
    # Supabase
    print("\n1. Testing Supabase client...")
    supabase = get_supabase_client()
    response = supabase.table("organizations").select("id, name").limit(3).execute()
    print(f"   ✓ Retrieved {len(response.data)} organizations:")
    for org in response.data:
        print(f"     - {org['name']}")
    
    # MongoDB
    print("\n2. Testing MongoDB client...")
    db = get_mongo_database()
    collections = db.list_collection_names()
    print(f"   ✓ Found {len(collections)} collections:")
    for coll in collections:
        count = db[coll].count_documents({})
        print(f"     - {coll}: {count} documents")


def test_context_managers():
    """Test context manager usage."""
    print("\n" + "=" * 80)
    print("TEST 2: Context Managers")
    print("=" * 80)
    
    # Supabase context manager
    print("\n1. Using SupabaseConnection context manager...")
    with SupabaseConnection() as supabase:
        response = supabase.table("users").select("id, name, email").limit(3).execute()
        print(f"   ✓ Retrieved {len(response.data)} users:")
        for user in response.data:
            print(f"     - {user['name']} ({user['email']})")
    
    # MongoDB context manager
    print("\n2. Using MongoConnection context manager...")
    with MongoConnection() as db:
        # Try to query (even though collections are empty)
        users_count = db.users.count_documents({})
        projects_count = db.projects.count_documents({})
        print(f"   ✓ MongoDB query successful:")
        print(f"     - Users: {users_count}")
        print(f"     - Projects: {projects_count}")


def test_connection_info():
    """Test connection info function."""
    print("\n" + "=" * 80)
    print("TEST 3: Connection Information")
    print("=" * 80)
    
    info = get_connection_info()
    
    print("\nSupabase Configuration:")
    print(f"  URL: {info['supabase']['url']}")
    print(f"  Key configured: {info['supabase']['key_set']}")
    print(f"  Client initialized: {info['supabase']['connected']}")
    
    print("\nMongoDB Configuration:")
    print(f"  URI: {info['mongodb']['uri']}")
    print(f"  Database: {info['mongodb']['database']}")
    print(f"  Connection pool: {info['mongodb']['pool_size']}")
    print(f"  Timeout: {info['mongodb']['timeout_ms']}ms")
    print(f"  Client initialized: {info['mongodb']['connected']}")
    
    print("\nETL Settings:")
    print(f"  Batch size: {info['etl']['batch_size']}")
    print(f"  Log level: {info['etl']['log_level']}")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("ETL CONFIGURATION MODULE TESTS")
    print("=" * 80)
    
    # First test connections
    results = test_connections()
    
    if not results["all_connected"]:
        print("\n❌ Cannot proceed with tests - connection failures detected")
        return
    
    # Run tests
    test_direct_connections()
    test_context_managers()
    test_connection_info()
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

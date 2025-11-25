# MongoDB Best Practices & Agent Guidelines

This document provides comprehensive guidelines for AI agents working with MongoDB, specifically for database migration scenarios.

## Table of Contents
1. [Schema Design Principles](#schema-design-principles)
2. [Indexing Standards](#indexing-standards)
3. [Query Patterns](#query-patterns)
4. [Data Modeling Rules](#data-modeling-rules)
5. [Python/PyMongo Standards](#pythonpymongo-standards)
6. [Migration-Specific Guidelines](#migration-specific-guidelines)
7. [Performance Considerations](#performance-considerations)
8. [Code Style](#code-style)

---

## Schema Design Principles

### When to Embed vs Reference

**Embed When:**
- Data is accessed together (one-to-one, one-to-few)
- Child data has no meaning outside parent context
- Data doesn't change frequently
- Document size stays under 16MB
- Example: Comments embedded in tasks, addresses in user profiles

**Reference When:**
- Many-to-many relationships
- Data is accessed independently
- Data is shared across multiple documents
- Unbounded growth potential (one-to-many where "many" is large)
- Example: Users referenced in multiple organizations

### Document Size Limits

**Hard Rules:**
- Maximum document size: 16MB
- Maximum nesting depth: 100 levels (practical limit ~10)
- Maximum array size: No hard limit, but keep under 1000 items for performance

**Best Practices:**
- Keep documents under 1MB for optimal performance
- If arrays grow unbounded, use references instead
- Monitor document sizes during migration

### Avoiding Unbounded Growth

**Anti-Pattern:**
```javascript
// BAD: Unbounded array growth
{
  "task_id": 1,
  "comments": [/* could grow to thousands */]
}
```

**Solution 1: Bucket Pattern**
```javascript
// GOOD: Limited bucket size
{
  "task_id": 1,
  "comment_bucket": 1,
  "comments": [/* max 100 comments */]
}
```

**Solution 2: Separate Collection**
```javascript
// GOOD: Separate collection with reference
// tasks collection
{ "task_id": 1, "title": "..." }

// comments collection
{ "task_id": 1, "content": "...", "created_at": "..." }
```

---

## Indexing Standards

### Index Creation Rules

**Always Index:**
- Fields used in queries (WHERE clauses)
- Fields used in sorts (ORDER BY)
- Fields used in joins (lookups)
- Unique identifiers

**Index Types:**

1. **Single Field Index**
```python
db.tasks.create_index("status")
db.tasks.create_index("due_date")
```

2. **Compound Index** (order matters!)
```python
# Query: find tasks by status, sort by due_date
db.tasks.create_index([("status", 1), ("due_date", 1)])
```

3. **Text Index** (for full-text search)
```python
db.tasks.create_index([("title", "text"), ("description", "text")])
```

4. **Unique Index**
```python
db.users.create_index("email", unique=True)
```

### Index Naming Conventions

**Format:** `{field1}_{direction}_{field2}_{direction}`

```python
# Single field
db.tasks.create_index("status", name="status_1")

# Compound
db.tasks.create_index(
    [("project_id", 1), ("status", 1)],
    name="project_id_1_status_1"
)
```

### Index Guidelines

- **Limit indexes**: Each index has write overhead (max 64 indexes per collection)
- **Compound index order**: Most selective field first, then sort fields
- **Covered queries**: Include all query fields in index for best performance
- **Monitor index usage**: Remove unused indexes

---

## Query Patterns

### Efficient Query Structures

**DO:**
```python
# Use projection to limit returned fields
db.tasks.find(
    {"status": "in_progress"},
    {"title": 1, "due_date": 1, "_id": 0}
)

# Use limit for pagination
db.tasks.find({"status": "todo"}).limit(20)

# Use specific field matching
db.tasks.find({"status": "completed", "priority": "high"})
```

**DON'T:**
```python
# Avoid returning all fields when not needed
db.tasks.find({"status": "in_progress"})  # Returns everything

# Avoid regex without anchors (can't use index)
db.tasks.find({"title": {"$regex": ".*bug.*"}})

# Avoid $where or $expr when possible (slow)
db.tasks.find({"$where": "this.field1 > this.field2"})
```

### Aggregation Pipeline Best Practices

**Optimize Pipeline Order:**
1. `$match` - Filter early to reduce documents
2. `$project` - Reduce fields early
3. `$sort` - Sort before limit
4. `$limit` - Limit results
5. `$lookup` - Join last (expensive)

**Example:**
```python
pipeline = [
    {"$match": {"status": "in_progress"}},  # Filter first
    {"$project": {"title": 1, "due_date": 1}},  # Reduce fields
    {"$sort": {"due_date": 1}},  # Sort
    {"$limit": 20},  # Limit results
    {"$lookup": {  # Join last
        "from": "users",
        "localField": "assignee_id",
        "foreignField": "_id",
        "as": "assignee"
    }}
]
```

### Common Anti-Patterns to Avoid

1. **N+1 Queries**: Use aggregation or embed data instead
2. **Missing Indexes**: Always index query fields
3. **Large $in Arrays**: Keep under 1000 items
4. **Unbounded $lookup**: Can cause memory issues
5. **Client-Side Joins**: Do joins in database when possible

---

## Data Modeling Rules

### One-to-One Relationships

**Embed in Parent Document:**
```javascript
{
  "_id": ObjectId("..."),
  "name": "Alice Johnson",
  "email": "alice@example.com",
  "profile": {
    "bio": "Software engineer",
    "avatar_url": "https://...",
    "timezone": "America/New_York"
  }
}
```

### One-to-Many Relationships

**Few (< 100): Embed**
```javascript
{
  "_id": ObjectId("..."),
  "task_title": "Build feature",
  "comments": [
    {"user": "Alice", "content": "Looks good", "created_at": "..."},
    {"user": "Bob", "content": "Approved", "created_at": "..."}
  ]
}
```

**Many (> 100): Reference**
```javascript
// tasks collection
{
  "_id": ObjectId("task1"),
  "title": "Build feature"
}

// comments collection
{
  "_id": ObjectId("..."),
  "task_id": ObjectId("task1"),
  "user": "Alice",
  "content": "Looks good"
}
```

### Many-to-Many Relationships

**Option 1: Array of References (Preferred)**
```javascript
// users collection
{
  "_id": ObjectId("user1"),
  "name": "Alice",
  "organization_ids": [ObjectId("org1"), ObjectId("org2")]
}

// organizations collection
{
  "_id": ObjectId("org1"),
  "name": "Acme Corp",
  "member_ids": [ObjectId("user1"), ObjectId("user2")]
}
```

**Option 2: Junction Collection (When metadata needed)**
```javascript
// org_members collection
{
  "_id": ObjectId("..."),
  "org_id": ObjectId("org1"),
  "user_id": ObjectId("user1"),
  "role": "admin",
  "joined_at": "2024-01-15"
}
```

### Polymorphic Pattern

When documents in a collection have different structures:

```javascript
// activities collection
{
  "_id": ObjectId("..."),
  "type": "task_created",
  "task_id": ObjectId("..."),
  "created_by": "Alice",
  "created_at": "..."
}

{
  "_id": ObjectId("..."),
  "type": "comment_added",
  "task_id": ObjectId("..."),
  "comment_id": ObjectId("..."),
  "created_by": "Bob",
  "created_at": "..."
}
```

**Index on type field:**
```python
db.activities.create_index("type")
```

### Attribute Pattern

For sparse fields or dynamic attributes:

```javascript
{
  "_id": ObjectId("..."),
  "task_title": "Build feature",
  "custom_fields": [
    {"key": "estimated_hours", "value": 8},
    {"key": "complexity", "value": "high"},
    {"key": "client_name", "value": "Acme Corp"}
  ]
}
```

**Index for searching:**
```python
db.tasks.create_index("custom_fields.key")
db.tasks.create_index("custom_fields.value")
```

---

## Python/PyMongo Standards

### Connection Management

**DO:**
```python
from pymongo import MongoClient
from contextlib import contextmanager

class DatabaseConnection:
    def __init__(self, uri):
        self.client = MongoClient(uri)
        self.db = self.client.get_database()
    
    def close(self):
        self.client.close()
    
    @contextmanager
    def get_collection(self, name):
        try:
            yield self.db[name]
        except Exception as e:
            print(f"Error accessing collection {name}: {e}")
            raise

# Usage
conn = DatabaseConnection("mongodb://localhost:27017/mydb")
with conn.get_collection("tasks") as tasks:
    tasks.find_one({"_id": task_id})
conn.close()
```

### Error Handling

**Always Handle:**
- `ConnectionFailure`: Network issues
- `DuplicateKeyError`: Unique constraint violations
- `BulkWriteError`: Batch operation failures
- `OperationFailure`: General operation errors

```python
from pymongo.errors import DuplicateKeyError, BulkWriteError

try:
    db.users.insert_one({"email": "alice@example.com"})
except DuplicateKeyError:
    print("User already exists")
except Exception as e:
    print(f"Unexpected error: {e}")
    raise
```

### Batch Operations

**Use Bulk Operations for Performance:**

```python
from pymongo import InsertOne, UpdateOne

# Prepare bulk operations
operations = [
    InsertOne({"name": "Alice", "email": "alice@example.com"}),
    InsertOne({"name": "Bob", "email": "bob@example.com"}),
    UpdateOne({"email": "carol@example.com"}, {"$set": {"name": "Carol"}})
]

# Execute in batches
try:
    result = db.users.bulk_write(operations, ordered=False)
    print(f"Inserted: {result.inserted_count}")
    print(f"Modified: {result.modified_count}")
except BulkWriteError as e:
    print(f"Errors: {e.details}")
```

**Batch Size Guidelines:**
- Default batch size: 1000 documents
- Adjust based on document size
- Monitor memory usage

### Type Hints and Validation

**Use Type Hints:**
```python
from typing import Dict, List, Optional
from bson import ObjectId

def get_task_by_id(task_id: ObjectId) -> Optional[Dict]:
    """Retrieve a task by its ID."""
    return db.tasks.find_one({"_id": task_id})

def get_tasks_by_status(status: str) -> List[Dict]:
    """Retrieve all tasks with given status."""
    return list(db.tasks.find({"status": status}))
```

### Transaction Usage

**Use Transactions for Multi-Document Operations:**

```python
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client.mydb

with client.start_session() as session:
    with session.start_transaction():
        try:
            # Multiple operations that must succeed together
            db.accounts.update_one(
                {"_id": account1_id},
                {"$inc": {"balance": -100}},
                session=session
            )
            db.accounts.update_one(
                {"_id": account2_id},
                {"$inc": {"balance": 100}},
                session=session
            )
            # Transaction commits automatically if no exception
        except Exception as e:
            # Transaction aborts automatically on exception
            print(f"Transaction failed: {e}")
            raise
```

**Note:** Transactions require MongoDB 4.0+ and replica set or sharded cluster.

---

## Migration-Specific Guidelines

### Data Transformation Patterns

**1. Handling NULL Values**

```python
# PostgreSQL NULL -> MongoDB
def transform_field(value):
    """Convert NULL to None or omit field."""
    return None if value is None else value

# Or omit field entirely
document = {
    k: v for k, v in data.items() 
    if v is not None
}
```

**2. Date/Timestamp Conversion**

```python
from datetime import datetime

# PostgreSQL timestamp -> MongoDB ISODate
def convert_timestamp(pg_timestamp):
    """Convert PostgreSQL timestamp to Python datetime."""
    if isinstance(pg_timestamp, str):
        return datetime.fromisoformat(pg_timestamp)
    return pg_timestamp

# Usage
document = {
    "created_at": convert_timestamp(row['created_at'])
}
```

**3. ID Mapping Strategy**

```python
from bson import ObjectId

# Keep original IDs for reference during migration
id_mapping = {}

def map_id(original_id: int) -> ObjectId:
    """Map relational ID to MongoDB ObjectId."""
    if original_id not in id_mapping:
        id_mapping[original_id] = ObjectId()
    return id_mapping[original_id]

# Usage
document = {
    "_id": map_id(row['id']),
    "original_id": row['id']  # Keep for validation
}
```

**4. Many-to-Many Transformation**

```python
# From junction table to embedded array
def transform_task_with_assignees(task, assignees):
    """Transform task with assignees from junction table."""
    return {
        "_id": map_id(task['id']),
        "title": task['title'],
        "assignees": [
            {
                "user_id": map_id(a['user_id']),
                "name": a['user_name'],
                "email": a['user_email']
            }
            for a in assignees
        ]
    }
```

### Validation Approaches

**1. Count Validation**

```python
def validate_counts(pg_conn, mongo_db):
    """Compare record counts between databases."""
    results = {}
    
    # PostgreSQL counts
    pg_cursor = pg_conn.cursor()
    pg_cursor.execute("SELECT COUNT(*) FROM tasks")
    pg_count = pg_cursor.fetchone()[0]
    
    # MongoDB counts
    mongo_count = mongo_db.tasks.count_documents({})
    
    results['tasks'] = {
        'postgres': pg_count,
        'mongodb': mongo_count,
        'match': pg_count == mongo_count
    }
    
    return results
```

**2. Sample Data Validation**

```python
def validate_sample_data(pg_conn, mongo_db, sample_size=10):
    """Compare sample records between databases."""
    pg_cursor = pg_conn.cursor()
    pg_cursor.execute("SELECT * FROM tasks LIMIT %s", (sample_size,))
    
    for pg_row in pg_cursor.fetchall():
        mongo_doc = mongo_db.tasks.find_one({"original_id": pg_row['id']})
        
        if not mongo_doc:
            print(f"Missing task {pg_row['id']} in MongoDB")
            continue
        
        # Compare fields
        if pg_row['title'] != mongo_doc['title']:
            print(f"Title mismatch for task {pg_row['id']}")
```

**3. Relationship Validation**

```python
def validate_relationships(mongo_db):
    """Verify referential integrity in MongoDB."""
    # Check that all referenced IDs exist
    tasks = mongo_db.tasks.find({})
    
    for task in tasks:
        # Validate project exists
        project = mongo_db.projects.find_one({"_id": task['project_id']})
        if not project:
            print(f"Task {task['_id']} references missing project")
        
        # Validate assignees exist
        for assignee in task.get('assignees', []):
            user = mongo_db.users.find_one({"_id": assignee['user_id']})
            if not user:
                print(f"Task {task['_id']} references missing user")
```

---

## Performance Considerations

### Bulk Write Operations

**Always Use Bulk Operations for Large Datasets:**

```python
from pymongo import InsertOne

def bulk_insert(collection, documents, batch_size=1000):
    """Insert documents in batches."""
    operations = []
    
    for doc in documents:
        operations.append(InsertOne(doc))
        
        if len(operations) >= batch_size:
            collection.bulk_write(operations, ordered=False)
            operations = []
    
    # Insert remaining
    if operations:
        collection.bulk_write(operations, ordered=False)
```

### Connection Pooling

**Configure Connection Pool:**

```python
from pymongo import MongoClient

client = MongoClient(
    "mongodb://localhost:27017/",
    maxPoolSize=50,  # Max connections
    minPoolSize=10,  # Min connections
    maxIdleTimeMS=45000,  # Close idle connections
    waitQueueTimeoutMS=5000  # Wait timeout
)
```

### Write Concerns

**Choose Appropriate Write Concern:**

```python
from pymongo import WriteConcern

# Default: Acknowledge from primary
db.tasks.insert_one(
    {"title": "Task"},
    write_concern=WriteConcern(w=1)
)

# Majority: Acknowledge from majority of replica set
db.tasks.insert_one(
    {"title": "Important Task"},
    write_concern=WriteConcern(w="majority", wtimeout=5000)
)

# Unacknowledged: Fire and forget (fast but risky)
db.tasks.insert_one(
    {"title": "Log Entry"},
    write_concern=WriteConcern(w=0)
)
```

### Read Preferences

**Choose Read Preference Based on Use Case:**

```python
from pymongo import ReadPreference

# Primary: Read from primary (default, consistent)
db.tasks.find({}).read_preference(ReadPreference.PRIMARY)

# Secondary: Read from secondary (reduce primary load)
db.tasks.find({}).read_preference(ReadPreference.SECONDARY)

# Nearest: Read from nearest node (lowest latency)
db.tasks.find({}).read_preference(ReadPreference.NEAREST)
```

---

## Code Style

### Naming Conventions

**Collections:**
- Use plural nouns: `tasks`, `users`, `organizations`
- Use snake_case: `task_assignees`, `org_members`

**Fields:**
- Use snake_case: `created_at`, `user_id`, `task_title`
- Use descriptive names: `assignee_email` not `ae`
- Suffix IDs with `_id`: `user_id`, `project_id`

**Functions:**
- Use verb_noun pattern: `get_task`, `create_user`, `update_status`
- Be specific: `get_tasks_by_status` not `get_tasks`

### Function Organization

**Group Related Functions:**

```python
# extraction.py
def extract_organizations(pg_conn):
    """Extract all organizations from PostgreSQL."""
    pass

def extract_users(pg_conn):
    """Extract all users from PostgreSQL."""
    pass

# transformation.py
def transform_organization(org_data):
    """Transform organization data for MongoDB."""
    pass

def transform_user(user_data):
    """Transform user data for MongoDB."""
    pass

# loading.py
def load_organizations(mongo_db, organizations):
    """Load organizations into MongoDB."""
    pass

def load_users(mongo_db, users):
    """Load users into MongoDB."""
    pass
```

### Documentation Standards

**Docstring Format:**

```python
def migrate_tasks(pg_conn, mongo_db, batch_size=1000):
    """
    Migrate tasks from PostgreSQL to MongoDB.
    
    Args:
        pg_conn: PostgreSQL connection object
        mongo_db: MongoDB database object
        batch_size: Number of documents to insert per batch (default: 1000)
    
    Returns:
        dict: Migration statistics including counts and errors
    
    Raises:
        ConnectionError: If database connection fails
        ValueError: If invalid batch_size provided
    
    Example:
        >>> stats = migrate_tasks(pg_conn, mongo_db, batch_size=500)
        >>> print(f"Migrated {stats['inserted']} tasks")
    """
    pass
```

### Error Messages

**Provide Actionable Error Messages:**

```python
# BAD
raise Exception("Error")

# GOOD
raise ValueError(
    f"Invalid batch_size: {batch_size}. "
    f"Must be between 1 and 10000."
)

# BETTER
raise ValueError(
    f"Invalid batch_size: {batch_size}. "
    f"Must be between 1 and 10000. "
    f"Recommended: 1000 for documents < 1KB, "
    f"100 for documents > 10KB."
)
```

### Logging

**Use Structured Logging:**

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def migrate_tasks(pg_conn, mongo_db):
    logger.info("Starting task migration")
    
    try:
        # Migration logic
        logger.info(f"Migrated {count} tasks successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise
```

---

## Summary Checklist

When working with MongoDB migrations, ensure:

- [ ] Schema design considers read/write patterns
- [ ] Embed vs. reference decisions are documented
- [ ] All query fields are indexed
- [ ] Bulk operations are used for large datasets
- [ ] Error handling covers all database operations
- [ ] Validation compares source and target data
- [ ] Document sizes stay under 16MB
- [ ] Arrays don't grow unbounded
- [ ] Type hints are used for all functions
- [ ] Code is well-documented with docstrings
- [ ] Logging provides useful debugging information
- [ ] Connection pooling is configured appropriately

---

**Remember:** MongoDB is flexible, but with flexibility comes responsibility. Always consider the trade-offs of your design decisions and validate thoroughly.

# ETL Scripts

This directory will contain the Python scripts for extracting data from Postgres, transforming it for MongoDB, and loading it into the target database.

## Overview

The ETL (Extract, Transform, Load) process migrates data from a relational database structure to a document-oriented structure, handling the transformation from normalized tables to denormalized documents.

## Suggested File Structure

During the demo, you might create the following files:

### `config.py`
Database connection management for both source and target databases.

**Responsibilities:**
- Load environment variables
- Create database connections
- Provide connection objects to other modules
- Handle connection pooling and cleanup

### `extract.py`
Extract data from the Postgres source database.

**Responsibilities:**
- Connect to Supabase/Postgres
- Query all relevant tables
- Handle relationships and joins
- Return data in a structured format

**Key Considerations:**
- Efficient querying (avoid N+1 queries)
- Handle large datasets with pagination
- Preserve relationships between entities

### `transform.py`
Transform relational data into MongoDB document structure.

**Responsibilities:**
- Convert normalized data to denormalized documents
- Decide what to embed vs. reference
- Handle data type conversions
- Map relational IDs to MongoDB ObjectIds

**Key Considerations:**
- Denormalization strategy (embed vs. reference)
- Document size limits (16MB max)
- Array size considerations
- Data duplication trade-offs

### `load.py`
Load transformed data into MongoDB.

**Responsibilities:**
- Insert documents into MongoDB collections
- Handle bulk operations for performance
- Manage errors and retries
- Maintain referential consistency

**Key Considerations:**
- Use bulk operations for efficiency
- Handle duplicate key errors
- Maintain insertion order for dependencies
- Transaction support if needed

### `migrate.py`
Main orchestrator that runs the complete migration.

**Responsibilities:**
- Coordinate extract, transform, and load phases
- Provide progress reporting
- Handle errors and rollback if needed
- Log migration statistics

**Typical Flow:**
1. Connect to both databases
2. Extract data from Postgres
3. Transform data for MongoDB
4. Load data into MongoDB
5. Report results and statistics

### `validate.py`
Validation queries to verify migration success.

**Responsibilities:**
- Compare record counts between databases
- Verify data integrity
- Check for missing or duplicate data
- Generate validation report

**Validation Checks:**
- Count of documents matches source records
- Sample data comparison
- Relationship integrity
- Data type correctness

## General Approach

### Phase 1: Extract
1. Query organizations, users, and org_members
2. Query projects with organization details
3. Query tasks with project details
4. Query labels, task_labels, task_assignees
5. Query comments with user details

### Phase 2: Transform
1. Decide on document schema (embed vs. reference)
2. Group related data together
3. Denormalize frequently accessed data
4. Handle NULL values and data type conversions

### Phase 3: Load
1. Create collections and indexes
2. Insert documents in correct order (handle dependencies)
3. Use bulk operations for performance
4. Verify insertion success

## Common Patterns

### Pattern 1: Embed One-to-Many
When a parent has a limited number of children that are always accessed together:
```python
# Relational: tasks table + comments table
# Document: Embed comments in task document
{
  "task": {...},
  "comments": [
    {"user": {...}, "content": "..."},
    {"user": {...}, "content": "..."}
  ]
}
```

### Pattern 2: Reference Many-to-Many
When entities have independent lifecycles:
```python
# Keep as separate collections with references
# Users collection and Organizations collection
# Reference by ID in application code
```

### Pattern 3: Denormalize Frequently Accessed Data
When you need to avoid lookups:
```python
# Instead of just storing user_id
# Store commonly needed user fields
{
  "assignee_id": "user123",
  "assignee_name": "Alice Johnson",
  "assignee_email": "alice@example.com"
}
```

## Tips for Implementation

1. **Start Simple**: Begin with a basic schema, iterate as needed
2. **Test with Small Dataset**: Validate logic before full migration
3. **Use Transactions**: For multi-document operations that must succeed together
4. **Monitor Performance**: Track execution time and optimize bottlenecks
5. **Validate Early**: Check data integrity at each phase
6. **Handle Errors Gracefully**: Log errors, continue processing when possible
7. **Make It Idempotent**: Allow re-running without duplicating data

## Environment Variables Required

Make sure your `.env` file contains:
- Supabase/Postgres connection details
- MongoDB connection details
- Optional: batch size, log level, etc.

## Running the Migration

Once implemented, the migration would typically be run as:

```bash
python etl/migrate.py
```

And validation:

```bash
python etl/validate.py
```

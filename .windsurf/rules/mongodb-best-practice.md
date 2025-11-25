---
trigger: model_decision
description: Guidelines for AI agents working with MongoDB and database migrations.
---

# MongoDB Agent Rules
---
## Schema Design

### Embed vs Reference

**Embed data** when it's accessed together, has no meaning outside the parent, changes infrequently, and keeps documents under 16MB. Good for one-to-one and one-to-few relationships like comments on tasks or addresses in user profiles.

**Reference data** when you have many-to-many relationships, data accessed independently, shared across documents, or unbounded growth potential. Use separate collections with ID references.

### Document Limits

- **Hard limit**: 16MB per document, 100 nesting levels
- **Practical targets**: Keep documents under 1MB, arrays under 1000 items, nesting under 10 levels
- **Unbounded arrays**: Move to separate collection or use bucket pattern with fixed-size chunks

---

## Indexing

### When to Index

Index all fields used in queries, sorts, and lookups. Always index unique identifiers. Use compound indexes for multi-field queries, placing the most selective field first, then sort fields.

### Index Rules

- Name indexes as `{field}_{direction}` (e.g., `status_1`, `project_id_1_status_1`)
- Limit to necessary indexes only—each adds write overhead
- Maximum 64 indexes per collection
- Remove unused indexes; monitor usage regularly

---

## Query Patterns

### Best Practices

- Always use projection to return only needed fields
- Apply `limit()` for pagination
- Use specific field matching over broad queries
- Avoid regex without anchors, `$where`, and `$expr` when possible

### Aggregation Pipeline Order

Structure pipelines for efficiency: `$match` first to filter early, then `$project` to reduce fields, `$sort` before `$limit`, and `$lookup` last since joins are expensive.

### Anti-Patterns to Avoid

- **N+1 queries**: Use aggregation or embedding instead
- **Large `$in` arrays**: Keep under 1000 items
- **Client-side joins**: Do joins in the database
- **Missing indexes**: Always index query fields

---

## Data Modeling

### Relationship Patterns

- **One-to-one**: Embed in parent document
- **One-to-few** (under 100): Embed as array
- **One-to-many** (over 100): Use separate collection with references
- **Many-to-many**: Use arrays of references on both sides, or a junction collection when you need relationship metadata

### Special Patterns

- **Polymorphic**: Store different document types in one collection with a `type` field; index the type field
- **Attribute pattern**: Use key-value arrays for sparse or dynamic fields; index both key and value

---

## Python/PyMongo Standards

### Connection & Error Handling

Use context managers for connections. Always close connections when done. Handle `ConnectionFailure`, `DuplicateKeyError`, `BulkWriteError`, and `OperationFailure` explicitly.

### Batch Operations

Use `bulk_write()` for large datasets with batch sizes around 1000 documents. Adjust based on document size. Use `ordered=False` when operation order doesn't matter for better performance.

### Transactions

Use transactions for multi-document operations that must succeed or fail together. Requires MongoDB 4.0+ with replica set or sharded cluster. Session context managers handle commit/abort automatically.

### Type Hints

Always use type hints with `Optional[Dict]`, `List[Dict]`, and `ObjectId` types for MongoDB operations.

---

## Migration Guidelines

### Data Transformation

- **NULLs**: Convert to `None` or omit field entirely
- **Timestamps**: Convert to Python `datetime` objects for proper ISODate storage
- **ID mapping**: Maintain a mapping dictionary from source IDs to ObjectIds; preserve original IDs in a separate field for validation
- **Junction tables**: Transform to embedded arrays or reference arrays based on relationship size

### Validation

Validate migrations with three approaches:
1. **Count validation**: Compare record counts between source and target
2. **Sample validation**: Spot-check field values on sample records
3. **Relationship validation**: Verify all referenced IDs exist in target collections

---

## Performance

### Key Settings

- **Connection pooling**: Configure `maxPoolSize`, `minPoolSize`, and timeout settings
- **Write concern**: Use `w=1` for default, `w="majority"` for critical data, `w=0` only for non-critical logs
- **Read preference**: Use `PRIMARY` for consistency, `SECONDARY` to reduce primary load, `NEAREST` for lowest latency

---

## Code Style

### Naming Conventions

- **Collections**: Plural nouns in snake_case (`tasks`, `org_members`)
- **Fields**: snake_case with descriptive names; suffix IDs with `_id` (`user_id`, `created_at`)
- **Functions**: verb_noun pattern, be specific (`get_tasks_by_status`, not `get_tasks`)

### Organization

Group code by ETL phase: extraction functions, transformation functions, and loading functions in separate modules.

### Documentation

Use docstrings with Args, Returns, Raises, and Example sections. Provide actionable error messages with valid ranges and recommendations. Use structured logging with timestamps and log levels.

---

## Checklist

- Schema design matches read/write patterns
- Embed vs reference decisions documented
- All query fields indexed
- Bulk operations for large datasets
- Error handling on all database operations
- Validation compares source and target
- Documents under 16MB, arrays bounded
- Type hints on all functions
- Docstrings and structured logging

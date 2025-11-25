---
trigger: model_decision
description: Guidelines for writing Python code for the PostgreSQL to MongoDB migration.
---

# Python ETL Rules and Standards

---

## Project Structure

```
etl/
├── config.py      # Database connections (Supabase + MongoDB)
├── extract.py     # Source queries from Supabase
├── transform.py   # Data reshaping for MongoDB
├── load.py        # Target insertion to MongoDB
├── migrate.py     # Main orchestrator
└── validate.py    # Migration verification
```

---

## Code Standards

### Imports & Dependencies

- Use `supabase` client library for source database access
- Use `pymongo` for MongoDB operations (target runs in Docker)
- Use `python-dotenv` for environment variables
- Keep imports at the top of each file, grouped by standard library, third-party, then local modules

### Type Hints

Always use type hints on function signatures. Use `Optional[T]` for nullable values, `List[Dict]` for document collections, and `ObjectId` from `bson` for MongoDB IDs.

### Docstrings

Every function needs a docstring with a brief description, Args, Returns, and Raises sections. Keep them concise.

### Error Handling

- Wrap database operations in try/except blocks
- Handle `APIError` and `AuthApiError` from the Supabase client for source operations
- Handle `pymongo.errors.ConnectionFailure`, `DuplicateKeyError`, and `BulkWriteError` for MongoDB
- Log errors with context before re-raising
- Never silently swallow exceptions

---

## Configuration

### Environment Variables

Load all connection strings and credentials from environment variables using `python-dotenv`. Never hardcode credentials. Required variables:
- Supabase: `SUPABASE_URL` and `SUPABASE_KEY` (service role key for full access)
- MongoDB: connection URI (default `mongodb://localhost:27017` for Docker) and database name

### Connection Management

Initialize the Supabase client once using `create_client(url, key)` and reuse it. For MongoDB, use `MongoClient` with the Docker container's exposed port. Close MongoDB connections explicitly when done.

---

## Extraction

### Supabase Query Patterns

- Use the Supabase client's query builder: `response = (supabase.table("users").select("*").execute())`
- Fetch data in batches using `.range(start, end)` for large tables
- Use `.select("*, related_table(*)")` for related data to avoid N+1 patterns
- Select only needed columns in the select string, not `*` unless necessary

### Data Retrieval

Access results via `response.data` which returns a list of dictionaries. Preserve original IDs for mapping during transformation. Handle NULL values explicitly—Supabase returns `None` for nulls.

---

## Transformation

### ID Mapping

Maintain a dictionary mapping source integer IDs to MongoDB ObjectIds. Generate ObjectIds once and reuse them for consistency. Store original IDs in a separate field for validation.

### Data Conversion

- Convert PostgreSQL `NULL` to Python `None` or omit the field
- Convert timestamps to Python `datetime` objects
- Convert PostgreSQL arrays to Python lists
- Convert numeric types appropriately (Decimal to float if precision allows)

### Document Structure

Follow the MongoDB rules file for embed vs reference decisions. Denormalize frequently accessed fields like user names and emails. Keep documents under 1MB and arrays under 1000 items.

---

## Loading

### Bulk Operations

Always use `bulk_write()` for inserting multiple documents. Use batch sizes of 1000 documents by default. Set `ordered=False` when insertion order doesn't matter for better performance.

### Insertion Order

Insert collections in dependency order: organizations first, then users, then projects, then tasks, then comments. This ensures referenced documents exist before referencing documents.

### Idempotency

Design loads to be re-runnable. Use `upsert=True` with `UpdateOne` operations, or clear collections before re-loading. Check for existing documents before inserting.

---

## Validation

### Required Checks

1. **Count validation**: Total records in source equals documents in target
2. **Sample validation**: Spot-check 10-20 random records for field accuracy
3. **Relationship validation**: All referenced IDs exist in target collections

### Reporting

Print clear validation results with pass/fail status. Log discrepancies with specific record identifiers. Return a summary dictionary with counts and error details.

---

## Logging

Use Python's `logging` module with INFO level for progress and ERROR level for failures. Include timestamps in log format. Log at each phase: extraction start/complete, transformation progress, load batches, validation results.

---

## Naming Conventions

- **Functions**: `snake_case` with verb_noun pattern (`extract_users`, `transform_task`, `load_organizations`)
- **Variables**: `snake_case`, descriptive names (`user_count`, `batch_size`, `id_mapping`)
- **Constants**: `UPPER_SNAKE_CASE` (`BATCH_SIZE`, `MAX_RETRIES`)
- **Classes**: `PascalCase` (`DatabaseConnection`, `MigrationResult`)

---

## Checklist

- [ ] All credentials loaded from environment variables
- [ ] Type hints on all function signatures
- [ ] Docstrings on all functions
- [ ] Error handling with logging on all database operations
- [ ] Bulk operations for all multi-document inserts
- [ ] ID mapping maintained throughout transformation
- [ ] Validation checks implemented and passing
- [ ] Code runs without modification after generation

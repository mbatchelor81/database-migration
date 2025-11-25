# Demo Walkthrough: Postgres to MongoDB Migration

This guide provides step-by-step instructions with exact prompts to use during your 20-minute database migration demo.

## Table of Contents
1. [Pre-Demo Setup](#pre-demo-setup)
2. [Phase 1: Explore Source Schema (5 min)](#phase-1-explore-source-schema-5-min)
3. [Phase 2: Design MongoDB Schema (5 min)](#phase-2-design-mongodb-schema-5-min)
4. [Phase 3: Build ETL Pipeline (8 min)](#phase-3-build-etl-pipeline-8-min)
5. [Phase 4: Validation (2 min)](#phase-4-validation-2-min)
6. [Troubleshooting Prompts](#troubleshooting-prompts)
7. [Advanced Extensions](#advanced-extensions)

---

## Pre-Demo Setup

**Complete these steps 5-10 minutes before the demo:**

### 1. Environment Setup
```bash
# Navigate to project
cd database-migration

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### 2. Configure Supabase
- [ ] Supabase project created
- [ ] Schema executed (`source/schema.sql`)
- [ ] Seed data loaded (`source/seed_data.sql`)
- [ ] Credentials added to `.env` file
- [ ] Test connection with a simple query

### 3. Start MongoDB
```bash
cd sink
docker-compose up -d
cd ..

# Verify MongoDB is running
docker ps | grep mongodb
```

### 4. Verify Setup
```bash
# Test Supabase connection
python -c "from supabase import create_client; import os; from dotenv import load_dotenv; load_dotenv(); client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY')); print('Supabase OK')"

# Test MongoDB connection
python -c "from pymongo import MongoClient; import os; from dotenv import load_dotenv; load_dotenv(); client = MongoClient(os.getenv('MONGO_URI')); print('MongoDB OK')"
```

### 5. Open Files in IDE
- [ ] `source/schema.sql` (for reference)
- [ ] `docs/mongodb_best_practices.md` (for agent reference)
- [ ] Terminal ready for commands
- [ ] Browser tabs: Supabase dashboard, MongoDB (optional)

---

## Phase 1: Explore Source Schema (5 min)

**Goal:** Understand the relational structure and relationships.

### Prompt 1: Schema Analysis

**Say to Agent:**
```
Analyze the Postgres schema in source/schema.sql and explain:
1. The relational structure and table relationships
2. The many-to-many relationships and junction tables
3. The foreign key constraints
4. How data is normalized

Focus on understanding how organizations, projects, tasks, users, labels, and comments are related.
```

**Expected Output:**
- Description of 9 tables
- Explanation of relationships (1-to-many, many-to-many)
- Identification of junction tables (org_members, task_labels, task_assignees)
- Discussion of normalization

**Talking Points While Agent Responds:**
- "Notice how the relational model enforces referential integrity"
- "See the many-to-many relationships requiring junction tables"
- "This is typical of a normalized OLTP database"

---

### Prompt 2: Explore Sample Data

**Say to Agent:**
```
Create a Python script that connects to Supabase and shows me:
1. Sample data from organizations, projects, and tasks
2. A specific task with all its related data (assignees, labels, comments)
3. The SQL queries needed to fetch this data with JOINs

Save this as source/inspect_data.py and run it to show the results.
```

**Expected Output:**
- Python script with Supabase connection
- Queries showing JOINs across multiple tables
- Sample output displaying related data
- Demonstration of N+1 query problem potential

**Talking Points:**
- "See how many JOINs are needed to get complete task information"
- "This is where MongoDB's embedded documents can help"
- "Notice the complexity of fetching related data"

---

## Phase 2: Design MongoDB Schema (5 min)

**Goal:** Design an appropriate document schema for MongoDB.

### Prompt 3: Schema Design Strategy

**Say to Agent:**
```
Based on the relational schema we just explored, design a MongoDB document schema for this project management app. 

Consider these read patterns:
- Frequently display projects with all their tasks
- Often show tasks with assignees, labels, and comments together
- Need to list all organizations a user belongs to
- Search tasks by status, priority, and labels

Follow the guidelines in docs/mongodb_best_practices.md. Explain your decisions about what to embed vs. reference, and provide example documents for each collection.
```

**Expected Output:**
- Document schema design with rationale
- Example documents for main collections
- Explanation of embed vs. reference decisions
- Discussion of denormalization trade-offs

**Talking Points:**
- "Notice how we're optimizing for read patterns"
- "Embedding comments reduces the need for JOINs"
- "We're denormalizing user data in assignees for performance"
- "Trade-off: Data duplication vs. query performance"

---

### Prompt 4: Create Schema Definition

**Say to Agent:**
```
Create a Python script at sink/collections_schema.py that:
1. Defines the MongoDB collections based on the schema you designed
2. Creates appropriate indexes for our query patterns
3. Includes schema validation rules (optional but nice to have)
4. Has a function to initialize the collections and indexes

Include detailed comments explaining each index and why it's needed.
```

**Expected Output:**
- Python script with collection definitions
- Index creation for common queries
- Comments explaining design decisions
- Initialization function

**Talking Points:**
- "Indexes are crucial for query performance"
- "Compound indexes support multiple query patterns"
- "Schema validation is optional but adds safety"

---

## Phase 3: Build ETL Pipeline (8 min)

**Goal:** Create scripts to extract, transform, and load data.

### Prompt 5: Database Configuration

**Say to Agent:**
```
Create etl/config.py to manage connections to both Supabase and MongoDB. 

Include:
1. Functions to get Postgres and MongoDB connections using environment variables
2. Connection pooling configuration
3. Proper error handling for connection failures
4. Context managers for safe connection handling
5. A function to test both connections

Make it production-ready with proper logging.
```

**Expected Output:**
- Configuration module with connection management
- Error handling for connection issues
- Context managers for resource cleanup
- Connection testing function

**Talking Points:**
- "Proper connection management prevents resource leaks"
- "Environment variables keep credentials secure"
- "Connection pooling improves performance"

---

### Prompt 6: Data Extraction

**Say to Agent:**
```
Create etl/extract.py to extract all data from Postgres.

Include functions to:
1. Extract organizations with their members
2. Extract users with their organization memberships
3. Extract projects with organization details
4. Extract tasks with all related data (assignees, labels, comments) using efficient JOINs
5. Handle pagination for large datasets

Use efficient SQL queries to minimize database round trips. Add logging to track progress.
```

**Expected Output:**
- Extraction functions for each entity
- Efficient SQL with JOINs
- Pagination support
- Progress logging

**Talking Points:**
- "We're using JOINs to fetch related data efficiently"
- "Pagination prevents memory issues with large datasets"
- "Notice how we're avoiding N+1 queries"

---

### Prompt 7: Data Transformation

**Say to Agent:**
```
Create etl/transform.py to transform relational data into MongoDB documents.

Based on the schema design from Phase 2, implement:
1. Transform organizations with embedded member information
2. Transform projects with organization references
3. Transform tasks with embedded assignees, labels, and comments (denormalized)
4. Handle ID mapping from Postgres integers to MongoDB ObjectIds
5. Handle NULL values and data type conversions (especially timestamps)
6. Preserve original IDs for validation

Follow the patterns in docs/mongodb_best_practices.md. Add type hints and comprehensive docstrings.
```

**Expected Output:**
- Transformation functions for each entity
- ID mapping strategy
- Data type conversions
- Denormalization logic
- Type hints and documentation

**Talking Points:**
- "This is where we implement our embed vs. reference decisions"
- "Denormalizing user data in tasks for faster reads"
- "ID mapping allows us to maintain relationships"
- "Keeping original IDs helps with validation"

---

### Prompt 8: Data Loading

**Say to Agent:**
```
Create etl/load.py to load transformed data into MongoDB.

Include:
1. Functions to load each collection using bulk operations
2. Proper error handling for duplicate keys and other failures
3. Progress reporting (e.g., "Loaded 100/500 tasks...")
4. Maintain insertion order to handle dependencies (orgs before projects, projects before tasks)
5. Return statistics (inserted count, failed count, errors)

Use bulk_write for performance. Batch size should be configurable (default 1000).
```

**Expected Output:**
- Loading functions with bulk operations
- Error handling and recovery
- Progress reporting
- Statistics tracking
- Configurable batch size

**Talking Points:**
- "Bulk operations are much faster than individual inserts"
- "We handle errors gracefully to continue processing"
- "Order matters: must insert referenced documents first"

---

### Prompt 9: Migration Orchestrator

**Say to Agent:**
```
Create etl/migrate.py as the main script that orchestrates the entire migration.

It should:
1. Initialize connections to both databases
2. Run extraction, transformation, and loading in sequence
3. Show progress for each phase
4. Handle errors and provide rollback capability if needed
5. Display final statistics (total records migrated, time taken, any errors)
6. Include a --dry-run flag to test without actually loading data

Make it runnable from command line with: python etl/migrate.py
```

**Expected Output:**
- Main orchestration script
- Progress reporting for each phase
- Error handling and rollback
- Statistics summary
- Command-line interface

**Talking Points:**
- "This ties everything together"
- "Progress reporting helps monitor long-running migrations"
- "Dry-run mode is essential for testing"

---

## Phase 4: Validation (2 min)

**Goal:** Verify the migration was successful.

### Prompt 10: Validation Script

**Say to Agent:**
```
Create etl/validate.py to verify the migration was successful.

Include validation checks for:
1. Record counts match between Postgres and MongoDB for each entity
2. Sample data comparison (pick 5 random records and compare fields)
3. Relationship integrity (verify referenced IDs exist)
4. Data type correctness (dates, numbers, strings)
5. Generate a validation report with pass/fail for each check

Make it runnable with: python etl/validate.py
```

**Expected Output:**
- Comprehensive validation script
- Multiple validation checks
- Comparison logic
- Validation report
- Pass/fail indicators

**Talking Points:**
- "Validation is crucial for production migrations"
- "We check both counts and data quality"
- "Relationship integrity ensures no broken references"

---

### Prompt 11: Run Migration and Validate

**Say to Agent:**
```
Now let's run the complete migration:
1. First, run a dry-run to test: python etl/migrate.py --dry-run
2. Then run the actual migration: python etl/migrate.py
3. Finally, run validation: python etl/validate.py

Show me the output and any issues that need to be addressed.
```

**Expected Output:**
- Execution of migration
- Progress updates
- Final statistics
- Validation results
- Any errors or warnings

**Talking Points:**
- "Watch the progress as data flows through the pipeline"
- "See how bulk operations make this fast"
- "Validation confirms everything migrated correctly"

---

## Troubleshooting Prompts

Use these if you encounter issues during the demo:

### Connection Issues
```
The database connection is failing. Check the connection string in .env and add better error messages to help diagnose the issue.
```

### Performance Issues
```
The migration is running slowly. Optimize the bulk operations and increase the batch size. Show me the performance improvement.
```

### Data Mismatch
```
The validation is showing mismatched counts. Debug the extraction query for [entity] and show me what records are missing.
```

### Memory Issues
```
The script is using too much memory. Implement streaming/pagination for the extraction phase to process data in chunks.
```

### Schema Issues
```
I'm getting schema validation errors in MongoDB. Review the document structure and fix any field type mismatches.
```

---

## Advanced Extensions

If you have extra time or want to showcase more capabilities:

### Extension 1: Incremental Migration
```
Add support for incremental migration that only migrates records created or updated after a certain timestamp. This would be useful for keeping databases in sync during a gradual migration.
```

### Extension 2: Data Comparison Tool
```
Create a tool that compares specific records between Postgres and MongoDB to find any discrepancies in the data. Show side-by-side comparison for a sample task.
```

### Extension 3: Performance Monitoring
```
Add detailed performance monitoring that tracks:
- Time spent in each phase (extract, transform, load)
- Records processed per second
- Memory usage
- Database query performance

Display this in a nice summary at the end.
```

### Extension 4: Rollback Mechanism
```
Implement a rollback mechanism that can undo the migration by:
1. Saving a backup of MongoDB state before migration
2. Providing a rollback command to restore the previous state
3. Logging all changes for audit purposes
```

### Extension 5: Migration Report
```
Generate a comprehensive HTML or PDF report of the migration including:
- Source and target database statistics
- Schema comparison diagrams
- Data transformation decisions
- Validation results
- Performance metrics
- Recommendations for optimization
```

---

## Key Talking Points Throughout Demo

### Introduction (30 seconds)
- "Today we're migrating from a relational database to MongoDB"
- "This simulates a real client scenario moving from Oracle to MongoDB"
- "We'll see how Windsurf helps with schema design and code generation"

### During Schema Exploration
- "Relational databases use normalization to avoid data duplication"
- "This requires JOINs to fetch related data"
- "Notice the complexity of the relationships"

### During Schema Design
- "MongoDB uses denormalization for read performance"
- "We embed frequently accessed data together"
- "Trade-off: data duplication vs. query simplicity"
- "Design is driven by read patterns, not normalization rules"

### During ETL Building
- "Windsurf understands context across multiple files"
- "It follows best practices from our guidelines document"
- "Notice the comprehensive error handling and logging"
- "Bulk operations are key for performance"

### During Validation
- "Always validate migrations in production scenarios"
- "We check both counts and data quality"
- "Validation gives confidence in the migration"

### Conclusion
- "We successfully migrated from relational to document model"
- "Windsurf helped with schema design and code generation"
- "The result is optimized for our read patterns"
- "This approach scales to real-world migrations"

---

## Demo Timing Breakdown

| Phase | Time | Activities |
|-------|------|------------|
| Setup Check | 1 min | Verify connections, open files |
| Phase 1: Explore | 5 min | Schema analysis, sample data |
| Phase 2: Design | 5 min | Schema design, collection setup |
| Phase 3: ETL | 8 min | Config, extract, transform, load, orchestrate |
| Phase 4: Validate | 2 min | Run migration, validate results |
| Q&A Buffer | 4 min | Questions, troubleshooting |
| **Total** | **25 min** | *Includes 5 min buffer* |

---

## Success Criteria

By the end of the demo, you should have:

- ✅ Analyzed the relational schema
- ✅ Designed an appropriate MongoDB schema
- ✅ Created a complete ETL pipeline
- ✅ Successfully migrated all data
- ✅ Validated the migration results
- ✅ Demonstrated Windsurf's capabilities
- ✅ Showed best practices for MongoDB migrations

---

## Post-Demo Cleanup

```bash
# Stop MongoDB
cd sink
docker-compose down

# Deactivate virtual environment
deactivate

# Optional: Remove MongoDB data
docker-compose down -v
```

---

## Tips for a Smooth Demo

1. **Practice First**: Run through the demo at least once before presenting
2. **Have Backup**: Keep completed scripts in a separate branch as backup
3. **Monitor Time**: Keep an eye on the clock, adjust pace as needed
4. **Engage Audience**: Ask questions, explain decisions
5. **Handle Errors Gracefully**: If something fails, use troubleshooting prompts
6. **Show, Don't Tell**: Let the agent generate code, explain as it works
7. **Highlight Key Points**: Emphasize Windsurf's context awareness and best practices
8. **Be Ready to Adapt**: If audience is interested in something specific, explore it

---

## Common Questions & Answers

**Q: Why not just use references everywhere?**
A: Embedding reduces queries and improves read performance. We embed data that's always accessed together.

**Q: What about data duplication?**
A: It's a trade-off. We duplicate data that rarely changes (like user names) to avoid lookups.

**Q: How do you handle schema changes?**
A: MongoDB is schema-less, so you can add fields without migrations. Use schema versioning for major changes.

**Q: What about transactions?**
A: MongoDB supports multi-document transactions since v4.0, but they're often not needed with proper document design.

**Q: How does this scale?**
A: MongoDB scales horizontally through sharding. Document model makes sharding easier than relational.

**Q: What about data consistency?**
A: We trade immediate consistency for performance. Use transactions when strong consistency is required.

---

**Good luck with your demo! Remember: the goal is to showcase Windsurf's ability to understand context, follow best practices, and generate production-quality code.**

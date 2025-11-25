# Sink Database: MongoDB

This directory contains the infrastructure setup for the MongoDB target database.

## Setup Instructions

### 1. Start MongoDB with Docker

```bash
cd sink
docker-compose up -d
```

This will:
- Start a MongoDB instance on port 27017
- Create a database named `project_management`
- Set up authentication with username `admin` and password `admin123`
- Persist data in a local volume

### 2. Verify MongoDB is Running

```bash
docker-compose ps
```

You should see the MongoDB container running.

### 3. Connect to MongoDB

#### Using MongoDB Shell (mongosh)

```bash
docker exec -it mongodb mongosh -u admin -p admin123 --authenticationDatabase admin
```

#### Using Python (pymongo)

```python
from pymongo import MongoClient

client = MongoClient('mongodb://admin:admin123@localhost:27017/')
db = client['project_management']

# Test connection
print(db.list_collection_names())
```

### 4. Access Mongo Express (Optional Web UI)

If you enabled Mongo Express in docker-compose.yml:

1. Open browser to: http://localhost:8081
2. Login with credentials from docker-compose.yml
3. Browse collections and documents visually

## MongoDB Basics

### Key Concepts

- **Database**: Container for collections (like a schema in SQL)
- **Collection**: Group of documents (like a table in SQL)
- **Document**: JSON-like object (like a row in SQL)
- **Field**: Key-value pair in a document (like a column in SQL)

### Common Commands

```javascript
// Show all databases
show dbs

// Switch to database
use project_management

// Show all collections
show collections

// Insert a document
db.tasks.insertOne({
  title: "Sample Task",
  status: "todo"
})

// Find documents
db.tasks.find()
db.tasks.find({ status: "todo" })

// Count documents
db.tasks.countDocuments()

// Create an index
db.tasks.createIndex({ status: 1 })

// Drop a collection
db.tasks.drop()
```

## Differences from Relational Databases

### No Schema Required
- Collections don't enforce a schema by default
- Documents in the same collection can have different fields
- Schema validation can be added optionally

### No JOINs
- Data is typically denormalized
- Related data can be embedded in documents
- References can be used when needed (manual joins in application code)

### Flexible Structure
- Easy to add new fields without migrations
- Nested objects and arrays are native
- Better for hierarchical and semi-structured data

## Schema Management

### collections_schema.py

Python script to manage MongoDB collections, indexes, and validation rules.

**Commands:**

```bash
# Initialize collections and indexes
python collections_schema.py init

# Inspect current schema
python collections_schema.py inspect

# Drop all collections (requires confirmation)
python collections_schema.py drop
```

### Collections Created

1. **organizations** - Top-level container for projects and labels
   - 1 index on `name`
   - Validation enabled

2. **users** - User profiles with embedded organization memberships
   - 3 indexes: `email` (unique), `name`, `organizations.org_id`
   - Validation enabled

3. **labels** - Master label definitions scoped to organizations
   - 2 indexes: `org_id + name` (unique), `org_id`
   - Validation enabled

4. **projects** - Projects with embedded tasks, assignees, labels, comments
   - 12 indexes for optimal query performance
   - Validation enabled with array size limits

### Index Strategy

**Project-level indexes:**
- `org_id + status` - Find projects by organization and status
- `org_id + created_at` - List projects sorted by creation date

**Task-level indexes (on embedded arrays):**
- `tasks.assignees.user_id` - **CRITICAL**: Find user's assigned tasks
- `tasks.status` - Filter tasks by status
- `tasks.priority` - Sort/filter by priority
- `tasks.due_date` - Sort by due date
- `tasks.labels.label_id` - Find tasks by label
- `tasks.labels.name` - Search tasks by label name

**Compound indexes (for common queries):**
- `org_id + tasks.status + tasks.priority` - Org tasks by status and priority
- `tasks.assignees.user_id + tasks.status` - User's tasks by status
- `tasks.assignees.user_id + tasks.due_date` - User's tasks by due date
- `tasks.status + tasks.priority + tasks.due_date` - Complex filtering

### Schema Validation

All collections have JSON schema validation enabled:
- Required fields enforced
- Data types validated
- Array size limits (prevent document bloat)
- Enum constraints on status/priority fields
- Email pattern validation

### Document Size Limits

- **Projects**: Max 500 tasks per project (~1MB)
- **Tasks**: Max 20 assignees, 20 labels, 100 comments per task
- **Users**: Max 100 organization memberships

These limits ensure documents stay well under MongoDB's 16MB limit.

## Next Steps

During the demo, you will:
1. ✅ Design the MongoDB document schema based on the relational model
2. ✅ Decide what to embed vs. reference
3. ✅ Create appropriate indexes for query performance
4. Implement the ETL pipeline to migrate data

## Stopping MongoDB

```bash
cd sink
docker-compose down
```

To remove data volumes as well:
```bash
docker-compose down -v
```

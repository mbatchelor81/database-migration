# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         DEMO ENVIRONMENT                         │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────┐                    ┌──────────────────────┐
│   SOURCE DATABASE    │                    │   TARGET DATABASE    │
│                      │                    │                      │
│   Supabase/Postgres  │                    │      MongoDB         │
│   ┌──────────────┐   │                    │   ┌──────────────┐   │
│   │ organizations│   │                    │   │ organizations│   │
│   │    users     │   │                    │   │    users     │   │
│   │ org_members  │   │                    │   │   projects   │   │
│   │   projects   │   │    ETL PIPELINE    │   │    tasks     │   │
│   │    tasks     │───┼───────────────────>│   │              │   │
│   │    labels    │   │                    │   │  (embedded:  │   │
│   │ task_labels  │   │                    │   │   comments,  │   │
│   │task_assignees│   │                    │   │   assignees, │   │
│   │   comments   │   │                    │   │   labels)    │   │
│   └──────────────┘   │                    │   └──────────────┘   │
│                      │                    │                      │
│  ✅ Pre-populated    │                    │  ⚠️  Empty (ready)   │
│  ✅ Normalized       │                    │  ⚠️  To be designed  │
│  ✅ Relational       │                    │  ⚠️  Document-based  │
└──────────────────────┘                    └──────────────────────┘
         │                                              ▲
         │                                              │
         │              ┌──────────────────┐            │
         │              │   ETL SCRIPTS    │            │
         │              │  (to be built)   │            │
         │              │                  │            │
         └─────────────>│  1. Extract      │            │
                        │  2. Transform    │────────────┘
                        │  3. Load         │
                        │  4. Validate     │
                        └──────────────────┘
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        MIGRATION PROCESS                         │
└─────────────────────────────────────────────────────────────────┘

PHASE 1: EXTRACT
┌──────────────────────────────────────────────────────────────────┐
│  Postgres                                                         │
│  ┌────────┐  ┌────────┐  ┌────────┐                             │
│  │  Org   │  │ Users  │  │Projects│  ... (9 tables)              │
│  └────────┘  └────────┘  └────────┘                             │
│       │           │           │                                   │
│       └───────────┴───────────┘                                   │
│                   │                                               │
│                   ▼                                               │
│          ┌─────────────────┐                                     │
│          │  SQL JOINs      │  Fetch related data efficiently     │
│          │  Pagination     │  Handle large datasets              │
│          └─────────────────┘                                     │
│                   │                                               │
│                   ▼                                               │
│          ┌─────────────────┐                                     │
│          │  Python Dicts   │  In-memory representation           │
│          └─────────────────┘                                     │
└──────────────────────────────────────────────────────────────────┘
                    │
                    ▼
PHASE 2: TRANSFORM
┌──────────────────────────────────────────────────────────────────┐
│  Transformation Logic                                             │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  DECISIONS:                                              │    │
│  │  • Embed comments in tasks (1-to-many, small)           │    │
│  │  • Embed assignees in tasks (denormalize user data)     │    │
│  │  • Embed labels in tasks (denormalize label data)       │    │
│  │  • Reference projects in tasks (many tasks per project) │    │
│  │  • Reference orgs in projects (many projects per org)   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  OPERATIONS:                                             │    │
│  │  • Map Postgres IDs → MongoDB ObjectIds                 │    │
│  │  • Convert timestamps → ISODate                         │    │
│  │  • Handle NULL values                                   │    │
│  │  • Denormalize frequently accessed data                 │    │
│  │  • Group related data for embedding                     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                   │                                               │
│                   ▼                                               │
│          ┌─────────────────┐                                     │
│          │ MongoDB Docs    │  Document structure                 │
│          └─────────────────┘                                     │
└──────────────────────────────────────────────────────────────────┘
                    │
                    ▼
PHASE 3: LOAD
┌──────────────────────────────────────────────────────────────────┐
│  MongoDB                                                          │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  BULK OPERATIONS:                                        │    │
│  │  • Batch size: 1000 documents                           │    │
│  │  • Ordered: False (parallel inserts)                    │    │
│  │  • Error handling: Continue on failure                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  INSERTION ORDER:                                        │    │
│  │  1. Organizations (no dependencies)                     │    │
│  │  2. Users (no dependencies)                             │    │
│  │  3. Projects (references orgs)                          │    │
│  │  4. Tasks (references projects, embeds everything else) │    │
│  └─────────────────────────────────────────────────────────┘    │
│                   │                                               │
│                   ▼                                               │
│          ┌─────────────────┐                                     │
│          │  Collections    │  Persisted in MongoDB               │
│          └─────────────────┘                                     │
└──────────────────────────────────────────────────────────────────┘
                    │
                    ▼
PHASE 4: VALIDATE
┌──────────────────────────────────────────────────────────────────┐
│  Validation Checks                                                │
│                                                                   │
│  ✓ Count validation: Postgres count == MongoDB count             │
│  ✓ Sample comparison: Random records match                       │
│  ✓ Relationship integrity: All references exist                  │
│  ✓ Data type correctness: Types match expected                   │
│  ✓ Completeness: No missing required fields                      │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  REPORT:                                                 │    │
│  │  • Total records migrated                               │    │
│  │  • Time taken                                           │    │
│  │  • Success rate                                         │    │
│  │  • Errors (if any)                                      │    │
│  └─────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

## Schema Transformation Example

### Before: Relational (Normalized)

```sql
-- Task table
tasks
├── id: 1
├── project_id: 10
├── title: "Build feature"
├── status: "in_progress"
└── priority: "high"

-- Task assignees (junction table)
task_assignees
├── task_id: 1, user_id: 5
└── task_id: 1, user_id: 7

-- Users table
users
├── id: 5, name: "Alice", email: "alice@example.com"
└── id: 7, name: "Bob", email: "bob@example.com"

-- Comments table
comments
├── id: 100, task_id: 1, user_id: 5, content: "Looking good"
└── id: 101, task_id: 1, user_id: 7, content: "Approved"

-- Labels table
labels
├── id: 20, name: "Bug", color: "#FF0000"
└── id: 21, name: "Urgent", color: "#FF6600"

-- Task labels (junction table)
task_labels
├── task_id: 1, label_id: 20
└── task_id: 1, label_id: 21
```

**Query to get complete task:**
```sql
SELECT t.*, 
       u.name as assignee_name, 
       u.email as assignee_email,
       l.name as label_name,
       l.color as label_color,
       c.content as comment_content
FROM tasks t
LEFT JOIN task_assignees ta ON t.id = ta.task_id
LEFT JOIN users u ON ta.user_id = u.id
LEFT JOIN task_labels tl ON t.id = tl.task_id
LEFT JOIN labels l ON tl.label_id = l.id
LEFT JOIN comments c ON t.id = c.task_id
WHERE t.id = 1;
```

### After: Document (Denormalized)

```javascript
// Single document with embedded data
{
  "_id": ObjectId("..."),
  "original_id": 1,
  "project_id": ObjectId("..."),
  "title": "Build feature",
  "status": "in_progress",
  "priority": "high",
  
  // Embedded assignees (denormalized)
  "assignees": [
    {
      "user_id": ObjectId("..."),
      "name": "Alice",
      "email": "alice@example.com"
    },
    {
      "user_id": ObjectId("..."),
      "name": "Bob",
      "email": "bob@example.com"
    }
  ],
  
  // Embedded labels (denormalized)
  "labels": [
    {
      "label_id": ObjectId("..."),
      "name": "Bug",
      "color": "#FF0000"
    },
    {
      "label_id": ObjectId("..."),
      "name": "Urgent",
      "color": "#FF6600"
    }
  ],
  
  // Embedded comments
  "comments": [
    {
      "comment_id": ObjectId("..."),
      "user": {
        "user_id": ObjectId("..."),
        "name": "Alice"
      },
      "content": "Looking good",
      "created_at": ISODate("2024-03-20T10:00:00Z")
    },
    {
      "comment_id": ObjectId("..."),
      "user": {
        "user_id": ObjectId("..."),
        "name": "Bob"
      },
      "content": "Approved",
      "created_at": ISODate("2024-03-20T11:00:00Z")
    }
  ],
  
  "created_at": ISODate("2024-03-15T09:00:00Z"),
  "updated_at": ISODate("2024-03-20T11:00:00Z")
}
```

**Query to get complete task:**
```javascript
db.tasks.findOne({ "_id": ObjectId("...") })
```

**Benefits:**
- ✅ Single query (no JOINs)
- ✅ All data in one place
- ✅ Faster reads
- ✅ Better for caching

**Trade-offs:**
- ⚠️ Data duplication (user names, label names)
- ⚠️ Updates need to propagate (if Alice changes name)
- ⚠️ Larger document size

## Component Responsibilities

### Source (`source/`)
**Status**: ✅ Complete
- Provides relational schema definition
- Contains seed data for realistic demo
- Includes setup instructions for Supabase

### Sink (`sink/`)
**Status**: ✅ Infrastructure only
- Docker configuration for MongoDB
- Setup instructions
- No schema defined (built during demo)

### ETL (`etl/`)
**Status**: ⚠️ To be built during demo

#### `config.py`
- Database connection management
- Environment variable loading
- Connection pooling configuration

#### `extract.py`
- Query Postgres with efficient JOINs
- Fetch all related data
- Handle pagination for large datasets

#### `transform.py`
- Map relational structure to documents
- Handle ID conversions
- Implement denormalization logic
- Data type conversions

#### `load.py`
- Bulk insert operations
- Error handling and recovery
- Progress reporting
- Statistics tracking

#### `migrate.py`
- Orchestrate extract → transform → load
- Progress reporting
- Error handling
- Final statistics

#### `validate.py`
- Compare record counts
- Sample data verification
- Relationship integrity checks
- Generate validation report

### Documentation (`docs/`)
**Status**: ✅ Complete

#### `mongodb_best_practices.md`
- Comprehensive guidelines for AI agent
- Schema design patterns
- Code standards
- Performance tips

#### `demo_walkthrough.md`
- Step-by-step demo script
- Exact prompts to use
- Expected outputs
- Timing guide

## Technology Decisions

### Why Supabase?
- ✅ Free tier available
- ✅ Quick setup (no local Postgres)
- ✅ Web UI for easy data inspection
- ✅ Represents Oracle DB (relational)

### Why MongoDB in Docker?
- ✅ Local control
- ✅ No cloud account needed
- ✅ Easy to reset/restart
- ✅ Production-like environment

### Why Python?
- ✅ Popular for data engineering
- ✅ Great database drivers
- ✅ Easy to read and understand
- ✅ Good for demos

### Why This Data Model?
- ✅ Realistic complexity
- ✅ Shows many-to-many relationships
- ✅ Demonstrates normalization
- ✅ Familiar domain (project management)

## Performance Considerations

### Extraction
- Use JOINs to avoid N+1 queries
- Implement pagination for large datasets
- Fetch related data in single query

### Transformation
- In-memory processing (fast)
- Batch processing for large datasets
- ID mapping dictionary for lookups

### Loading
- Bulk operations (1000 docs per batch)
- Unordered inserts (parallel)
- Error handling without stopping

### Expected Performance
- **Small dataset** (100 records): < 1 second
- **Medium dataset** (10,000 records): < 10 seconds
- **Large dataset** (1M records): < 5 minutes

## Security Considerations

### Credentials
- ✅ Environment variables (not hardcoded)
- ✅ .env in .gitignore
- ✅ .env.example as template

### Database Access
- ✅ Supabase: API keys with row-level security
- ✅ MongoDB: Username/password authentication
- ✅ Docker: Isolated network

### Data Validation
- ✅ Type checking
- ✅ Required field validation
- ✅ Referential integrity checks

## Scalability Considerations

### Current Implementation
- Single-threaded processing
- In-memory transformation
- Suitable for datasets up to 100K records

### For Production Scale
- Multi-threaded extraction
- Stream processing for transformation
- Distributed loading
- Incremental migration support
- Change data capture (CDC)

## Monitoring & Observability

### Logging
- Progress updates per phase
- Record counts
- Error messages
- Timing information

### Metrics
- Records processed per second
- Success/failure rates
- Memory usage
- Database connection health

### Validation
- Count comparisons
- Sample data verification
- Relationship integrity
- Data type correctness

---

**This architecture provides a solid foundation for demonstrating database migration with AI assistance while maintaining production-quality patterns and practices.**

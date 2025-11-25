# Source Database: Supabase (Postgres)

This directory contains the complete relational database schema and seed data for the project management application.

## Setup Instructions

### 1. Create a Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Sign up or log in
3. Click "New Project"
4. Choose an organization
5. Set project name: `migration-demo`
6. Set database password (save this!)
7. Choose region closest to you
8. Click "Create new project"

### 2. Get Your Credentials

Once the project is created:

1. Go to Project Settings → API
2. Copy the following to your `.env` file:
   - **Project URL** → `SUPABASE_URL`
   - **anon/public key** → `SUPABASE_KEY`
   - **service_role key** → `SUPABASE_SERVICE_KEY`

3. Go to Project Settings → Database
4. Copy the connection string details:
   - **Host** → `POSTGRES_HOST`
   - **Database** → `POSTGRES_DB`
   - **User** → `POSTGRES_USER`
   - **Password** → (use the one you set during project creation)

### 3. Run the Schema

1. Go to the SQL Editor in Supabase dashboard
2. Click "New Query"
3. Copy the contents of `schema.sql`
4. Paste and click "Run"
5. Verify tables were created in the Table Editor

### 4. Load Seed Data

1. In SQL Editor, create another new query
2. Copy the contents of `seed_data.sql`
3. Paste and click "Run"
4. Verify data in the Table Editor

## Database Schema Overview

### Core Tables

- **organizations**: Companies or teams using the platform
- **users**: Individual users across all organizations
- **org_members**: Many-to-many relationship (users ↔ organizations)

### Project Management

- **projects**: Projects within an organization
- **tasks**: Individual tasks within projects
- **labels**: Reusable labels per organization
- **task_labels**: Many-to-many relationship (tasks ↔ labels)
- **task_assignees**: Many-to-many relationship (tasks ↔ users)
- **comments**: Comments on tasks

### Relationships

```
organizations (1) ──→ (N) projects
organizations (1) ──→ (N) labels
organizations (N) ←──→ (N) users (via org_members)

projects (1) ──→ (N) tasks

tasks (N) ←──→ (N) labels (via task_labels)
tasks (N) ←──→ (N) users (via task_assignees)
tasks (1) ──→ (N) comments

users (1) ──→ (N) comments
```

## Sample Queries

### View all tasks with their project and organization
```sql
SELECT 
    o.name as org_name,
    p.name as project_name,
    t.title as task_title,
    t.status,
    t.priority
FROM tasks t
JOIN projects p ON t.project_id = p.id
JOIN organizations o ON p.org_id = o.id
ORDER BY o.name, p.name, t.created_at;
```

### View task with all assignees
```sql
SELECT 
    t.title,
    u.name as assignee_name,
    u.email as assignee_email
FROM tasks t
JOIN task_assignees ta ON t.id = ta.task_id
JOIN users u ON ta.user_id = u.id
WHERE t.id = 1;
```

### View task with all labels
```sql
SELECT 
    t.title,
    l.name as label_name,
    l.color as label_color
FROM tasks t
JOIN task_labels tl ON t.id = tl.task_id
JOIN labels l ON tl.label_id = l.id
WHERE t.id = 1;
```

### View task with all comments
```sql
SELECT 
    t.title,
    c.content,
    u.name as commenter,
    c.created_at
FROM tasks t
JOIN comments c ON t.id = c.task_id
JOIN users u ON c.user_id = u.id
WHERE t.id = 1
ORDER BY c.created_at;
```

## Data Statistics

After running the seed data, you should have approximately:

- 3 organizations
- 12 users
- 8 projects
- 25 tasks
- 10 labels
- 40+ task assignments
- 30+ task labels
- 35+ comments

## Notes

- All timestamps use `TIMESTAMPTZ` for proper timezone handling
- Foreign keys enforce referential integrity
- Indexes are created on foreign key columns for query performance
- The schema follows PostgreSQL best practices for normalization

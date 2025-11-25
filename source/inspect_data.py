#!/usr/bin/env python3
"""
Inspect Supabase PostgreSQL data and demonstrate relational queries.
Shows sample data and complex JOIN queries for the project management schema.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
import json

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

supabase: Client = create_client(supabase_url, supabase_key)


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_query(query: str):
    """Print a formatted SQL query."""
    print("SQL Query:")
    print("-" * 80)
    print(query)
    print("-" * 80 + "\n")


def show_sample_data():
    """Display sample data from organizations, projects, and tasks."""
    print_section("1. SAMPLE DATA FROM CORE TABLES")
    
    # Organizations
    print("📊 ORGANIZATIONS:")
    orgs = supabase.table("organizations").select("*").limit(5).execute()
    for org in orgs.data:
        print(f"  • ID: {org['id']}, Name: {org['name']}, Created: {org['created_at']}")
    
    print(f"\n  Total organizations: {len(orgs.data)}\n")
    
    # Projects
    print("📁 PROJECTS:")
    query = """
    SELECT p.id, p.name, p.status, o.name as org_name
    FROM projects p
    JOIN organizations o ON p.org_id = o.id
    LIMIT 5
    """
    print_query(query)
    
    projects = supabase.table("projects").select("id, name, status, organizations(name)").limit(5).execute()
    for proj in projects.data:
        org_name = proj['organizations']['name'] if proj.get('organizations') else 'N/A'
        print(f"  • ID: {proj['id']}, Name: {proj['name']}, Status: {proj['status']}, Org: {org_name}")
    
    print(f"\n  Total projects: {len(projects.data)}\n")
    
    # Tasks
    print("✅ TASKS:")
    query = """
    SELECT t.id, t.title, t.status, t.priority, p.name as project_name
    FROM tasks t
    JOIN projects p ON t.project_id = p.id
    LIMIT 5
    """
    print_query(query)
    
    tasks = supabase.table("tasks").select("id, title, status, priority, projects(name)").limit(5).execute()
    for task in tasks.data:
        proj_name = task['projects']['name'] if task.get('projects') else 'N/A'
        print(f"  • ID: {task['id']}, Title: {task['title']}, Status: {task['status']}, Priority: {task['priority']}, Project: {proj_name}")
    
    print(f"\n  Total tasks: {len(tasks.data)}\n")


def show_task_with_relations():
    """Display a specific task with all its related data."""
    print_section("2. TASK WITH ALL RELATED DATA (FULL JOIN EXAMPLE)")
    
    # Get first task with data
    tasks = supabase.table("tasks").select("id").limit(1).execute()
    
    if not tasks.data:
        print("❌ No tasks found in database")
        return
    
    task_id = tasks.data[0]['id']
    
    # Complex query to get task with all relations
    query = f"""
    -- Main task data with project and organization
    SELECT 
        t.id, t.title, t.description, t.status, t.priority, t.due_date,
        p.name as project_name, p.status as project_status,
        o.name as organization_name
    FROM tasks t
    JOIN projects p ON t.project_id = p.id
    JOIN organizations o ON p.org_id = o.id
    WHERE t.id = {task_id};
    
    -- Task assignees
    SELECT u.id, u.name, u.email, ta.assigned_at
    FROM task_assignees ta
    JOIN users u ON ta.user_id = u.id
    WHERE ta.task_id = {task_id};
    
    -- Task labels
    SELECT l.id, l.name, l.color
    FROM task_labels tl
    JOIN labels l ON tl.label_id = l.id
    WHERE tl.task_id = {task_id};
    
    -- Task comments
    SELECT c.id, c.content, c.created_at, u.name as author_name, u.email as author_email
    FROM comments c
    JOIN users u ON c.user_id = u.id
    WHERE c.task_id = {task_id}
    ORDER BY c.created_at DESC;
    """
    
    print_query(query)
    
    # Fetch task with nested relations using Supabase
    task = supabase.table("tasks").select(
        "*, projects(name, status, organizations(name))"
    ).eq("id", task_id).single().execute()
    
    print("🎯 TASK DETAILS:")
    print(f"  ID: {task.data['id']}")
    print(f"  Title: {task.data['title']}")
    print(f"  Description: {task.data.get('description', 'N/A')}")
    print(f"  Status: {task.data['status']}")
    print(f"  Priority: {task.data['priority']}")
    print(f"  Due Date: {task.data.get('due_date', 'N/A')}")
    
    if task.data.get('projects'):
        print(f"  Project: {task.data['projects']['name']} ({task.data['projects']['status']})")
        if task.data['projects'].get('organizations'):
            print(f"  Organization: {task.data['projects']['organizations']['name']}")
    
    # Get assignees
    print("\n👥 ASSIGNEES:")
    assignees = supabase.table("task_assignees").select(
        "assigned_at, users(id, name, email)"
    ).eq("task_id", task_id).execute()
    
    if assignees.data:
        for assignee in assignees.data:
            user = assignee['users']
            print(f"  • {user['name']} ({user['email']}) - Assigned: {assignee['assigned_at']}")
    else:
        print("  No assignees")
    
    # Get labels
    print("\n🏷️  LABELS:")
    labels = supabase.table("task_labels").select(
        "labels(id, name, color)"
    ).eq("task_id", task_id).execute()
    
    if labels.data:
        for label in labels.data:
            lbl = label['labels']
            print(f"  • {lbl['name']} ({lbl['color']})")
    else:
        print("  No labels")
    
    # Get comments
    print("\n💬 COMMENTS:")
    comments = supabase.table("comments").select(
        "id, content, created_at, users(name, email)"
    ).eq("task_id", task_id).order("created_at", desc=True).execute()
    
    if comments.data:
        for comment in comments.data:
            user = comment['users']
            print(f"  • [{comment['created_at']}] {user['name']}: {comment['content'][:50]}...")
    else:
        print("  No comments")


def show_complex_queries():
    """Demonstrate complex JOIN queries."""
    print_section("3. COMPLEX JOIN QUERIES")
    
    # Query 1: Users with their organizations and roles
    print("📋 Query 1: Users with Organization Memberships")
    query = """
    SELECT 
        u.id, u.name, u.email,
        o.name as org_name,
        om.role,
        om.joined_at
    FROM users u
    JOIN org_members om ON u.id = om.user_id
    JOIN organizations o ON om.org_id = o.id
    ORDER BY u.name, o.name
    LIMIT 10;
    """
    print_query(query)
    
    users = supabase.table("users").select(
        "id, name, email, org_members(role, joined_at, organizations(name))"
    ).limit(5).execute()
    
    for user in users.data:
        print(f"  👤 {user['name']} ({user['email']})")
        if user.get('org_members'):
            for membership in user['org_members']:
                org_name = membership['organizations']['name'] if membership.get('organizations') else 'N/A'
                print(f"     └─ {org_name} - {membership['role']} (joined: {membership['joined_at']})")
    
    # Query 2: Projects with task counts and label usage
    print("\n📊 Query 2: Project Statistics")
    query = """
    SELECT 
        p.id,
        p.name as project_name,
        o.name as org_name,
        COUNT(DISTINCT t.id) as task_count,
        COUNT(DISTINCT tl.label_id) as unique_labels,
        COUNT(DISTINCT ta.user_id) as unique_assignees
    FROM projects p
    JOIN organizations o ON p.org_id = o.id
    LEFT JOIN tasks t ON p.id = t.project_id
    LEFT JOIN task_labels tl ON t.id = tl.task_id
    LEFT JOIN task_assignees ta ON t.id = ta.task_id
    GROUP BY p.id, p.name, o.name
    ORDER BY task_count DESC
    LIMIT 5;
    """
    print_query(query)
    
    # Note: Supabase doesn't support aggregations in select, so we'll show the structure
    projects = supabase.table("projects").select(
        "id, name, organizations(name), tasks(id)"
    ).limit(5).execute()
    
    for proj in projects.data:
        org_name = proj['organizations']['name'] if proj.get('organizations') else 'N/A'
        task_count = len(proj.get('tasks', []))
        print(f"  📁 {proj['name']} ({org_name}) - {task_count} tasks")
    
    # Query 3: Most active users (by comments and assignments)
    print("\n🌟 Query 3: Most Active Users")
    query = """
    SELECT 
        u.id,
        u.name,
        u.email,
        COUNT(DISTINCT ta.task_id) as assigned_tasks,
        COUNT(DISTINCT c.id) as comments_made
    FROM users u
    LEFT JOIN task_assignees ta ON u.id = ta.user_id
    LEFT JOIN comments c ON u.id = c.user_id
    GROUP BY u.id, u.name, u.email
    ORDER BY (COUNT(DISTINCT ta.task_id) + COUNT(DISTINCT c.id)) DESC
    LIMIT 5;
    """
    print_query(query)
    
    users = supabase.table("users").select(
        "id, name, email, task_assignees(task_id), comments(id)"
    ).limit(5).execute()
    
    for user in users.data:
        assigned = len(user.get('task_assignees', []))
        comments = len(user.get('comments', []))
        print(f"  👤 {user['name']} - {assigned} assigned tasks, {comments} comments")


def main():
    """Main execution function."""
    print("\n" + "🔍 SUPABASE DATA INSPECTION TOOL" + "\n")
    print(f"Connected to: {supabase_url}")
    
    try:
        # Run all inspection functions
        show_sample_data()
        show_task_with_relations()
        show_complex_queries()
        
        print_section("✅ INSPECTION COMPLETE")
        print("Key Observations:")
        print("  • Data is highly normalized across multiple tables")
        print("  • Many-to-many relationships use junction tables")
        print("  • Complex queries require multiple JOINs")
        print("  • Foreign key relationships maintain referential integrity")
        print("\nThis relational structure will need to be denormalized for MongoDB migration.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  1. .env file exists with SUPABASE_URL and SUPABASE_KEY")
        print("  2. Database has been seeded with data")
        print("  3. Supabase connection is active")


if __name__ == "__main__":
    main()

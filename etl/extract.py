#!/usr/bin/env python3
"""
ETL Extraction Module

Extracts data from Supabase (PostgreSQL source) using efficient queries
to minimize database round trips. Uses Supabase client's query builder
with nested selects to avoid N+1 query problems.

Usage:
    from etl.extract import extract_all_data
    
    data = extract_all_data()
    print(f"Extracted {len(data['users'])} users")
"""

import logging
from typing import List, Dict, Any, Optional
from postgrest.exceptions import APIError

from config import get_supabase_client, SupabaseConnection

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# ORGANIZATIONS EXTRACTION
# ============================================================================

def extract_organizations() -> List[Dict[str, Any]]:
    """
    Extract all organizations from Supabase.
    
    Returns:
        List[Dict[str, Any]]: List of organization records
        
    Raises:
        APIError: If Supabase query fails
        
    Example:
        >>> orgs = extract_organizations()
        >>> print(f"Found {len(orgs)} organizations")
    """
    logger.info("Extracting organizations...")
    
    try:
        with SupabaseConnection() as supabase:
            response = supabase.table("organizations").select("*").execute()
            
            organizations = response.data
            logger.info(f"✓ Extracted {len(organizations)} organizations")
            
            # Log sample
            if organizations:
                logger.debug(f"  Sample: {organizations[0]['name']}")
            
            return organizations
            
    except APIError as e:
        logger.error(f"Failed to extract organizations: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error extracting organizations: {e}")
        raise


def extract_organizations_with_members() -> List[Dict[str, Any]]:
    """
    Extract organizations with their member relationships.
    
    Uses nested select to get org_members in a single query.
    This avoids N+1 queries (one per organization).
    
    Returns:
        List[Dict[str, Any]]: Organizations with embedded members
        
    Example:
        >>> orgs = extract_organizations_with_members()
        >>> for org in orgs:
        ...     print(f"{org['name']}: {len(org['org_members'])} members")
    """
    logger.info("Extracting organizations with members...")
    
    try:
        with SupabaseConnection() as supabase:
            # Use nested select to get members in one query
            response = supabase.table("organizations").select(
                "*, org_members(user_id, role, joined_at)"
            ).execute()
            
            organizations = response.data
            
            # Count total members
            total_members = sum(len(org.get('org_members', [])) for org in organizations)
            
            logger.info(f"✓ Extracted {len(organizations)} organizations with {total_members} total memberships")
            
            return organizations
            
    except APIError as e:
        logger.error(f"Failed to extract organizations with members: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


# ============================================================================
# USERS EXTRACTION
# ============================================================================

def extract_users() -> List[Dict[str, Any]]:
    """
    Extract all users from Supabase.
    
    Returns:
        List[Dict[str, Any]]: List of user records
        
    Example:
        >>> users = extract_users()
        >>> print(f"Found {len(users)} users")
    """
    logger.info("Extracting users...")
    
    try:
        with SupabaseConnection() as supabase:
            response = supabase.table("users").select("*").execute()
            
            users = response.data
            logger.info(f"✓ Extracted {len(users)} users")
            
            if users:
                logger.debug(f"  Sample: {users[0]['name']} ({users[0]['email']})")
            
            return users
            
    except APIError as e:
        logger.error(f"Failed to extract users: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error extracting users: {e}")
        raise


def extract_users_with_organizations() -> List[Dict[str, Any]]:
    """
    Extract users with their organization memberships.
    
    Uses nested select to get org_members and organization details
    in a single query. This is critical for the MongoDB schema where
    we embed organization memberships in user documents.
    
    Returns:
        List[Dict[str, Any]]: Users with embedded organization memberships
        
    Example:
        >>> users = extract_users_with_organizations()
        >>> for user in users:
        ...     orgs = user.get('org_members', [])
        ...     print(f"{user['name']}: member of {len(orgs)} organizations")
    """
    logger.info("Extracting users with organization memberships...")
    
    try:
        with SupabaseConnection() as supabase:
            # Nested select: get org_members with organization details
            response = supabase.table("users").select(
                "*, org_members(org_id, role, joined_at, organizations(id, name))"
            ).execute()
            
            users = response.data
            
            # Count total memberships
            total_memberships = sum(len(user.get('org_members', [])) for user in users)
            
            logger.info(f"✓ Extracted {len(users)} users with {total_memberships} total organization memberships")
            
            return users
            
    except APIError as e:
        logger.error(f"Failed to extract users with organizations: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


# ============================================================================
# LABELS EXTRACTION
# ============================================================================

def extract_labels() -> List[Dict[str, Any]]:
    """
    Extract all labels from Supabase.
    
    Labels are scoped to organizations and will be used as a master list
    in MongoDB, with denormalized copies embedded in tasks.
    
    Returns:
        List[Dict[str, Any]]: List of label records
        
    Example:
        >>> labels = extract_labels()
        >>> print(f"Found {len(labels)} labels")
    """
    logger.info("Extracting labels...")
    
    try:
        with SupabaseConnection() as supabase:
            response = supabase.table("labels").select("*").execute()
            
            labels = response.data
            logger.info(f"✓ Extracted {len(labels)} labels")
            
            # Group by org for logging
            if labels:
                orgs = set(label['org_id'] for label in labels)
                logger.debug(f"  Labels across {len(orgs)} organizations")
            
            return labels
            
    except APIError as e:
        logger.error(f"Failed to extract labels: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error extracting labels: {e}")
        raise


# ============================================================================
# PROJECTS EXTRACTION
# ============================================================================

def extract_projects() -> List[Dict[str, Any]]:
    """
    Extract all projects with organization details.
    
    Uses nested select to get organization name in one query.
    This provides the denormalized org_name needed for MongoDB.
    
    Returns:
        List[Dict[str, Any]]: Projects with organization details
        
    Example:
        >>> projects = extract_projects()
        >>> for proj in projects:
        ...     org = proj['organizations']
        ...     print(f"{proj['name']} ({org['name']})")
    """
    logger.info("Extracting projects with organization details...")
    
    try:
        with SupabaseConnection() as supabase:
            # Get projects with organization details
            response = supabase.table("projects").select(
                "*, organizations(id, name)"
            ).execute()
            
            projects = response.data
            logger.info(f"✓ Extracted {len(projects)} projects")
            
            # Group by status for logging
            if projects:
                status_counts = {}
                for proj in projects:
                    status = proj.get('status', 'unknown')
                    status_counts[status] = status_counts.get(status, 0) + 1
                logger.debug(f"  Status breakdown: {status_counts}")
            
            return projects
            
    except APIError as e:
        logger.error(f"Failed to extract projects: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error extracting projects: {e}")
        raise


# ============================================================================
# TASKS EXTRACTION
# ============================================================================

def extract_tasks_for_project(project_id: int) -> List[Dict[str, Any]]:
    """
    Extract all tasks for a specific project with all related data.
    
    Uses nested selects to get assignees, labels, and comments in a single query.
    This is the most complex extraction as it needs to gather data from 5 tables.
    
    Args:
        project_id: The project ID to extract tasks for
        
    Returns:
        List[Dict[str, Any]]: Tasks with all related data embedded
        
    Example:
        >>> tasks = extract_tasks_for_project(1)
        >>> for task in tasks:
        ...     print(f"{task['title']}: {len(task['task_assignees'])} assignees")
    """
    logger.debug(f"  Extracting tasks for project {project_id}...")
    
    try:
        with SupabaseConnection() as supabase:
            # Complex nested select to get all related data
            response = supabase.table("tasks").select(
                """
                *,
                task_assignees(assigned_at, users(id, name, email)),
                task_labels(labels(id, name, color)),
                comments(id, content, created_at, users(id, name, email))
                """
            ).eq("project_id", project_id).execute()
            
            tasks = response.data
            
            # Count related items
            total_assignees = sum(len(task.get('task_assignees', [])) for task in tasks)
            total_labels = sum(len(task.get('task_labels', [])) for task in tasks)
            total_comments = sum(len(task.get('comments', [])) for task in tasks)
            
            logger.debug(
                f"    ✓ {len(tasks)} tasks with {total_assignees} assignees, "
                f"{total_labels} labels, {total_comments} comments"
            )
            
            return tasks
            
    except APIError as e:
        logger.error(f"Failed to extract tasks for project {project_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


def extract_all_tasks() -> List[Dict[str, Any]]:
    """
    Extract all tasks with all related data.
    
    This is a convenience function that extracts all tasks at once.
    For large datasets, prefer extract_tasks_by_project() for better memory management.
    
    Returns:
        List[Dict[str, Any]]: All tasks with related data
        
    Example:
        >>> tasks = extract_all_tasks()
        >>> print(f"Total tasks: {len(tasks)}")
    """
    logger.info("Extracting all tasks with related data...")
    
    try:
        with SupabaseConnection() as supabase:
            # Complex nested select to get all related data in ONE query
            response = supabase.table("tasks").select(
                """
                *,
                task_assignees(assigned_at, users(id, name, email)),
                task_labels(labels(id, name, color)),
                comments(id, content, created_at, users(id, name, email))
                """
            ).execute()
            
            tasks = response.data
            
            # Calculate statistics
            total_assignees = sum(len(task.get('task_assignees', [])) for task in tasks)
            total_labels = sum(len(task.get('task_labels', [])) for task in tasks)
            total_comments = sum(len(task.get('comments', [])) for task in tasks)
            
            logger.info(f"✓ Extracted {len(tasks)} tasks")
            logger.info(f"  • {total_assignees} total task assignments")
            logger.info(f"  • {total_labels} total task labels")
            logger.info(f"  • {total_comments} total comments")
            
            # Status breakdown
            status_counts = {}
            for task in tasks:
                status = task.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            logger.debug(f"  Status breakdown: {status_counts}")
            
            return tasks
            
    except APIError as e:
        logger.error(f"Failed to extract tasks: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error extracting tasks: {e}")
        raise


def extract_tasks_by_project() -> Dict[int, List[Dict[str, Any]]]:
    """
    Extract tasks grouped by project.
    
    This is more memory-efficient for large datasets as it processes
    one project at a time. Returns a dictionary mapping project_id to tasks.
    
    Returns:
        Dict[int, List[Dict[str, Any]]]: Tasks grouped by project ID
        
    Example:
        >>> tasks_by_project = extract_tasks_by_project()
        >>> for project_id, tasks in tasks_by_project.items():
        ...     print(f"Project {project_id}: {len(tasks)} tasks")
    """
    logger.info("Extracting tasks grouped by project...")
    
    try:
        # First get all project IDs
        projects = extract_projects()
        project_ids = [proj['id'] for proj in projects]
        
        logger.info(f"  Processing {len(project_ids)} projects...")
        
        tasks_by_project = {}
        total_tasks = 0
        
        for project_id in project_ids:
            tasks = extract_tasks_for_project(project_id)
            tasks_by_project[project_id] = tasks
            total_tasks += len(tasks)
        
        logger.info(f"✓ Extracted {total_tasks} tasks across {len(project_ids)} projects")
        
        return tasks_by_project
        
    except Exception as e:
        logger.error(f"Failed to extract tasks by project: {e}")
        raise


# ============================================================================
# PAGINATION SUPPORT
# ============================================================================

def extract_with_pagination(
    table_name: str,
    select_query: str = "*",
    batch_size: int = 1000,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Extract data from a table with pagination support.
    
    Useful for very large tables to avoid memory issues.
    Fetches data in batches and combines results.
    
    Args:
        table_name: Name of the table to query
        select_query: Columns to select (default: "*")
        batch_size: Number of records per batch (default: 1000)
        filters: Optional filters to apply (e.g., {"status": "active"})
        
    Returns:
        List[Dict[str, Any]]: All records from the table
        
    Example:
        >>> # Extract large table in batches
        >>> tasks = extract_with_pagination("tasks", batch_size=500)
        >>> print(f"Extracted {len(tasks)} tasks in batches")
    """
    logger.info(f"Extracting {table_name} with pagination (batch size: {batch_size})...")
    
    try:
        with SupabaseConnection() as supabase:
            all_records = []
            offset = 0
            batch_num = 1
            
            while True:
                # Build query with pagination
                query = supabase.table(table_name).select(select_query)
                
                # Apply filters if provided
                if filters:
                    for key, value in filters.items():
                        query = query.eq(key, value)
                
                # Apply pagination
                query = query.range(offset, offset + batch_size - 1)
                
                # Execute query
                response = query.execute()
                batch = response.data
                
                if not batch:
                    break
                
                all_records.extend(batch)
                logger.debug(f"  Batch {batch_num}: {len(batch)} records (total: {len(all_records)})")
                
                # Check if we got fewer records than batch_size (last batch)
                if len(batch) < batch_size:
                    break
                
                offset += batch_size
                batch_num += 1
            
            logger.info(f"✓ Extracted {len(all_records)} records from {table_name} in {batch_num} batches")
            
            return all_records
            
    except APIError as e:
        logger.error(f"Failed to extract {table_name} with pagination: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


# ============================================================================
# COMPLETE EXTRACTION
# ============================================================================

def extract_all_data() -> Dict[str, Any]:
    """
    Extract all data from Supabase in the correct order.
    
    Extracts data in dependency order and uses efficient nested queries
    to minimize database round trips. Returns a dictionary with all data
    ready for transformation.
    
    Returns:
        Dict[str, Any]: Dictionary containing all extracted data
            {
                "organizations": [...],
                "users": [...],
                "labels": [...],
                "projects": [...],
                "tasks": [...]
            }
            
    Example:
        >>> data = extract_all_data()
        >>> print(f"Extracted {len(data['users'])} users")
        >>> print(f"Extracted {len(data['tasks'])} tasks")
    """
    logger.info("=" * 80)
    logger.info("STARTING DATA EXTRACTION FROM SUPABASE")
    logger.info("=" * 80)
    
    data = {}
    
    try:
        # 1. Organizations (no dependencies)
        logger.info("\n1. Extracting organizations...")
        data['organizations'] = extract_organizations_with_members()
        
        # 2. Users (no dependencies, but we get org memberships)
        logger.info("\n2. Extracting users...")
        data['users'] = extract_users_with_organizations()
        
        # 3. Labels (depends on organizations)
        logger.info("\n3. Extracting labels...")
        data['labels'] = extract_labels()
        
        # 4. Projects (depends on organizations)
        logger.info("\n4. Extracting projects...")
        data['projects'] = extract_projects()
        
        # 5. Tasks (depends on projects, users, labels)
        logger.info("\n5. Extracting tasks with all related data...")
        data['tasks'] = extract_all_tasks()
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("✅ EXTRACTION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"  Organizations: {len(data['organizations'])}")
        logger.info(f"  Users: {len(data['users'])}")
        logger.info(f"  Labels: {len(data['labels'])}")
        logger.info(f"  Projects: {len(data['projects'])}")
        logger.info(f"  Tasks: {len(data['tasks'])}")
        
        # Calculate total records
        total_records = sum(len(v) for v in data.values() if isinstance(v, list))
        logger.info(f"  Total records: {total_records}")
        logger.info("=" * 80 + "\n")
        
        return data
        
    except Exception as e:
        logger.error(f"\n❌ EXTRACTION FAILED: {e}")
        raise


# ============================================================================
# MAIN (for testing)
# ============================================================================

def main():
    """
    Main function for testing extraction.
    
    Run this script directly to test data extraction:
        python etl/extract.py
    """
    try:
        # Extract all data
        data = extract_all_data()
        
        # Show sample data
        logger.info("\nSample Data:")
        
        if data['organizations']:
            org = data['organizations'][0]
            logger.info(f"\nOrganization: {org['name']}")
            logger.info(f"  Members: {len(org.get('org_members', []))}")
        
        if data['users']:
            user = data['users'][0]
            logger.info(f"\nUser: {user['name']} ({user['email']})")
            logger.info(f"  Organizations: {len(user.get('org_members', []))}")
        
        if data['projects']:
            project = data['projects'][0]
            logger.info(f"\nProject: {project['name']}")
            logger.info(f"  Status: {project['status']}")
            logger.info(f"  Organization: {project['organizations']['name']}")
        
        if data['tasks']:
            task = data['tasks'][0]
            logger.info(f"\nTask: {task['title']}")
            logger.info(f"  Status: {task['status']}, Priority: {task['priority']}")
            logger.info(f"  Assignees: {len(task.get('task_assignees', []))}")
            logger.info(f"  Labels: {len(task.get('task_labels', []))}")
            logger.info(f"  Comments: {len(task.get('comments', []))}")
        
        logger.info("\n✅ Extraction test completed successfully")
        
    except Exception as e:
        logger.error(f"\n❌ Extraction test failed: {e}")
        raise


if __name__ == "__main__":
    main()

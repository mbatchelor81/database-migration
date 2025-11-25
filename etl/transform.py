#!/usr/bin/env python3
"""
ETL Transformation Module

Transforms relational data from PostgreSQL into MongoDB document format.
Handles ID mapping, denormalization, and data type conversions.

Key transformations:
- Integer IDs → MongoDB ObjectIds
- NULL values → None or omitted fields
- Timestamps → Python datetime objects
- Junction tables → Embedded arrays
- Denormalized fields for performance

Usage:
    from etl.transform import transform_all_data
    from etl.extract import extract_all_data
    
    source_data = extract_all_data()
    mongo_data = transform_all_data(source_data)
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from bson import ObjectId

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# ID MAPPING
# ============================================================================

class IDMapper:
    """
    Manages mapping between PostgreSQL integer IDs and MongoDB ObjectIds.
    
    Maintains bidirectional mappings for validation and preserves original
    IDs in documents for verification.
    """
    
    def __init__(self):
        """Initialize empty ID mappings."""
        # Maps: postgres_id -> ObjectId
        self.org_ids: Dict[int, ObjectId] = {}
        self.user_ids: Dict[int, ObjectId] = {}
        self.label_ids: Dict[int, ObjectId] = {}
        self.project_ids: Dict[int, ObjectId] = {}
        self.task_ids: Dict[int, ObjectId] = {}
        self.comment_ids: Dict[int, ObjectId] = {}
        
        logger.debug("IDMapper initialized")
    
    def generate_org_id(self, pg_id: int) -> ObjectId:
        """Generate or retrieve ObjectId for organization."""
        if pg_id not in self.org_ids:
            self.org_ids[pg_id] = ObjectId()
        return self.org_ids[pg_id]
    
    def generate_user_id(self, pg_id: int) -> ObjectId:
        """Generate or retrieve ObjectId for user."""
        if pg_id not in self.user_ids:
            self.user_ids[pg_id] = ObjectId()
        return self.user_ids[pg_id]
    
    def generate_label_id(self, pg_id: int) -> ObjectId:
        """Generate or retrieve ObjectId for label."""
        if pg_id not in self.label_ids:
            self.label_ids[pg_id] = ObjectId()
        return self.label_ids[pg_id]
    
    def generate_project_id(self, pg_id: int) -> ObjectId:
        """Generate or retrieve ObjectId for project."""
        if pg_id not in self.project_ids:
            self.project_ids[pg_id] = ObjectId()
        return self.project_ids[pg_id]
    
    def generate_task_id(self, pg_id: int) -> ObjectId:
        """Generate or retrieve ObjectId for task."""
        if pg_id not in self.task_ids:
            self.task_ids[pg_id] = ObjectId()
        return self.task_ids[pg_id]
    
    def generate_comment_id(self, pg_id: int) -> ObjectId:
        """Generate or retrieve ObjectId for comment."""
        if pg_id not in self.comment_ids:
            self.comment_ids[pg_id] = ObjectId()
        return self.comment_ids[pg_id]
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about ID mappings."""
        return {
            "organizations": len(self.org_ids),
            "users": len(self.user_ids),
            "labels": len(self.label_ids),
            "projects": len(self.project_ids),
            "tasks": len(self.task_ids),
            "comments": len(self.comment_ids)
        }


# ============================================================================
# DATA TYPE CONVERSIONS
# ============================================================================

def convert_timestamp(timestamp_str: Optional[str]) -> Optional[datetime]:
    """
    Convert PostgreSQL timestamp string to Python datetime.
    
    Args:
        timestamp_str: ISO format timestamp string or None
        
    Returns:
        datetime object or None if input is None
        
    Example:
        >>> dt = convert_timestamp("2024-01-15T10:00:00+00:00")
        >>> print(dt)
        2024-01-15 10:00:00+00:00
    """
    if timestamp_str is None:
        return None
    
    try:
        # Parse ISO format timestamp
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError) as e:
        logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}")
        return None


def handle_null(value: Any, omit_if_none: bool = False) -> Any:
    """
    Handle NULL values from PostgreSQL.
    
    Args:
        value: Value to check
        omit_if_none: If True, return a sentinel to omit field
        
    Returns:
        None for NULL, or original value
        
    Example:
        >>> handle_null(None)
        None
        >>> handle_null("value")
        'value'
    """
    if value is None and omit_if_none:
        return "__OMIT__"  # Sentinel value to omit field
    return value


# ============================================================================
# ORGANIZATIONS TRANSFORMATION
# ============================================================================

def transform_organization(
    org: Dict[str, Any],
    id_mapper: IDMapper
) -> Dict[str, Any]:
    """
    Transform a single organization from relational to document format.
    
    Transformation:
    - Generate MongoDB ObjectId
    - Preserve original PostgreSQL ID
    - Convert timestamps
    - Calculate member count (denormalized)
    
    Args:
        org: Organization record from PostgreSQL
        id_mapper: ID mapping manager
        
    Returns:
        MongoDB document for organization
        
    Example:
        >>> org = {"id": 1, "name": "Acme Corp", "created_at": "2024-01-15T10:00:00Z"}
        >>> doc = transform_organization(org, id_mapper)
        >>> print(doc["name"])
        'Acme Corp'
    """
    mongo_id = id_mapper.generate_org_id(org['id'])
    
    doc = {
        "_id": mongo_id,
        "pg_id": org['id'],  # Preserve for validation
        "name": org['name'],
        "created_at": convert_timestamp(org['created_at']),
        "member_count": len(org.get('org_members', [])),  # Denormalized
        "project_count": 0  # Will be updated during project transformation
    }
    
    # Optional settings (omit if None)
    if org.get('settings'):
        doc['settings'] = org['settings']
    
    return doc


def transform_organizations(
    organizations: List[Dict[str, Any]],
    id_mapper: IDMapper
) -> List[Dict[str, Any]]:
    """
    Transform all organizations.
    
    Args:
        organizations: List of organization records
        id_mapper: ID mapping manager
        
    Returns:
        List of MongoDB documents
    """
    logger.info("Transforming organizations...")
    
    mongo_docs = []
    for org in organizations:
        doc = transform_organization(org, id_mapper)
        mongo_docs.append(doc)
    
    logger.info(f"✓ Transformed {len(mongo_docs)} organizations")
    return mongo_docs


# ============================================================================
# USERS TRANSFORMATION
# ============================================================================

def transform_user(
    user: Dict[str, Any],
    id_mapper: IDMapper
) -> Dict[str, Any]:
    """
    Transform a single user with embedded organization memberships.
    
    Transformation:
    - Generate MongoDB ObjectId
    - Preserve original PostgreSQL ID
    - Embed org_members as organizations[] array
    - Denormalize organization names
    - Convert timestamps
    
    Args:
        user: User record from PostgreSQL
        id_mapper: ID mapping manager
        
    Returns:
        MongoDB document for user
        
    Example:
        >>> user = {
        ...     "id": 1,
        ...     "name": "Alice",
        ...     "email": "alice@example.com",
        ...     "org_members": [...]
        ... }
        >>> doc = transform_user(user, id_mapper)
        >>> print(len(doc["organizations"]))
        2
    """
    mongo_id = id_mapper.generate_user_id(user['id'])
    
    # Transform org_members junction table into embedded array
    organizations = []
    for membership in user.get('org_members', []):
        org_data = membership.get('organizations', {})
        
        organizations.append({
            "org_id": id_mapper.generate_org_id(membership['org_id']),
            "org_name": org_data.get('name', ''),  # Denormalized
            "role": membership['role'],
            "joined_at": convert_timestamp(membership['joined_at'])
        })
    
    doc = {
        "_id": mongo_id,
        "pg_id": user['id'],  # Preserve for validation
        "email": user['email'],
        "name": user['name'],
        "created_at": convert_timestamp(user['created_at']),
        "organizations": organizations,  # Embedded memberships
        "stats": {
            "assigned_tasks": 0,  # Will be calculated during task transformation
            "completed_tasks": 0,
            "comments_made": 0
        }
    }
    
    return doc


def transform_users(
    users: List[Dict[str, Any]],
    id_mapper: IDMapper
) -> List[Dict[str, Any]]:
    """
    Transform all users.
    
    Args:
        users: List of user records
        id_mapper: ID mapping manager
        
    Returns:
        List of MongoDB documents
    """
    logger.info("Transforming users...")
    
    mongo_docs = []
    for user in users:
        doc = transform_user(user, id_mapper)
        mongo_docs.append(doc)
    
    logger.info(f"✓ Transformed {len(mongo_docs)} users")
    return mongo_docs


# ============================================================================
# LABELS TRANSFORMATION
# ============================================================================

def transform_label(
    label: Dict[str, Any],
    id_mapper: IDMapper
) -> Dict[str, Any]:
    """
    Transform a single label.
    
    Labels are kept as a separate collection (master list) but will be
    denormalized into tasks during task transformation.
    
    Args:
        label: Label record from PostgreSQL
        id_mapper: ID mapping manager
        
    Returns:
        MongoDB document for label
    """
    mongo_id = id_mapper.generate_label_id(label['id'])
    
    doc = {
        "_id": mongo_id,
        "pg_id": label['id'],  # Preserve for validation
        "org_id": id_mapper.generate_org_id(label['org_id']),
        "name": label['name'],
        "color": label['color'],
        "created_at": convert_timestamp(label['created_at']),
        "usage_count": 0  # Will be calculated during task transformation
    }
    
    return doc


def transform_labels(
    labels: List[Dict[str, Any]],
    id_mapper: IDMapper
) -> List[Dict[str, Any]]:
    """
    Transform all labels.
    
    Args:
        labels: List of label records
        id_mapper: ID mapping manager
        
    Returns:
        List of MongoDB documents
    """
    logger.info("Transforming labels...")
    
    mongo_docs = []
    for label in labels:
        doc = transform_label(label, id_mapper)
        mongo_docs.append(doc)
    
    logger.info(f"✓ Transformed {len(mongo_docs)} labels")
    return mongo_docs


# ============================================================================
# TASKS TRANSFORMATION (Complex - with embedded data)
# ============================================================================

def transform_task(
    task: Dict[str, Any],
    id_mapper: IDMapper,
    labels_lookup: Dict[int, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Transform a single task with all embedded relationships.
    
    This is the most complex transformation as it embeds:
    - Assignees (with denormalized user data)
    - Labels (with denormalized label data)
    - Comments (with denormalized author data)
    
    Args:
        task: Task record from PostgreSQL
        id_mapper: ID mapping manager
        labels_lookup: Dictionary mapping label pg_id to label data
        
    Returns:
        MongoDB subdocument for task (to be embedded in project)
        
    Example:
        >>> task = {
        ...     "id": 1,
        ...     "title": "Design homepage",
        ...     "task_assignees": [...],
        ...     "task_labels": [...],
        ...     "comments": [...]
        ... }
        >>> doc = transform_task(task, id_mapper, labels_lookup)
        >>> print(len(doc["assignees"]))
        2
    """
    mongo_id = id_mapper.generate_task_id(task['id'])
    
    # Transform task_assignees junction table into embedded array
    assignees = []
    for assignment in task.get('task_assignees', []):
        user_data = assignment.get('users', {})
        
        assignees.append({
            "user_id": id_mapper.generate_user_id(user_data['id']),
            "name": user_data.get('name', ''),  # Denormalized
            "email": user_data.get('email', ''),  # Denormalized
            "assigned_at": convert_timestamp(assignment['assigned_at'])
        })
    
    # Transform task_labels junction table into embedded array
    labels = []
    for task_label in task.get('task_labels', []):
        label_data = task_label.get('labels', {})
        label_pg_id = label_data.get('id')
        
        if label_pg_id:
            labels.append({
                "label_id": id_mapper.generate_label_id(label_pg_id),
                "name": label_data.get('name', ''),  # Denormalized
                "color": label_data.get('color', '#000000')  # Denormalized
            })
    
    # Transform comments into embedded array
    comments = []
    for comment in task.get('comments', []):
        user_data = comment.get('users', {})
        
        comments.append({
            "_id": id_mapper.generate_comment_id(comment['id']),
            "pg_id": comment['id'],  # Preserve for validation
            "user_id": id_mapper.generate_user_id(user_data['id']),
            "author_name": user_data.get('name', ''),  # Denormalized
            "content": comment['content'],
            "created_at": convert_timestamp(comment['created_at'])
        })
    
    # Sort comments by creation date
    comments.sort(key=lambda c: c['created_at'] or datetime.min)
    
    # Build task document
    doc = {
        "_id": mongo_id,
        "pg_id": task['id'],  # Preserve for validation
        "title": task['title'],
        "description": task.get('description'),  # May be None
        "status": task['status'],
        "priority": task['priority'],
        "due_date": convert_timestamp(task.get('due_date')),
        "created_at": convert_timestamp(task['created_at']),
        "updated_at": convert_timestamp(task['updated_at']),
        "assignees": assignees,  # Embedded with denormalized data
        "labels": labels,  # Embedded with denormalized data
        "comments": comments,  # Embedded with denormalized data
        "comment_count": len(comments),  # Denormalized count
        "assignee_count": len(assignees)  # Denormalized count
    }
    
    # Omit None description if not set
    if doc['description'] is None:
        del doc['description']
    
    return doc


# ============================================================================
# PROJECTS TRANSFORMATION (with embedded tasks)
# ============================================================================

def transform_project(
    project: Dict[str, Any],
    tasks: List[Dict[str, Any]],
    id_mapper: IDMapper,
    labels_lookup: Dict[int, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Transform a single project with all embedded tasks.
    
    This creates the main document structure for MongoDB:
    - Project metadata
    - Organization reference (with denormalized name)
    - All tasks embedded as an array
    - Denormalized statistics
    
    Args:
        project: Project record from PostgreSQL
        tasks: List of task records for this project
        id_mapper: ID mapping manager
        labels_lookup: Dictionary mapping label pg_id to label data
        
    Returns:
        MongoDB document for project
        
    Example:
        >>> project = {"id": 1, "name": "Website Redesign", ...}
        >>> tasks = [...]  # Tasks for this project
        >>> doc = transform_project(project, tasks, id_mapper, labels_lookup)
        >>> print(len(doc["tasks"]))
        10
    """
    mongo_id = id_mapper.generate_project_id(project['id'])
    org_data = project.get('organizations', {})
    
    # Transform all tasks for this project
    transformed_tasks = []
    for task in tasks:
        if task['project_id'] == project['id']:
            task_doc = transform_task(task, id_mapper, labels_lookup)
            transformed_tasks.append(task_doc)
    
    # Calculate statistics (denormalized for performance)
    stats = {
        "total_tasks": len(transformed_tasks),
        "completed_tasks": sum(1 for t in transformed_tasks if t['status'] == 'completed'),
        "in_progress_tasks": sum(1 for t in transformed_tasks if t['status'] == 'in_progress'),
        "todo_tasks": sum(1 for t in transformed_tasks if t['status'] == 'todo'),
        "total_comments": sum(t['comment_count'] for t in transformed_tasks)
    }
    
    doc = {
        "_id": mongo_id,
        "pg_id": project['id'],  # Preserve for validation
        "org_id": id_mapper.generate_org_id(project['org_id']),
        "org_name": org_data.get('name', ''),  # Denormalized
        "name": project['name'],
        "description": project.get('description'),  # May be None
        "status": project['status'],
        "created_at": convert_timestamp(project['created_at']),
        "tasks": transformed_tasks,  # Embedded tasks array
        "stats": stats  # Denormalized statistics
    }
    
    # Omit None description if not set
    if doc['description'] is None:
        del doc['description']
    
    return doc


def transform_projects(
    projects: List[Dict[str, Any]],
    tasks: List[Dict[str, Any]],
    id_mapper: IDMapper,
    labels_lookup: Dict[int, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Transform all projects with embedded tasks.
    
    Args:
        projects: List of project records
        tasks: List of all task records
        id_mapper: ID mapping manager
        labels_lookup: Dictionary mapping label pg_id to label data
        
    Returns:
        List of MongoDB documents
    """
    logger.info("Transforming projects with embedded tasks...")
    
    mongo_docs = []
    total_tasks = 0
    
    for project in projects:
        doc = transform_project(project, tasks, id_mapper, labels_lookup)
        mongo_docs.append(doc)
        total_tasks += len(doc['tasks'])
    
    logger.info(f"✓ Transformed {len(mongo_docs)} projects with {total_tasks} embedded tasks")
    return mongo_docs


# ============================================================================
# COMPLETE TRANSFORMATION
# ============================================================================

def transform_all_data(source_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform all relational data into MongoDB document format.
    
    Performs complete transformation in the correct order:
    1. Generate all ObjectIds (ID mapping)
    2. Transform organizations
    3. Transform users (with embedded org memberships)
    4. Transform labels
    5. Transform projects (with embedded tasks, assignees, labels, comments)
    
    Args:
        source_data: Dictionary with extracted PostgreSQL data
            {
                "organizations": [...],
                "users": [...],
                "labels": [...],
                "projects": [...],
                "tasks": [...]
            }
            
    Returns:
        Dictionary with transformed MongoDB documents
            {
                "organizations": [...],
                "users": [...],
                "labels": [...],
                "projects": [...]  # Contains embedded tasks
            }
            
    Example:
        >>> from etl.extract import extract_all_data
        >>> source_data = extract_all_data()
        >>> mongo_data = transform_all_data(source_data)
        >>> print(f"Projects: {len(mongo_data['projects'])}")
    """
    logger.info("=" * 80)
    logger.info("STARTING DATA TRANSFORMATION")
    logger.info("=" * 80)
    
    # Initialize ID mapper
    id_mapper = IDMapper()
    
    # Create labels lookup for efficient access during task transformation
    labels_lookup = {label['id']: label for label in source_data['labels']}
    
    mongo_data = {}
    
    try:
        # 1. Transform organizations
        logger.info("\n1. Transforming organizations...")
        mongo_data['organizations'] = transform_organizations(
            source_data['organizations'],
            id_mapper
        )
        
        # 2. Transform users (with embedded org memberships)
        logger.info("\n2. Transforming users...")
        mongo_data['users'] = transform_users(
            source_data['users'],
            id_mapper
        )
        
        # 3. Transform labels
        logger.info("\n3. Transforming labels...")
        mongo_data['labels'] = transform_labels(
            source_data['labels'],
            id_mapper
        )
        
        # 4. Transform projects (with embedded tasks)
        logger.info("\n4. Transforming projects with embedded tasks...")
        mongo_data['projects'] = transform_projects(
            source_data['projects'],
            source_data['tasks'],
            id_mapper,
            labels_lookup
        )
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("✅ TRANSFORMATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"  Organizations: {len(mongo_data['organizations'])}")
        logger.info(f"  Users: {len(mongo_data['users'])}")
        logger.info(f"  Labels: {len(mongo_data['labels'])}")
        logger.info(f"  Projects: {len(mongo_data['projects'])}")
        
        # Calculate embedded counts
        total_tasks = sum(len(p['tasks']) for p in mongo_data['projects'])
        total_comments = sum(
            sum(len(t['comments']) for t in p['tasks'])
            for p in mongo_data['projects']
        )
        
        logger.info(f"  Embedded tasks: {total_tasks}")
        logger.info(f"  Embedded comments: {total_comments}")
        
        # ID mapping stats
        id_stats = id_mapper.get_stats()
        logger.info(f"\nID Mappings created:")
        for entity, count in id_stats.items():
            logger.info(f"  {entity}: {count}")
        
        logger.info("=" * 80 + "\n")
        
        return mongo_data
        
    except Exception as e:
        logger.error(f"\n❌ TRANSFORMATION FAILED: {e}")
        raise


# ============================================================================
# MAIN (for testing)
# ============================================================================

def main():
    """
    Main function for testing transformation.
    
    Run this script directly to test data transformation:
        python etl/transform.py
    """
    from extract import extract_all_data
    
    try:
        # Extract data
        logger.info("Extracting source data...")
        source_data = extract_all_data()
        
        # Transform data
        mongo_data = transform_all_data(source_data)
        
        # Show sample transformed data
        logger.info("\nSample Transformed Data:")
        
        if mongo_data['organizations']:
            org = mongo_data['organizations'][0]
            logger.info(f"\nOrganization:")
            logger.info(f"  _id: {org['_id']}")
            logger.info(f"  pg_id: {org['pg_id']}")
            logger.info(f"  name: {org['name']}")
            logger.info(f"  member_count: {org['member_count']}")
        
        if mongo_data['users']:
            user = mongo_data['users'][0]
            logger.info(f"\nUser:")
            logger.info(f"  _id: {user['_id']}")
            logger.info(f"  pg_id: {user['pg_id']}")
            logger.info(f"  name: {user['name']}")
            logger.info(f"  organizations: {len(user['organizations'])} memberships")
        
        if mongo_data['projects']:
            project = mongo_data['projects'][0]
            logger.info(f"\nProject:")
            logger.info(f"  _id: {project['_id']}")
            logger.info(f"  pg_id: {project['pg_id']}")
            logger.info(f"  name: {project['name']}")
            logger.info(f"  org_name: {project['org_name']}")
            logger.info(f"  tasks: {len(project['tasks'])} embedded")
            
            if project['tasks']:
                task = project['tasks'][0]
                logger.info(f"\n  Sample Task:")
                logger.info(f"    _id: {task['_id']}")
                logger.info(f"    title: {task['title']}")
                logger.info(f"    assignees: {len(task['assignees'])}")
                logger.info(f"    labels: {len(task['labels'])}")
                logger.info(f"    comments: {len(task['comments'])}")
        
        logger.info("\n✅ Transformation test completed successfully")
        
    except Exception as e:
        logger.error(f"\n❌ Transformation test failed: {e}")
        raise


if __name__ == "__main__":
    main()

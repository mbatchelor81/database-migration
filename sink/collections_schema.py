#!/usr/bin/env python3
"""
MongoDB Collections Schema Manager

This script manages the MongoDB collections, indexes, and validation rules
for the project management application. It provides commands to initialize,
drop, and inspect the database schema.

Usage:
    python collections_schema.py init      # Initialize collections and indexes
    python collections_schema.py drop      # Drop all collections
    python collections_schema.py inspect   # Show current schema and indexes
"""

import os
import sys
from typing import Dict, List, Optional
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING, IndexModel
from pymongo.errors import CollectionInvalid, OperationFailure
import json

# Load environment variables
load_dotenv()


class MongoSchemaManager:
    """
    Manages MongoDB schema including collections, indexes, and validation rules.
    
    This class implements the document model designed for optimal read performance:
    - Embeds tasks in projects (primary read pattern)
    - Embeds assignees, labels, comments in tasks (always displayed together)
    - Embeds org memberships in users (frequently accessed)
    - References users, orgs, labels (shared data, accessed independently)
    """
    
    def __init__(self):
        """Initialize MongoDB connection."""
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise ValueError("MONGO_URI must be set in .env file")
        
        self.client = MongoClient(mongo_uri)
        self.db = self.client[os.getenv("MONGO_DB", "project_management")]
        
        print(f"Connected to MongoDB: {self.db.name}")
    
    def close(self):
        """Close MongoDB connection."""
        self.client.close()
    
    # =========================================================================
    # COLLECTION DEFINITIONS
    # =========================================================================
    
    def get_organizations_schema(self) -> Dict:
        """
        Organizations collection schema.
        
        Purpose: Top-level container for projects and labels.
        Size: Small documents (~300 bytes each)
        Access: Referenced by projects, labels, and users
        """
        return {
            "validator": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["name", "created_at"],
                    "properties": {
                        "name": {
                            "bsonType": "string",
                            "maxLength": 255,
                            "description": "Organization name (required)"
                        },
                        "created_at": {
                            "bsonType": "date",
                            "description": "Creation timestamp (required)"
                        },
                        "member_count": {
                            "bsonType": "int",
                            "minimum": 0,
                            "description": "Denormalized count of members"
                        },
                        "project_count": {
                            "bsonType": "int",
                            "minimum": 0,
                            "description": "Denormalized count of projects"
                        },
                        "settings": {
                            "bsonType": "object",
                            "description": "Optional organization settings"
                        }
                    }
                }
            }
        }
    
    def get_users_schema(self) -> Dict:
        """
        Users collection schema.
        
        Purpose: User profiles with embedded organization memberships.
        Size: ~1-2KB per document (including embedded orgs)
        Access: Referenced by tasks (assignees) and comments
        
        Design Decision: Embed org memberships (one-to-few relationship)
        - Users typically belong to 2-10 organizations (bounded)
        - Always displayed together ("show user's organizations")
        - Denormalize org_name to avoid lookups
        """
        return {
            "validator": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["email", "name", "created_at"],
                    "properties": {
                        "email": {
                            "bsonType": "string",
                            "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
                            "description": "User email (required, unique)"
                        },
                        "name": {
                            "bsonType": "string",
                            "maxLength": 255,
                            "description": "User full name (required)"
                        },
                        "created_at": {
                            "bsonType": "date",
                            "description": "Account creation timestamp (required)"
                        },
                        "organizations": {
                            "bsonType": "array",
                            "maxItems": 100,
                            "description": "Embedded organization memberships",
                            "items": {
                                "bsonType": "object",
                                "required": ["org_id", "org_name", "role", "joined_at"],
                                "properties": {
                                    "org_id": {
                                        "bsonType": "objectId",
                                        "description": "Reference to organization"
                                    },
                                    "org_name": {
                                        "bsonType": "string",
                                        "description": "Denormalized org name (for display)"
                                    },
                                    "role": {
                                        "enum": ["admin", "member", "viewer"],
                                        "description": "User role in organization"
                                    },
                                    "joined_at": {
                                        "bsonType": "date",
                                        "description": "Membership start date"
                                    }
                                }
                            }
                        },
                        "stats": {
                            "bsonType": "object",
                            "description": "Denormalized activity metrics",
                            "properties": {
                                "assigned_tasks": {"bsonType": "int", "minimum": 0},
                                "completed_tasks": {"bsonType": "int", "minimum": 0},
                                "comments_made": {"bsonType": "int", "minimum": 0}
                            }
                        }
                    }
                }
            }
        }
    
    def get_labels_schema(self) -> Dict:
        """
        Labels collection schema.
        
        Purpose: Master label definitions scoped to organizations.
        Size: Small documents (~200 bytes each)
        Access: Referenced by tasks, but denormalized into task.labels[]
        
        Design Decision: Keep as separate collection (not embedded in orgs)
        - Labels are managed centrally
        - Reused across many projects/tasks
        - Need to track usage and enforce uniqueness per org
        """
        return {
            "validator": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["org_id", "name", "color", "created_at"],
                    "properties": {
                        "org_id": {
                            "bsonType": "objectId",
                            "description": "Organization this label belongs to (required)"
                        },
                        "name": {
                            "bsonType": "string",
                            "maxLength": 100,
                            "description": "Label name (required, unique per org)"
                        },
                        "color": {
                            "bsonType": "string",
                            "pattern": "^#[0-9A-Fa-f]{6}$",
                            "description": "Hex color code (required)"
                        },
                        "created_at": {
                            "bsonType": "date",
                            "description": "Creation timestamp (required)"
                        },
                        "usage_count": {
                            "bsonType": "int",
                            "minimum": 0,
                            "description": "Denormalized count of tasks using this label"
                        }
                    }
                }
            }
        }
    
    def get_projects_schema(self) -> Dict:
        """
        Projects collection schema.
        
        Purpose: Projects with embedded tasks (primary collection for reads).
        Size: ~200KB-1MB per document (including all embedded tasks)
        Access: Primary read pattern - "show project with all tasks"
        
        Design Decision: Embed tasks with all their relations
        - Tasks always accessed with project (primary read pattern)
        - Eliminates 5+ JOINs from relational model
        - Bounded array: typical project has 50-200 tasks (~200KB)
        - Safe limit: 500 tasks per project (~1MB, well under 16MB)
        
        Nested Embeddings:
        - tasks[].assignees[] - Always displayed with task (2-5 per task)
        - tasks[].labels[] - Always displayed with task (3-10 per task)
        - tasks[].comments[] - Always displayed with task (10-50 per task)
        """
        return {
            "validator": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["org_id", "name", "status", "created_at", "tasks"],
                    "properties": {
                        "org_id": {
                            "bsonType": "objectId",
                            "description": "Organization this project belongs to (required)"
                        },
                        "org_name": {
                            "bsonType": "string",
                            "description": "Denormalized org name (for display)"
                        },
                        "name": {
                            "bsonType": "string",
                            "maxLength": 255,
                            "description": "Project name (required)"
                        },
                        "description": {
                            "bsonType": "string",
                            "description": "Project description (optional)"
                        },
                        "status": {
                            "enum": ["active", "planning", "completed", "archived"],
                            "description": "Project status (required)"
                        },
                        "created_at": {
                            "bsonType": "date",
                            "description": "Creation timestamp (required)"
                        },
                        "tasks": {
                            "bsonType": "array",
                            "maxItems": 500,
                            "description": "Embedded tasks (bounded to prevent document bloat)",
                            "items": {
                                "bsonType": "object",
                                "required": ["_id", "title", "status", "priority", "created_at"],
                                "properties": {
                                    "_id": {
                                        "bsonType": "objectId",
                                        "description": "Task ID (for positional updates)"
                                    },
                                    "title": {
                                        "bsonType": "string",
                                        "maxLength": 255,
                                        "description": "Task title (required)"
                                    },
                                    "description": {
                                        "bsonType": "string",
                                        "description": "Task description (optional)"
                                    },
                                    "status": {
                                        "enum": ["todo", "in_progress", "completed", "blocked"],
                                        "description": "Task status (required)"
                                    },
                                    "priority": {
                                        "enum": ["low", "medium", "high", "critical"],
                                        "description": "Task priority (required)"
                                    },
                                    "due_date": {
                                        "bsonType": "date",
                                        "description": "Task due date (optional)"
                                    },
                                    "created_at": {
                                        "bsonType": "date",
                                        "description": "Creation timestamp (required)"
                                    },
                                    "updated_at": {
                                        "bsonType": "date",
                                        "description": "Last update timestamp"
                                    },
                                    "assignees": {
                                        "bsonType": "array",
                                        "maxItems": 20,
                                        "description": "Embedded assignees with denormalized user data",
                                        "items": {
                                            "bsonType": "object",
                                            "required": ["user_id", "name", "email", "assigned_at"],
                                            "properties": {
                                                "user_id": {"bsonType": "objectId"},
                                                "name": {"bsonType": "string"},
                                                "email": {"bsonType": "string"},
                                                "assigned_at": {"bsonType": "date"}
                                            }
                                        }
                                    },
                                    "labels": {
                                        "bsonType": "array",
                                        "maxItems": 20,
                                        "description": "Embedded labels with denormalized label data",
                                        "items": {
                                            "bsonType": "object",
                                            "required": ["label_id", "name", "color"],
                                            "properties": {
                                                "label_id": {"bsonType": "objectId"},
                                                "name": {"bsonType": "string"},
                                                "color": {"bsonType": "string"}
                                            }
                                        }
                                    },
                                    "comments": {
                                        "bsonType": "array",
                                        "maxItems": 100,
                                        "description": "Embedded comments with denormalized author data",
                                        "items": {
                                            "bsonType": "object",
                                            "required": ["_id", "user_id", "author_name", "content", "created_at"],
                                            "properties": {
                                                "_id": {"bsonType": "objectId"},
                                                "user_id": {"bsonType": "objectId"},
                                                "author_name": {"bsonType": "string"},
                                                "content": {"bsonType": "string"},
                                                "created_at": {"bsonType": "date"}
                                            }
                                        }
                                    },
                                    "comment_count": {
                                        "bsonType": "int",
                                        "minimum": 0,
                                        "description": "Denormalized comment count"
                                    },
                                    "assignee_count": {
                                        "bsonType": "int",
                                        "minimum": 0,
                                        "description": "Denormalized assignee count"
                                    }
                                }
                            }
                        },
                        "stats": {
                            "bsonType": "object",
                            "description": "Denormalized project statistics",
                            "properties": {
                                "total_tasks": {"bsonType": "int", "minimum": 0},
                                "completed_tasks": {"bsonType": "int", "minimum": 0},
                                "in_progress_tasks": {"bsonType": "int", "minimum": 0},
                                "todo_tasks": {"bsonType": "int", "minimum": 0},
                                "total_comments": {"bsonType": "int", "minimum": 0}
                            }
                        }
                    }
                }
            }
        }
    
    # =========================================================================
    # INDEX DEFINITIONS
    # =========================================================================
    
    def get_organizations_indexes(self) -> List[IndexModel]:
        """
        Indexes for organizations collection.
        
        Query patterns:
        - Find org by name (for lookups and searches)
        """
        return [
            IndexModel(
                [("name", ASCENDING)],
                name="name_1"
                # Purpose: Search organizations by name
            )
        ]
    
    def get_users_indexes(self) -> List[IndexModel]:
        """
        Indexes for users collection.
        
        Query patterns:
        - Find user by email (login, unique constraint)
        - Find users by name (search, autocomplete)
        - Find users in an organization (list org members)
        """
        return [
            IndexModel(
                [("email", ASCENDING)],
                name="email_1",
                unique=True
                # Purpose: Unique constraint on email, used for login and user lookups
            ),
            IndexModel(
                [("name", ASCENDING)],
                name="name_1"
                # Purpose: Search users by name (autocomplete, user search)
            ),
            IndexModel(
                [("organizations.org_id", ASCENDING)],
                name="organizations_org_id_1"
                # Purpose: Find all users in an organization (list members, permissions)
            )
        ]
    
    def get_labels_indexes(self) -> List[IndexModel]:
        """
        Indexes for labels collection.
        
        Query patterns:
        - Find labels by org (list all labels in org)
        - Ensure unique label names per org
        """
        return [
            IndexModel(
                [("org_id", ASCENDING), ("name", ASCENDING)],
                name="org_id_1_name_1",
                unique=True
                # Purpose: Unique constraint: label names must be unique per organization
            ),
            IndexModel(
                [("org_id", ASCENDING)],
                name="org_id_1"
                # Purpose: List all labels in an organization (label management)
            )
        ]
    
    def get_projects_indexes(self) -> List[IndexModel]:
        """
        Indexes for projects collection.
        
        Query patterns (in order of frequency):
        1. Find tasks by assignee (most common: "my tasks")
        2. Find tasks by status (filter by todo/in_progress/completed)
        3. Find tasks by priority (sort by priority)
        4. Find tasks by due date (upcoming deadlines)
        5. Find tasks by labels (filter by label)
        6. Find projects by org (list org's projects)
        
        Index Strategy:
        - Index embedded array fields (tasks.assignees.user_id, tasks.status, etc.)
        - Use compound indexes for common filter combinations
        - Place most selective field first in compound indexes
        """
        return [
            # ===== PROJECT-LEVEL INDEXES =====
            
            IndexModel(
                [("org_id", ASCENDING), ("status", ASCENDING)],
                name="org_id_1_status_1"
                # Purpose: Find projects by organization and status (list active projects)
            ),
            IndexModel(
                [("org_id", ASCENDING), ("created_at", DESCENDING)],
                name="org_id_1_created_at_-1"
                # Purpose: List projects by org, sorted by creation date (newest first)
            ),
            
            # ===== TASK-LEVEL INDEXES (on embedded tasks array) =====
            
            IndexModel(
                [("tasks.assignees.user_id", ASCENDING)],
                name="tasks_assignees_user_id_1"
                # Purpose: CRITICAL: Find all tasks assigned to a user (most common query: 'my tasks')
            ),
            IndexModel(
                [("tasks.status", ASCENDING)],
                name="tasks_status_1"
                # Purpose: Filter tasks by status (todo, in_progress, completed, blocked)
            ),
            IndexModel(
                [("tasks.priority", ASCENDING)],
                name="tasks_priority_1"
                # Purpose: Sort/filter tasks by priority (low, medium, high, critical)
            ),
            IndexModel(
                [("tasks.due_date", ASCENDING)],
                name="tasks_due_date_1"
                # Purpose: Sort tasks by due date (upcoming deadlines, overdue tasks)
            ),
            IndexModel(
                [("tasks.labels.label_id", ASCENDING)],
                name="tasks_labels_label_id_1"
                # Purpose: Find tasks with specific labels (filter by label)
            ),
            IndexModel(
                [("tasks.labels.name", ASCENDING)],
                name="tasks_labels_name_1"
                # Purpose: Search tasks by label name (alternative to label_id)
            ),
            
            # ===== COMPOUND INDEXES (for common filter combinations) =====
            
            IndexModel(
                [("org_id", ASCENDING), ("tasks.status", ASCENDING), ("tasks.priority", ASCENDING)],
                name="org_id_1_tasks_status_1_tasks_priority_1"
                # Purpose: Find tasks in org by status and priority (e.g., 'high priority in-progress tasks')
            ),
            IndexModel(
                [("tasks.assignees.user_id", ASCENDING), ("tasks.status", ASCENDING)],
                name="tasks_assignees_user_id_1_tasks_status_1"
                # Purpose: Find user's tasks filtered by status (e.g., 'my in-progress tasks')
            ),
            IndexModel(
                [("tasks.assignees.user_id", ASCENDING), ("tasks.due_date", ASCENDING)],
                name="tasks_assignees_user_id_1_tasks_due_date_1"
                # Purpose: Find user's tasks sorted by due date (e.g., 'my upcoming deadlines')
            ),
            IndexModel(
                [("tasks.status", ASCENDING), ("tasks.priority", ASCENDING), ("tasks.due_date", ASCENDING)],
                name="tasks_status_1_tasks_priority_1_tasks_due_date_1"
                # Purpose: Complex task filtering: status + priority + due date
            )
        ]
    
    # =========================================================================
    # COLLECTION MANAGEMENT
    # =========================================================================
    
    def create_collection_with_validation(self, collection_name: str, schema: Dict) -> None:
        """
        Create a collection with schema validation.
        
        Args:
            collection_name: Name of the collection
            schema: JSON schema validation rules
        """
        try:
            self.db.create_collection(collection_name, **schema)
            print(f"✓ Created collection: {collection_name}")
        except CollectionInvalid:
            print(f"⚠ Collection {collection_name} already exists, updating validator...")
            self.db.command({
                "collMod": collection_name,
                "validator": schema["validator"]
            })
            print(f"✓ Updated validator for: {collection_name}")
    
    def create_indexes(self, collection_name: str, indexes: List[IndexModel]) -> None:
        """
        Create indexes for a collection.
        
        Args:
            collection_name: Name of the collection
            indexes: List of IndexModel objects
        """
        collection = self.db[collection_name]
        
        # Drop existing indexes (except _id)
        existing_indexes = collection.index_information()
        for index_name in existing_indexes:
            if index_name != "_id_":
                collection.drop_index(index_name)
                print(f"  ✗ Dropped old index: {index_name}")
        
        # Create new indexes
        if indexes:
            result = collection.create_indexes(indexes)
            for index_name in result:
                print(f"  ✓ Created index: {index_name}")
    
    def initialize_schema(self) -> None:
        """
        Initialize all collections with validation rules and indexes.
        
        This creates the complete MongoDB schema optimized for the
        project management application's read patterns.
        """
        print("\n" + "=" * 80)
        print("INITIALIZING MONGODB SCHEMA")
        print("=" * 80 + "\n")
        
        # Organizations
        print("📊 Organizations Collection")
        self.create_collection_with_validation("organizations", self.get_organizations_schema())
        self.create_indexes("organizations", self.get_organizations_indexes())
        
        # Users
        print("\n👤 Users Collection")
        self.create_collection_with_validation("users", self.get_users_schema())
        self.create_indexes("users", self.get_users_indexes())
        
        # Labels
        print("\n🏷️  Labels Collection")
        self.create_collection_with_validation("labels", self.get_labels_schema())
        self.create_indexes("labels", self.get_labels_indexes())
        
        # Projects (with embedded tasks)
        print("\n📁 Projects Collection (with embedded tasks)")
        self.create_collection_with_validation("projects", self.get_projects_schema())
        self.create_indexes("projects", self.get_projects_indexes())
        
        print("\n" + "=" * 80)
        print("✅ SCHEMA INITIALIZATION COMPLETE")
        print("=" * 80)
        print("\nCollections created: organizations, users, labels, projects")
        print("Total indexes created: ~15")
        print("\nSchema is optimized for:")
        print("  • Fast project + tasks retrieval (single query, no JOINs)")
        print("  • Efficient task filtering by status, priority, assignee")
        print("  • Quick user task lookups ('my tasks')")
        print("  • Label-based task searches")
    
    def drop_database(self) -> None:
        """
        Drop the entire database and all collections.
        
        WARNING: This is destructive and cannot be undone!
        """
        print("\n" + "=" * 80)
        print("⚠️  WARNING: DROPPING DATABASE")
        print("=" * 80 + "\n")
        
        response = input(f"Are you sure you want to drop database '{self.db.name}'? (yes/no): ")
        if response.lower() != "yes":
            print("❌ Operation cancelled")
            return
        
        # List all collections
        collections = self.db.list_collection_names()
        print(f"\nDropping {len(collections)} collections...")
        
        for collection_name in collections:
            self.db[collection_name].drop()
            print(f"  ✗ Dropped: {collection_name}")
        
        print("\n" + "=" * 80)
        print("✅ DATABASE DROPPED")
        print("=" * 80)
    
    def inspect_schema(self) -> None:
        """
        Inspect current database schema, collections, and indexes.
        
        Displays:
        - List of collections
        - Document counts
        - Indexes for each collection
        - Validation rules
        """
        print("\n" + "=" * 80)
        print(f"INSPECTING DATABASE: {self.db.name}")
        print("=" * 80 + "\n")
        
        collections = self.db.list_collection_names()
        
        if not collections:
            print("❌ No collections found. Run 'init' to create schema.")
            return
        
        print(f"Found {len(collections)} collections:\n")
        
        for collection_name in collections:
            collection = self.db[collection_name]
            doc_count = collection.count_documents({})
            
            print(f"📦 {collection_name}")
            print(f"   Documents: {doc_count:,}")
            
            # Show indexes
            indexes = collection.index_information()
            print(f"   Indexes ({len(indexes)}):")
            for index_name, index_info in indexes.items():
                keys = index_info.get("key", [])
                unique = " [UNIQUE]" if index_info.get("unique", False) else ""
                
                # Format keys
                key_str = ", ".join([f"{k}: {v}" for k, v in keys])
                
                print(f"     • {index_name}{unique}")
                print(f"       Keys: {key_str}")
            
            # Show validation rules (if any)
            try:
                coll_info = self.db.command({"listCollections": 1, "filter": {"name": collection_name}})
                if coll_info["cursor"]["firstBatch"]:
                    validator = coll_info["cursor"]["firstBatch"][0].get("options", {}).get("validator")
                    if validator:
                        print(f"   Validation: ✓ Enabled")
            except Exception:
                pass
            
            print()
        
        print("=" * 80)
        print("✅ INSPECTION COMPLETE")
        print("=" * 80)


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: python collections_schema.py [init|drop|inspect]")
        print("\nCommands:")
        print("  init     - Initialize collections, indexes, and validation rules")
        print("  drop     - Drop all collections (requires confirmation)")
        print("  inspect  - Display current schema and indexes")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command not in ["init", "drop", "inspect"]:
        print(f"❌ Unknown command: {command}")
        print("Valid commands: init, drop, inspect")
        sys.exit(1)
    
    try:
        manager = MongoSchemaManager()
        
        if command == "init":
            manager.initialize_schema()
        elif command == "drop":
            manager.drop_database()
        elif command == "inspect":
            manager.inspect_schema()
        
        manager.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

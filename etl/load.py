#!/usr/bin/env python3
"""
ETL Load Module

Loads transformed MongoDB documents into the target database using bulk operations.
Handles errors, tracks progress, and maintains insertion order for dependencies.

Usage:
    from etl.load import load_all_data
    from etl.transform import transform_all_data
    
    mongo_data = transform_all_data(source_data)
    results = load_all_data(mongo_data)
    print(f"Loaded {results['total_inserted']} documents")
"""

import logging
from typing import Dict, List, Any, Optional
from pymongo import InsertOne, UpdateOne
from pymongo.errors import (
    BulkWriteError,
    DuplicateKeyError,
    OperationFailure,
    ConnectionFailure
)

from config import get_mongo_database, MongoConnection, BATCH_SIZE

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# LOAD STATISTICS
# ============================================================================

class LoadStats:
    """
    Tracks statistics for a single collection load operation.
    """
    
    def __init__(self, collection_name: str):
        """Initialize load statistics."""
        self.collection_name = collection_name
        self.total_documents = 0
        self.inserted_count = 0
        self.failed_count = 0
        self.errors: List[str] = []
        self.batches_processed = 0
    
    def add_success(self, count: int):
        """Record successful insertions."""
        self.inserted_count += count
    
    def add_failure(self, count: int, error: str):
        """Record failed insertions."""
        self.failed_count += count
        self.errors.append(error)
    
    def increment_batch(self):
        """Increment batch counter."""
        self.batches_processed += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        return {
            "collection": self.collection_name,
            "total_documents": self.total_documents,
            "inserted": self.inserted_count,
            "failed": self.failed_count,
            "batches": self.batches_processed,
            "success_rate": (
                f"{(self.inserted_count / self.total_documents * 100):.1f}%"
                if self.total_documents > 0 else "0%"
            ),
            "errors": self.errors
        }
    
    def log_summary(self):
        """Log summary statistics."""
        if self.failed_count > 0:
            logger.warning(
                f"  {self.collection_name}: {self.inserted_count}/{self.total_documents} "
                f"inserted ({self.failed_count} failed)"
            )
            for error in self.errors[:3]:  # Show first 3 errors
                logger.warning(f"    Error: {error}")
        else:
            logger.info(
                f"  ✓ {self.collection_name}: {self.inserted_count}/{self.total_documents} "
                f"inserted in {self.batches_processed} batches"
            )


# ============================================================================
# BULK LOAD OPERATIONS
# ============================================================================

def load_collection_bulk(
    collection_name: str,
    documents: List[Dict[str, Any]],
    batch_size: int = BATCH_SIZE,
    ordered: bool = False
) -> LoadStats:
    """
    Load documents into a collection using bulk operations.
    
    Uses bulk_write with InsertOne operations for optimal performance.
    Processes documents in batches to manage memory and provide progress updates.
    
    Args:
        collection_name: Name of the MongoDB collection
        documents: List of documents to insert
        batch_size: Number of documents per batch (default from config)
        ordered: If True, stop on first error; if False, continue on errors
        
    Returns:
        LoadStats: Statistics about the load operation
        
    Raises:
        ConnectionFailure: If MongoDB connection fails
        
    Example:
        >>> docs = [{"name": "Alice"}, {"name": "Bob"}]
        >>> stats = load_collection_bulk("users", docs)
        >>> print(f"Inserted: {stats.inserted_count}")
    """
    stats = LoadStats(collection_name)
    stats.total_documents = len(documents)
    
    if not documents:
        logger.warning(f"No documents to load for {collection_name}")
        return stats
    
    logger.info(f"Loading {len(documents)} documents into {collection_name}...")
    
    try:
        with MongoConnection() as db:
            collection = db[collection_name]
            
            # Process in batches
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(documents) + batch_size - 1) // batch_size
                
                try:
                    # Create bulk operations
                    operations = [InsertOne(doc) for doc in batch]
                    
                    # Execute bulk write
                    result = collection.bulk_write(operations, ordered=ordered)
                    
                    # Record success
                    stats.add_success(result.inserted_count)
                    stats.increment_batch()
                    
                    # Progress update
                    logger.info(
                        f"  Batch {batch_num}/{total_batches}: "
                        f"Inserted {len(batch)} documents "
                        f"(Total: {stats.inserted_count}/{stats.total_documents})"
                    )
                    
                except BulkWriteError as e:
                    # Handle partial success in bulk write
                    inserted = e.details.get('nInserted', 0)
                    stats.add_success(inserted)
                    
                    # Record failures
                    write_errors = e.details.get('writeErrors', [])
                    failed = len(write_errors)
                    stats.add_failure(failed, f"BulkWriteError: {len(write_errors)} documents failed")
                    
                    # Log specific errors
                    for error in write_errors[:3]:  # Show first 3
                        logger.error(f"    Document error: {error.get('errmsg', 'Unknown error')}")
                    
                    if len(write_errors) > 3:
                        logger.error(f"    ... and {len(write_errors) - 3} more errors")
                    
                    stats.increment_batch()
                    
                except DuplicateKeyError as e:
                    stats.add_failure(len(batch), f"DuplicateKeyError: {str(e)}")
                    logger.error(f"  Batch {batch_num}: Duplicate key error - {e}")
                    stats.increment_batch()
                    
                except Exception as e:
                    stats.add_failure(len(batch), f"Unexpected error: {str(e)}")
                    logger.error(f"  Batch {batch_num}: Unexpected error - {e}")
                    stats.increment_batch()
            
            # Final summary
            stats.log_summary()
            
            return stats
            
    except ConnectionFailure as e:
        error_msg = f"MongoDB connection failure while loading {collection_name}: {e}"
        logger.error(error_msg)
        stats.add_failure(len(documents), error_msg)
        raise
    except Exception as e:
        error_msg = f"Failed to load {collection_name}: {e}"
        logger.error(error_msg)
        stats.add_failure(len(documents), error_msg)
        raise


# ============================================================================
# UPSERT OPERATIONS (for idempotency)
# ============================================================================

def upsert_collection_bulk(
    collection_name: str,
    documents: List[Dict[str, Any]],
    batch_size: int = BATCH_SIZE
) -> LoadStats:
    """
    Upsert documents into a collection using bulk operations.
    
    Uses UpdateOne with upsert=True to make the operation idempotent.
    Useful for re-running migrations without duplicating data.
    
    Args:
        collection_name: Name of the MongoDB collection
        documents: List of documents to upsert
        batch_size: Number of documents per batch
        
    Returns:
        LoadStats: Statistics about the upsert operation
        
    Example:
        >>> docs = [{"_id": ObjectId(...), "name": "Alice"}]
        >>> stats = upsert_collection_bulk("users", docs)
        >>> print(f"Upserted: {stats.inserted_count}")
    """
    stats = LoadStats(collection_name)
    stats.total_documents = len(documents)
    
    if not documents:
        logger.warning(f"No documents to upsert for {collection_name}")
        return stats
    
    logger.info(f"Upserting {len(documents)} documents into {collection_name}...")
    
    try:
        with MongoConnection() as db:
            collection = db[collection_name]
            
            # Process in batches
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(documents) + batch_size - 1) // batch_size
                
                try:
                    # Create upsert operations
                    operations = [
                        UpdateOne(
                            {"_id": doc["_id"]},
                            {"$set": doc},
                            upsert=True
                        )
                        for doc in batch
                    ]
                    
                    # Execute bulk write
                    result = collection.bulk_write(operations, ordered=False)
                    
                    # Record success (upserted + modified)
                    upserted = result.upserted_count + result.modified_count
                    stats.add_success(upserted)
                    stats.increment_batch()
                    
                    # Progress update
                    logger.info(
                        f"  Batch {batch_num}/{total_batches}: "
                        f"Upserted {upserted} documents "
                        f"(Total: {stats.inserted_count}/{stats.total_documents})"
                    )
                    
                except BulkWriteError as e:
                    # Handle partial success
                    upserted = e.details.get('nUpserted', 0) + e.details.get('nModified', 0)
                    stats.add_success(upserted)
                    
                    write_errors = e.details.get('writeErrors', [])
                    stats.add_failure(len(write_errors), f"BulkWriteError: {len(write_errors)} failed")
                    
                    for error in write_errors[:3]:
                        logger.error(f"    Document error: {error.get('errmsg', 'Unknown')}")
                    
                    stats.increment_batch()
                    
                except Exception as e:
                    stats.add_failure(len(batch), f"Unexpected error: {str(e)}")
                    logger.error(f"  Batch {batch_num}: Unexpected error - {e}")
                    stats.increment_batch()
            
            stats.log_summary()
            return stats
            
    except Exception as e:
        error_msg = f"Failed to upsert {collection_name}: {e}"
        logger.error(error_msg)
        stats.add_failure(len(documents), error_msg)
        raise


# ============================================================================
# COLLECTION-SPECIFIC LOAD FUNCTIONS
# ============================================================================

def load_organizations(
    documents: List[Dict[str, Any]],
    batch_size: int = BATCH_SIZE
) -> LoadStats:
    """
    Load organizations into MongoDB.
    
    Organizations have no dependencies, so they're loaded first.
    
    Args:
        documents: List of organization documents
        batch_size: Batch size for bulk operations
        
    Returns:
        LoadStats: Load statistics
    """
    logger.info("\n1. Loading organizations...")
    return load_collection_bulk("organizations", documents, batch_size)


def load_users(
    documents: List[Dict[str, Any]],
    batch_size: int = BATCH_SIZE
) -> LoadStats:
    """
    Load users into MongoDB.
    
    Users have no dependencies (org references are embedded).
    
    Args:
        documents: List of user documents
        batch_size: Batch size for bulk operations
        
    Returns:
        LoadStats: Load statistics
    """
    logger.info("\n2. Loading users...")
    return load_collection_bulk("users", documents, batch_size)


def load_labels(
    documents: List[Dict[str, Any]],
    batch_size: int = BATCH_SIZE
) -> LoadStats:
    """
    Load labels into MongoDB.
    
    Labels depend on organizations (org_id reference).
    
    Args:
        documents: List of label documents
        batch_size: Batch size for bulk operations
        
    Returns:
        LoadStats: Load statistics
    """
    logger.info("\n3. Loading labels...")
    return load_collection_bulk("labels", documents, batch_size)


def load_projects(
    documents: List[Dict[str, Any]],
    batch_size: int = BATCH_SIZE
) -> LoadStats:
    """
    Load projects with embedded tasks into MongoDB.
    
    Projects depend on organizations. Tasks are embedded, so they're
    loaded together with projects.
    
    Args:
        documents: List of project documents (with embedded tasks)
        batch_size: Batch size for bulk operations
        
    Returns:
        LoadStats: Load statistics
    """
    logger.info("\n4. Loading projects with embedded tasks...")
    
    # Count embedded tasks for logging
    total_tasks = sum(len(proj.get('tasks', [])) for proj in documents)
    logger.info(f"  Projects contain {total_tasks} embedded tasks")
    
    return load_collection_bulk("projects", documents, batch_size)


# ============================================================================
# CLEAR COLLECTIONS (for clean re-runs)
# ============================================================================

def clear_collection(collection_name: str) -> int:
    """
    Clear all documents from a collection.
    
    Useful for re-running migrations from scratch.
    
    Args:
        collection_name: Name of collection to clear
        
    Returns:
        int: Number of documents deleted
        
    Example:
        >>> deleted = clear_collection("users")
        >>> print(f"Deleted {deleted} documents")
    """
    try:
        with MongoConnection() as db:
            collection = db[collection_name]
            result = collection.delete_many({})
            
            logger.info(f"  Cleared {result.deleted_count} documents from {collection_name}")
            return result.deleted_count
            
    except Exception as e:
        logger.error(f"Failed to clear {collection_name}: {e}")
        raise


def clear_all_collections() -> Dict[str, int]:
    """
    Clear all collections in the database.
    
    Returns:
        Dict[str, int]: Dictionary mapping collection names to deleted counts
    """
    logger.info("Clearing all collections...")
    
    collections = ["organizations", "users", "labels", "projects"]
    deleted_counts = {}
    
    for collection_name in collections:
        deleted_counts[collection_name] = clear_collection(collection_name)
    
    total_deleted = sum(deleted_counts.values())
    logger.info(f"✓ Cleared {total_deleted} total documents")
    
    return deleted_counts


# ============================================================================
# COMPLETE LOAD OPERATION
# ============================================================================

def load_all_data(
    mongo_data: Dict[str, List[Dict[str, Any]]],
    batch_size: int = BATCH_SIZE,
    clear_existing: bool = False
) -> Dict[str, Any]:
    """
    Load all transformed data into MongoDB.
    
    Loads collections in dependency order:
    1. Organizations (no dependencies)
    2. Users (no dependencies, org refs are embedded)
    3. Labels (depends on organizations)
    4. Projects (depends on organizations, contains embedded tasks)
    
    Args:
        mongo_data: Dictionary with transformed MongoDB documents
            {
                "organizations": [...],
                "users": [...],
                "labels": [...],
                "projects": [...]  # Contains embedded tasks
            }
        batch_size: Batch size for bulk operations (default from config)
        clear_existing: If True, clear collections before loading
        
    Returns:
        Dict[str, Any]: Summary statistics
            {
                "total_inserted": int,
                "total_failed": int,
                "collections": {
                    "organizations": {...},
                    "users": {...},
                    ...
                }
            }
            
    Example:
        >>> results = load_all_data(mongo_data)
        >>> print(f"Loaded {results['total_inserted']} documents")
        >>> if results['total_failed'] > 0:
        ...     print(f"Failed: {results['total_failed']}")
    """
    logger.info("=" * 80)
    logger.info("STARTING DATA LOAD TO MONGODB")
    logger.info("=" * 80)
    logger.info(f"Batch size: {batch_size}")
    logger.info(f"Clear existing: {clear_existing}")
    
    # Clear existing data if requested
    if clear_existing:
        logger.info("\nClearing existing collections...")
        clear_all_collections()
    
    # Track overall statistics
    all_stats = {}
    
    try:
        # Load in dependency order
        all_stats['organizations'] = load_organizations(
            mongo_data['organizations'],
            batch_size
        )
        
        all_stats['users'] = load_users(
            mongo_data['users'],
            batch_size
        )
        
        all_stats['labels'] = load_labels(
            mongo_data['labels'],
            batch_size
        )
        
        all_stats['projects'] = load_projects(
            mongo_data['projects'],
            batch_size
        )
        
        # Calculate totals
        total_inserted = sum(s.inserted_count for s in all_stats.values())
        total_failed = sum(s.failed_count for s in all_stats.values())
        total_documents = sum(s.total_documents for s in all_stats.values())
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("✅ LOAD COMPLETE")
        logger.info("=" * 80)
        logger.info(f"  Total documents: {total_documents}")
        logger.info(f"  Successfully inserted: {total_inserted}")
        logger.info(f"  Failed: {total_failed}")
        
        if total_failed > 0:
            logger.warning(f"  Success rate: {(total_inserted / total_documents * 100):.1f}%")
        else:
            logger.info(f"  Success rate: 100%")
        
        logger.info("\nCollection Summary:")
        for name, stats in all_stats.items():
            logger.info(f"  • {name}: {stats.inserted_count}/{stats.total_documents}")
        
        logger.info("=" * 80 + "\n")
        
        # Return summary
        return {
            "total_documents": total_documents,
            "total_inserted": total_inserted,
            "total_failed": total_failed,
            "success_rate": f"{(total_inserted / total_documents * 100):.1f}%" if total_documents > 0 else "0%",
            "collections": {
                name: stats.get_summary()
                for name, stats in all_stats.items()
            }
        }
        
    except Exception as e:
        logger.error(f"\n❌ LOAD FAILED: {e}")
        raise


# ============================================================================
# MAIN (for testing)
# ============================================================================

def main():
    """
    Main function for testing load operations.
    
    Run this script directly to test data loading:
        python etl/load.py
    """
    from extract import extract_all_data
    from transform import transform_all_data
    
    try:
        # Extract and transform data
        logger.info("Extracting source data...")
        source_data = extract_all_data()
        
        logger.info("\nTransforming data...")
        mongo_data = transform_all_data(source_data)
        
        # Load data
        results = load_all_data(mongo_data, clear_existing=True)
        
        # Show results
        logger.info("\nLoad Results:")
        logger.info(f"  Total inserted: {results['total_inserted']}")
        logger.info(f"  Total failed: {results['total_failed']}")
        logger.info(f"  Success rate: {results['success_rate']}")
        
        # Show collection details
        logger.info("\nCollection Details:")
        for coll_name, coll_stats in results['collections'].items():
            logger.info(f"\n  {coll_name}:")
            logger.info(f"    Inserted: {coll_stats['inserted']}/{coll_stats['total_documents']}")
            logger.info(f"    Batches: {coll_stats['batches']}")
            if coll_stats['errors']:
                logger.info(f"    Errors: {len(coll_stats['errors'])}")
        
        # Verify data in MongoDB
        logger.info("\nVerifying data in MongoDB...")
        with MongoConnection() as db:
            for coll_name in ['organizations', 'users', 'labels', 'projects']:
                count = db[coll_name].count_documents({})
                logger.info(f"  {coll_name}: {count} documents")
        
        logger.info("\n✅ Load test completed successfully")
        
    except Exception as e:
        logger.error(f"\n❌ Load test failed: {e}")
        raise


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
ETL Migration Orchestrator

Main script that orchestrates the complete PostgreSQL to MongoDB migration.
Runs extraction, transformation, and loading in sequence with comprehensive
error handling and progress reporting.

Usage:
    python etl/migrate.py                    # Run full migration
    python etl/migrate.py --dry-run          # Test without loading
    python etl/migrate.py --clear            # Clear existing data first
    python etl/migrate.py --batch-size 500   # Custom batch size
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Import ETL modules
from config import test_connections, get_connection_info, close_mongo_client, BATCH_SIZE
from extract import extract_all_data
from transform import transform_all_data
from load import load_all_data, clear_all_collections

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# MIGRATION ORCHESTRATOR
# ============================================================================

class MigrationOrchestrator:
    """
    Orchestrates the complete ETL migration process.
    
    Manages extraction, transformation, and loading phases with
    comprehensive error handling, progress tracking, and statistics.
    """
    
    def __init__(
        self,
        dry_run: bool = False,
        clear_existing: bool = False,
        batch_size: int = BATCH_SIZE
    ):
        """
        Initialize migration orchestrator.
        
        Args:
            dry_run: If True, skip loading phase (test only)
            clear_existing: If True, clear collections before loading
            batch_size: Batch size for bulk operations
        """
        self.dry_run = dry_run
        self.clear_existing = clear_existing
        self.batch_size = batch_size
        
        # Track statistics
        self.stats = {
            "start_time": None,
            "end_time": None,
            "duration": None,
            "phase_durations": {},
            "source_data": {},
            "transformed_data": {},
            "load_results": {},
            "errors": []
        }
        
        logger.info("Migration orchestrator initialized")
        logger.info(f"  Dry run: {dry_run}")
        logger.info(f"  Clear existing: {clear_existing}")
        logger.info(f"  Batch size: {batch_size}")
    
    def print_banner(self, text: str, char: str = "="):
        """Print a formatted banner."""
        banner = char * 80
        logger.info("\n" + banner)
        logger.info(f"  {text}")
        logger.info(banner)
    
    def print_phase_header(self, phase_num: int, phase_name: str):
        """Print phase header."""
        logger.info("\n" + "=" * 80)
        logger.info(f"PHASE {phase_num}: {phase_name}")
        logger.info("=" * 80)
    
    def test_connections(self) -> bool:
        """
        Test connections to both databases.
        
        Returns:
            bool: True if both connections successful
        """
        self.print_banner("TESTING DATABASE CONNECTIONS")
        
        try:
            results = test_connections()
            
            if not results["all_connected"]:
                logger.error("\n❌ Connection test failed")
                if not results["supabase"]:
                    logger.error("  • Supabase (PostgreSQL) connection failed")
                if not results["mongodb"]:
                    logger.error("  • MongoDB connection failed")
                return False
            
            logger.info("\n✅ All database connections successful")
            return True
            
        except Exception as e:
            logger.error(f"\n❌ Connection test error: {e}")
            self.stats["errors"].append(f"Connection test: {str(e)}")
            return False
    
    def extract_phase(self) -> Optional[Dict[str, Any]]:
        """
        Execute extraction phase.
        
        Returns:
            Dict with extracted data, or None if failed
        """
        self.print_phase_header(1, "EXTRACTION FROM SUPABASE (PostgreSQL)")
        
        phase_start = time.time()
        
        try:
            source_data = extract_all_data()
            
            # Record statistics
            self.stats["source_data"] = {
                "organizations": len(source_data.get("organizations", [])),
                "users": len(source_data.get("users", [])),
                "labels": len(source_data.get("labels", [])),
                "projects": len(source_data.get("projects", [])),
                "tasks": len(source_data.get("tasks", []))
            }
            
            phase_duration = time.time() - phase_start
            self.stats["phase_durations"]["extraction"] = phase_duration
            
            logger.info(f"\n✅ Extraction completed in {phase_duration:.2f}s")
            return source_data
            
        except Exception as e:
            logger.error(f"\n❌ Extraction failed: {e}")
            self.stats["errors"].append(f"Extraction: {str(e)}")
            return None
    
    def transform_phase(self, source_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute transformation phase.
        
        Args:
            source_data: Extracted data from PostgreSQL
            
        Returns:
            Dict with transformed data, or None if failed
        """
        self.print_phase_header(2, "TRANSFORMATION TO MONGODB FORMAT")
        
        phase_start = time.time()
        
        try:
            mongo_data = transform_all_data(source_data)
            
            # Record statistics
            self.stats["transformed_data"] = {
                "organizations": len(mongo_data.get("organizations", [])),
                "users": len(mongo_data.get("users", [])),
                "labels": len(mongo_data.get("labels", [])),
                "projects": len(mongo_data.get("projects", []))
            }
            
            # Count embedded data
            total_tasks = sum(
                len(proj.get("tasks", []))
                for proj in mongo_data.get("projects", [])
            )
            total_comments = sum(
                sum(len(task.get("comments", [])) for task in proj.get("tasks", []))
                for proj in mongo_data.get("projects", [])
            )
            
            self.stats["transformed_data"]["embedded_tasks"] = total_tasks
            self.stats["transformed_data"]["embedded_comments"] = total_comments
            
            phase_duration = time.time() - phase_start
            self.stats["phase_durations"]["transformation"] = phase_duration
            
            logger.info(f"\n✅ Transformation completed in {phase_duration:.2f}s")
            return mongo_data
            
        except Exception as e:
            logger.error(f"\n❌ Transformation failed: {e}")
            self.stats["errors"].append(f"Transformation: {str(e)}")
            return None
    
    def load_phase(self, mongo_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute loading phase.
        
        Args:
            mongo_data: Transformed MongoDB documents
            
        Returns:
            Dict with load results, or None if failed
        """
        if self.dry_run:
            self.print_phase_header(3, "LOADING TO MONGODB (DRY RUN - SKIPPED)")
            logger.info("\n⚠️  Dry run mode: Skipping data load")
            logger.info("  Data would be loaded to MongoDB in production mode")
            return {
                "total_documents": sum(len(v) for v in mongo_data.values() if isinstance(v, list)),
                "total_inserted": 0,
                "total_failed": 0,
                "success_rate": "N/A (dry run)",
                "collections": {}
            }
        
        self.print_phase_header(3, "LOADING TO MONGODB")
        
        phase_start = time.time()
        
        try:
            load_results = load_all_data(
                mongo_data,
                batch_size=self.batch_size,
                clear_existing=self.clear_existing
            )
            
            # Record statistics
            self.stats["load_results"] = load_results
            
            phase_duration = time.time() - phase_start
            self.stats["phase_durations"]["loading"] = phase_duration
            
            logger.info(f"\n✅ Loading completed in {phase_duration:.2f}s")
            return load_results
            
        except Exception as e:
            logger.error(f"\n❌ Loading failed: {e}")
            self.stats["errors"].append(f"Loading: {str(e)}")
            return None
    
    def print_final_summary(self):
        """Print comprehensive migration summary."""
        self.print_banner("MIGRATION SUMMARY", "=")
        
        # Duration
        duration = self.stats.get("duration", 0)
        logger.info(f"\n⏱️  Total Duration: {duration:.2f}s ({timedelta(seconds=int(duration))})")
        
        # Phase durations
        logger.info("\nPhase Durations:")
        for phase, duration in self.stats.get("phase_durations", {}).items():
            logger.info(f"  • {phase.capitalize()}: {duration:.2f}s")
        
        # Source data
        logger.info("\n📊 Source Data (PostgreSQL):")
        for entity, count in self.stats.get("source_data", {}).items():
            logger.info(f"  • {entity}: {count}")
        
        # Transformed data
        logger.info("\n🔄 Transformed Data (MongoDB format):")
        for entity, count in self.stats.get("transformed_data", {}).items():
            logger.info(f"  • {entity}: {count}")
        
        # Load results
        if not self.dry_run:
            load_results = self.stats.get("load_results", {})
            logger.info("\n💾 Load Results:")
            logger.info(f"  • Total documents: {load_results.get('total_documents', 0)}")
            logger.info(f"  • Successfully inserted: {load_results.get('total_inserted', 0)}")
            logger.info(f"  • Failed: {load_results.get('total_failed', 0)}")
            logger.info(f"  • Success rate: {load_results.get('success_rate', 'N/A')}")
            
            # Collection details
            logger.info("\n  Collection Breakdown:")
            for coll_name, coll_stats in load_results.get("collections", {}).items():
                inserted = coll_stats.get("inserted", 0)
                total = coll_stats.get("total_documents", 0)
                logger.info(f"    - {coll_name}: {inserted}/{total}")
        else:
            logger.info("\n💾 Load Results: Skipped (dry run mode)")
        
        # Errors
        errors = self.stats.get("errors", [])
        if errors:
            logger.error(f"\n❌ Errors ({len(errors)}):")
            for error in errors:
                logger.error(f"  • {error}")
        else:
            logger.info("\n✅ No errors encountered")
        
        logger.info("\n" + "=" * 80)
    
    def run(self) -> bool:
        """
        Execute the complete migration process.
        
        Returns:
            bool: True if migration successful, False otherwise
        """
        self.stats["start_time"] = datetime.now()
        start_time = time.time()
        
        try:
            # Print header
            self.print_banner("POSTGRESQL TO MONGODB MIGRATION", "=")
            logger.info(f"\nStarted at: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Test connections
            if not self.test_connections():
                logger.error("\n❌ Migration aborted: Connection test failed")
                return False
            
            # Phase 1: Extract
            source_data = self.extract_phase()
            if source_data is None:
                logger.error("\n❌ Migration aborted: Extraction failed")
                return False
            
            # Phase 2: Transform
            mongo_data = self.transform_phase(source_data)
            if mongo_data is None:
                logger.error("\n❌ Migration aborted: Transformation failed")
                return False
            
            # Phase 3: Load
            load_results = self.load_phase(mongo_data)
            if load_results is None and not self.dry_run:
                logger.error("\n❌ Migration aborted: Loading failed")
                return False
            
            # Calculate duration
            self.stats["end_time"] = datetime.now()
            self.stats["duration"] = time.time() - start_time
            
            # Print summary
            self.print_final_summary()
            
            # Check for errors
            if self.stats["errors"]:
                logger.warning("\n⚠️  Migration completed with errors")
                return False
            
            if self.dry_run:
                logger.info("\n✅ DRY RUN COMPLETED SUCCESSFULLY")
                logger.info("  Run without --dry-run to perform actual migration")
            else:
                logger.info("\n✅ MIGRATION COMPLETED SUCCESSFULLY")
            
            return True
            
        except KeyboardInterrupt:
            logger.warning("\n\n⚠️  Migration interrupted by user")
            self.stats["errors"].append("User interrupted migration")
            return False
            
        except Exception as e:
            logger.error(f"\n\n❌ Unexpected error during migration: {e}")
            self.stats["errors"].append(f"Unexpected: {str(e)}")
            return False
            
        finally:
            # Cleanup
            close_mongo_client()
            logger.info("\nCleaned up database connections")


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="PostgreSQL to MongoDB Migration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python etl/migrate.py                    # Run full migration
  python etl/migrate.py --dry-run          # Test without loading
  python etl/migrate.py --clear            # Clear existing data first
  python etl/migrate.py --batch-size 500   # Custom batch size
  python etl/migrate.py --dry-run --clear  # Test with clear
        """
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test migration without actually loading data to MongoDB"
    )
    
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing MongoDB collections before loading"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Batch size for bulk operations (default: {BATCH_SIZE})"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)"
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the migration script."""
    # Parse arguments
    args = parse_arguments()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Print configuration
    logger.info("=" * 80)
    logger.info("PostgreSQL to MongoDB Migration Tool")
    logger.info("=" * 80)
    logger.info("\nConfiguration:")
    logger.info(f"  Dry run: {args.dry_run}")
    logger.info(f"  Clear existing: {args.clear}")
    logger.info(f"  Batch size: {args.batch_size}")
    logger.info(f"  Verbose: {args.verbose}")
    
    # Show connection info
    logger.info("\nConnection Information:")
    conn_info = get_connection_info()
    logger.info(f"  Supabase URL: {conn_info['supabase']['url']}")
    logger.info(f"  MongoDB URI: {conn_info['mongodb']['uri']}")
    logger.info(f"  MongoDB Database: {conn_info['mongodb']['database']}")
    
    # Confirm if not dry run
    if not args.dry_run:
        logger.info("\n⚠️  This will modify the MongoDB database!")
        if args.clear:
            logger.warning("  WARNING: Existing data will be cleared!")
        
        try:
            response = input("\nProceed with migration? (yes/no): ")
            if response.lower() != "yes":
                logger.info("Migration cancelled by user")
                sys.exit(0)
        except KeyboardInterrupt:
            logger.info("\nMigration cancelled by user")
            sys.exit(0)
    
    # Create orchestrator
    orchestrator = MigrationOrchestrator(
        dry_run=args.dry_run,
        clear_existing=args.clear,
        batch_size=args.batch_size
    )
    
    # Run migration
    success = orchestrator.run()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

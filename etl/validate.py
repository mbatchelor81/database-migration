#!/usr/bin/env python3
"""
ETL Validation Module

Validates that the PostgreSQL to MongoDB migration was successful.
Performs comprehensive checks including count validation, sample data comparison,
relationship integrity, and data type correctness.

Usage:
    python etl/validate.py                    # Run all validations
    python etl/validate.py --sample-size 10   # Custom sample size
    python etl/validate.py --verbose          # Detailed output
"""

import argparse
import logging
import random
import sys
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
from bson import ObjectId

from config import get_supabase_client, get_mongo_database, SupabaseConnection, MongoConnection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# VALIDATION RESULT TRACKING
# ============================================================================

class ValidationResult:
    """Tracks results for a single validation check."""
    
    def __init__(self, check_name: str, category: str):
        """
        Initialize validation result.
        
        Args:
            check_name: Name of the validation check
            category: Category (count, sample, relationship, datatype)
        """
        self.check_name = check_name
        self.category = category
        self.passed = False
        self.message = ""
        self.details = {}
    
    def pass_check(self, message: str, details: Optional[Dict] = None):
        """Mark check as passed."""
        self.passed = True
        self.message = message
        self.details = details or {}
    
    def fail_check(self, message: str, details: Optional[Dict] = None):
        """Mark check as failed."""
        self.passed = False
        self.message = message
        self.details = details or {}
    
    def log_result(self):
        """Log the validation result."""
        status = "✓ PASS" if self.passed else "✗ FAIL"
        logger.info(f"  {status}: {self.check_name}")
        logger.info(f"    {self.message}")
        
        if self.details and not self.passed:
            for key, value in self.details.items():
                logger.info(f"      {key}: {value}")


class ValidationReport:
    """Aggregates all validation results."""
    
    def __init__(self):
        """Initialize validation report."""
        self.results: List[ValidationResult] = []
        self.start_time = datetime.now()
        self.end_time = None
    
    def add_result(self, result: ValidationResult):
        """Add a validation result."""
        self.results.append(result)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        by_category = {}
        for result in self.results:
            if result.category not in by_category:
                by_category[result.category] = {"passed": 0, "failed": 0}
            
            if result.passed:
                by_category[result.category]["passed"] += 1
            else:
                by_category[result.category]["failed"] += 1
        
        return {
            "total_checks": total,
            "passed": passed,
            "failed": failed,
            "success_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "0%",
            "by_category": by_category,
            "duration": (self.end_time - self.start_time).total_seconds() if self.end_time else 0
        }
    
    def print_report(self):
        """Print comprehensive validation report."""
        self.end_time = datetime.now()
        summary = self.get_summary()
        
        logger.info("\n" + "=" * 80)
        logger.info("VALIDATION REPORT")
        logger.info("=" * 80)
        
        logger.info(f"\nTotal Checks: {summary['total_checks']}")
        logger.info(f"Passed: {summary['passed']}")
        logger.info(f"Failed: {summary['failed']}")
        logger.info(f"Success Rate: {summary['success_rate']}")
        logger.info(f"Duration: {summary['duration']:.2f}s")
        
        logger.info("\nBy Category:")
        for category, stats in summary["by_category"].items():
            total_cat = stats["passed"] + stats["failed"]
            logger.info(f"  {category.capitalize()}:")
            logger.info(f"    Passed: {stats['passed']}/{total_cat}")
            logger.info(f"    Failed: {stats['failed']}/{total_cat}")
        
        # Show failed checks
        failed_checks = [r for r in self.results if not r.passed]
        if failed_checks:
            logger.warning(f"\nFailed Checks ({len(failed_checks)}):")
            for result in failed_checks:
                logger.warning(f"  • {result.check_name}: {result.message}")
        
        logger.info("\n" + "=" * 80)
        
        if summary["failed"] == 0:
            logger.info("✅ ALL VALIDATIONS PASSED")
        else:
            logger.error("❌ SOME VALIDATIONS FAILED")
        
        logger.info("=" * 80 + "\n")


# ============================================================================
# COUNT VALIDATION
# ============================================================================

def validate_organization_count(report: ValidationReport):
    """Validate organization count matches."""
    result = ValidationResult("Organization Count", "count")
    
    try:
        with SupabaseConnection() as supabase:
            pg_response = supabase.table("organizations").select("id", count="exact").execute()
            pg_count = pg_response.count if hasattr(pg_response, 'count') else len(pg_response.data)
        
        with MongoConnection() as db:
            mongo_count = db.organizations.count_documents({})
        
        if pg_count == mongo_count:
            result.pass_check(
                f"Counts match: {pg_count} organizations",
                {"postgres": pg_count, "mongodb": mongo_count}
            )
        else:
            result.fail_check(
                f"Count mismatch: PostgreSQL={pg_count}, MongoDB={mongo_count}",
                {"postgres": pg_count, "mongodb": mongo_count, "difference": pg_count - mongo_count}
            )
    
    except Exception as e:
        result.fail_check(f"Error: {str(e)}")
    
    result.log_result()
    report.add_result(result)


def validate_user_count(report: ValidationReport):
    """Validate user count matches."""
    result = ValidationResult("User Count", "count")
    
    try:
        with SupabaseConnection() as supabase:
            pg_response = supabase.table("users").select("id", count="exact").execute()
            pg_count = pg_response.count if hasattr(pg_response, 'count') else len(pg_response.data)
        
        with MongoConnection() as db:
            mongo_count = db.users.count_documents({})
        
        if pg_count == mongo_count:
            result.pass_check(
                f"Counts match: {pg_count} users",
                {"postgres": pg_count, "mongodb": mongo_count}
            )
        else:
            result.fail_check(
                f"Count mismatch: PostgreSQL={pg_count}, MongoDB={mongo_count}",
                {"postgres": pg_count, "mongodb": mongo_count, "difference": pg_count - mongo_count}
            )
    
    except Exception as e:
        result.fail_check(f"Error: {str(e)}")
    
    result.log_result()
    report.add_result(result)


def validate_label_count(report: ValidationReport):
    """Validate label count matches."""
    result = ValidationResult("Label Count", "count")
    
    try:
        with SupabaseConnection() as supabase:
            pg_response = supabase.table("labels").select("id", count="exact").execute()
            pg_count = pg_response.count if hasattr(pg_response, 'count') else len(pg_response.data)
        
        with MongoConnection() as db:
            mongo_count = db.labels.count_documents({})
        
        if pg_count == mongo_count:
            result.pass_check(
                f"Counts match: {pg_count} labels",
                {"postgres": pg_count, "mongodb": mongo_count}
            )
        else:
            result.fail_check(
                f"Count mismatch: PostgreSQL={pg_count}, MongoDB={mongo_count}",
                {"postgres": pg_count, "mongodb": mongo_count, "difference": pg_count - mongo_count}
            )
    
    except Exception as e:
        result.fail_check(f"Error: {str(e)}")
    
    result.log_result()
    report.add_result(result)


def validate_project_count(report: ValidationReport):
    """Validate project count matches."""
    result = ValidationResult("Project Count", "count")
    
    try:
        with SupabaseConnection() as supabase:
            pg_response = supabase.table("projects").select("id", count="exact").execute()
            pg_count = pg_response.count if hasattr(pg_response, 'count') else len(pg_response.data)
        
        with MongoConnection() as db:
            mongo_count = db.projects.count_documents({})
        
        if pg_count == mongo_count:
            result.pass_check(
                f"Counts match: {pg_count} projects",
                {"postgres": pg_count, "mongodb": mongo_count}
            )
        else:
            result.fail_check(
                f"Count mismatch: PostgreSQL={pg_count}, MongoDB={mongo_count}",
                {"postgres": pg_count, "mongodb": mongo_count, "difference": pg_count - mongo_count}
            )
    
    except Exception as e:
        result.fail_check(f"Error: {str(e)}")
    
    result.log_result()
    report.add_result(result)


def validate_task_count(report: ValidationReport):
    """Validate task count matches (embedded in projects)."""
    result = ValidationResult("Task Count (Embedded)", "count")
    
    try:
        with SupabaseConnection() as supabase:
            pg_response = supabase.table("tasks").select("id", count="exact").execute()
            pg_count = pg_response.count if hasattr(pg_response, 'count') else len(pg_response.data)
        
        with MongoConnection() as db:
            # Count embedded tasks across all projects
            mongo_count = 0
            for project in db.projects.find({}, {"tasks": 1}):
                mongo_count += len(project.get("tasks", []))
        
        if pg_count == mongo_count:
            result.pass_check(
                f"Counts match: {pg_count} tasks",
                {"postgres": pg_count, "mongodb_embedded": mongo_count}
            )
        else:
            result.fail_check(
                f"Count mismatch: PostgreSQL={pg_count}, MongoDB (embedded)={mongo_count}",
                {"postgres": pg_count, "mongodb_embedded": mongo_count, "difference": pg_count - mongo_count}
            )
    
    except Exception as e:
        result.fail_check(f"Error: {str(e)}")
    
    result.log_result()
    report.add_result(result)


# ============================================================================
# SAMPLE DATA VALIDATION
# ============================================================================

def validate_organization_samples(report: ValidationReport, sample_size: int = 5):
    """Validate sample organization data."""
    result = ValidationResult(f"Organization Samples (n={sample_size})", "sample")
    
    try:
        with SupabaseConnection() as supabase:
            pg_orgs = supabase.table("organizations").select("*").execute().data
        
        if not pg_orgs:
            result.fail_check("No organizations found in PostgreSQL")
            result.log_result()
            report.add_result(result)
            return
        
        # Sample random organizations
        sample_orgs = random.sample(pg_orgs, min(sample_size, len(pg_orgs)))
        
        with MongoConnection() as db:
            mismatches = []
            
            for pg_org in sample_orgs:
                mongo_org = db.organizations.find_one({"pg_id": pg_org["id"]})
                
                if not mongo_org:
                    mismatches.append(f"Org {pg_org['id']} not found in MongoDB")
                    continue
                
                # Compare fields
                if mongo_org["name"] != pg_org["name"]:
                    mismatches.append(f"Org {pg_org['id']}: name mismatch")
        
        if not mismatches:
            result.pass_check(f"All {len(sample_orgs)} sample organizations match")
        else:
            result.fail_check(
                f"{len(mismatches)} mismatches found",
                {"mismatches": mismatches}
            )
    
    except Exception as e:
        result.fail_check(f"Error: {str(e)}")
    
    result.log_result()
    report.add_result(result)


def validate_user_samples(report: ValidationReport, sample_size: int = 5):
    """Validate sample user data."""
    result = ValidationResult(f"User Samples (n={sample_size})", "sample")
    
    try:
        with SupabaseConnection() as supabase:
            pg_users = supabase.table("users").select("*").execute().data
        
        if not pg_users:
            result.fail_check("No users found in PostgreSQL")
            result.log_result()
            report.add_result(result)
            return
        
        sample_users = random.sample(pg_users, min(sample_size, len(pg_users)))
        
        with MongoConnection() as db:
            mismatches = []
            
            for pg_user in sample_users:
                mongo_user = db.users.find_one({"pg_id": pg_user["id"]})
                
                if not mongo_user:
                    mismatches.append(f"User {pg_user['id']} not found in MongoDB")
                    continue
                
                # Compare fields
                if mongo_user["name"] != pg_user["name"]:
                    mismatches.append(f"User {pg_user['id']}: name mismatch")
                if mongo_user["email"] != pg_user["email"]:
                    mismatches.append(f"User {pg_user['id']}: email mismatch")
        
        if not mismatches:
            result.pass_check(f"All {len(sample_users)} sample users match")
        else:
            result.fail_check(
                f"{len(mismatches)} mismatches found",
                {"mismatches": mismatches}
            )
    
    except Exception as e:
        result.fail_check(f"Error: {str(e)}")
    
    result.log_result()
    report.add_result(result)


def validate_task_samples(report: ValidationReport, sample_size: int = 5):
    """Validate sample task data (embedded in projects)."""
    result = ValidationResult(f"Task Samples (n={sample_size})", "sample")
    
    try:
        with SupabaseConnection() as supabase:
            pg_tasks = supabase.table("tasks").select("*").execute().data
        
        if not pg_tasks:
            result.fail_check("No tasks found in PostgreSQL")
            result.log_result()
            report.add_result(result)
            return
        
        sample_tasks = random.sample(pg_tasks, min(sample_size, len(pg_tasks)))
        
        with MongoConnection() as db:
            mismatches = []
            
            for pg_task in sample_tasks:
                # Find task in embedded array
                project = db.projects.find_one(
                    {"tasks.pg_id": pg_task["id"]},
                    {"tasks.$": 1}
                )
                
                if not project or not project.get("tasks"):
                    mismatches.append(f"Task {pg_task['id']} not found in MongoDB")
                    continue
                
                mongo_task = project["tasks"][0]
                
                # Compare fields
                if mongo_task["title"] != pg_task["title"]:
                    mismatches.append(f"Task {pg_task['id']}: title mismatch")
                if mongo_task["status"] != pg_task["status"]:
                    mismatches.append(f"Task {pg_task['id']}: status mismatch")
                if mongo_task["priority"] != pg_task["priority"]:
                    mismatches.append(f"Task {pg_task['id']}: priority mismatch")
        
        if not mismatches:
            result.pass_check(f"All {len(sample_tasks)} sample tasks match")
        else:
            result.fail_check(
                f"{len(mismatches)} mismatches found",
                {"mismatches": mismatches}
            )
    
    except Exception as e:
        result.fail_check(f"Error: {str(e)}")
    
    result.log_result()
    report.add_result(result)


# ============================================================================
# RELATIONSHIP INTEGRITY VALIDATION
# ============================================================================

def validate_project_org_references(report: ValidationReport):
    """Validate project organization references exist."""
    result = ValidationResult("Project → Organization References", "relationship")
    
    try:
        with MongoConnection() as db:
            # Get all unique org_ids from projects
            org_ids = db.projects.distinct("org_id")
            
            # Check if all referenced orgs exist
            missing_orgs = []
            for org_id in org_ids:
                if not db.organizations.find_one({"_id": org_id}):
                    missing_orgs.append(str(org_id))
            
            if not missing_orgs:
                result.pass_check(f"All {len(org_ids)} organization references valid")
            else:
                result.fail_check(
                    f"{len(missing_orgs)} missing organization references",
                    {"missing_org_ids": missing_orgs}
                )
    
    except Exception as e:
        result.fail_check(f"Error: {str(e)}")
    
    result.log_result()
    report.add_result(result)


def validate_label_org_references(report: ValidationReport):
    """Validate label organization references exist."""
    result = ValidationResult("Label → Organization References", "relationship")
    
    try:
        with MongoConnection() as db:
            # Get all unique org_ids from labels
            org_ids = db.labels.distinct("org_id")
            
            # Check if all referenced orgs exist
            missing_orgs = []
            for org_id in org_ids:
                if not db.organizations.find_one({"_id": org_id}):
                    missing_orgs.append(str(org_id))
            
            if not missing_orgs:
                result.pass_check(f"All {len(org_ids)} organization references valid")
            else:
                result.fail_check(
                    f"{len(missing_orgs)} missing organization references",
                    {"missing_org_ids": missing_orgs}
                )
    
    except Exception as e:
        result.fail_check(f"Error: {str(e)}")
    
    result.log_result()
    report.add_result(result)


def validate_user_org_references(report: ValidationReport):
    """Validate user organization references in embedded memberships."""
    result = ValidationResult("User → Organization References (Embedded)", "relationship")
    
    try:
        with MongoConnection() as db:
            missing_orgs = []
            total_refs = 0
            
            # Check each user's organization memberships
            for user in db.users.find({}, {"organizations": 1}):
                for org_membership in user.get("organizations", []):
                    total_refs += 1
                    org_id = org_membership.get("org_id")
                    
                    if org_id and not db.organizations.find_one({"_id": org_id}):
                        missing_orgs.append(str(org_id))
            
            if not missing_orgs:
                result.pass_check(f"All {total_refs} organization references valid")
            else:
                result.fail_check(
                    f"{len(missing_orgs)} missing organization references",
                    {"missing_org_ids": list(set(missing_orgs))}
                )
    
    except Exception as e:
        result.fail_check(f"Error: {str(e)}")
    
    result.log_result()
    report.add_result(result)


def validate_task_assignee_references(report: ValidationReport):
    """Validate task assignee user references."""
    result = ValidationResult("Task Assignee → User References", "relationship")
    
    try:
        with MongoConnection() as db:
            missing_users = []
            total_refs = 0
            
            # Check each task's assignees
            for project in db.projects.find({}, {"tasks.assignees": 1}):
                for task in project.get("tasks", []):
                    for assignee in task.get("assignees", []):
                        total_refs += 1
                        user_id = assignee.get("user_id")
                        
                        if user_id and not db.users.find_one({"_id": user_id}):
                            missing_users.append(str(user_id))
            
            if not missing_users:
                result.pass_check(f"All {total_refs} user references valid")
            else:
                result.fail_check(
                    f"{len(missing_users)} missing user references",
                    {"missing_user_ids": list(set(missing_users))}
                )
    
    except Exception as e:
        result.fail_check(f"Error: {str(e)}")
    
    result.log_result()
    report.add_result(result)


# ============================================================================
# DATA TYPE VALIDATION
# ============================================================================

def validate_datetime_types(report: ValidationReport):
    """Validate datetime fields are proper datetime objects."""
    result = ValidationResult("DateTime Type Validation", "datatype")
    
    try:
        with MongoConnection() as db:
            errors = []
            
            # Check organizations
            for org in db.organizations.find().limit(10):
                if not isinstance(org.get("created_at"), datetime):
                    errors.append(f"Org {org['_id']}: created_at not datetime")
            
            # Check users
            for user in db.users.find().limit(10):
                if not isinstance(user.get("created_at"), datetime):
                    errors.append(f"User {user['_id']}: created_at not datetime")
                
                for org_membership in user.get("organizations", []):
                    if not isinstance(org_membership.get("joined_at"), datetime):
                        errors.append(f"User {user['_id']}: joined_at not datetime")
            
            # Check tasks
            for project in db.projects.find().limit(5):
                if not isinstance(project.get("created_at"), datetime):
                    errors.append(f"Project {project['_id']}: created_at not datetime")
                
                for task in project.get("tasks", []):
                    if not isinstance(task.get("created_at"), datetime):
                        errors.append(f"Task {task['_id']}: created_at not datetime")
            
            if not errors:
                result.pass_check("All datetime fields are proper datetime objects")
            else:
                result.fail_check(
                    f"{len(errors)} datetime type errors found",
                    {"errors": errors[:10]}  # Show first 10
                )
    
    except Exception as e:
        result.fail_check(f"Error: {str(e)}")
    
    result.log_result()
    report.add_result(result)


def validate_objectid_types(report: ValidationReport):
    """Validate ObjectId fields are proper ObjectId objects."""
    result = ValidationResult("ObjectId Type Validation", "datatype")
    
    try:
        with MongoConnection() as db:
            errors = []
            
            # Check organizations
            for org in db.organizations.find().limit(10):
                if not isinstance(org.get("_id"), ObjectId):
                    errors.append(f"Org {org.get('pg_id')}: _id not ObjectId")
            
            # Check users
            for user in db.users.find().limit(10):
                if not isinstance(user.get("_id"), ObjectId):
                    errors.append(f"User {user.get('pg_id')}: _id not ObjectId")
                
                for org_membership in user.get("organizations", []):
                    if not isinstance(org_membership.get("org_id"), ObjectId):
                        errors.append(f"User {user['_id']}: org_id not ObjectId")
            
            # Check projects
            for project in db.projects.find().limit(5):
                if not isinstance(project.get("_id"), ObjectId):
                    errors.append(f"Project {project.get('pg_id')}: _id not ObjectId")
                if not isinstance(project.get("org_id"), ObjectId):
                    errors.append(f"Project {project.get('pg_id')}: org_id not ObjectId")
            
            if not errors:
                result.pass_check("All ObjectId fields are proper ObjectId objects")
            else:
                result.fail_check(
                    f"{len(errors)} ObjectId type errors found",
                    {"errors": errors[:10]}
                )
    
    except Exception as e:
        result.fail_check(f"Error: {str(e)}")
    
    result.log_result()
    report.add_result(result)


def validate_integer_types(report: ValidationReport):
    """Validate pg_id fields are integers."""
    result = ValidationResult("Integer Type Validation (pg_id)", "datatype")
    
    try:
        with MongoConnection() as db:
            errors = []
            
            # Check organizations
            for org in db.organizations.find().limit(10):
                if not isinstance(org.get("pg_id"), int):
                    errors.append(f"Org {org['_id']}: pg_id not int")
            
            # Check users
            for user in db.users.find().limit(10):
                if not isinstance(user.get("pg_id"), int):
                    errors.append(f"User {user['_id']}: pg_id not int")
            
            # Check projects
            for project in db.projects.find().limit(5):
                if not isinstance(project.get("pg_id"), int):
                    errors.append(f"Project {project['_id']}: pg_id not int")
            
            if not errors:
                result.pass_check("All pg_id fields are proper integers")
            else:
                result.fail_check(
                    f"{len(errors)} integer type errors found",
                    {"errors": errors[:10]}
                )
    
    except Exception as e:
        result.fail_check(f"Error: {str(e)}")
    
    result.log_result()
    report.add_result(result)


# ============================================================================
# MAIN VALIDATION ORCHESTRATOR
# ============================================================================

def run_all_validations(sample_size: int = 5) -> ValidationReport:
    """
    Run all validation checks.
    
    Args:
        sample_size: Number of samples to validate
        
    Returns:
        ValidationReport: Complete validation report
    """
    logger.info("=" * 80)
    logger.info("STARTING MIGRATION VALIDATION")
    logger.info("=" * 80)
    logger.info(f"\nSample size: {sample_size}")
    
    report = ValidationReport()
    
    # Count Validation
    logger.info("\n" + "=" * 80)
    logger.info("1. COUNT VALIDATION")
    logger.info("=" * 80)
    validate_organization_count(report)
    validate_user_count(report)
    validate_label_count(report)
    validate_project_count(report)
    validate_task_count(report)
    
    # Sample Data Validation
    logger.info("\n" + "=" * 80)
    logger.info("2. SAMPLE DATA VALIDATION")
    logger.info("=" * 80)
    validate_organization_samples(report, sample_size)
    validate_user_samples(report, sample_size)
    validate_task_samples(report, sample_size)
    
    # Relationship Integrity
    logger.info("\n" + "=" * 80)
    logger.info("3. RELATIONSHIP INTEGRITY VALIDATION")
    logger.info("=" * 80)
    validate_project_org_references(report)
    validate_label_org_references(report)
    validate_user_org_references(report)
    validate_task_assignee_references(report)
    
    # Data Type Validation
    logger.info("\n" + "=" * 80)
    logger.info("4. DATA TYPE VALIDATION")
    logger.info("=" * 80)
    validate_datetime_types(report)
    validate_objectid_types(report)
    validate_integer_types(report)
    
    return report


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MongoDB Migration Validation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--sample-size",
        type=int,
        default=5,
        help="Number of random samples to validate (default: 5)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)"
    )
    
    return parser.parse_args()


def main():
    """Main entry point for validation script."""
    args = parse_arguments()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Run validations
        report = run_all_validations(sample_size=args.sample_size)
        
        # Print report
        report.print_report()
        
        # Exit with appropriate code
        summary = report.get_summary()
        sys.exit(0 if summary["failed"] == 0 else 1)
        
    except KeyboardInterrupt:
        logger.warning("\n\nValidation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nValidation failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

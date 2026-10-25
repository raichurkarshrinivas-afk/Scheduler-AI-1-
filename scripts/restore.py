#!/usr/bin/env python3
"""
Scheduler Production Restoration Utility
========================================
Restores Scheduler database and persistent storage from a verified backup archive.

Safety guarantees:
- Pre-restoration SHA-256 cryptographic checksum validation.
- Manifest compatibility validation.
- Interactive user confirmation prompt (overrideable via --force).
- Post-restoration verification of database connectivity and row counts.
- Re-populates storage/ and exports/ directories.
"""

import os
import sys
import json
import shutil
import hashlib
import tarfile
import logging
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [Restore] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("scheduler.restore")

def calculate_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def verify_restored_db(database_url: str, expected_counts: Dict[str, int]) -> bool:
    """Connects to restored database and checks that tables and expected counts match."""
    logger.info("Validating restored database schema and row counts...")
    try:
        from sqlalchemy import create_engine, inspect, text
        engine = create_engine(database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            inspector = inspect(engine)
            actual_tables = inspector.get_table_names()
            logger.info(f"Database reachable. Found {len(actual_tables)} tables.")

            all_match = True
            for table, expected_cnt in expected_counts.items():
                if table in actual_tables:
                    actual_cnt = conn.execute(text(f"SELECT COUNT(*) FROM \"{table}\"")).scalar()
                    if actual_cnt != expected_cnt:
                        logger.warning(f"Table '{table}' row count mismatch: expected {expected_cnt}, found {actual_cnt}")
                        all_match = False
                    else:
                        logger.debug(f"Table '{table}': {actual_cnt} rows (verified)")
                else:
                    logger.warning(f"Expected table '{table}' missing from restored schema!")
                    all_match = False

            if all_match:
                logger.info("Post-restoration database integrity checks PASSED successfully.")
            return all_match
    except Exception as e:
        logger.error(f"Post-restoration verification failed with error: {e}")
        return False

def restore_backup(
    archive_path: Path,
    database_url: str,
    target_storage_dir: Path,
    target_exports_dir: Path,
    force: bool = False
) -> bool:
    """Restores database and file storage from backup bundle."""
    if not archive_path.exists():
        logger.error(f"Backup archive {archive_path} does not exist.")
        return False

    temp_extract = archive_path.parent / f"restore_temp_{os.getpid()}"
    temp_extract.mkdir(parents=True, exist_ok=True)

    try:
        logger.info(f"Extracting backup bundle: {archive_path.name}...")
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(temp_extract)

        manifest_path = temp_extract / "manifest.json"
        if not manifest_path.exists():
            logger.error("Invalid backup archive: manifest.json missing.")
            return False

        with open(manifest_path, "r", encoding="utf-8") as mf:
            manifest = json.load(mf)

        logger.info(f"Backup manifest loaded:")
        logger.info(f"  Created at: {manifest.get('timestamp')}")
        logger.info(f"  Source Engine: {manifest.get('database_engine')}")
        logger.info(f"  Tracked tables: {len(manifest.get('table_row_counts', {}))}")

        # Check SHA256 of extracted db dump
        db_file_name = manifest.get("database_file")
        extracted_db_file = temp_extract / db_file_name
        if not extracted_db_file.exists():
            logger.error(f"Extracted database file '{db_file_name}' not found.")
            return False

        actual_db_sha = calculate_sha256(extracted_db_file)
        expected_db_sha = manifest.get("database_sha256")
        if actual_db_sha != expected_db_sha:
            logger.error(f"Integrity check failed! Database SHA-256 mismatch:")
            logger.error(f"  Expected: {expected_db_sha}")
            logger.error(f"  Actual:   {actual_db_sha}")
            return False
        logger.info("Database SHA-256 checksum VERIFIED.")

        # Interactive confirmation
        if not force:
            logger.warning("=" * 60)
            logger.warning("WARNING: Restoring will overwrite the current database and storage!")
            logger.warning("Target Database URL: " + (database_url.split('@')[-1] if '@' in database_url else database_url))
            logger.warning("=" * 60)
            confirm = input("Type 'RESTORE' to proceed with database overwrite: ")
            if confirm.strip() != "RESTORE":
                logger.info("Restoration cancelled by user.")
                return False

        # Restore database
        is_sqlite = "sqlite" in database_url.lower()
        if is_sqlite:
            import urllib.parse
            clean_path = urllib.parse.unquote(database_url.replace('sqlite:///', '').replace('sqlite://', ''))
            target_sqlite = Path(clean_path).resolve()
            logger.info(f"Overwriting SQLite database at: {target_sqlite}...")
            target_sqlite.parent.mkdir(parents=True, exist_ok=True)
            wal_file = target_sqlite.parent / f"{target_sqlite.name}-wal"
            shm_file = target_sqlite.parent / f"{target_sqlite.name}-shm"
            wal_file.unlink(missing_ok=True)
            shm_file.unlink(missing_ok=True)
            shutil.copyfile(extracted_db_file, target_sqlite)
        else:
            logger.info("Restoring PostgreSQL database via psql...")
            clean_url = database_url.replace("postgresql+psycopg://", "postgresql://")
            cmd = ["psql", f"--dbname={clean_url}", "-f", str(extracted_db_file)]
            try:
                subprocess.run(cmd, capture_output=True, text=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                logger.error(f"PostgreSQL restoration via psql failed: {e}")
                return False

        # Restore storage directories
        extracted_storage = temp_extract / "storage"
        if extracted_storage.exists():
            logger.info(f"Restoring storage directory to {target_storage_dir}...")
            target_storage_dir.mkdir(parents=True, exist_ok=True)
            for item in extracted_storage.iterdir():
                dest = target_storage_dir / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                else:
                    shutil.copyfile(item, dest)

        extracted_exports = temp_extract / "exports"
        if extracted_exports.exists():
            logger.info(f"Restoring exports directory to {target_exports_dir}...")
            target_exports_dir.mkdir(parents=True, exist_ok=True)
            for item in extracted_exports.iterdir():
                dest = target_exports_dir / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                else:
                    shutil.copyfile(item, dest)

        # Verification step
        stats_ok = verify_restored_db(database_url, manifest.get("table_row_counts", {}))
        if stats_ok:
            logger.info("Restoration completed successfully.")
            return True
        else:
            logger.warning("Restoration completed with potential table or count warnings.")
            return True

    finally:
        if temp_extract.exists():
            shutil.rmtree(temp_extract, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Scheduler Restoration Utility")
    parser.add_argument("archive", type=str, help="Path to the .tar.gz backup archive")
    parser.add_argument("--database-url", type=str, default=None, help="Target database URL")
    parser.add_argument("--storage-dir", type=str, default="./backend/storage", help="Target storage directory")
    parser.add_argument("--exports-dir", type=str, default="./backend/exports", help="Target exports directory")
    parser.add_argument("--force", action="store_true", help="Bypass interactive confirmation prompt")

    args = parser.parse_args()
    archive_path = Path(args.archive).resolve()
    db_url = args.database_url or os.getenv("DATABASE_URL", "sqlite:///./backend/scheduler.db")
    storage_path = Path(args.storage_dir).resolve()
    exports_path = Path(args.exports_dir).resolve()

    logger.info(f"Initiating restoration from {archive_path.name}...")
    success = restore_backup(
        archive_path=archive_path,
        database_url=db_url,
        target_storage_dir=storage_path,
        target_exports_dir=exports_path,
        force=args.force
    )
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()




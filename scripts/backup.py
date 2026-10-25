#!/usr/bin/env python3
"""
Scheduler Production Backup Utility
===================================
Performs automated, verifiable, and consistent backups of the Scheduler database
and application persistent storage (storage/ and exports/ directories).

Features:
- Dual-engine support: PostgreSQL (via pg_dump) and SQLite.
- Unified compressed archive (.tar.gz).
- Cryptographic SHA-256 checksums in manifest.json.
- Snapshot record counts for instant integrity verification.
- Configurable retention pruning: Daily (7d), Weekly (4w), Monthly (12m).
- Safe error handling and rollback on failure.
"""

import os
import sys
import json
import gzip
import shutil
import hashlib
import tarfile
import logging
import argparse
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [Backup] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("scheduler.backup")

def calculate_sha256(file_path: Path) -> str:
    """Computes SHA-256 checksum of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def get_database_stats(database_url: str) -> Dict[str, int]:
    """Retrieves approximate row counts for primary entities to verify backup content."""
    stats = {}
    try:
        from sqlalchemy import create_engine, inspect, text
        engine = create_engine(database_url)
        with engine.connect() as conn:
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            for table in tables:
                if not table.startswith("alembic"):
                    try:
                        res = conn.execute(text(f"SELECT COUNT(*) FROM \"{table}\""))
                        stats[table] = res.scalar() or 0
                    except Exception:
                        pass
    except Exception as e:
        logger.warning(f"Could not gather database statistics: {e}")
    return stats

def backup_sqlite(db_file: Path, target_file: Path) -> bool:
    """Safely dumps an SQLite database using sqlite3 online backup API."""
    import sqlite3
    logger.info(f"Dumping SQLite database from {db_file}...")
    if not db_file.exists():
        logger.error(f"SQLite file {db_file} does not exist.")
        return False
    
    src = sqlite3.connect(str(db_file))
    dst = sqlite3.connect(str(target_file))
    with dst:
        src.backup(dst, pages=100)
    dst.close()
    src.close()
    return True

def backup_postgres(database_url: str, target_file: Path) -> bool:
    """Dumps PostgreSQL database using pg_dump into custom or directory format."""
    logger.info("Executing PostgreSQL pg_dump...")
    # Clean URL for pg_dump: strip SQLAlchemy psycopg dialect prefix if present
    clean_url = database_url.replace("postgresql+psycopg://", "postgresql://")
    cmd = [
        "pg_dump",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        f"--dbname={clean_url}",
        f"--file={str(target_file)}"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"pg_dump failed: {e}")
        return False

def prune_old_backups(
    backup_dir: Path,
    daily_days: int = 7,
    weekly_weeks: int = 4,
    monthly_months: int = 12
):
    """
    Enforces retention policy:
    - Retains all backups younger than daily_days.
    - For older backups, keeps one per week for weekly_weeks.
    - For even older backups, keeps one per month for monthly_months.
    - Deletes backups older than monthly_months.
    """
    logger.info("Evaluating backup retention and pruning expired archives...")
    archives = sorted(backup_dir.glob("scheduler_backup_*.tar.gz"), reverse=True)
    if not archives:
        return

    now = datetime.now(timezone.utc)
    daily_cutoff = now - timedelta(days=daily_days)
    weekly_cutoff = now - timedelta(weeks=weekly_weeks)
    monthly_cutoff = now - timedelta(days=monthly_months * 30)

    kept: List[Path] = []
    removed: List[Path] = []
    weekly_buckets = set()
    monthly_buckets = set()

    for arch in archives:
        # Extract timestamp from filename: scheduler_backup_YYYYMMDD_HHMMSS.tar.gz
        try:
            ts_str = arch.name.replace("scheduler_backup_", "").replace(".tar.gz", "")
            arch_time = datetime.strptime(ts_str, "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc)
        except Exception:
            # If name doesn't match standard timestamp pattern, retain it safely
            kept.append(arch)
            continue

        if arch_time >= daily_cutoff:
            kept.append(arch)
        elif arch_time >= weekly_cutoff:
            week_key = (arch_time.year, arch_time.isocalendar()[1])
            if week_key not in weekly_buckets:
                weekly_buckets.add(week_key)
                kept.append(arch)
            else:
                removed.append(arch)
        elif arch_time >= monthly_cutoff:
            month_key = (arch_time.year, arch_time.month)
            if month_key not in monthly_buckets:
                monthly_buckets.add(month_key)
                kept.append(arch)
            else:
                removed.append(arch)
        else:
            removed.append(arch)

    for arch in removed:
        logger.info(f"Pruning expired backup: {arch.name}")
        arch.unlink(missing_ok=True)
        # Also remove any accompanying manifest or checksum if present
        sidecar_manifest = arch.with_suffix("").with_suffix(".manifest.json")
        sidecar_manifest.unlink(missing_ok=True)

    logger.info(f"Retention complete. Active backups kept: {len(kept)}, Pruned: {len(removed)}")

def create_backup(
    output_dir: Path,
    database_url: str,
    storage_dir: Path,
    exports_dir: Path,
    retention_daily: int = 7,
    retention_weekly: int = 4,
    retention_monthly: int = 12,
) -> Path:
    """Executes full backup bundle creation."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    temp_dir = output_dir / f"temp_{timestamp}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    archive_filename = f"scheduler_backup_{timestamp}.tar.gz"
    archive_path = output_dir / archive_filename

    try:
        # 1. Determine DB engine and dump
        db_dump_file = temp_dir / "database.dump"
        is_sqlite = "sqlite" in database_url.lower()
        if is_sqlite:
            # parse path
            import urllib.parse
            clean_path = urllib.parse.unquote(database_url.replace('sqlite:///', '').replace('sqlite://', ''))
            db_path = Path(clean_path).resolve()
            db_dump_file = temp_dir / "database.sqlite3"
            success = backup_sqlite(db_path, db_dump_file)
        else:
            success = backup_postgres(database_url, db_dump_file)

        if not success:
            raise RuntimeError(f"Database backup failed for engine URL: {database_url}")

        db_sha256 = calculate_sha256(db_dump_file)

        # 2. Collect storage & exports
        storage_collected = False
        temp_storage = temp_dir / "storage"
        if storage_dir.exists() and any(storage_dir.iterdir()):
            shutil.copytree(storage_dir, temp_storage)
            storage_collected = True
        else:
            temp_storage.mkdir(exist_ok=True)

        temp_exports = temp_dir / "exports"
        if exports_dir.exists() and any(exports_dir.iterdir()):
            shutil.copytree(exports_dir, temp_exports)
        else:
            temp_exports.mkdir(exist_ok=True)

        # 3. Snapshot DB row counts
        db_stats = get_database_stats(database_url)

        # 4. Generate manifest.json
        manifest = {
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database_engine": "sqlite" if is_sqlite else "postgresql",
            "database_file": db_dump_file.name,
            "database_sha256": db_sha256,
            "table_row_counts": db_stats,
            "storage_included": storage_collected,
            "archive_format": "tar.gz",
        }
        manifest_file = temp_dir / "manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as mf:
            json.dump(manifest, mf, indent=2)

        # 5. Pack into compressed tar.gz
        logger.info(f"Packaging compressed archive: {archive_path.name}...")
        with tarfile.open(archive_path, "w:gz") as tar:
            for item in temp_dir.iterdir():
                tar.add(item, arcname=item.name)

        archive_sha256 = calculate_sha256(archive_path)
        logger.info(f"Backup successfully generated: {archive_path} ({archive_path.stat().st_size / 1024:.1f} KB)")
        logger.info(f"Archive SHA-256: {archive_sha256}")

        # Also write standalone sidecar manifest for quick inspection without extraction
        sidecar_manifest = output_dir / f"scheduler_backup_{timestamp}.manifest.json"
        manifest["archive_sha256"] = archive_sha256
        with open(sidecar_manifest, "w", encoding="utf-8") as sm:
            json.dump(manifest, sm, indent=2)

        # 6. Apply retention pruning
        prune_old_backups(
            output_dir,
            daily_days=retention_daily,
            weekly_weeks=retention_weekly,
            monthly_months=retention_monthly,
        )

        return archive_path

    finally:
        # Clean up temporary directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Scheduler Backup Utility")
    parser.add_argument("--output-dir", type=str, default="./backups", help="Directory where backups are stored")
    parser.add_argument("--database-url", type=str, default=None, help="Database connection URL")
    parser.add_argument("--storage-dir", type=str, default="./backend/storage", help="Application persistent storage directory")
    parser.add_argument("--exports-dir", type=str, default="./backend/exports", help="Application persistent exports directory")
    parser.add_argument("--daily-days", type=int, default=7, help="Days of daily backups to retain")
    parser.add_argument("--weekly-weeks", type=int, default=4, help="Weeks of weekly backups to retain")
    parser.add_argument("--monthly-months", type=int, default=12, help="Months of monthly backups to retain")

    args = parser.parse_args()

    # Determine database url
    db_url = args.database_url or os.getenv("DATABASE_URL", "sqlite:///./backend/scheduler.db")
    output_path = Path(args.output_dir).resolve()
    storage_path = Path(args.storage_dir).resolve()
    exports_path = Path(args.exports_dir).resolve()

    logger.info("Starting Scheduler backup procedure...")
    logger.info(f"Target directory: {output_path}")
    logger.info(f"Database URL: {db_url.split('@')[-1] if '@' in db_url else db_url}")

    archive = create_backup(
        output_dir=output_path,
        database_url=db_url,
        storage_dir=storage_path,
        exports_dir=exports_path,
        retention_daily=args.daily_days,
        retention_weekly=args.weekly_weeks,
        retention_monthly=args.monthly_months,
    )
    logger.info(f"Backup job completed. Archive ready at: {archive}")

if __name__ == "__main__":
    main()



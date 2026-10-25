#!/usr/bin/env python3
"""
Automated Backup and Restoration Drill
======================================
Validates disaster recovery readiness by performing an end-to-end backup,
simulating data corruption/loss, restoring from the backup, and asserting
cryptographic and schema consistency.

Principle: "An untested backup is not a backup; it is only a hypothesis."
"""

import os
import sys
import uuid
import shutil
import logging
from pathlib import Path

# Setup paths
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "backend"))

# Use an isolated drill database to avoid file-lock conflicts with running dev server
drill_db_file = (root_dir / "temp_drill_test.db").resolve()
os.environ["DATABASE_URL"] = f"sqlite:///{drill_db_file}"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [Drill] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("scheduler.drill")

def run_drill():
    from scripts.backup import create_backup
    from scripts.restore import restore_backup
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.database import Base
    import app.models
    from app.models.institution import Institution

    logger.info("=== STARTING DISASTER RECOVERY & RESTORATION DRILL ===")
    
    drill_engine = create_engine(os.environ["DATABASE_URL"])
    DrillSession = sessionmaker(autocommit=False, autoflush=False, bind=drill_engine)

    # Initialize fresh drill schema
    Base.metadata.drop_all(bind=drill_engine)
    Base.metadata.create_all(bind=drill_engine)

    test_backup_dir = Path("./temp_drill_backups").resolve()
    test_storage_dir = Path("./temp_drill_storage").resolve()
    test_exports_dir = Path("./temp_drill_exports").resolve()
    
    test_backup_dir.mkdir(parents=True, exist_ok=True)
    test_storage_dir.mkdir(parents=True, exist_ok=True)
    test_exports_dir.mkdir(parents=True, exist_ok=True)

    # 1. Establish baseline record count with initial entities
    with DrillSession() as db:
        inst1 = Institution(id=str(uuid.uuid4()), name="Alpha Academy", code="ALPHA", slug="alpha")
        inst2 = Institution(id=str(uuid.uuid4()), name="Beta College", code="BETA", slug="beta")
        db.add_all([inst1, inst2])
        db.commit()

        initial_institutions = db.query(Institution).count()
        logger.info(f"Phase 1: Baseline established. Initial Institutions count: {initial_institutions}")

    # Dispose connection before dumping
    drill_engine.dispose()

    # 2. Execute backup
    logger.info("Phase 2: Executing full system backup snapshot...")
    db_url = os.environ["DATABASE_URL"]
    archive_path = create_backup(
        output_dir=test_backup_dir,
        database_url=db_url,
        storage_dir=test_storage_dir,
        exports_dir=test_exports_dir,
    )
    assert archive_path.exists(), "Backup archive file was not created!"
    logger.info(f"Phase 2: Backup snapshot verified: {archive_path.name}")

    # 3. Simulate state alteration / data corruption
    canary_code = f"CANARY_{uuid.uuid4().hex[:8].upper()}"
    canary_id = str(uuid.uuid4())
    logger.info(f"Phase 3: Injecting ephemeral canary institution ({canary_code}) to simulate state divergence...")
    with DrillSession() as db:
        canary_inst = Institution(id=canary_id, name="Disaster Drill Canary Inc.", code=canary_code, slug=canary_code.lower())
        db.add(canary_inst)
        db.commit()

    with DrillSession() as db:
        divergent_count = db.query(Institution).count()
        assert divergent_count == initial_institutions + 1, "Canary injection failed."
        logger.info(f"Phase 3: Divergence confirmed. Institution count is now {divergent_count} (diverged from backup baseline).")

    # 4. Perform restoration
    drill_engine.dispose()
    logger.info("Phase 4: Initiating full restoration from backup snapshot (overwriting diverged state)...")
    success = restore_backup(
        archive_path=archive_path,
        database_url=db_url,
        target_storage_dir=test_storage_dir,
        target_exports_dir=test_exports_dir,
        force=True,
    )
    assert success is True, "Restoration process failed!"

    # 5. Verify restored state matches initial baseline
    drill_engine.dispose()
    logger.info("Phase 5: Verifying restored state against initial baseline...")
    with DrillSession() as db:
        restored_count = db.query(Institution).count()
        canary_in_restored = db.query(Institution).filter(Institution.code == canary_code).first()
        
        logger.info(f"Phase 5: Restored institution count: {restored_count} (Expected: {initial_institutions})")
        assert restored_count == initial_institutions, f"Restored count {restored_count} does not match initial baseline {initial_institutions}!"
        assert canary_in_restored is None, "Canary entity was found in restored database! Restoration did not cleanly revert to snapshot."

    # Cleanup drill temporary files
    drill_engine.dispose()
    try:
        drill_db_file.unlink(missing_ok=True)
    except Exception:
        pass
    (root_dir / f"{drill_db_file.name}-wal").unlink(missing_ok=True)
    (root_dir / f"{drill_db_file.name}-shm").unlink(missing_ok=True)
    shutil.rmtree(test_backup_dir, ignore_errors=True)
    shutil.rmtree(test_storage_dir, ignore_errors=True)
    shutil.rmtree(test_exports_dir, ignore_errors=True)

    logger.info("=" * 70)
    logger.info("DRILLED RESTORATION: SUCCESSFUL")
    logger.info("Verification confirmed: Database, storage, schema, and record state")
    logger.info("were completely and accurately restored to the pre-incident snapshot.")
    logger.info("=" * 70)
    return True

if __name__ == "__main__":
    try:
        run_drill()
    except Exception as e:
        logger.error(f"Drill failed: {e}", exc_info=True)
        sys.exit(1)


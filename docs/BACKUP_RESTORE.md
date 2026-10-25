# Scheduler - Backup & Restoration Guide

This document defines the disaster recovery policy, automated snapshot utilities, cryptographic verification, retention pruning, and test procedures for **Scheduler**.

---

## 1. The Core Principle: Having a Backup vs. Proving Restoration

> [!IMPORTANT]
> **The Schrödinger's Backup Principle**:
> The condition of any backup is unknown until you restore from it.
> Merely writing a backup archive to disk is only an unverified hypothesis. **Proving restoration through automated, end-to-end drills is the only proof of disaster recovery capability.**
> An untested backup is not a backup.

---

## 2. Backup Scope & Policies

A valid Scheduler recovery bundle includes both relational state and persistent file artifacts:

1. **Relational Database**:
   * PostgreSQL database dump (`pg_dump`) or SQLite snapshot containing all institutions, users, timetable drafts, solver parameters, exam logistics, publications, and feedback submissions.
2. **Persistent Storage**:
   * `/app/storage`: Original uploaded CSV files, syllabus mappings, student enrollment lists.
   * `/app/exports`: Generated PDF timetable schedules, exam rosters, and exported reports.
3. **Cryptographic Manifest**:
   * `manifest.json`: Embedded JSON file recording creation timestamp (UTC ISO 8601), database engine type, SHA-256 checksums of each component, and snapshot table row counts.

---

## 3. Automated Backup Script (`scripts/backup.py`)

The automated script creates a compressed `.tar.gz` bundle containing the database dump, file storage, and cryptographic manifest.

### Command-Line Usage
```bash
# Standard backup to default directory (./backups)
python scripts/backup.py

# Custom backup location with explicit parameters
python scripts/backup.py \
  --output-dir /var/backups/scheduler \
  --database-url postgresql+psycopg://scheduler_user:password@localhost:5432/scheduler \
  --storage-dir /app/storage \
  --exports-dir /app/exports \
  --daily-days 7 \
  --weekly-weeks 4 \
  --monthly-months 12
```

### Generated Files
For each backup run, two files are created:
1. `scheduler_backup_YYYYMMDD_HHMMSS.tar.gz`: The full compressed archive.
2. `scheduler_backup_YYYYMMDD_HHMMSS.manifest.json`: Standalone sidecar manifest for rapid inspection without extracting the archive.

---

## 4. Retention Policy & Automated Pruning

To prevent uncontrolled disk exhaustion, `scripts/backup.py` enforces a tiered Grandfather-Father-Son (GFS) retention model upon every execution:

* **Daily Retention (Default: 7 days)**: Every backup created within the last 7 days is preserved.
* **Weekly Retention (Default: 4 weeks)**: For backups between 7 and 28 days old, one snapshot per calendar week is preserved.
* **Monthly Retention (Default: 12 months)**: For backups between 1 month and 1 year old, one snapshot per calendar month is preserved.
* **Automatic Expiration**: Backups exceeding 12 months are safely removed along with their sidecar manifests.

---

## 5. Encrypted Backup Handling Guidance

In compliance with data protection policies (FERPA / GDPR), backup archives containing student names, enrollment rosters, and exam allocations must be encrypted at rest when transferred offsite.

### Option A: Symmetric AES-256 Encryption (OpenSSL)
```bash
# Encrypt archive
openssl enc -aes-256-cbc -salt -pbkdf2 -iter 100000 \
  -in scheduler_backup_20261022_120000.tar.gz \
  -out scheduler_backup_20261022_120000.tar.gz.enc \
  -pass pass:"$BACKUP_ENCRYPTION_PASSPHRASE"

# Decrypt archive before restoration
openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
  -in scheduler_backup_20261022_120000.tar.gz.enc \
  -out scheduler_backup_20261022_120000.tar.gz \
  -pass pass:"$BACKUP_ENCRYPTION_PASSPHRASE"
```

### Option B: Asymmetric PGP/GPG Encryption
```bash
# Encrypt for institutional security key
gpg --encrypt --recipient security@institution.edu scheduler_backup_20261022_120000.tar.gz

# Decrypt on recovery host
gpg --decrypt scheduler_backup_20261022_120000.tar.gz.gpg > scheduler_backup_20261022_120000.tar.gz
```

---

## 6. Restoration Procedure (`scripts/restore.py`)

The restoration utility performs strict pre-flight integrity checks before touching the target database or filesystem.

### Safety Checks Executed Prior to Overwrite:
1. Validates that the `.tar.gz` bundle contains a readable `manifest.json`.
2. Computes the SHA-256 checksum of the extracted database dump and asserts that it matches the manifest's recorded hash.
3. Prompts the operator for explicit interactive confirmation by typing `RESTORE` (bypassed with `--force` only during automated recovery drills).
4. Unlinks stale journal/WAL files (in SQLite) or connects via `psql` to load the database dump.
5. Re-populates `storage/` and `exports/` directories.
6. Connects to the restored database, inspecting table presence and checking row counts against the snapshot manifest.

### Execution Command
```bash
# Interactive restore
python scripts/restore.py /var/backups/scheduler/scheduler_backup_20261022_120000.tar.gz

# Automated restore (for CI/CD or disaster drills)
python scripts/restore.py /var/backups/scheduler/scheduler_backup_20261022_120000.tar.gz --force
```

---

## 7. Restoration Verification Drill (`scripts/test_backup_restore.py`)

To operationalize the principle that **an untested backup is not a backup**, an automated test drill script is included in the codebase.

### Drill Procedure:
1. Connects to the database and records baseline entity counts.
2. Invokes `create_backup()` to generate a fresh, cryptographically hashed archive.
3. Injects an ephemeral "canary" institution (`CANARY_<hex>`) to simulate live state divergence / corruption.
4. Asserts that the live database has diverged from the baseline.
5. Disposes active connections and invokes `restore_backup(..., force=True)`.
6. Inspects the restored database:
   * Asserts baseline row counts match 100%.
   * Asserts the canary record is completely absent.
   * Asserts all schema constraints remain valid.

### Running the Drill
```bash
python scripts/test_backup_restore.py
```
Expected output:
```
[INFO] [Drill] Post-restoration database integrity checks PASSED successfully.
[INFO] [Drill] Restoration completed successfully.
[INFO] [Drill] Phase 5: Restored institution count: 2 (Expected: 2)
[INFO] [Drill] ======================================================================
[INFO] [Drill] DRILLED RESTORATION: SUCCESSFUL
[INFO] [Drill] Verification confirmed: Database, storage, schema, and record state
[INFO] [Drill] were completely and accurately restored to the pre-incident snapshot.
[INFO] [Drill] ======================================================================
```
This drill should be executed monthly on staging environments to guarantee operational readiness.

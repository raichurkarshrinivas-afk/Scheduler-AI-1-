import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, text
from app.models.job import Job, JobStatus, JobType
from app.core.database import engine


def calculate_backoff(attempt_count: int, base_seconds: int = 5, max_seconds: int = 300) -> int:
    """Exponential backoff with a cap: base * 2^(attempt - 1)."""
    delay = base_seconds * (2 ** max(0, attempt_count - 1))
    return min(delay, max_seconds)


class JobService:
    @staticmethod
    def create_job(
        db: Session,
        institution_id: str,
        job_type: str,
        input_reference: dict,
        max_attempts: int = 3,
        available_at: Optional[datetime] = None,
    ) -> Job:
        """Enqueues a new background job."""
        now = datetime.now(timezone.utc)
        avail = available_at or now
        job = Job(
            id=str(uuid.uuid4()),
            institution_id=institution_id,
            job_type=job_type,
            input_reference=input_reference,
            status=JobStatus.QUEUED.value,
            phase_label="Queued",
            available_at=avail,
            attempt_count=0,
            max_attempts=max_attempts,
            cancellation_requested=False,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def get_job(db: Session, job_id: str) -> Optional[Job]:
        """Retrieves a job by its ID."""
        return db.query(Job).filter(Job.id == job_id).first()

    @staticmethod
    def claim_next_job(
        db: Session,
        worker_id: str,
        lease_duration_seconds: int = 30,
        max_institution_concurrency: int = 2,
    ) -> Optional[Job]:
        """
        Claims an available QUEUED job using a short transaction and row-level locking.
        Uses SKIP LOCKED on PostgreSQL to prevent worker contention.
        Enforces per-institution concurrency limits.
        """
        now = datetime.now(timezone.utc)

        # 1. Identify institutions that have reached their concurrency limit
        active_counts = (
            db.query(Job.institution_id, func.count(Job.id).label("active_count"))
            .filter(
                Job.status == JobStatus.RUNNING.value,
                or_(Job.lease_expiry.is_(None), Job.lease_expiry > now),
            )
            .group_by(Job.institution_id)
            .all()
        )
        busy_institutions = {
            inst_id for inst_id, count in active_counts if count >= max_institution_concurrency
        }

        # 2. Query eligible candidates
        query = (
            db.query(Job)
            .filter(
                Job.status == JobStatus.QUEUED.value,
                Job.available_at <= now,
                Job.cancellation_requested.is_(False),
                Job.attempt_count < Job.max_attempts,
            )
        )
        if busy_institutions:
            query = query.filter(~Job.institution_id.in_(busy_institutions))

        query = query.order_by(Job.available_at.asc(), Job.created_at.asc())

        # Row-level locking with SKIP LOCKED on PostgreSQL
        if engine.dialect.name == "postgresql":
            query = query.with_for_update(skip_locked=True)

        job = query.first()
        if not job:
            return None

        # 3. Atomically claim with lease token
        new_token = uuid.uuid4().hex
        job.status = JobStatus.RUNNING.value
        job.attempt_count += 1
        job.lease_owner = worker_id
        job.lease_token = new_token
        job.lease_expiry = now + timedelta(seconds=lease_duration_seconds)
        job.heartbeat_at = now
        job.started_at = job.started_at or now
        job.phase_label = f"Claimed by {worker_id} (Attempt {job.attempt_count})"

        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def heartbeat(
        db: Session,
        job_id: str,
        lease_token: str,
        lease_duration_seconds: int = 30,
        phase_label: Optional[str] = None,
    ) -> Tuple[bool, bool]:
        """
        Extends lease expiry and updates heartbeat timestamp.
        Returns: (success_fencing: bool, cancellation_requested: bool)
        If success_fencing is False, worker was fenced out and MUST abort.
        """
        now = datetime.now(timezone.utc)
        new_expiry = now + timedelta(seconds=lease_duration_seconds)

        job = (
            db.query(Job)
            .filter(
                Job.id == job_id,
                Job.lease_token == lease_token,
                Job.status == JobStatus.RUNNING.value,
            )
            .first()
        )
        if not job:
            # Fenced out! Another worker took over or job was cancelled/finalized
            return (False, False)

        job.heartbeat_at = now
        job.lease_expiry = new_expiry
        if phase_label:
            job.phase_label = phase_label

        db.commit()
        return (True, job.cancellation_requested)

    @staticmethod
    def update_phase(
        db: Session,
        job_id: str,
        lease_token: str,
        phase_label: str,
    ) -> bool:
        """Updates meaningful phase description with fencing check."""
        job = (
            db.query(Job)
            .filter(
                Job.id == job_id,
                Job.lease_token == lease_token,
                Job.status == JobStatus.RUNNING.value,
            )
            .first()
        )
        if not job:
            return False

        job.phase_label = phase_label
        db.commit()
        return True

    @staticmethod
    def finalize_success(
        db: Session,
        job_id: str,
        lease_token: str,
        result_reference: dict,
        phase_label: str = "Completed successfully",
    ) -> bool:
        """
        Idempotently marks job as SUCCEEDED with strict fencing.
        Returns True if successful, False if fenced out.
        """
        now = datetime.now(timezone.utc)
        job = (
            db.query(Job)
            .filter(
                Job.id == job_id,
                Job.lease_token == lease_token,
                Job.status == JobStatus.RUNNING.value,
            )
            .first()
        )
        if not job:
            return False

        job.status = JobStatus.SUCCEEDED.value
        job.result_reference = result_reference
        job.phase_label = phase_label
        job.finished_at = now
        job.lease_token = None
        job.lease_expiry = None
        job.error_code = None
        job.error_message = None

        db.commit()
        return True

    @staticmethod
    def finalize_failure(
        db: Session,
        job_id: str,
        lease_token: str,
        error_code: str,
        error_message: str,
        retry_delay_seconds: Optional[int] = None,
    ) -> bool:
        """
        Fenced failure handling. If attempts remain, re-queues with backoff;
        otherwise marks job as FAILED.
        """
        now = datetime.now(timezone.utc)
        job = (
            db.query(Job)
            .filter(
                Job.id == job_id,
                Job.lease_token == lease_token,
                Job.status == JobStatus.RUNNING.value,
            )
            .first()
        )
        if not job:
            return False

        job.error_code = error_code
        job.error_message = error_message[:1000] if error_message else None

        if not job.cancellation_requested and job.attempt_count < job.max_attempts:
            # Re-queue for retry
            delay = (
                retry_delay_seconds
                if retry_delay_seconds is not None
                else calculate_backoff(job.attempt_count)
            )
            job.status = JobStatus.QUEUED.value
            job.available_at = now + timedelta(seconds=delay)
            job.lease_token = None
            job.lease_expiry = None
            job.phase_label = f"Queued for retry (attempt {job.attempt_count}/{job.max_attempts})"
        else:
            job.status = JobStatus.FAILED.value
            job.finished_at = now
            job.lease_token = None
            job.lease_expiry = None
            job.phase_label = f"Failed: {error_code}"

        db.commit()
        return True

    @staticmethod
    def finalize_cancelled(
        db: Session,
        job_id: str,
        lease_token: Optional[str] = None,
    ) -> bool:
        """Marks a running or queued job as CANCELLED."""
        now = datetime.now(timezone.utc)
        query = db.query(Job).filter(Job.id == job_id)
        if lease_token:
            query = query.filter(Job.lease_token == lease_token)

        job = query.first()
        if not job:
            return False

        job.status = JobStatus.CANCELLED.value
        job.cancellation_requested = True
        job.error_code = "CANCELLED_BY_USER"
        job.error_message = "Execution cancelled by user or operator."
        job.phase_label = "Cancelled"
        job.finished_at = now
        job.lease_token = None
        job.lease_expiry = None

        db.commit()
        return True

    @staticmethod
    def request_cancellation(
        db: Session,
        job_id: str,
        institution_id: Optional[str] = None,
    ) -> Optional[Job]:
        """
        Requests cancellation. If QUEUED, cancels immediately.
        If RUNNING, sets cancellation_requested=True so worker aborts.
        """
        now = datetime.now(timezone.utc)
        query = db.query(Job).filter(Job.id == job_id)
        if institution_id:
            query = query.filter(Job.institution_id == institution_id)

        job = query.first()
        if not job:
            return None

        if job.status == JobStatus.QUEUED.value:
            job.status = JobStatus.CANCELLED.value
            job.cancellation_requested = True
            job.error_code = "CANCELLED_BY_USER"
            job.error_message = "Cancelled before execution began."
            job.phase_label = "Cancelled"
            job.finished_at = now
            db.commit()
            db.refresh(job)
            return job

        if job.status == JobStatus.RUNNING.value:
            job.cancellation_requested = True
            job.phase_label = "Cancellation requested"
            db.commit()
            db.refresh(job)
            return job

        # If already finished, return as is
        return job

    @staticmethod
    def recover_expired_leases(db: Session) -> int:
        """
        Recovers jobs whose worker crashed or missed heartbeats (lease_expiry < now).
        If attempts remain, re-queues them; otherwise marks as FAILED.
        """
        now = datetime.now(timezone.utc)
        expired_jobs = (
            db.query(Job)
            .filter(
                Job.status == JobStatus.RUNNING.value,
                Job.lease_expiry < now,
            )
            .all()
        )
        recovered_count = 0
        for job in expired_jobs:
            if not job.cancellation_requested and job.attempt_count < job.max_attempts:
                job.status = JobStatus.QUEUED.value
                job.available_at = now
                job.lease_token = None
                job.lease_expiry = None
                job.phase_label = f"Recovered from expired lease (attempt {job.attempt_count}/{job.max_attempts})"
            else:
                job.status = JobStatus.FAILED.value
                job.error_code = "LEASE_EXPIRED_MAX_ATTEMPTS"
                job.error_message = "Worker lease expired and maximum attempts reached."
                job.phase_label = "Failed: Worker lease expired"
                job.finished_at = now
                job.lease_token = None
                job.lease_expiry = None
            recovered_count += 1

        if recovered_count > 0:
            db.commit()

        return recovered_count

import threading
from uuid import uuid4

from pydantic import BaseModel


class JobStatus(BaseModel):
    total_pages: int
    processed_pages: int
    status: str  # "queuing", "processing", "completed", "failed", "downloaded"
    total_time: float
    output_filename: str | None = None


class JobManager:
    def __init__(self):
        self._jobs: dict[str, JobStatus] = {}
        self._lock = threading.Lock()

    async def create(self, total_pages: int) -> str:
        """Create a new job and return its ID."""
        job_id = uuid4().hex
        with self._lock:
            self._jobs[job_id] = JobStatus(
                total_pages=total_pages,
                processed_pages=0,
                status="queuing",
                total_time=0.0,
            )
        return job_id

    async def increment_progress(self, job_id: str) -> None:
        """Increment the progress of a job."""
        with self._lock:
            if job_id in self._jobs:
                job = self._jobs[job_id]
                if job.status == "processing":
                    job.processed_pages += 1

    async def start_job(self, job_id: str) -> None:
        """Mark a job as processing (transition from queuing)."""
        with self._lock:
            if job_id in self._jobs:
                job = self._jobs[job_id]
                job.status = "processing"

    async def fail_job(self, job_id: str) -> None:
        """Mark a job as failed."""
        with self._lock:
            if job_id in self._jobs:
                job = self._jobs[job_id]
                job.status = "failed"

    async def complete_job(self, job_id: str, total_time: float) -> None:
        """Complete a job"""
        with self._lock:
            if job_id in self._jobs:
                job = self._jobs[job_id]
                job.status = "completed"
                job.total_time = total_time

    async def set_output_filename(self, job_id: str, filename: str) -> None:
        """Attach the output filename to a job."""
        with self._lock:
            if job_id in self._jobs:
                job = self._jobs[job_id]
                job.output_filename = filename

    async def set_downloaded(self, job_id: str) -> None:
        """Set a job as downloaded."""
        with self._lock:
            if job_id in self._jobs:
                job = self._jobs[job_id]
                job.status = "downloaded"

    async def get_status(self) -> dict[str, JobStatus]:
        """Get the status of all jobs."""
        # Return a shallow copy to avoid race conditions while iterating
        with self._lock:
            return dict(self._jobs)

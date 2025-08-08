from uuid import uuid4

from pydantic import BaseModel


class JobStatus(BaseModel):
    total_pages: int
    processed_pages: int
    status: str  # "processing", "completed", "failed", "downloaded"
    total_time: float
    output_filename: str | None = None


class JobManager:
    def __init__(self):
        self._jobs: dict[str, JobStatus] = {}

    async def create(self, total_pages: int) -> str:
        """Create a new job and return its ID."""
        job_id = uuid4().hex
        self._jobs[job_id] = JobStatus(
            total_pages=total_pages,
            processed_pages=0,
            status="processing",
            total_time=0.0,
        )
        return job_id

    async def increment_progress(self, job_id: str) -> None:
        """Increment the progress of a job."""
        if job_id in self._jobs:
            job = self._jobs[job_id]
            if job.status == "processing":
                job.processed_pages += 1

    async def fail_job(self, job_id: str) -> None:
        """Mark a job as failed."""
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job.status = "failed"

    async def complete_job(self, job_id: str, total_time: float) -> None:
        """Complete a job"""
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job.status = "completed"
            job.total_time = total_time

    async def set_output_filename(self, job_id: str, filename: str) -> None:
        """Attach the output filename to a job."""
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job.output_filename = filename

    async def set_downloaded(self, job_id: str) -> None:
        """Set a job as downloaded."""
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job.status = "downloaded"

    async def get_status(self) -> dict[str, JobStatus]:
        """Get the status of all jobs."""
        return self._jobs

from uuid import uuid4

from pydantic import BaseModel


class JobStatus(BaseModel):
    total_pages: int
    processed_pages: int
    status: str  # "processing", "completed", "failed"


class JobManager:
    def __init__(self, ws_manager=None):
        self._jobs: dict[str, JobStatus] = {}
        self._ws_manager = ws_manager

    async def create(self, total_pages: int) -> str:
        """Create a new job and return its ID."""
        job_id = uuid4().hex
        self._jobs[job_id] = JobStatus(
            total_pages=total_pages, 
            processed_pages=0, 
            status="processing"
        )
        await self._send_update(job_id)
        return job_id

    async def increment_progress(self, job_id: str) -> None:
        """Increment the progress of a job."""
        if job_id in self._jobs:
            job = self._jobs[job_id]
            if job.status == "processing" and job.processed_pages < job.total_pages:
                job.processed_pages += 1
                await self._send_update(job_id)

    async def fail_job(self, job_id: str) -> None:
        """Mark a job as failed."""
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job.status = "failed"
            await self._send_update(job_id)

    async def complete_job(self, job_id: str) -> None:
        """Complete a job"""
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job.status = "completed"
            job.processed_pages = job.total_pages
            await self._send_update(job_id)

    async def _send_update(self, job_id: str) -> None:
        """Send job status update via WebSocket if available."""
        if self._ws_manager and job_id in self._jobs:
            try:
                await self._ws_manager.send_job_update(job_id, self._jobs[job_id].model_dump())
            except Exception as e:
                print(f"Error sending WebSocket update for job {job_id}: {e}")

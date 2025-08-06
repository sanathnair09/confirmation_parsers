from uuid import uuid4

from pydantic import BaseModel


class JobStatus(BaseModel):
    pages_to_process: int
    progress: int  # -1 for failed, 0, 1, 2, ..., pages_to_process for success


class JobManager:
    def __init__(self):
        self.jobs: dict[str, JobStatus] = {}

    def create(self, pages_to_process: int) -> str:
        """Create a new job and return its ID."""
        job_id = uuid4().hex
        self.jobs[job_id] = JobStatus(pages_to_process=pages_to_process, progress=0)
        return job_id

    def increment_progress(self, job_id: str) -> None:
        """Increment the progress of a job."""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            if job.progress >= 0 and job.progress < job.pages_to_process:
                job.progress += 1

    def fail_job(self, job_id: str) -> None:
        """Mark a job as failed."""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job.progress = -1

    def complete_job(self, job_id: str) -> None:
        """Complete a job"""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job.progress = job.pages_to_process

    def get_job_status(self, job_id: str) -> JobStatus | None:
        """Get job status."""
        return self.jobs.get(job_id, None)

    def get_all_jobs_status(self) -> dict[str, JobStatus]:
        """Get status of all jobs."""
        return self.jobs

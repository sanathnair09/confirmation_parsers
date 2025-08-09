import os

from dotenv import load_dotenv
from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from openai import AsyncOpenAI  # type: ignore
from src.models.responses import (
    FidelityResponseList,
    HealthResponse,
    RobinhoodResponseList,
)
from src.parsers.confirmation_parser import Broker, ConfirmationParser
from src.utils.job_manager import JobManager
from src.utils.worker_pool import GlobalWorkerPool, GlobalParserJob

load_dotenv()
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory setup
uploads_dir = "./uploads"
output_dir = "./output"

os.makedirs(uploads_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

# Initialize managers and parsers
job_manager = JobManager()

rh_parser = ConfirmationParser(
    "./configs/robinhood.yaml", Broker.ROBINHOOD, job_manager
)
fidelity_parser = ConfirmationParser(
    "./configs/fidelity.yaml", Broker.FIDELITY, job_manager
)

# Initialize a single global worker pool (6 workers) with broker dispatch
broker_to_parser = {
    Broker.ROBINHOOD: (rh_parser, RobinhoodResponseList),
    Broker.FIDELITY: (fidelity_parser, FidelityResponseList),
}
global_pool = GlobalWorkerPool(
    broker_to_parser=broker_to_parser,
    job_manager=job_manager,
    output_dir=output_dir,
    num_workers=6,
)
global_pool.start()


def upload_response(
    filename, status: str, /, reason: str | None = None, job_id: str | None = None
):
    """Helper function to create upload response."""
    if reason:
        return {"filename": filename, "status": status, "reason": reason}
    return {"filename": filename, "status": status, "job_id": job_id}


@app.post("/upload")
async def upload_files(
    background_tasks: BackgroundTasks, files: list[UploadFile] = File(...)
):
    """Upload and process PDF confirmation files."""
    results = []

    for file in files:
        if not file.filename:
            results.append(
                upload_response(file.filename, "failed", reason="File has no name.")
            )
            continue

        if not file.filename.lower().endswith(".pdf"):
            results.append(
                upload_response(file.filename, "failed", reason="File is not a PDF.")
            )
            continue

        # Save uploaded file
        file_path = os.path.join(uploads_dir, file.filename)
        with open(file_path, "wb") as out_file:
            content = await file.read()
            out_file.write(content)

        # Determine broker and process accordingly
        broker = ConfirmationParser.determine_broker(file_path)
        print(f"Detected broker: {broker.value}")

        if broker == Broker.ROBINHOOD:
            start_page = 1  # Start from the second page for Robinhood
            job_id = await job_manager.create(
                ConfirmationParser.num_pages(file_path) - start_page
            )
            global_pool.enqueue(
                GlobalParserJob(
                    broker=broker,
                    file_path=file_path,
                    job_id=job_id,
                    start_page=start_page,
                )
            )
        elif broker == Broker.FIDELITY:
            job_id = await job_manager.create(ConfirmationParser.num_pages(file_path))
            global_pool.enqueue(
                GlobalParserJob(
                    broker=broker,
                    file_path=file_path,
                    job_id=job_id,
                    start_page=0,
                )
            )
        else:
            results.append(
                upload_response(file.filename, "failed", reason="Unknown broker.")
            )
            continue

        results.append(upload_response(file.filename, "queuing", job_id=job_id))

    return {"results": results}


@app.get("/status")
async def get_status():
    return await job_manager.get_status()


@app.post("/set-downloaded/{job_id}")
async def set_downloaded(job_id: str):
    await job_manager.set_downloaded(job_id)
    return {"message": "Job marked as downloaded"}


@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download processed CSV files."""
    if not os.path.exists(os.path.join(output_dir, filename)):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        os.path.join(output_dir, filename), media_type="text/csv", filename=filename
    )


@app.get("/health")
async def health_check():
    """Health check endpoint that verifies Ollama is running."""
    try:
        # Try to connect to Ollama and list models
        base_url = os.getenv("OLLAMA_URL", "http://localhost:11434/v1")
        api_key = "ollama"
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        _ = await client.models.list()
        return HealthResponse(
            status="healthy",
            ollama_available=True,
            message="Ollama is running and accessible",
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            ollama_available=False,
            message=f"Ollama connection failed: {str(e)}",
        )

import os

from fastapi.responses import FileResponse
from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import ollama

from src.parsers.confirmation_parser import Broker, ConfirmationParser
from src.utils.job_manager import JobManager, JobStatus
from src.utils.websocket_manager import WebSocketManager

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


uploads_dir = "./uploads"
output_dir = "./output"

os.makedirs(uploads_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)
ws_manager = WebSocketManager()
job_manager = JobManager(ws_manager)

rh_parser = ConfirmationParser(
    "./configs/robinhood.yaml", Broker.ROBINHOOD, job_manager
)
fidelity_parser = ConfirmationParser(
    "./configs/fidelity.yaml", Broker.FIDELITY, job_manager
)


class RobinhoodResponse(BaseModel):
    symbol: str
    action: str  # Buy or Sell
    trade_date: str
    settle_date: str
    account_type: str
    price: float
    quantity: int
    principal: float
    commission: float
    contract_fee: float
    transaction_fee: float
    net_amount: float
    market: str  # Market type, e.g., "NASDAQ"
    cap: str  # Capitalization type, e.g., "Large Cap"
    us: str


class RobinhoodResponseList(BaseModel):
    data: list[RobinhoodResponse]


class FidelityResponse(BaseModel):
    date: str
    action: str
    symbol: str
    quantity: int
    price: float
    total: float
    order_no: str
    reference_no: str


class FidelityResponseList(BaseModel):
    data: list[FidelityResponse]


class HealthResponse(BaseModel):
    status: str
    ollama_available: bool
    message: str


def upload_response(
    filename, status: str, /, reason: str | None = None, job_id: str | None = None
):
    if reason:
        return {"filename": filename, "status": status, "reason": reason}
    return {"filename": filename, "status": status, "job_id": job_id}


async def process_file_background(
    file_path: str,
    job_id: str,
    parser: ConfirmationParser,
    response_format,
    start_page: int = 0,
):
    """Background function to process a file using the given parser."""
    try:
        transactions = await parser.parse_confirmation_file(
            file_path, response_format, job_id, start_page
        )
    except Exception as e:
        print(f"[{job_id}] Background processing failed: {e}")
        job_manager.fail_job(job_id)
        return
    output_file = f"{job_id}.csv"
    if parser.broker == Broker.ROBINHOOD:
        date = transactions[0].get("trade_date", "unknown").replace("/", "_")
        output_file = f"rh_{date}.csv"
    elif parser.broker == Broker.FIDELITY:
        date = transactions[0].get("date", "unknown").replace("-", "_")
        output_file = f"fidelity_{date}.csv"
    output_path = os.path.join(output_dir, output_file)
    parser.to_csv(transactions, output_path)
    await ws_manager.send_file_ready(output_file)


@app.post("/upload")
async def upload_files(
    background_tasks: BackgroundTasks, files: list[UploadFile] = File(...)
):
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

        file_path = os.path.join(uploads_dir, file.filename)

        with open(file_path, "wb") as out_file:
            content = await file.read()
            out_file.write(content)

        broker = ConfirmationParser.determine_broker(file_path)
        print(f"Detected broker: {broker.value}")
        if broker == Broker.ROBINHOOD:
            start_page = 1  # Start from the second page for Robinhood
            job_id = await job_manager.create(
                ConfirmationParser.num_pages(file_path) - start_page
            )
            background_tasks.add_task(
                process_file_background,
                file_path,
                job_id,
                rh_parser,
                RobinhoodResponseList,
                start_page,
            )
        elif broker == Broker.FIDELITY:
            job_id = await job_manager.create(ConfirmationParser.num_pages(file_path))
            background_tasks.add_task(
                process_file_background,
                file_path,
                job_id,
                fidelity_parser,
                FidelityResponseList,
            )
        else:
            results.append(
                upload_response(file.filename, "failed", reason="Unknown broker.")
            )
            continue
        results.append(upload_response(file.filename, "processing", job_id=job_id))

    return {"results": results}





@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # No-op: keeps connection alive
    except WebSocketDisconnect:
        ws_manager.disconnect()


@app.get("/download/{filename}")
async def download_file(filename: str):
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
        client = ollama.AsyncClient()
        models = await client.list()
        return HealthResponse(
            status="healthy",
            ollama_available=True,
            message="Ollama is running and accessible"
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            ollama_available=False,
            message=f"Ollama connection failed: {str(e)}"
        )

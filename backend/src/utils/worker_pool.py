import asyncio
import os
import threading
from dataclasses import dataclass
from queue import Queue
from typing import Any

from src.parsers.confirmation_parser import Broker, ConfirmationParser
from src.utils.job_manager import JobManager


@dataclass
class ParserJob:
    file_path: str
    job_id: str
    start_page: int


class ParserWorkerPool:
    def __init__(
        self,
        parser: ConfirmationParser,
        response_format,
        job_manager: JobManager,
        output_dir: str,
        num_workers: int = 3,
    ) -> None:
        self._parser = parser
        self._response_format = response_format
        self._job_manager = job_manager
        self._output_dir = output_dir
        self._num_workers = num_workers
        self._queue: Queue[ParserJob] = Queue()
        self._threads: list[threading.Thread] = []
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        for idx in range(self._num_workers):
            t = threading.Thread(target=self._worker_loop, name=f"{self._parser.broker.value}-worker-{idx}", daemon=True)
            t.start()
            self._threads.append(t)

    def enqueue(self, job: ParserJob) -> None:
        self._queue.put(job)

    def _worker_loop(self) -> None:
        while True:
            job = self._queue.get()
            try:
                # Transition job to processing
                asyncio.run(self._job_manager.start_job(job.job_id))

                # Run the async parser in this worker thread
                transactions = asyncio.run(
                    self._parser.parse_confirmation_file(
                        job.file_path,
                        self._response_format,
                        job.job_id,
                        job.start_page,
                    )
                )

                # Build output filename based on broker and first transaction date
                output_file = f"{job.job_id}.csv"
                try:
                    if self._parser.broker == Broker.ROBINHOOD and transactions:
                        date = transactions[0].get("trade_date", "unknown").replace("/", "_")
                        output_file = f"rh_{date}.csv"
                    elif self._parser.broker == Broker.FIDELITY and transactions:
                        date = transactions[0].get("date", "unknown").replace("-", "_")
                        output_file = f"fidelity_{date}.csv"
                except Exception:
                    # Keep fallback name on any error deriving name
                    pass

                output_path = os.path.join(self._output_dir, output_file)
                # Expose filename to frontend/status
                asyncio.run(self._job_manager.set_output_filename(job.job_id, output_file))
                # Write CSV to disk
                self._parser.to_csv(transactions, output_path)
            except Exception as e:
                try:
                    asyncio.run(self._job_manager.fail_job(job.job_id))
                except Exception:
                    pass
            finally:
                self._queue.task_done()


# Global pool implementation (single queue, N workers, dispatch by broker)
@dataclass
class GlobalParserJob:
    broker: Broker
    file_path: str
    job_id: str
    start_page: int


class GlobalWorkerPool:
    def __init__(
        self,
        broker_to_parser: dict[Broker, tuple[ConfirmationParser, Any]],
        job_manager: JobManager,
        output_dir: str,
        num_workers: int = 6,
    ) -> None:
        self._broker_to_parser = broker_to_parser
        self._job_manager = job_manager
        self._output_dir = output_dir
        self._num_workers = num_workers
        self._queue: Queue[GlobalParserJob] = Queue()
        self._threads: list[threading.Thread] = []
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        for idx in range(self._num_workers):
            t = threading.Thread(target=self._worker_loop, name=f"global-worker-{idx}", daemon=True)
            t.start()
            self._threads.append(t)

    def enqueue(self, job: GlobalParserJob) -> None:
        self._queue.put(job)

    def _worker_loop(self) -> None:
        while True:
            job = self._queue.get()
            try:
                asyncio.run(self._job_manager.start_job(job.job_id))

                parser_response = self._broker_to_parser.get(job.broker)
                if parser_response is None:
                    asyncio.run(self._job_manager.fail_job(job.job_id))
                    continue
                parser, response_format = parser_response

                transactions = asyncio.run(
                    parser.parse_confirmation_file(
                        job.file_path,
                        response_format,
                        job.job_id,
                        job.start_page,
                    )
                )

                output_file = f"{job.job_id}.csv"
                try:
                    if job.broker == Broker.ROBINHOOD and transactions:
                        date = transactions[0].get("trade_date", "unknown").replace("/", "_")
                        output_file = f"rh_{date}.csv"
                    elif job.broker == Broker.FIDELITY and transactions:
                        date = transactions[0].get("date", "unknown").replace("-", "_")
                        output_file = f"fidelity_{date}.csv"
                except Exception:
                    pass

                output_path = os.path.join(self._output_dir, output_file)
                asyncio.run(self._job_manager.set_output_filename(job.job_id, output_file))
                parser.to_csv(transactions, output_path)
            except Exception:
                try:
                    asyncio.run(self._job_manager.fail_job(job.job_id))
                except Exception:
                    pass
            finally:
                self._queue.task_done()


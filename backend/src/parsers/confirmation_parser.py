import time
from enum import Enum
from typing import Generator

import ollama
import orjson as json
import polars as pl
import pymupdf
from pydantic import BaseModel

from src.utils.config_loader import LLMConfigLoader
from src.utils.job_manager import JobManager


class Broker(Enum):
    ROBINHOOD = "robinhood"
    FIDELITY = "fidelity"
    UNKNOWN = "unknown"


class ConfirmationParser:
    def __init__(self, config_path: str, broker: Broker, job_manager: JobManager):
        self._config = LLMConfigLoader(config_path).get_config()
        self._job_manager = job_manager
        self.broker = broker

    def _parse_pdf(
        self, file_path: str, start_page: int = 0
    ) -> Generator[str, None, None]:
        """
        Parse the PDF file and yield text from each page starting from `start_page`.
        By default, it starts from the first page (0).
        """
        doc = pymupdf.open(file_path)
        doc = doc[start_page:]
        for page in doc:
            pdf_text = page.get_text("text")  # type: ignore
            yield pdf_text

    @staticmethod
    def num_pages(file_path: str) -> int:
        """Return the number of pages in the PDF file."""
        doc = pymupdf.open(file_path)
        return len(doc)

    @staticmethod
    def determine_broker(file_path: str) -> Broker:
        """Determine the broker based on the content."""
        first_page = pymupdf.open(file_path)[0]
        text = first_page.get_text("text").lower()  # type: ignore
        if "fidelity" in text:
            return Broker.FIDELITY
        elif "robinhood" in text:
            return Broker.ROBINHOOD
        else:
            return Broker.UNKNOWN

    def _clean_pdf_text(self, pdf_text: str) -> str:
        """
        Clean the PDF text by removing unwanted parts.
        By default, this method does nothing.
        """
        return pdf_text

    def _build_prompt(self, pdf_text: str) -> str:
        return self._config.prompt_template.replace("{pdf_text}", pdf_text)

    def _clean_model_response(self, raw_output: str) -> list[dict] | str:
        # raw_output = re.sub(
        #     r"<think>.*?</think>", "", raw_output, flags=re.DOTALL | re.IGNORECASE
        # )
        # # Step 2: Extract the first JSON array or object from remaining output
        # json_pattern = r"(\{.*?\}|\[.*?\])"

        # matches = re.finditer(json_pattern, raw_output, re.DOTALL)
        # for match in matches:
        #     candidate = match.group(1).strip()
        #     try:
        #         return json.loads(candidate)
        #     except json.JSONDecodeError:
        #         print(f"Error decoding JSON: {raw_output}")

        # # Fallback: return trimmed raw if no valid JSON found
        # return raw_output.strip()
        return json.loads(raw_output.strip())["data"]

    async def _call_model(
        self, prompt: str, format: BaseModel, model: str = "qwen3:4b"
    ) -> str:
        """
        Call the AI model with the given prompt and return the response.
        """
        response = await ollama.AsyncClient().chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            format=format.model_json_schema(),
        )
        return response["message"]["content"]

    async def parse_confirmation_file(
        self,
        file_path: str,
        response_format: BaseModel,
        job_id: str,
        start_page: int = 0,
    ) -> list:
        """
        Parse the confirmation file and return a list of transactions.
        This method processes the PDF file, builds prompts for each page, calls the AI model,
        and collects structured data from the responses.
        """
        model = self._config.model
        print(f"[{job_id}] Parsing file: {file_path} using model: {model}")

        all_transactions = []
        page = start_page
        start_time = time.perf_counter()
        for text in self._parse_pdf(file_path, start_page=page):
            try:
                text = self._clean_pdf_text(text)
                prompt = self._build_prompt(text)
                raw_response = await self._call_model(
                    prompt, response_format, model=model
                )
                cleaned_json = self._clean_model_response(raw_response)
                all_transactions.extend(cleaned_json)

                page += 1
                print(
                    f"[{job_id}] Processed page {page}: {len(cleaned_json)} transactions found"
                )
                await self._job_manager.increment_progress(job_id)
            except Exception as e:
                print(f"[{job_id}] Error processing page {page}: {e}")
                await self._job_manager.fail_job(job_id)
                return all_transactions

        end_time = time.perf_counter()
        await self._job_manager.complete_job(job_id)
        print(f"[{job_id}] SUMMARY:")
        print(f"[{job_id}] Total pages processed: {page}")
        print(f"[{job_id}] Total transactions found: {len(all_transactions)}")
        print(f"[{job_id}] Total processing time: {end_time - start_time:.4f} seconds")
        print(
            f"[{job_id}] Average time per page: {(end_time - start_time) / page:.4f} seconds"
        )

        return all_transactions

    def to_csv(self, transactions: list, output_file: str):
        """
        Convert the list of transactions to a CSV file.
        """
        df = pl.DataFrame(transactions)
        df.write_csv(output_file)

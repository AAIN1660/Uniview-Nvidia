"""
GraphRAG indexing queue worker.

Polls AZURE_GRAPHRAG_QUEUE_STORAGE_NAME and runs ``helper.startGraphRagIndexing``.

Run (keep this terminal open):
  cd Backend
  .\\.venv\\Scripts\\activate
  python graphrag_queue_service_app.py

Or: uvicorn graphrag_queue_service_app:app --port 8091
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from azure.storage.queue.aio import QueueClient
from dotenv import load_dotenv
from fastapi import FastAPI

from utility import helper

load_dotenv("unified.env")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.ERROR)
logging.getLogger("azure.monitor.opentelemetry.exporter.export._base").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
queue_name = os.getenv("AZURE_GRAPHRAG_QUEUE_STORAGE_NAME")
if not connection_string or not queue_name:
    raise RuntimeError(
        "AZURE_STORAGE_CONNECTION_STRING and AZURE_GRAPHRAG_QUEUE_STORAGE_NAME must be set in unified.env"
    )

queue_client = QueueClient.from_connection_string(connection_string, queue_name)


async def queue_service() -> None:
    logger.info("GraphRAG queue worker started (queue=%s)", queue_name)
    while True:
        print("Checking queue", flush=True)
        messages = queue_client.receive_messages(visibility_timeout=100)
        tasks = []
        async for msg in messages:
            tasks.append(process_message(msg))

        if tasks:
            await asyncio.gather(*tasks)

        await asyncio.sleep(10)


async def process_message(msg) -> None:
    try:
        message_content = json.loads(msg.content)
        graph_rag_files = message_content.get("graph_rag_files", [])
        data_dir = message_content.get("data_dir")
        category_id = message_content.get("category_id")

        print("****** Processing message:", msg, flush=True)

        file_name = None
        for file_info in graph_rag_files:
            file_name = file_info.get("file_name")
            file_path = file_info.get("file_path")
            if file_name and file_path:
                print(f"Processing file: {file_name} in directory: {data_dir}", flush=True)

        if not file_name:
            logger.warning("Queue message has no graph_rag_files with file_name; skipping indexing")
        else:
            await helper.startGraphRagIndexing(
                file_name, data_dir, category_id, graph_rag_files
            )

        await queue_client.delete_message(msg.id, msg.pop_receipt)
        logger.info("Queue message processed and deleted")
    except Exception as e:
        logger.error("Error processing message: %s - %s", msg, e, exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(queue_service())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "queue": queue_name}


if __name__ == "__main__":
    port = int(os.getenv("GRAPHRAG_QUEUE_PORT", "8091"))
    print(f"Starting GraphRAG queue worker on http://127.0.0.1:{port} (queue={queue_name})", flush=True)
    uvicorn.run(
        "graphrag_queue_service_app:app",
        host="127.0.0.1",
        port=port,
        reload=False,
    )

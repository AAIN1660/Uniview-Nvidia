import uvicorn
import asyncio
import os
from fastapi import FastAPI
from azure.storage.queue.aio import QueueClient
from dotenv import load_dotenv
import json
from utility import helper
import logging

load_dotenv("unified.env")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# Set logging level to ERROR or CRITICAL
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.ERROR)
logging.getLogger('azure.monitor.opentelemetry.exporter.export._base').setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

app = FastAPI()

connection_string = os.getenv('BLOB_STORAGE_CONNECTION_STRING')
queue_name = os.getenv("AZURE_GRAPHRAG_QUEUE_STORAGE_NAME")
queue_client = QueueClient.from_connection_string(connection_string, queue_name)

async def queue_service():
    while True:
        print("Checking queue")
        messages = queue_client.receive_messages(visibility_timeout=100)
        tasks = []
        async for msg in messages:
            tasks.append(process_message(msg))

        if tasks:
            await asyncio.gather(*tasks)

        await asyncio.sleep(10)

async def process_message(msg):
    try:
        message_content = json.loads(msg.content)
        graph_rag_files = message_content.get("graph_rag_files", [])
        data_dir = message_content.get("data_dir")
        category_id = message_content.get("category_id")

        print('****** Processing message:', msg)

        # Process each file in the graph_rag_files array
        for file_info in graph_rag_files:
            file_name = file_info.get("file_name")
            file_path = file_info.get("file_path")

            if file_name and file_path:
                print(f"Processing file: {file_name} in directory: {data_dir}")
        await helper.startGraphRagIndexing(file_name, data_dir, category_id, graph_rag_files)

        # Delete the message from the queue after processing
        await queue_client.delete_message(msg.id, msg.pop_receipt)
    except Exception as e:
        logger.error(f"Error processing message: {msg} - {e}")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(queue_service())

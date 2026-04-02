import uvicorn
import asyncio
import os
from fastapi import FastAPI
from azure.storage.queue.aio import QueueClient
from dotenv import load_dotenv
import json
from services import embedService
import logging

load_dotenv("unified.env")
logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# Set logging level to ERROR or CRITICAL
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.ERROR)
logging.getLogger('azure.monitor.opentelemetry.exporter.export._base').setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

app = FastAPI()

connection_string = os.getenv('BLOB_STORAGE_CONNECTION_STRING')
queue_name = os.getenv("AZURE_QUEUE_STORAGE_NAME")
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
    message_content = json.loads(msg.content)
    file_name = message_content.get("file_name")
    file_id = message_content.get("file_id")
    email = message_content.get("email")
    
    print('******', msg)
    
    await embedService.startEmbedding(file_name,file_id,email)
    


    await queue_client.delete_message(msg.id,msg.pop_receipt)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(queue_service())


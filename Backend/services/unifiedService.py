from fastapi import Request, HTTPException,Form, status, APIRouter,Query
from fastapi.responses import JSONResponse
from azure.cosmos import exceptions
from typing import Optional
from pydantic import BaseModel
from azure.cosmos import CosmosClient
from azure.cosmos import CosmosClient
from typing import List, Union, Dict, Any
from fastapi.responses import JSONResponse
from starlette.requests import Request
from datetime import datetime
import os
import uuid
from utility.creditServiceHelper import *
from utility.helper import get_active_categories
import bcrypt
from jose import jwt
from datetime import datetime, timezone, timedelta
from utility.unifiedServiceHelper import *


router = APIRouter()

COSMOS_DATABASE_NAME = os.environ["COSMOS_DATABASE_NAME"]
COSMOS_ENDPOINT = os.environ["COSMOS_ENDPOINT"]
COSMOS_KEY = os.environ["COSMOS_KEY"]


from utility.cosmos_db import tran_container, uploads_container, user_container


class PromptData(BaseModel):
    # Define your user data fields
    question: Optional[str]

@router.post("/generateResponse")
async def generate_response(question: str = Form(...)):
    try:
        if question:
            start = time.time()
            templete = f""""question": {question}"""

            chat_history = user_proxy.initiate_chat(
                manager,
                message=templete,
                summary_method="reflection_with_llm"
            )
            end = time.time()

            attempt, cost, token = process_chat_history(chat_history)

            print("cost:", cost)
            print("token count", token)
            print("Total Time Taken : ",end-start)
            return {"message": "Response generated successfully.", "attempt": attempt, "cost": cost, "token": token, "status": "success"}
    except Exception as e:
        traceback.print_exc()
        return {"message": "Error occurred while generating response: " + str(e), "status": "error"}
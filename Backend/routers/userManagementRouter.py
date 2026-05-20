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
from utility.helper import get_active_categories,encrypt_password
import bcrypt
from jose import jwt
from datetime import datetime, timezone, timedelta


router = APIRouter()

def _clean_env(value, default=None):
    value = value if value is not None else default
    if value is None:
        return None
    value = str(value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1].strip()
    return value


COSMOS_DATABASE_NAME = _clean_env(os.getenv("COSMOS_DATABASE_NAME"))
COSMOS_ENDPOINT = _clean_env(os.getenv("COSMOS_ENDPOINT"))
COSMOS_KEY = _clean_env(os.getenv("COSMOS_KEY"))


from utility.cosmos_db import (
    client,
    config_container,
    qa_container,
    transaction_container,
    user_container,
)


class UserData(BaseModel):
    # Define your user data fields
    id: Optional[str]
    name: Optional[str]
    email: Optional[str]
    role: Optional[str]
    access_token: Optional[str]
    expiration_time: Optional[str]
    last_logged_in: Optional[str]
    status: Optional[int]
    updated_by: Optional[str]
    updated_at: Optional[str]
    categories: Optional[list]
    db_connection_id: Optional[str]
    tables_list: Optional[list]
    _rid: Optional[str]
    _self: Optional[str]
    _etag: Optional[str]
    _attachments: Optional[str]
    _ts: Optional[int]


class UserCreationResponseData(BaseModel):
    user: UserData

class CustomLoginModel(BaseModel):
    email:str
    password:str

def verify_password(plainPassword:str, storedPassword:str):
    return bcrypt.checkpw(plainPassword.encode('utf-8'), storedPassword.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=int(os.getenv('JWT_TOKEN_EXPIRE_MINUTES')))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, os.getenv('JWT_SECRET_KEY'), algorithm=os.getenv('JWT_TOKEN_ALGORITHM'))
    response = {"token": encoded_jwt, "expire": expire.strftime("%Y-%m-%d %H:%M:%S")}
    return response


@router.post("/login_custom")
async def login_custom(request: CustomLoginModel):
    payload = request
    print("------------PAYLOAD CUSTOM LOGIN---------------")
    print(payload)
    # Checking User Existance
    user_query = f"SELECT * FROM c WHERE c.email = '{payload.email}'"
    user = list(user_container.query_items(query=user_query,enable_cross_partition_query=True))

    if not user or 'password' not in user[0]:
        error_msg = "Incorrect email or password"
        print(error_msg, user)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error_msg)

    if not verify_password(payload.password, user[0]['password']):
        error_msg = "Incorrect email or password"
        print(error_msg, user)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error_msg)

    if user[0]['status'] != 1:
        error_msg = "User is not active"
        print(error_msg, user)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="User is not active")

    balance = await calculate_balance(payload.email,transaction_container)
    if balance is None:
        balance = 0
    user_item = user[0]
    jwtdata = {
       "email":payload.email,
       'role':user_item['role']
    }
    jwt_token = create_access_token(jwtdata)

    response_data = {"message":"User login successfully",'id':user_item['id'],'name':user_item['name'],'email':user_item['email'],"role": user_item['role'],"balance": balance,"status": user_item['status'],"jwt_token": jwt_token, "categories": user_item["categories"] or []}

    return JSONResponse(content=response_data)

@router.post("/user")
async def create_or_update_user(request: Request):
    try:
        data = await request.json()
        print("************data",data)
        current_user_id = await get_current_user_id_from_database()
        user_id = str(current_user_id + 1)
        username = data.get("name")
        email = data.get("email")
        role = data.get("role", "General") # Default role is set to "general"
        access_token = data.get("accessToken")
        expiration_time = data.get("expirationTime")
        last_logged_in = data.get("lastLoggedIn")
        query = "SELECT * FROM c Where c.status = 1 and c.role='Admin'"
        user_count = list(user_container.query_items(query=query, enable_cross_partition_query=True))
        print('length of user count',len(user_count))
        if len(user_count)==0:
            role = "Admin"
        # Check if the user already exists
        query = f"SELECT * FROM c WHERE c.email = '{email}'"
        existing_users = list(user_container.query_items(query=query, enable_cross_partition_query=True))
        if existing_users:
            # If the user exists, update the access_token, expiration_time, and last_logged_in
            existing_user = existing_users[0]
            existing_user["access_token"] = access_token
            existing_user["expiration_time"] = expiration_time
            existing_user["last_logged_in"] = last_logged_in

            user_container.upsert_item(existing_user)
            balance = await calculate_balance(email,transaction_container)
            response_data = {"message":"User updated successfully","role": existing_user.get("role"), "balance": balance, "status": existing_user.get("status"), "categories": existing_user.get("categories", [])}
            return JSONResponse(content=response_data)

        else:
            # If the user does not exist, create a new user
            config_values = get_config_data()
            pending_license = config_values.get("pending_license", 0)
            cat_list = await get_active_categories()
            categories = [category['id'] for category in cat_list]
            if pending_license > 0:
                # If the user does not exist, create a new user
                new_user = {
                    "numericId":int(user_id),
                    "id": user_id,
                    "name": username,
                    "email": email,
                    "role": role,
                    "categories": categories,
                    "db_connection_id": "1",
                    "tables_list": ["Inventory","Invoice_2","Order","shipping"],
                    "access_token": access_token,
                    "expiration_time": expiration_time,
                    "last_logged_in": last_logged_in,
                    "status": 1,
                    "updated_by": None,
                    "updated_at": None
                }
                update_pending_license(pending_license - 1)
                user_container.create_item(body=new_user)
                await update_transactions_table(email, credit_assigned=0, balance = 0, service_type = "New User")
                response_data = {"message":"User created successfully","role": new_user.get("role"),  "balance": 0, "status": new_user.get("status"), "categories": new_user.get("categories", [])}
            else:
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Total users limit exceeded")
            return JSONResponse(content=response_data)

    except exceptions.CosmosHttpResponseError as cosmos_error:
        print(cosmos_error)
        response_data = UserCreationResponseData(user=None)  # or create a meaningful user instance
        return response_data
    except HTTPException as http_err:
        if http_err.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            raise HTTPException(status_code=429, detail="Total users limit exceeded")
        else:
            raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error occurred: {str(e)}")




@router.get("/get_user_balance")
async def get_user_balance_api(email: str = Query(...)):
    try:
        print("email:", email)
        if email is None or not email:
            raise HTTPException(status_code=400, detail="Missing 'email' parameter in the request")

        user_info = await get_user_info(email)

        if user_info is None:
            raise HTTPException(status_code=500, detail="Unexpected error: 'user_info' is None")

        return JSONResponse({
            "email": email,
            "balance": user_info.get("balance", 0),
            "role": user_info.get("role", None)
        })

    except HTTPException as http_error:
        return JSONResponse({"message": f"HTTPException: {http_error.detail}"}, status_code=http_error.status_code)
    except exceptions.CosmosHttpResponseError as cosmos_error:
        return JSONResponse({"message": f"Error occurred while fetching transactions: {cosmos_error}"}, status_code=500)
    except Exception as e:
        print(f"Unexpected error occurred: {str(e)}")
        return JSONResponse({"message": "Unexpected error occurred"}, status_code=500)



@router.get("/getusers")
async def get_users_api():
    try:
        # Retrieve data from containers
        user_data = list( user_container.read_all_items())
        transaction_data = list(transaction_container.read_all_items())
        upload_data = list(upload_container.read_all_items())
        config_values = list(config_container.read_all_items())
        if config_values:
            config_values = config_values[0]
        else:
            config_values = None

        user_info_list = []
        for user in user_data:
            print(f"Processing transactions for user: {user['email']}")
            if 'categories' not in user:
                categories = []
            else:
                categories = user["categories"]
            user_info = {
                "id": user["id"],
                "username": user["name"],
                "email": user["email"],
                "role": user["role"],
                "file_uploaded": 0,
                "query_count": 0,
                "credit_assigned": 0,
                "credit_revoked": 0,
                "credit_used": 0,
                "balance": 0,
                "status": user["status"],
                "updated_at": user["updated_at"],
                "updated_by": user["updated_by"],
                "categories": categories,
                "db_connection_id": user["db_connection_id"],
                "tables_list": user["tables_list"]
            }
            email = user["email"]
            for transaction_item in transaction_data:
                if transaction_item.get("email", "") == user["email"]:
                    try:
                        # Your existing transaction processing logic here...
                        if transaction_item["service_type"] == "Index":
                            user_info["credit_used"] += transaction_item.get("debit", 0)
                        elif transaction_item["service_type"] == "Assigned":
                            user_info["credit_assigned"] += transaction_item.get("credit", 0)
                        elif transaction_item["service_type"] == "Revoked":
                            user_info["credit_revoked"] += transaction_item.get("debit", 0)
                        elif transaction_item["service_type"] == "Query":
                            user_info["query_count"] += 1
                            user_info["credit_used"] += transaction_item["debit"]
                    except KeyError as e:
                        print(f"KeyError: {e}. Skipping transaction.")
            for uploaded_item in upload_data:
                if uploaded_item.get("uploaded_by", "") == user["email"]:
                    user_info["file_uploaded"] += 1
            user_info["balance"] =await calculate_balance(user["email"],transaction_container)
            user_info["credit_used"] = round(user_info["credit_used"], 2)
            user_info["credit_assigned"] = round(user_info["credit_assigned"], 2)
            user_info["credit_revoked"] = round(user_info["credit_revoked"], 2)
            user_info_list.append(user_info)

        # Create the final response dictionary
        response_dict = {
            "users": user_info_list,
            "config": {
                "credit_pool_assigned": config_values.get("credit_pool_assigned", 0),
                "credit_pool_balance": round(config_values.get("credit_pool_balance", 0), 2),
                "use_credit_pool": config_values.get("use_credit_pool", False),
            }
        }

        return JSONResponse(content=response_dict)
    except exceptions.CosmosHttpResponseError as cosmos_error:
        return JSONResponse({"error": cosmos_error.message}, status_code=cosmos_error.status_code)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    
@router.post("/add_user_by_admin/")
async def add_user_by_admin(request: Request,
                            current_utc_datetime: str = Form(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))):
    try:
        current_utc_datetime = datetime.strptime(current_utc_datetime, "%Y-%m-%d %H:%M:%S")
        data = await request.json()
        admin_email = data.get("admin_email")

        # Get list of Admin users
        query = "SELECT c.email FROM gi_users c WHERE c.role = 'Admin'"
        admin_list = list(user_container.query_items(query, enable_cross_partition_query=True))
        is_admin_email = True if admin_email in [admin["email"] for admin in admin_list] else False

        if is_admin_email:
            email = data.get("email")
            is_user_exist = True if email in [user["email"] for user in list(user_container.query_items("SELECT c.email FROM c", enable_cross_partition_query=True))] else False

            if not is_user_exist:
                current_user_id = await get_current_user_id_from_database()
                create_id = str(current_user_id + 1)
                config_values = get_config_data()
                pending_license = config_values.get("pending_license", 0)
                credit_pool_balance = config_values.get("credit_pool_balance", 0) or 0
                CreditAssigned = data.get("CreditAssigned", 0)
                Credit_Revoked = data.get("Credit_Revoked", 0)

                if pending_license > 0:
                    # Ensure assigned credits do not exceed the available balance
                    if CreditAssigned > credit_pool_balance:
                        raise HTTPException(status_code=400, detail="Assigned credits exceed available credit pool balance")

                    # Create the user
                    add_user = {
                        "numericId": int(create_id),
                        "id": create_id,
                        "name": data.get("name"),
                        "email": data.get("email"),
                        "password":encrypt_password(data.get("password")),
                        "role": data.get("new_role"),
                        "status": 1,
                        "categories": data.get("categories"),
                        "db_connection_id": "1",
                        "tables_list": ["Inventory","Invoice_2","Order","shipping"],
                        "updated_by": admin_email,
                        "updated_at": current_utc_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                        "access_token": "",
                        "expiration_time": "",
                        "last_logged_in": "",
                        "show_service_ticket_menu": "",
                        "jwt_token": ""
                    }
                    user_container.create_item(body=add_user)

                    # Get the current transaction ID and latest balance
                    current_trans_id = get_current_trans_id_from_database()
                    latest_balance = await calculate_balance(email, transaction_container)

                    if latest_balance is None:
                        latest_balance = 0  # Set balance to 0 if no previous transactions exist

                    # Calculate new balance
                    initial_balance = latest_balance + CreditAssigned
                    if Credit_Revoked > 0:
                        if Credit_Revoked > initial_balance:
                            raise HTTPException(status_code=400, detail="Revoked credits exceed available balance")
                        initial_balance -= Credit_Revoked

                    # Create transaction entries for assigned credits
                    if CreditAssigned > 0:
                        transaction_container.create_item({
                            "surr_no": current_trans_id + 1,
                            "id": str(uuid.uuid4()),
                            "email": email,
                            "credit": CreditAssigned,
                            "balance": initial_balance,
                            "debit": 0,
                            "purchase_type": 1,
                            "service_type": "Assigned",
                            "transaction_type": 1,
                            "transaction_ts": current_utc_datetime.strftime("%Y-%m-%d %H:%M:%S")  # Convert datetime to string
                        })

                    # Create transaction entries for revoked credits
                    if Credit_Revoked > 0:
                        transaction_container.create_item({
                            "surr_no": current_trans_id + 2,
                            "id": str(uuid.uuid4()),
                            "email": email,
                            "credit": 0,
                            "balance": initial_balance,
                            "debit": Credit_Revoked,
                            "purchase_type": 1,
                            "service_type": "Revoked",
                            "transaction_type": 2,
                            "transaction_ts": current_utc_datetime.strftime("%Y-%m-%d %H:%M:%S")  # Convert datetime to string
                        })

                    # Update the credit pool balance if applicable
                    if config_values.get("use_credit_pool", False):
                        new_credit_pool_balance = credit_pool_balance - CreditAssigned + Credit_Revoked
                        update_config_data({"credit_pool_balance": new_credit_pool_balance})

                    response_data = {
                        "message": "User created successfully",
                        "role": add_user.get("role"),
                        "balance": initial_balance,
                        "status": add_user.get("status"),
                        "categories": add_user.get("categories", []),
                        "updated_at": add_user["updated_at"]  # Ensure datetime is serialized as string
                    }

            else:
                response_data = {"message": "User already exists"}

            return JSONResponse(content=response_data)

        else:
            response_data = {"message": "Only admin can add user"}
            return JSONResponse(content=response_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.put("/updateroleandtransactions/")
async def updateroleandtransactions(
    request: Request,
    current_utc_datetime: str = Form(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
):
    try:
        current_utc_datetime = datetime.utcnow()
        formatted_datetime = current_utc_datetime.strftime("%Y-%m-%d %H:%M:%S")
        data = await request.json()
        print("data:", data)
        # Step 1: Get list of users with Admin role
        query = "SELECT c.email FROM gi_users c WHERE c.role = 'Admin'"
        admin_list = list(user_container.query_items(query, enable_cross_partition_query=True))
        count = len(admin_list)

        config_data = get_config_data()
        user_id = data.get("id")
        email = data.get("email")
        new_role = data.get("new_role")
        CreditAssigned = data.get("CreditAssigned")
        Credit_Revoked = data.get("Credit_Revoked")
        credit_pool_balance = config_data.get("credit_pool_balance", 0) or 0
        if credit_pool_balance is None:
            credit_pool_balance = 0
        print("credit pool balance:", credit_pool_balance)
        current_trans_id = get_current_trans_id_from_database()
        print(f"current_trans_id: {current_trans_id}")
        latest_balance = await calculate_balance(email, transaction_container)
        print("latestbalncacee:", latest_balance)
        # Handle the case when the balance is 0 or not found
        if latest_balance is None:
            latest_balance = 0

        # Update user role if needed
        parameters = [{"name": "@user_id", "value": user_id}]
        items = list(
            user_container.query_items(
                f"SELECT * FROM gi_users c WHERE c.id = @user_id",
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )
        response = {}
        if items:
            # Process financial transactions
            if CreditAssigned is not None and CreditAssigned > 0:
                CreditAssigned = round(CreditAssigned, 2)
                # Update credit pool balance if use_credit_pool is True
                if config_data.get("use_credit_pool", False):
                    if CreditAssigned <= credit_pool_balance:
                        # Calculate the new balance
                        new_balance = round(latest_balance + CreditAssigned, 2)

                        record = {
                            "surr_no": current_trans_id + 1,
                            "id": str(uuid.uuid4()),
                            "email": email,
                            "credit": CreditAssigned,
                            "balance": new_balance,
                            "debit": 0,
                            "purchase_type": 1,
                            "service_type": "Assigned",
                            "transaction_type": 1,
                            "transaction_ts": formatted_datetime,
                            # Add other columns as needed
                        }
                        response = transaction_container.create_item(body=record)
                        credit_pool_balance -= CreditAssigned
                        update_config_data({"credit_pool_balance": credit_pool_balance})
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Credit assigned exceeds credit pool balance {credit_pool_balance}",
                        )
                else:
                    new_balance = latest_balance + CreditAssigned

                    record = {
                        "surr_no": current_trans_id + 1,
                        "id": str(uuid.uuid4()),
                        "email": email,
                        "credit": CreditAssigned,
                        "balance": new_balance,
                        "debit": 0,
                        "purchase_type": 1,
                        "service_type": "Assigned",
                        "transaction_type": 1,
                        "transaction_ts": formatted_datetime,
                        # Add other columns as needed
                    }
                    response = transaction_container.create_item(body=record)

            elif CreditAssigned is not None and CreditAssigned < 0:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot assign credits less than zero",
                )

            if Credit_Revoked is not None and Credit_Revoked > 0:
                Credit_Revoked = round(Credit_Revoked, 2)
                # Ensure that Credit_Revoked is not greater than the latest_balance
                if Credit_Revoked is not None and Credit_Revoked <= latest_balance:
                    # Calculate the new balance after revoking credit
                    new_balance_after_revoke = round(latest_balance - Credit_Revoked, 2)
                    record1 = {
                        "surr_no": current_trans_id + 1,
                        "id": str(uuid.uuid4()),
                        "email": email,
                        "credit": 0,
                        "balance": new_balance_after_revoke,
                        "debit": Credit_Revoked,
                        "purchase_type": 1,
                        "service_type": "Revoked",
                        "transaction_type": 2,
                        "transaction_ts": formatted_datetime,
                    }
                    response = transaction_container.create_item(body=record1)
                    # Update credit pool balance if use_credit_pool is True
                    if config_data.get("use_credit_pool", False):
                        credit_pool_balance += Credit_Revoked
                        update_config_data({"credit_pool_balance": credit_pool_balance})
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="Insufficient credit balance to revoke",
                    )
            elif Credit_Revoked is not None and Credit_Revoked < 0:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot revoke negative credits",
                )
            # print('datatables_list',  data['selectedtables'])
            document_to_update = items[0]
            # print('document_to_update', document_to_update)
            document_to_update['categories'] = data.get('categories', document_to_update.get('categories', []))
            document_to_update['tables_list'] = data.get('selectedtables', document_to_update.get('tables_list', []))
            # Only update the password if it's provided in the request
            if 'password' in data and data['password']:
                document_to_update['password'] = encrypt_password(data['password'])
            user_container.replace_item(document_to_update, document_to_update)
            # Step 2: Check conditions and update role if needed
            service_type = response.get("service_type", "")
            if any(user_dict.get("email") == email for user_dict in admin_list) and new_role == "General":
                print("count:", count)
                count -= 1  # Decrement count since we found an admin user with the required condition
                print("count after decrement:", count)
                if count > 0:
                    print("inside if condition")
                    # Perform the role update
                    if document_to_update["role"] != new_role:
                        # Update the role only once
                        document_to_update["role"] = new_role
                        user_container.replace_item(document_to_update, document_to_update)
                        if service_type == "Revoked":
                            response["message"] = f"Role for user updated Successfully. New role: {new_role} and Credit Revoked."
                        elif service_type == "Assigned":
                            response["message"] = f"Role for user updated Successfully. New role: {new_role} and Credit Assigned."
                        else:
                            response["message"] = f"Role for user updated Successfully. New role: {new_role}"

                else:
                    print("inside else condition")
                    response["message"] = "User Role Not Updated. At least 1 admin is required in the system."
            if new_role == "Admin":
                if document_to_update["role"] != new_role:
                    # Update the role only once
                    document_to_update["role"] = new_role
                    user_container.replace_item(document_to_update, document_to_update)
                    if service_type == "Revoked":
                        response["message"] = f"Role for user updated Successfully. New role: {new_role} and Credit Revoked."
                    elif service_type == "Assigned":
                        response["message"] = f"Role for user updated Successfully. New role: {new_role} and Credit Assigned."
                    else:
                        response["message"] = f"Role for user updated Successfully. New role: {new_role}"

            if config_data.get("use_credit_pool", False):
                response["credit_pool_balance"] = round(credit_pool_balance, 2)
            return response

    except exceptions.CosmosHttpResponseError as cosmos_error:
        raise HTTPException(status_code=cosmos_error.status_code, detail=cosmos_error.message)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@router.get("/transaction_details/")
async def add_category(email: str = Query(...)):

    query = f"SELECT * FROM c WHERE c.email = '{email}' AND c.service_type != 'New User' ORDER BY c.transaction_ts DESC"
    items = list(transaction_container.query_items(query, enable_cross_partition_query=True))

    trans_info_list = []
    for transaction in items:
        print(f"Processing transactions for user: {transaction['email']}")
        trans_info = {
            "Reference Id": transaction["surr_no"],
            "Date": transaction["transaction_ts"],
            "Transaction Type": transaction["service_type"],
            "Credit Used" : transaction["debit"],
            "Credit Assigned" : transaction["credit"],
            "Balance" : transaction["balance"],
            "email" : transaction["email"]
        }
        trans_info_list.append(trans_info)
    response_dict = {
        "transactions": trans_info_list,
    }

    return JSONResponse(response_dict)



@router.put("/update_user_status")
async def update_user_status(request: Request):
    try:
        data = await request.json()
        email = data.get("email")
        status = data.get("status")
        # Check if the user exists
        query = f"SELECT * FROM c WHERE c.email = '{email}'"
        existing_users = list(user_container.query_items(query=query, enable_cross_partition_query=True))

        if not existing_users:
            return {"message": f"User with email {email} not found", "status": 404}

        existing_user = existing_users[0]

        # Update user status to 0 and set updated_by and updated_at
        existing_user["status"] = status
        existing_user["updated_by"] = email
        existing_user["updated_at"] = datetime.utcnow().isoformat()

        # Update the user in the container
        user_container.upsert_item(existing_user)

        balance = calculate_balance(email,transaction_container)
        response_data = {
            "message": "User status updated successfully",
            "role": existing_user.get("role"),
            "balance": await balance,
            "status": existing_user.get("status"),
        }
        return JSONResponse(content=response_data)
    except exceptions.CosmosHttpResponseError as cosmos_error:
        return {"message": f"Error occurred while updating user status: {cosmos_error}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Unexpected error occurred: {str(e)}")

@router.put("/update_existing_users_categories")
async def update_existing_users_categories(request: Request):
    try:
        data = await request.json()
        database_name = data.get("database_name")
        database = client.get_database_client(database_name)
        category_container = database.get_container_client("gi_category")
        user_container = database.get_container_client("gi_users")
        query = f"SELECT cat.id FROM cat WHERE cat.status = 1"
        cat_list = list(category_container.query_items(query, enable_cross_partition_query=True))
        cat_ids = [];
        for cat in cat_list:
            cat_ids.append(cat['id'])
        # Check if the user exists
        query = f"SELECT * FROM c"
        existing_users = list(user_container.query_items(query=query, enable_cross_partition_query=True))
        for user in existing_users:
            if len(user.get('categories', [])) > 1:
                continue;
            else:
                user['categories'] = cat_ids
                user_container.upsert_item(user)
        return JSONResponse(content="Categories updated")
    except exceptions.CosmosHttpResponseError as cosmos_error:
        return {"message": f"Error occurred while updating user categories: {cosmos_error}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Unexpected error occurred: {str(e)}")
    


@router.post("/user/questions")
async def get_user_questions(request: Request):
   
    try:
        # Parse the request body
        data = await request.json()
        email = data.get("email")

        if not email:
            raise HTTPException(status_code=400, detail="Missing 'email' in request body.")

        # Query the Cosmos DB container
        query = (
            "SELECT DISTINCT TOP 7 c.question FROM c WHERE c.createdBy = @createdBy "
            "ORDER BY c.createdAt DESC"
        )
        params = [{"name": "@createdBy", "value": email}]

        items = list(qa_container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

        # Extract questions from the results
        questions = [item["question"] for item in items]

        return questions if questions else []

    except exceptions.CosmosHttpResponseError as e:
        raise HTTPException(status_code=500, detail=f"Cosmos DB error: {e.message}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
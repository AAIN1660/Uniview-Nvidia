from fastapi import HTTPException, File, Form,APIRouter,Query, Request
from typing import List, Optional
import os
from datetime import datetime
import uuid
from pydantic import BaseModel
from utility.cosmos_db import category_container, user_container


COSMOS_DATABASE_NAME = os.environ["COSMOS_DATABASE_NAME"]
COSMOS_ENDPOINT = os.environ["COSMOS_ENDPOINT"]
COSMOS_KEY = os.environ["COSMOS_KEY"]

router = APIRouter()

class AddCategory(BaseModel):
    category_code:str
    category_name:str
    db_connection_id:Optional[str] = None
    # tables_list:Optional[list] = None
    email:Optional[str] =None

class UpdateCategory(BaseModel):
    category_id: str
    status_flag: Optional[int] = None
    category_code:Optional[str] = None
    category_name:Optional[str] = None
    db_connection_id:Optional[str] = None
    # tables_list:Optional[list] = None

@router.get("/getCategories/")
async def get_categories(
        status_flag: Optional[str] = Query(None),
        email: Optional[str] = Query(None)
):
    try:
        category_list = []
        if email is not None:
            query = "SELECT r.categories FROM gi_users r WHERE r.email = @email AND IS_DEFINED(r.categories)"
            query_params = [{"name": "@email", "value": email}]
            query_result = user_container.query_items(
                query=query,
                parameters=query_params,
                enable_cross_partition_query=True
            )

            category_ids = [item["categories"] for item in query_result]
            
            # If there are category IDs, fetch the complete category objects
            if category_ids:
                for category_id in category_ids[0]:
                    query = "SELECT * FROM gi_category r WHERE r.id = @category_id and r.status = 1"
                    query_params = [{"name": "@category_id", "value": category_id}]
                    query_result = category_container.query_items(
                        query=query,
                        parameters=query_params,
                        enable_cross_partition_query=True
                    )
                    # Ensure query_result is a list before concatenation
                    category_list += list(query_result) if query_result else []
            
            # if category_ids:
            #     ids_str = ', '.join([f'"{id}"' for id in category_ids])
            #     query = f"SELECT * FROM gi_category c WHERE c.id IN ({ids_str})"
            #     items = list(category_container.query_items(query=query, enable_cross_partition_query=True))
            #     category_list = items


        elif status_flag == 1:
            try:
                status_flag = int(status_flag)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid status_flag value")

            query = "SELECT * FROM gi_category r WHERE r.status = @status_flag"
            query_params = [{"name": "@status_flag", "value": status_flag}]

            query_result = category_container.query_items(
                query=query,
                parameters=query_params,
                enable_cross_partition_query=True
            )
            category_list = list(query_result)

        else:
            query = "SELECT * FROM gi_category r"
            query_result = category_container.query_items(
                query=query,
                enable_cross_partition_query=True
            )
            category_list = list(query_result)

        return {"CategoryList": category_list if category_list else []}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/addCategory/")
async def add_category(
    # category_code: str = Query(..., alias="category_code"),
    # category_name: str = Query(..., alias="category_name"),
    # db_connection_id: str = None,
    # tables_list: list = None
    request: AddCategory
):
    try:
        payload = request
        user_name = 'super-admin'
        query = "SELECT * FROM gi_category r WHERE r.category_name = @category_name"
        query_params = [{"name": "@category_name", "value": str(payload.category_name)}]

        # existing_category = db.session.query(gi_category).filter(gi_category.category_name == category_name).first()
        existing_category = None
        query_result = category_container.query_items(
            query=query,
            parameters=query_params,
            enable_cross_partition_query=True
        )

        for item in query_result:
            existing_category = item

        if existing_category is not None:
            return {"message": "Category already exists"}

        # new_category = gi_category(category_code= category_code, category_name=category_name, created_by=user_name, created_at=datetime.now())
        # db.session.add(new_category)
        # db.session.commit()

        category_id = uuid.uuid4()
        item = {
            'id': str(category_id),
            'category_code': payload.category_code,
            'category_name': payload.category_name,
            'db_connection_id': payload.db_connection_id,
            # 'tables_list': payload.tables_list,
            'created_by': payload.email,
            'created_at': str(datetime.now()),
            'status': 1
        }
        category_container.create_item(body=item)

        query = f"SELECT * FROM c WHERE c.role = 'Admin'"
        users = list(user_container.query_items(query=query, enable_cross_partition_query=True))

        # Update each user
        for user in users:
            if 'categories' in user:
                if item['id'] not in user['categories']:
                    # Add new category_id if not present
                    user['categories'].append(item['id'])
            else:
                user['categories'] = [item['id']]
            user_container.upsert_item(user)
        return {"message": "Category added successfully"}
    except Exception as e:
        return {"message": "Error occurred while updating category: " + str(e)}
    

@router.put("/updateCategory")
async def update_category(
    # category_id: str = Query(..., alias="category_id"),
    # status_flag: Optional[str] = None,
    # category_name: Optional[str] = None,
    # category_code: Optional[str] = None,
    # db_connection_id: str = None,
    # tables_list: list = None
    request: UpdateCategory
    ):

    try:
        payload = request
        query = "SELECT * FROM gi_category cat WHERE cat.id = @category_id"
        query_params = [{"name": "@category_id", "value": str(payload.category_id)}]

        # Execute the parameterized query
        categories = category_container.query_items(
            query=query,
            parameters=query_params,
            enable_cross_partition_query=True
        )
        category = next(categories, None)

        if category is None:
            return {"message": "Category not found"}
        print("payload_sttusflag", payload)

        status_mapping = {"false": 0, "true": 1}
        # category['status'] = status_mapping.get(payload.status_flag, 1)
        category['status'] = payload.status_flag
        print( category['status'] )
        if payload.category_name:
            category["category_name"] = payload.category_name
        if payload.category_code:
            category["category_code"] = payload.category_code
        if payload.db_connection_id:
            category["db_connection_id"] = payload.db_connection_id
        # if payload.tables_list != None:
        #     category["tables_list"] = payload.tables_list

        response = category_container.replace_item(item=category, body=category)
        print(payload.status_flag  == 0 or payload.status_flag ==1)
        response_message = ""
        if payload.status_flag  == 0 or payload.status_flag ==1:
            response_message += "Category Activated." if category['status'] == 1 else "Category Deactivated."
        response_message += "Category is edited." if payload.category_name or payload.category_code or payload.db_connection_id  else ""
        return {"message": response_message}

    except Exception as e:
        return {"message": "Error occurred while updating category: " + str(e)}
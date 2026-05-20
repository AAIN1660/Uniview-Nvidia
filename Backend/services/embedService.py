import logging
import os
import re
import openai
import json
import time
import base64
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
# import fitz
from azure.cosmos import CosmosClient, exceptions
from azure.storage.blob import BlobServiceClient
from azure.core.credentials import AzureKeyCredential
from datetime import datetime
from azure.cosmos.errors import CosmosHttpResponseError
import uuid
import io
from utility.embedding_config import (
    embedding_backend,
    embedding_create_kwargs,
    embedding_model_id,
    get_embedding_client,
)
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.docx import partition_docx
from unstructured.partition.csv import partition_csv
from unstructured.partition.xlsx import partition_xlsx
from unstructured.partition.text import partition_text



from dotenv import load_dotenv
load_dotenv('unified.env')

# Configure logging
logging.basicConfig(level=logging.INFO)  # Set the desired logging level
# Define a logger
logger = logging.getLogger(__name__)

MAX_SECTION_LENGTH = 4000
SENTENCE_SEARCH_LIMIT = 100
SECTION_OVERLAP = 400

COSMOS_DATABASE_NAME = os.environ["COSMOS_DATABASE_NAME"]
COSMOS_UPLOAD_CONTAINER = os.environ["UPLOAD_CONTAINER_NAME"]
COSMOS_ENDPOINT = os.environ["COSMOS_ENDPOINT"]
COSMOS_KEY = os.environ["COSMOS_KEY"]

from utility.cosmos_db import client, database, tran_container, upload_container

container = upload_container

AZURE_OPENAI_API_REGION = os.environ["AZURE_OPENAI_API_REGION"]
EMBEDDING_MODEL_DEPLOYMENT_NAME = os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL"]
openai.api_type = os.environ["OPENAI_API_TYPE"]
openai.api_version = os.environ["AZURE_OPENAI_API_VERSION"]
openai.api_base = os.environ["AZURE_OPENAI_API_BASE"]
openai.api_key = os.environ["AZURE_OPENAI_API_KEY"]

chunk_size = int(os.environ["chunk_size"])
blob_storage_connection_string = os.environ["BLOB_STORAGE_CONNECTION_STRING"]
blob_storage_container_name = os.environ["BLOB_STORAGE_CONTAINER_NAME"]

blob_service_client = BlobServiceClient.from_connection_string(
    blob_storage_connection_string)
container_client = blob_service_client.get_container_client(
    blob_storage_container_name)

service_endpoint = os.environ["AZURE_SEARCH_SERVICE_ENDPOINT"]
index_name = os.environ["AZURE_SEARCH_INDEX_NAME"]
azure_search_admin_key = os.environ["AZURE_SEARCH_ADMIN_KEY"]
azure_search_credential = AzureKeyCredential(azure_search_admin_key)

search_client = SearchClient(
    endpoint=service_endpoint, index_name=index_name, credential=azure_search_credential)


openai_client = get_embedding_client()


# @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
# Function to generate embeddings for title and content fields, also used for query embeddings

def generate_embeddings(text):
    try:
        if embedding_backend() == "nvidia":
            kwargs = embedding_create_kwargs(input_type="passage")
            response = openai_client.embeddings.create(
                input=text,
                model=embedding_model_id(),
                **kwargs,
            )
        else:
            response = openai_client.embeddings.create(
                input=text, model=EMBEDDING_MODEL_DEPLOYMENT_NAME)
        logger.info("Response returned from embedding API: %s", response)
        embeddings = response.data[0].embedding
        token_used = getattr(response.usage, "total_tokens", 0) if response.usage else 0
        return embeddings, token_used
    except Exception as e:
        logger.error(f"An unexpected error occurred:{e}", exc_info=True)
        raise e





def modify_string(input_string):
    # Remove characters that don't match the allowed set: letters, digits, underscore, dash, equal sign, for Index key(id)
    modified_string = re.sub(r'[^a-zA-Z0-9_=\-]', '_', input_string)

    return modified_string

# def table_to_html(table):
#     table_html = "<table>"
#     rows = [sorted([cell for cell in table.cells if cell.row_index == i], key=lambda cell: cell.column_index) for i in range(table.row_count)]
#     for row_cells in rows:
#         table_html += "<tr>"
#         for cell in row_cells:
#             tag = "th" if (cell.kind == "columnHeader" or cell.kind == "rowHeader") else "td"
#             cell_spans = ""
#             if cell.column_span > 1: cell_spans += f" colSpan={cell.column_span}"
#             if cell.row_span > 1: cell_spans += f" rowSpan={cell.row_span}"
#             table_html += f"<{tag}{cell_spans}>{html.escape(cell.content)}</{tag}>"
#         table_html +="</tr>"
#     table_html += "</table>"
#     return table_html

# def convert_csv_to_pdf(csv_content):
#     pdf_buffer = BytesIO()
#     pdf_canvas = canvas.Canvas(pdf_buffer, pagesize=letter)
#     pdf_canvas.setFont("Helvetica", 12)

#     # Set the position for drawing the table
#     x = 30
#     y = 750
#     line_height = 12
#     page_height = 800

#     # Split the CSV content into lines
#     csv_lines = csv_content.splitlines()

#     # Set the chunk size based on your needs
#     chunk_size = 50

#     # Process the CSV content in chunks
#     for chunk_start in range(0, len(csv_lines), chunk_size):
#         chunk_end = min(chunk_start + chunk_size, len(csv_lines))
#         chunk = csv_lines[chunk_start:chunk_end]

#         for row in csv.reader(chunk):
#             row_str = ', '.join(row)
#             pdf_canvas.drawString(x, y, row_str)
#             y -= line_height

#             # Check if the next row exceeds the page height
#             if y < 50:
#                 pdf_canvas.showPage()  # Start a new page
#                 y = page_height - 50  # Reset y-coordinate for the new page

#     # Save the PDF
#     pdf_canvas.save()
#     pdf_content = pdf_buffer.getvalue()
#     pdf_buffer.close()

#     return pdf_content

# def convert_docx_to_pdf(docx_content):
#     """
#     Convert DOCX content to PDF.

#     Parameters:
#     - docx_content: Content of the DOCX file as a string.

#     Returns:
#     - pdf_buffer: BytesIO buffer containing the generated PDF content.
#     """
#     pdf_buffer = io.BytesIO()

#     # Create a PDF canvas
#     c = canvas.Canvas(pdf_buffer, pagesize=letter)
#     width, height = letter

#     # Set font and size
#     c.setFont("Helvetica", 12)

#     # Parse DOCX content and write to PDF
#     doc = Document(io.BytesIO(docx_content))
#     for paragraph in doc.paragraphs:
#         c.drawString(50, height - 50, paragraph.text)
#         height -= 12

#     # Save the PDF content in the buffer
#     c.save()

#     # Reset the buffer position to the beginning
#     pdf_buffer.seek(0)

#     return pdf_buffer

# def convert_excel_to_pdf(excel_content):
#     pdf_buffer = BytesIO()
#     pdf_canvas = canvas.Canvas(pdf_buffer, pagesize=letter)
#     pdf_canvas.setFont("Helvetica", 12)

#     # Set the position for drawing the table
#     x = 30
#     y = 750
#     line_height = 12
#     page_height = 800

#     # Load the Excel content
#     workbook = load_workbook(BytesIO(excel_content))
#     sheet = workbook.active

#     # Set the chunk size based on your needs
#     chunk_size = 50

#     # Process the Excel content in chunks
#     for row in sheet.iter_rows(values_only=True):
#         row_str = ', '.join(str(cell) for cell in row)
#         pdf_canvas.drawString(x, y, row_str)
#         y -= line_height

#         # Check if the next row exceeds the page height
#         if y < 50:
#             pdf_canvas.showPage()  # Start a new page
#             y = page_height - 50  # Reset y-coordinate for the new page

#     # Save the PDF
#     pdf_canvas.save()
#     pdf_content = pdf_buffer.getvalue()
#     pdf_buffer.close()

#     return pdf_content


# def fetch_file_from_azure_blob(blob_name):
#     """
#     Read blob pdf and convert it into text
#     """
#     try:
#         page_map = []
#         blob_client = container_client.get_blob_client(blob_name)
#         blob_data = blob_client.download_blob()
#         file_content = blob_data.readall()
#         content_type = blob_data.properties.content_settings.content_type
#         #logger.info("content_type"+str(content_type))
#         #logger.info("pdf documenttation: %s", file_content)
#         pdf_text = ""
#         offset = 0

#         if blob_name.lower().endswith('.csv'):
#             # Convert CSV to PDF
#             pdf_content = convert_csv_to_pdf(file_content.decode('utf-8'))
#             # Now, you can use pdf_content to send the PDF content to Form Recognizer
#             form_recognizer_client = DocumentAnalysisClient(endpoint=f"https://eryl-dev.cognitiveservices.azure.com/", credential=AzureKeyCredential("e3296ca624a743b1a3f51ccdab44113e"), headers={"x-ms-useragent": "azure-search-chat-demo/1.0.0"})
#             poller = form_recognizer_client.begin_analyze_document("prebuilt-layout", document=pdf_content)
#             form_recognizer_results = poller.result()
#             for table in form_recognizer_results.tables:
#                 logging.info("Table found:"+str(table))
#         elif blob_name.lower().endswith('.xlsx'):
#             # Convert DOC to PDF
#             pdf_path = convert_excel_to_pdf(file_content)
#             logging.info("after conerting"+str(pdf_path))
#             # Now, you can use pdf_path to send the PDF content to Form Recognizer
#             form_recognizer_client = DocumentAnalysisClient(endpoint=f"https://eryl-dev.cognitiveservices.azure.com/", credential=AzureKeyCredential("e3296ca624a743b1a3f51ccdab44113e"), headers={"x-ms-useragent": "azure-search-chat-demo/1.0.0"})
#             poller = form_recognizer_client.begin_analyze_document("prebuilt-layout", document=pdf_path)
#             form_recognizer_results = poller.result()
#             for table in form_recognizer_results.tables:
#                 logging.info("Table found:" + str(table))
#         elif blob_name.lower().endswith('.docx'):
#             # Convert DOCX to PDF
#             pdf_path = convert_docx_to_pdf(file_content)
#             # Now, you can use pdf_path to send the PDF content to Form Recognizer
#             form_recognizer_client = DocumentAnalysisClient(endpoint=f"https://eryl-dev.cognitiveservices.azure.com/", credential=AzureKeyCredential("e3296ca624a743b1a3f51ccdab44113e"), headers={"x-ms-useragent": "azure-search-chat-demo/1.0.0"})
#             poller = form_recognizer_client.begin_analyze_document("prebuilt-layout", document=pdf_path)
#             form_recognizer_results = poller.result()
#             # for table in form_recognizer_results.tables:
#             #     #logging.info("Table found:" + str(table))
#         else:
#             form_recognizer_client = DocumentAnalysisClient(endpoint=f"https://eryl-dev.cognitiveservices.azure.com/", credential=AzureKeyCredential("e3296ca624a743b1a3f51ccdab44113e"), headers={"x-ms-useragent": "azure-search-chat-demo/1.0.0"})
#             poller = form_recognizer_client.begin_analyze_document("prebuilt-layout", document=file_content)
#             form_recognizer_results = poller.result()

#         #print("ressssssssssssssssssssss::::", form_recognizer_results)

#             # pdf_document = fitz.open("pdf", file_content)
#         logging.info(" form recognizer results:"+str(form_recognizer_results.pages))
#         for page_num, page in enumerate(form_recognizer_results.pages):
#             logging.info(f"page_num - {str(page_num)}")
#             tables_on_page = [table for table in form_recognizer_results.tables if table.bounding_regions[0].page_number == page_num + 1]

#             # mark all positions of the table spans in the page
#             page_offset = page.spans[0].offset
#             page_length = page.spans[0].length
#             table_chars = [-1]*page_length
#             for table_id, table in enumerate(tables_on_page):
#                 for span in table.spans:
#                     # replace all table spans with "table_id" in table_chars array
#                     for i in range(span.length):
#                         idx = span.offset - page_offset + i
#                         if idx >=0 and idx < page_length:
#                             table_chars[idx] = table_id
#             #logging.info(f"Page text length: {len(page_text)}")

#             # build page text by replacing characters in table spans with table html
#             page_text = ""
#             added_tables = set()
#             for idx, table_id in enumerate(table_chars):
#                 if table_id == -1:
#                     page_text += form_recognizer_results.content[page_offset + idx]
#                     #logger.info("page text1: %s", page_text)
#                 elif table_id not in added_tables:
#                     page_text += table_to_html(tables_on_page[table_id])
#                     #logger.info("page text2:%s",page_text)
#                     added_tables.add(table_id)

#             page_text += " "
#             page_map.append((page_num+1, offset, page_text))
#             offset += len(page_text)
#             logger.info("page map:"+str(page_map))

#         return page_map

#     except Exception as e:
#         logger.error(f"An error occurred in fetch_file_from_azure_blob: {e}", exc_info=True)
#         # Initialize page_map even if an exception occurs
#         page_map = []

#         # Log additional details about the file
#         logger.error(f"Error processing file: {blob_name}")
#         logger.error(f"File size: {len(file_content)} bytes")
#         logger.error(f"File content: {file_content[:100]}... (truncated)")

# def split_text(page_map):
#     SENTENCE_ENDINGS = [".", "!", "?"]
#     WORDS_BREAKS = [",", ";", "(", ")", "[", "]", "{", "}", "\t", "\n"]
#     # WORDS_BREAKS = [",", ";", ":", " ", "(", ")", "[", "]", "{", "}", "\t", "\n"]

#     def find_page(offset):
#         num_pages = len(page_map)
#         for i in range(num_pages - 1):
#             if offset >= page_map[i][1] and offset < page_map[i + 1][1]:
#                 return i
#         return num_pages - 1

#     all_text = "".join(p[2] for p in page_map)
#     length = len(all_text)
#     start = 0
#     end = length
#     while start + SECTION_OVERLAP < length:
#         last_word = -1
#         end = start + MAX_SECTION_LENGTH

#         if end > length:
#             end = length
#         else:
#             # Try to find the end of the sentence
#             while end < length and (end - start - MAX_SECTION_LENGTH) < SENTENCE_SEARCH_LIMIT and all_text[end] not in SENTENCE_ENDINGS:
#                 if all_text[end] in WORDS_BREAKS:
#                     last_word = end
#                 end += 1
#             if end < length and all_text[end] not in SENTENCE_ENDINGS and last_word > 0:
#                 end = last_word # Fall back to at least keeping a whole word
#         if end < length:
#             end += 1

#         # Try to find the start of the sentence or at least a whole word boundary
#         last_word = -1
#         while start > 0 and start > end - MAX_SECTION_LENGTH - 2 * SENTENCE_SEARCH_LIMIT and all_text[start] not in SENTENCE_ENDINGS:
#             if all_text[start] in WORDS_BREAKS:
#                 last_word = start
#             start -= 1
#         if all_text[start] not in SENTENCE_ENDINGS and last_word > 0:
#             start = last_word
#         if start > 0:
#             start += 1

#         section_text = all_text[start:end]
#         yield (section_text, find_page(start))

#         last_table_start = section_text.rfind("<table")
#         if (last_table_start > 2 * SENTENCE_SEARCH_LIMIT and last_table_start > section_text.rfind("</table")):

#             start = min(end - SECTION_OVERLAP, start + last_table_start)
#         else:
#             start = end - SECTION_OVERLAP

#     if start + SECTION_OVERLAP < end:
#         yield (all_text[start:end], find_page(start))

# def blob_name_from_file_page(filename, page = 0):
#     if os.path.splitext(filename)[1].lower() == ".pdf":
#         return os.path.splitext(os.path.basename(filename))[0] + ".pdf" + f"-{page}"
#     elif os.path.splitext(filename)[1].lower() == ".csv":
#         return os.path.splitext(os.path.basename(filename))[0] + ".csv" + f"-{page}"
#     else:
#         return os.path.basename(filename)


def blob_name_from_file_page(filename, page=0):
    base_name, extension = os.path.splitext(filename)

    if extension.lower() in {".pdf", ".doc", ".docx",".xlsx"}:
        return f"{base_name}-{page}{extension}"
    elif extension.lower() == ".csv":
        return f"{base_name}-{page}.csv"
    else:
        return f"{base_name}-1{extension}"


# def split_text_into_batches(text, batch_size=MAX_SECTION_LENGTH):
#     SENTENCE_ENDINGS = [".", "!", "?"]
#     WORDS_BREAKS = [",", ";", "(", ")", "[", "]", "{", "}", "\t", "\n"]

#     batches = []
#     current_position = 0

#     while current_position < len(text):
#         # Determine the end of the batch
#         end_position = min(current_position + batch_size, len(text))

#         # If we are at the end of the text, take the remaining text
#         if end_position == len(text):
#             batches.append(text[current_position:end_position])
#             break

#         # Look for the nearest sentence ending or word break
#         for i in range(end_position, current_position, -1):
#             if text[i] in SENTENCE_ENDINGS:
#                 end_position = i + 1
#                 break
#             elif text[i] in WORDS_BREAKS:
#                 end_position = i + 1
#                 break

#         # Append the batch to the list
#         batches.append(text[current_position:end_position].strip())

#         # Move to the next position
#         current_position = end_position

#     return batches


# def get_image_description(blob_name):

#     # # Connect to Azure Storage
#     connection_string = blob_storage_connection_string
#     blob_service_client = BlobServiceClient.from_connection_string(
#         connection_string)

#     # Get a reference to the blob
#     blob_client = blob_service_client.get_blob_client(
#     container=blob_storage_container_name, blob=blob_name)

#     downloaded_blob = blob_client.download_blob().readall()


#     # Encode the downloaded image in base64
#     encoded_image = base64.b64encode(downloaded_blob).decode('utf-8')

#     # Create the GPT-4o API request


#     AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.getenv("GPT3_LLM_MODEL_DEPLOYMENT_NAME")
#     AZURE_OPENAI_CHATGPT_MODEL = os.getenv("GPT3_LLM_MODEL_NAME")

#     response = openai.ChatCompletion.create(
#         engine=AZURE_OPENAI_CHATGPT_DEPLOYMENT,
#         model=AZURE_OPENAI_CHATGPT_MODEL,
#         messages=[
#             {
#                 "role": "user",
#                 "content": [
#                     {"type": "text", "text": "Analyze the image and give detailed description of every item and person in the image"},
#                     {
#                         "type": "image_url",
#                         "image_url": {"url": f"data:image/png;base64,{encoded_image}"}
#                     },
#                 ],
#             }
#         ],
#         max_tokens=300,
#     )

#     # Extract and return the description
#     return split_text_into_batches(response.choices[0].message.content)

# def create_sections(blob_name, page_map, file_id, category_id):
#     # file_id = filename_to_id(filename)
#     input_data = []
#     if blob_name.lower().endswith(".jpg") or blob_name.lower().endswith(".png") or blob_name.lower().endswith(".jpeg"):
#         text = get_image_description(blob_name)
#         item = []
#         for index, textpart in enumerate(text):
#             item.append({
#                 'id': f"{file_id}_{index}",
#                 'title': blob_name,
#                 'category': category_id,
#                 "sourcepage": blob_name_from_file_page(blob_name),
#                 'content': textpart
#             })
#         return item
#     else:
#         text = split_text(page_map)

#     for i, (content, pagenum) in enumerate(text):
#         item = {
#             'id': f"{file_id}_{i+1}",
#             'title': blob_name,
#             'category': category_id,
#             "sourcepage": blob_name_from_file_page(blob_name, pagenum),
#             # 'blob_name': blob_name,
#             'content': content
#         }
#         input_data.append(item)
#     return input_data


# def chunk_pdf_file(category_id, page_map, blob_name, file_id):
#     try:
#         # Process PDF file (you can add your PDF processing logic here)
#         # For now, it uses the existing logic
#         return create_sections(blob_name, page_map, file_id, category_id)
#     except Exception as e:
#         logging.error(f"An error occurred in chunk_pdf_file: {e}", exc_info=True)

# def chunking_file(category_id, blob_name, file_id):
#     try:
#         page_map = fetch_file_from_azure_blob(blob_name)
#         logging.info("Page_map:"+str(page_map))

#         # Check the file extension
#         file_extension = os.path.splitext(blob_name)[1].lower()
#         if file_extension in ['.csv', '.pdf', '.doc', '.docx','.xlsx']:
#             # Process CSV, PDF, DOC, and DOCX files differently
#             return chunk_pdf_file(category_id, page_map, blob_name, file_id)
#         else:
#             # Process other file types using the existing logic
#             return create_sections(blob_name, page_map, file_id, category_id)
#     except Exception as e:
#         logging.error(f"An error occurred in chunking_file: {e}", exc_info=True)





def chunking_file(category_id, blob_name, file_id):
    try:
        blob_client = container_client.get_blob_client(blob_name)

        blob_data = blob_client.download_blob()
        file_content = blob_data.readall()  # Read the file content into memory

        #Convert file content to a file-like object
        file_stream = io.BytesIO(file_content)

        # Check the file extension
        file_extension = os.path.splitext(blob_name)[1].lower()
        if file_extension == '.pdf':
            return partition_pdf(
                file=file_stream,
                infer_table_structure=True,  # extract tables
                strategy="hi_res",  # mandatory to infer tables
                extract_image_block_types=[
                    "Image"
                ],  # Add 'Table' to list to extract image of tables
                # image_output_dir_path=output_path,  # if None, images and tables will saved in base64
                extract_image_block_to_payload=True,  # if true, will extract base64 for API usage
                chunking_strategy="by_title",  # or 'basic', by_page - api
                max_characters=10000,  # defaults to 500
                combine_text_under_n_chars=2000,  # defaults to 0
                new_after_n_chars=6000,
                # extract_images_in_pdf=True,          # deprecated
            )
        elif file_extension == ".docx":
            return partition_docx(
                file=file_stream,
                infer_table_structure=True,  # extract tables
                strategy="hi_res",  # mandatory to infer tables
                extract_image_block_types=[
                    "Image"
                ],  # Add 'Table' to list to extract image of tables
                # image_output_dir_path=output_path,  # if None, images and tables will saved in base64
                extract_image_block_to_payload=True,  # if true, will extract base64 for API usage
                chunking_strategy="by_title",  # or 'basic', by_page - api
                max_characters=10000,  # defaults to 500
                combine_text_under_n_chars=2000,  # defaults to 0
                new_after_n_chars=6000,
                # extract_images_in_pdf=True,          # deprecated
            )
        elif file_extension == ".csv":
            return partition_csv(
                file=file_stream,
                infer_table_structure=True,  # extract tables
                strategy="hi_res",  # mandatory to infer tables
                extract_image_block_types=[
                    "Image"
                ],  # Add 'Table' to list to extract image of tables
                # image_output_dir_path=output_path,  # if None, images and tables will saved in base64
                extract_image_block_to_payload=True,  # if true, will extract base64 for API usage
                chunking_strategy="by_title",  # or 'basic', by_page - api
                max_characters=10000,  # defaults to 500
                combine_text_under_n_chars=2000,  # defaults to 0
                new_after_n_chars=6000,
                # extract_images_in_pdf=True,          # deprecated
            )
        elif file_extension == ".xlsx":
            return partition_xlsx(
                file=file_stream,
                infer_table_structure=True,  # extract tables
                strategy="hi_res",  # mandatory to infer tables
                extract_image_block_types=[
                    "Image"
                ],  # Add 'Table' to list to extract image of tables
                # image_output_dir_path=output_path,  # if None, images and tables will saved in base64
                extract_image_block_to_payload=True,  # if true, will extract base64 for API usage
                chunking_strategy="by_title",  # or 'basic', by_page - api
                max_characters=10000,  # defaults to 500
                combine_text_under_n_chars=2000,  # defaults to 0
                new_after_n_chars=6000,
                # extract_images_in_pdf=True,          # deprecated
            )
        elif file_extension == ".txt":
            return partition_text(
                file=file_stream,
                infer_table_structure=True,  # extract tables
                strategy="hi_res",  # mandatory to infer tables
                extract_image_block_types=[
                    "Image"
                ],  # Add 'Table' to list to extract image of tables
                # image_output_dir_path=output_path,  # if None, images and tables will saved in base64
                extract_image_block_to_payload=True,  # if true, will extract base64 for API usage
                chunking_strategy="by_title",  # or 'basic', by_page - api
                max_characters=10000,  # defaults to 500
                combine_text_under_n_chars=2000,  # defaults to 0
                new_after_n_chars=6000,
                # extract_images_in_pdf=True,          # deprecated
            )
        else:
            return []
    except Exception as e:
        logging.error(f"An error occurred in chunking_file: {e}", exc_info=True)



def generate_image_description(image_base64):
    # Convert image to base64
    # image_base64 = base64.b64encode(image).decode('utf-8')

    AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.getenv("GPT3_LLM_MODEL_DEPLOYMENT_NAME")
    AZURE_OPENAI_CHATGPT_MODEL = os.getenv("GPT3_LLM_MODEL_NAME")

    # Prepare the prompt
    prompt = """Your task is to Provide a short description of the given image. Include specific details about the elements or text visible in the image.
    Image Description:"""

    response = openai_client.chat.completions.create(
        model=AZURE_OPENAI_CHATGPT_DEPLOYMENT,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{prompt}"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}",
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
        max_tokens=1024,
        n=1,
        temperature=0,
    )

    return response.choices[0].message.content



def get_base64_from_blob(blob_name):

    # # Connect to Azure Storage
    connection_string = blob_storage_connection_string
    blob_service_client = BlobServiceClient.from_connection_string(
        connection_string)

    # Get a reference to the blob
    blob_client = blob_service_client.get_blob_client(
    container=blob_storage_container_name, blob=blob_name)

    downloaded_blob = blob_client.download_blob().readall()


    # Encode the downloaded image in base64
    encoded_image = base64.b64encode(downloaded_blob).decode('utf-8')

    return encoded_image




async def startEmbedding(file_name, file_id, email):
    chunks_list = []
    credit_used = 0  # Initialize to prevent UnboundLocalError
    try:
        # Get the blob name from the blob trigger event
        blob_name = file_name
        query = "SELECT * FROM gi_uploads r WHERE r.file_name = @blob_name"
        query_params = [{"name": "@blob_name", "value": blob_name}]

        # Execute the parameterized query
        query_result = container.query_items(
            query=query,
            parameters=query_params,
            enable_cross_partition_query=True
        )

        # Extract file_item from query result
        file_item = None
        for item in query_result:
            file_item = item

        if not file_item:
            raise ValueError(f"No file_item found for blob_name: {blob_name}")

        logging.info(f"File_item is : {str(file_item)}")
        logging.info(f"Blob name is : {blob_name}")

        file_id = blob_name.replace(" ", "_").replace(".", "_")

        # Check the file extension
        file_extension = os.path.splitext(blob_name)[1].lower()
        chunks_list = []
        items = []
        chunk_ids = []
        total_tokens = 0
        if file_extension in ['.csv', '.pdf', '.doc', '.docx','.xlsx', '.txt']:
            # Generate chunks
            chunks_list = chunking_file(file_item['category_id'], blob_name, file_id)
        
            # print("chunks", chunks_list)
            logging.info(f"Number of chunks created for file {file_id} : {len(chunks_list)}")

            # Generate embeddings
            for id, chunk in enumerate(chunks_list):
                chunk_dict = chunk.to_dict()
                # print("chunnk dictionary", chunk_dict)
                elements = chunk.metadata.orig_elements
                chunk_images = [el.to_dict() for el in elements if "Image" in str(type(el))]
                item = {
                'id': f"{file_id}_{id+1}",
                'title': blob_name,
                'category': file_item['category_id'],
                "sourcepage": blob_name_from_file_page(blob_name, chunk_dict["metadata"]["page_number"]),
                # 'blob_name': blob_name,
                'content': chunk_dict["text"]
            }
                if "Table" in str(elements):
                    item["content"] = chunk_dict["text"] + "Table in Html format :"+ chunk_dict["metadata"]["text_as_html"]
                    
                else:
                    item["content"] = chunk_dict["text"]

                if chunk_images:
                    images_data = [
                        {
                            "image_id": (j + 1),
                            "image_associated_text": i["text"],
                            "image_base64": i["metadata"]["image_base64"],
                            "image_description": generate_image_description(
                                i["metadata"]["image_base64"]
                            ),
                        }
                        for j, i in enumerate(chunk_images)
                    ]
                    # item["images_info"] = str(images_data)
                    print("image data", images_data)
                    item["content"] = item["content"] + ", Image Descriptions: " + json.dumps(
                            [
                                {"Image Id - " + str(k["image_id"]): k["image_description"]}
                                for k in images_data
                            ]
                        )
                content_embeddings, token_used = generate_embeddings(item['content'])
                total_tokens += token_used
                item["contentVector"] = content_embeddings
                chunk_ids.append(item['id'])
                item['@search.action'] = 'upload'
                # print("itemmm", item)
                items.append(item)
                    
        elif file_extension in ['.png', '.jpg', '.jpeg']:
            base64_image = get_base64_from_blob(blob_name)
            image_description = generate_image_description(base64_image)
            item = {
                'id': f"{file_id}_0",
                'title': blob_name,
                'category': file_item['category_id'],
                "sourcepage": blob_name_from_file_page(blob_name),
                'content': image_description
            }
            content_embeddings, token_used = generate_embeddings(item['content'])
            total_tokens += token_used
            item["contentVector"] = content_embeddings
            chunk_ids.append(item['id'])
            item['@search.action'] = 'upload'
            # print("itemmm", item)
            items.append(item)


        credit_used = round(total_tokens / 1000, 1)
        file_item['chunk_ids'] = str(chunk_ids)
        file_item['token_used'] = total_tokens
        file_item['credit_used'] = credit_used
        file_item['ex_time'] = time.time() - file_item['ex_time']
        file_item['status'] = 1

        # Update file_item in the database
        container.replace_item(item=file_item, body=file_item)

    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        # If file_item is not set, create a dummy one for logging purposes
        if 'file_item' not in locals():
            file_item = {'chunk_ids': [], 'status': 0, 'credit_used': credit_used}

    # Upload chunks
    batch_size = MAX_SECTION_LENGTH
    try:
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            search_client.upload_documents(batch)
            logging.info(f"Uploaded batch {i // batch_size + 1}")
    except Exception as e:
        logging.error(f"Error uploading documents: {e}")

    # Final transaction update
    try:
        balance = calculate_balance(email) - credit_used
        update_transactions_table(
            email=email,
            balance=round(balance, 2),
            service_type="Index",
            token_usage=total_tokens,
            credit_used=credit_used,
            credit_assigned=0
        )
        logging.info("End of the function.")
    except Exception as e:
        logging.error(f"Error updating transactions: {e}", exc_info=True)
        
        
        

def get_current_trans_id_from_database():
    query = "SELECT Top 1 * FROM transactions t ORDER BY t.surr_no DESC"

    # Execute the parameterized query
    query_result = tran_container.query_items(
        query=query,
        enable_cross_partition_query=True
    )
    logging.info(f"Tran item is :    {str(query_result)}   ")

    # Print the query results
    tran_item = []
    for item in query_result:
        tran_item = item

    try:
        return tran_item['surr_no']
    except StopIteration:
        return 0
    except CosmosHttpResponseError as cosmos_error:
        print(f"Error querying Cosmos DB for transaction ID: {cosmos_error}")
        return 0
    
    


def calculate_balance(email):
    query = "SELECT Top 1 * FROM transactions t WHERE t.email = @email ORDER BY t.transaction_ts DESC"
    query_params = [{"name": "@email", "value": email}]

    # Execute the parameterized query
    query_result = tran_container.query_items(
        query=query,
        parameters=query_params,
        enable_cross_partition_query=True
    )
    logging.info(f"Tran item is :    {str(query_result)}   ")

    # Print the query results
    tran_item = []
    for item in query_result:
        tran_item = item

    # # Processing Cosmos transactions
    # user_credits = [transaction.get('credit', 0) for transaction in transactions]
    # sum_debit = sum(transaction.get('debit', 0) for transaction in transactions)

    # # Calculating balance
    # balance = sum(user_credits) - sum_debit
    logging.info(f"Current credit balance is :    {str(tran_item['balance'])}   ")

    return tran_item['balance']



def update_transactions_table(email, balance, service_type, token_usage=None, credit_used = 0, credit_assigned = 0):

    try:
        current_trans_id = get_current_trans_id_from_database()
        logging.info(f"current_trans_id: {str(current_trans_id)}")
        current_utc_datetime = datetime.utcnow()
        formatted_datetime = current_utc_datetime.strftime("%Y-%m-%d %H:%M:%S")
        # Add a new entry to transactions table with zero balance for the new user
        new_transaction = {
            "surr_no" : current_trans_id + 1,
            "id": str(uuid.uuid1()),
            "email": email,
            "credit": credit_assigned,
            "balance": balance,
            "debit": credit_used,
            "purchase_type": 1,
            "service_type": service_type,
            "transaction_type": 2,  # Assuming 1 represents a user creation transaction
            "transaction_ts": str(formatted_datetime)
        }
        # Include "token_usage" only if it's provided
        if credit_assigned is not 0:
            new_transaction["credit"] = credit_assigned
        if token_usage is not None:
            new_transaction["token_usage"] = token_usage
        if credit_used is not 0:
            new_transaction["debit"] = credit_used
        logging.info(f"New Transaction: {str(new_transaction)}")
        tran_container.create_item(body=new_transaction)
        logging.info(f"Record added successfully")

    except exceptions.CosmosHttpResponseError as cosmos_error:
        logging.info(f"Error updating transactions table: {cosmos_error}")
    except Exception as e:
        logging.info(f"Error updating transactions table: {str(e)}")
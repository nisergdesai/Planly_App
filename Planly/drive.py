import os
import io
import whisper
import PyPDF2
import tempfile
import datetime
import time
import random
from googleapiclient.http import MediaIoBaseDownload
from google.cloud import vision
import pandas as pd
from drive_service import Create_Service_Drive
from googleapiclient.discovery import build
import google.generativeai as genai

def retry_with_backoff(api_call, max_retries=5):
    """Retry logic with exponential backoff for API calls."""
    retries = 0
    while retries < max_retries:
        try:
            return api_call()
        except Exception as e:
            if "429" in str(e):  # Check for rate limit error
                wait_time = (2 ** retries) + random.uniform(0, 1)
                print(f"Rate limit reached. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
                retries += 1
            else:
                raise e
    raise Exception("Max retries reached")

def setup_whisper(model_name="base"):
    return whisper.load_model(model_name)

def transcribe_audio_video(whisper_model, file_path):
    result = whisper_model.transcribe(file_path)
    return result['text']

def read_audio_video(service, whisper_model, file_id, file_name):
    temp_file_path = None
    try:
        # Retry logic for API call to get media
        request = retry_with_backoff(lambda: service.files().get_media(fileId=file_id))
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file_name}") as temp_file:
            downloader = MediaIoBaseDownload(temp_file, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            temp_file_path = temp_file.name

        # Transcribe the content
        transcribed_text = transcribe_audio_video(whisper_model, temp_file_path)
    except Exception as e:
        print(f"Error transcribing {file_name}: {e}")
        transcribed_text = ""
    finally:
        # Ensure the temporary file is deleted
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    return transcribed_text

def setup_vision_client(service_account_path):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = service_account_path
    return vision.ImageAnnotatorClient()

def detect_text_from_image(client, image_content):
    image = vision.Image(content=image_content)
    response = client.text_detection(image=image)
    return response

def detect_handwriting_from_image(client, image_content):
    image = vision.Image(content=image_content)
    response = client.document_text_detection(image=image)
    return response

def process_text_annotations(response):
    df = pd.DataFrame(columns=['locale', 'description'])
    texts = response.text_annotations

    rows = []
    for text in texts:
        rows.append(dict(
            locale=text.locale,
            description=text.description
        ))

    df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
    return df

CLIENT_SECRET_FILE = 'credentials.json'
API_NAME = 'drive'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/drive']
service, credentials = Create_Service_Drive(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)

vision_client = setup_vision_client(r"ServiceAccountToken.json")

def setup_gemini(api_key):
    genai.configure(api_key=api_key)

def summarize_content_with_gemini(content):
    model_gemini_pro = genai.GenerativeModel('gemini-pro')
    prompt = (
    "You are going to be provided the text from multiple files. "
    "Go through the entire text and use it to make a list of actionable tasks and important notes. "
    "It is okay if some files have little or zero tasks. "
    "For each task or note, include the following details in this format: "
    "<input type='checkbox'> for the checkbox, "
    "**Actions/Notes**, "
    "**File Title**, "
    "**Date Modified**. "
    "Organize the output by importance level (low, medium, high) and display each item in the following format:\n\n"
    "<ul>\n"
    "<li><input type='checkbox'> **Actions/Notes**: [task/note description] <br> **Title**: [file title] <br> **Date Modified**: [last modified date]</li>\n"
    "</ul>\n\n"
    "Here is the content:\n\n"
    f"{content}"
    )
    response = model_gemini_pro.generate_content(prompt)
    return response.text

def get_cutoff_date():
    now = datetime.datetime.utcnow()
    cutoff_date = now - datetime.timedelta(weeks=16)
    return cutoff_date.isoformat() + 'Z'

def list_recent_drive_files(service):
    cutoff_date = get_cutoff_date()
    query = f"modifiedTime > '{cutoff_date}'"
    
    # Apply retry logic to the API call for listing files
    def api_call():
        return service.files().list(q=query, pageSize=100, fields="files(id, name, mimeType, modifiedTime)").execute()

    try:
        results = retry_with_backoff(api_call)
        items = results.get('files', [])
    except Exception as e:
        print(f"Error listing files: {e}")
        return []

    if not items:
        print('No recent files found.')
        return []
    else:
        print('Recent Files:')
        for item in items:
            print(f"File name: {item['name']}, File ID: {item['id']}, MIME Type: {item['mimeType']}, Modified Time: {item['modifiedTime']}")
    return items

def read_google_doc(credentials, file_id):
    docs_service = build('docs', 'v1', credentials=credentials)
    request = retry_with_backoff(lambda: docs_service.documents().get(documentId=file_id).execute())
    document = request
    content = document.get('body').get('content')

    text = ''
    for element in content:
        if 'paragraph' in element:
            for text_run in element.get('paragraph').get('elements', []):
                if 'textRun' in text_run:
                    text += text_run['textRun'].get('content', '')
    return text

def read_google_sheet(credentials, spreadsheet_id, range_name='A1:Z1000'):
    sheets_service = build('sheets', 'v4', credentials=credentials)
    request = retry_with_backoff(lambda: sheets_service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute())
    sheet = request
    values = sheet.get('values', [])
    
    content = "\n".join([", ".join(row) for row in values])
    return content

def read_google_slides(credentials, presentation_id):
    slides_service = build('slides', 'v1', credentials=credentials)
    request = retry_with_backoff(lambda: slides_service.presentations().get(presentationId=presentation_id).execute())
    presentation = request
    slides = presentation.get('slides')

    text = ''
    for slide in slides:
        for element in slide.get('pageElements', []):
            if 'shape' in element and 'text' in element['shape']:
                text_elements = element['shape']['text']['textElements']
                for text_element in text_elements:
                    if 'textRun' in text_element:
                        text += text_element['textRun'].get('content', '').strip() + '\n'
    return text

def read_pdf_file(service, file_id, file_name):
    request = service.files().get_media(fileId=file_id)
    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file_name}.pdf") as temp_file:
        downloader = MediaIoBaseDownload(temp_file, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        temp_file_path = temp_file.name

    try:
        text = ""
        with open(temp_file_path, "rb") as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            for page in reader.pages:
                # Extract text and replace any newlines with spaces
                page_text = page.extract_text() or ""
                text += page_text.replace("\n", " ")  # Replace newlines with spaces
    except Exception as e:
        print(f"Error reading PDF file {file_name}: {e}")
        text = ""
    finally:
        os.remove(temp_file_path)

    return text


def combine_file_contents(files, credentials, service, whisper_model):
    combined_content_list = []

    for file in files:
        file_id = file['id']
        file_name = file['name']
        mime_type = file['mimeType']
        modified_time = file['modifiedTime']

        content = ""

        if mime_type == 'application/vnd.google-apps.document':
            content = read_google_doc(credentials, file_id)

        elif mime_type == 'application/vnd.google-apps.presentation':
            content = read_google_slides(credentials, file_id)

        elif mime_type == 'application/vnd.google-apps.spreadsheet':
            content = read_google_sheet(credentials, file_id)

        elif mime_type.startswith('audio/') or mime_type.startswith('video/'):
            content = read_audio_video(service, whisper_model, file_id, file_name)

        elif mime_type == 'application/pdf':
            content = read_pdf_file(service, file_id, file_name)

        if content:
            combined_content_list.append(f"File Name: {file_name}\nModified Time: {modified_time}\nContent:\n{content}\n\n")

    return "".join(combined_content_list)

def generate_todo_list(content):
    return summarize_content_with_gemini(content)

final_todo_list = ""
def process_files(service, credentials, whisper_model):
    files = list_recent_drive_files(service)
    if not files:
        return

    combined_content = combine_file_contents(files, credentials, service, whisper_model)

    if combined_content:
        final_todo_list = generate_todo_list(combined_content)
        return (f"\n\nFinal To-Do List:\n{final_todo_list}")

'''if service and credentials:
    whisper_model = setup_whisper()
    setup_gemini(api_key="AIzaSyBrl4OwWlUfGzNjwo2brjNj73Z7jXop1oc")
    process_files(service, credentials, whisper_model)
'''


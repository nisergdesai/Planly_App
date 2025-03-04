from flask import Flask, render_template, request, redirect, url_for, jsonify, request
from configparser import ConfigParser
import google.generativeai as genai
import os
import time
import json

# Import Gmail processing functions
from gmail_service import Create_Service
from gmail import fetch_emails_in_date_ranges, get_message_content, get_message_metadata

# Import Google Drive processing functions
from drive_service import Create_Service_Drive
from drive import setup_whisper, setup_gemini, process_files, list_recent_drive_files, combine_file_contents

# Import Microsoft (Outlook, OneDrive) processing functions
from outlooks import display_and_summarize_emails
from one_drive import navigate_onedrive, format_combined_content, summarize_content_with_gemini, get_onedrive_file_content, combined_content
from graph_api import generate_access_token, generate_user_code

# Import Canvas processing functions
from canvas import summarize_combined_text, combined_results

from predict import predict_sentences, predict_sentences_action_notes

# Set up Flask app
app = Flask(__name__)

# Load API key from config file
config = ConfigParser()
config.read('credentials.ini')
api_key = config['API_KEY']['google_api_key']
genai.configure(api_key=api_key)

# Global variables to store Google Drive service and credentials after authentication
drive_service = None
drive_credentials = None
flow = None

gmail_service = None 

# Process Gmail emails
def fetch_email_metadata(g_service):
    emails = fetch_emails_in_date_ranges(g_service, days=15, chunk_size=10)
    email_list = []

    for email in emails:
        msg_id = email['id']
        try:
            sender, formatted_date, subject = get_message_metadata(g_service, msg_id=msg_id)
            email_link = f"https://mail.google.com/mail/u/0/#all/{msg_id}"
            email_list.append({"id": msg_id, "sender": sender, "subject": subject, "date": formatted_date, "link": email_link})
        except Exception as e:
            print(f"Error processing email {msg_id}: {e}")

    return email_list

# Gmail API setup
@app.route('/connect_gmail', methods=['POST'])
def connect_gmail():
    global gmail_service
    CLIENT_FILE = 'credentials.json'
    API_NAME = 'gmail'
    API_VERSION = 'v1'
    SCOPES = ['https://mail.google.com/']
    gmail_service = Create_Service(CLIENT_FILE, API_NAME, API_VERSION, SCOPES)

    if gmail_service:
        emails = fetch_email_metadata(gmail_service)
        return jsonify({"status": "success", "emails": emails})
    else:
        return jsonify({"status": "error", "message": "Failed to Connect to Gmail"}), 500

def list_drive_files(d_service):
    if d_service:
        return list_recent_drive_files(d_service)
    return ""

# Google Drive API setup triggered by button click
@app.route('/connect_google_drive', methods=['POST'])
def connect_google_drive():
    global drive_service, drive_credentials
    CLIENT_SECRET_FILE = 'credentials.json'
    API_NAME = 'drive'
    API_VERSION = 'v3'
    SCOPES = ['https://www.googleapis.com/auth/drive']

    drive_service, drive_credentials = Create_Service_Drive(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)

    if drive_service and drive_credentials:
        files = list_drive_files(drive_service)
        return jsonify({"status": "success", "files": files})
    else:
        return jsonify({"status": "error", "message": "Failed to Connect to Google Drive"}), 500

# List recent Google Drive files (only if already connected)

# Process Google Drive files (only if already connected)
def process_drive_files():
    if drive_service:
        whisper_model = setup_whisper()
        setup_gemini(api_key=api_key)
        return process_files(drive_service, drive_credentials, whisper_model)
    return ""

def is_token_valid():
    if os.path.exists("ms_graph_api_token.json"):
        with open("ms_graph_api_token.json", "r") as file:
            token_data = json.load(file)

            # Extract the AccessToken section
            access_tokens = token_data.get("AccessToken", {})

            if not access_tokens:
                return False  # No access token found

            # Get the first token (assuming there's only one key)
            for key, token_info in access_tokens.items():
                expiration_time = int(token_info.get("expires_on", 0))
                print("Expiration Time:", expiration_time)
                current_time = int(time.time())

                if expiration_time > current_time:
                    return True  # Token is still valid

    return False  # Token is invalid or doesn't exist


@app.route('/fetch_code', methods=['POST'])
def fetch_code():
    if is_token_valid():
        # If token is valid, skip authentication and proceed to fetch data
        return jsonify({
            "status": "success"
        })

    APP_ID = 'edf0be76-049c-4130-aa48-cad3cd75a2c9'
    SCOPES = ['Mail.Read', 'Files.Read', 'Notes.Read']
    global flow
    flow = generate_user_code(app_id=APP_ID, scopes=SCOPES)

    return jsonify({
        "status": "pending",
        "user_code": flow.get('user_code'),
        "verification_url": 'https://microsoft.com/devicelogin'
    })

@app.route('/fetch_onedrive_outlook', methods=['POST'])
def fetch_onedrive_outlook():
    APP_ID = 'edf0be76-049c-4130-aa48-cad3cd75a2c9'
    SCOPES = ['Mail.Read', 'Files.Read', 'Notes.Read']
    access_token = None

    # Get the cutoff_days from the frontend
    cutoff_days_onedrive = int(request.form.get("cutoff_days", -1))  # Default to 300 if not provided
    cutoff_days_outlook = int(request.form.get("cutoff_days", -1))   # Default to 300 if not provided
    type = request.form.get('type')  # 'onedrive' or 'outlook'
    print(f"Received cutoff_days: OneDrive={cutoff_days_onedrive}, Outlook={cutoff_days_outlook}")  # Debugging

    if is_token_valid():
        with open("ms_graph_api_token.json", "r") as file:
            data = json.load(file)
            access_token = list(data["AccessToken"].values())[0]["secret"]
        headers = {'Authorization': 'Bearer ' + access_token}
        
        # Based on the type, call the appropriate function for either OneDrive or Outlook
        if type == 'onedrive':
            onedrive_files = navigate_onedrive(headers, access_token, cutoff_days_onedrive)
            print(onedrive_files)
            outlook_summary = []  # No need to process Outlook data
        else:  # 'outlook'
            onedrive_files = []  # No need to process OneDrive data
            outlook_summary = display_and_summarize_emails(headers, cutoff_days_outlook)
            print(outlook_summary)

    else:
        # If token is not valid, get a new one (e.g., after successful authentication)
        access_token = generate_access_token(flow, app_id=APP_ID, scopes=SCOPES)
        headers = {'Authorization': 'Bearer ' + access_token['access_token']}
        
        # Based on the type, call the appropriate function for either OneDrive or Outlook
        if type == 'onedrive':
            onedrive_files = navigate_onedrive(headers, access_token['access_token'], cutoff_days_onedrive)
            outlook_summary = []  # No need to process Outlook data
        else:  # 'outlook'
            onedrive_files = []  # No need to process OneDrive data
            outlook_summary = display_and_summarize_emails(headers, cutoff_days_outlook)

    return jsonify({
        "status": "pending",
        "o_files": onedrive_files,
        "outlooks": outlook_summary,
    })


'''def process_onedrive_data():
    APP_ID = 'edf0be76-049c-4130-aa48-cad3cd75a2c9'
    SCOPES = ['Mail.Read', 'Files.Read', 'Notes.Read']

    access_token = generate_access_token(app_id=APP_ID, scopes=SCOPES)
    headers = {'Authorization': 'Bearer ' + access_token['access_token']}

    formatted = "Summary of OneDrive Files:\n" + format_combined_content(combined_content)
    file_summary = summarize_content_with_gemini(formatted)

    return file_summary
'''
def list_onedrive(headers, access_token):
    '''APP_ID = 'edf0be76-049c-4130-aa48-cad3cd75a2c9'
    SCOPES = ['Mail.Read', 'Files.Read', 'Notes.Read']

    access_token = generate_access_token(app_id=APP_ID, scopes=SCOPES)
    headers = {'Authorization': 'Bearer ' + access_token['access_token']}'''
    return navigate_onedrive(headers, access_token, 300)

def outlooks():
    APP_ID = 'edf0be76-049c-4130-aa48-cad3cd75a2c9'
    SCOPES = ['Mail.Read', 'Files.Read', 'Notes.Read']

    access_token = generate_access_token(app_id=APP_ID, scopes=SCOPES)
    headers = {'Authorization': 'Bearer ' + access_token['access_token']}

    return display_and_summarize_emails(headers, cutoff_days=365)

# Canvas Processing
def process_canvas_data():
    return summarize_combined_text(combined_results)

@app.route('/')
def home():
    #gmails_metadata = fetch_email_metadata()
    #drive_list = list_drive_files(drive_service)  # Only lists files if already connected
    #one_drive_list = list_onedrive()
    canvas_data = process_canvas_data()
    #outlook_summary = outlooks()

    return render_template(
        "index.html",
        #gmails_metadata=gmails_metadata,
        #outlook_summary=outlook_summary.replace("\n", "<br>"),
        canvas_data=canvas_data.replace("\n", "<br>"),
        #drive_list=drive_list,
        #one_drive_display=[(str(name), str(item_id)) for name, item_id in one_drive_list]
    )

@app.route('/summarize_emails', methods=['POST'])
def summarize_selected_emails():
    email_ids = request.json.get('email_ids', [])
    summaries = []

    for msg_id in email_ids:
        try:
            sender, formatted_date, subject = get_message_metadata(gmail_service, msg_id=msg_id)
            content = get_message_content(gmail_service, msg_id=msg_id)
            if content:
                summary = predict_sentences(content)
                if not any(char.isalpha() for char in summary):
                    summary = predict_sentences_action_notes(content)
                summaries.append(f"Email from {sender} ({subject}) sent on {formatted_date}:\n{summary}\n")
        except Exception as e:
            print(f"Error summarizing email {msg_id}: {e}")

    final_summary = "<br><br>".join(summaries) if summaries else "No emails selected for summarization."
    return jsonify({'summary': final_summary})

@app.route('/summarize', methods=['POST'])
def summarize():
    if request.method == 'POST':
        file_id = request.form.get('file_id')
        file_name = request.form.get('file_name')
        file_mime_type = request.form.get('file_mime_type')
        file_source = request.form.get('file_source')
        print(f"Received for summarization: ID={file_id}, Name={file_name}, Type={file_mime_type}, Source={file_source}")

        summary = ""

        if file_source == 'google_drive' and drive_service:
            whisper_model = setup_whisper()
            summary = combine_file_contents(file_name, file_id, file_mime_type, drive_credentials, drive_service, whisper_model)

        elif file_source == 'onedrive':
            APP_ID = 'edf0be76-049c-4130-aa48-cad3cd75a2c9'
            SCOPES = ['Mail.Read', 'Files.Read', 'Notes.Read']
            access_token = generate_access_token(flow, app_id=APP_ID, scopes=SCOPES)
            headers = {'Authorization': 'Bearer ' + access_token['access_token']}
            summary = get_onedrive_file_content(headers, file_id, file_name, access_token, 300)

        return jsonify({'summary': summary})

if __name__ == '__main__':
    app.run(debug=False)


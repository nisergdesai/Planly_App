from flask import Flask, render_template
from configparser import ConfigParser
import google.generativeai as genai
from gmail_service import Create_Service
from gmail import fetch_emails_in_date_ranges, get_message_content, get_message_metadata, batch_emails, summarize_combined_email_text
from drive_service import Create_Service_Drive
from drive import setup_whisper, setup_gemini, process_files

# Set up Flask app
app = Flask(__name__)

# Load API key from config file
config = ConfigParser()
config.read('credentials.ini')
api_key = config['API_KEY']['google_api_key']
genai.configure(api_key=api_key)

# Gmail API setup
def setup_gmail_service():
    CLIENT_FILE = 'credentials.json'
    API_NAME = 'gmail'
    API_VERSION = 'v1'
    SCOPES = ['https://mail.google.com/']
    return Create_Service(CLIENT_FILE, API_NAME, API_VERSION, SCOPES)

# Process Gmail emails
def fetch_and_process_emails():
    service = setup_gmail_service()
    emails = fetch_emails_in_date_ranges(service, days=200, chunk_size=20)
    email_texts = []

    for email in emails:
        msg_id = email['id']
        try:
            content = get_message_content(service, msg_id=msg_id)
            sender, formatted_date = get_message_metadata(service, msg_id=msg_id)
            email_link = f"https://mail.google.com/mail/u/0/#all/{msg_id}"
            
            if content:
                email_texts.append(f"Email from {sender} sent on {formatted_date} ({email_link}):\n{content}\n")
        except Exception as e:
            print(f"Error processing email {msg_id}: {e}")

    batched_summaries = []
    for batch in batch_emails(email_texts, batch_size=10):
        combined_text = "\n\n".join(batch)
        try:
            summary = summarize_combined_email_text(combined_text)
            batched_summaries.append(summary)
        except Exception as e:
            print(f"Error summarizing batch: {e}")

    return "\n\n".join(batched_summaries)

# Drive API setup and processing
def setup_drive_service():
    CLIENT_SECRET_FILE = 'credentials.json'
    API_NAME = 'drive'
    API_VERSION = 'v3'
    SCOPES = ['https://www.googleapis.com/auth/drive']
    return Create_Service_Drive(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)

def process_drive_files():
    service, credentials = setup_drive_service()
    if service and credentials:
        whisper_model = setup_whisper()
        setup_gemini(api_key=api_key)
        return process_files(service, credentials, whisper_model)
    return ""

# Outlook and OneDrive Processing
from outlooks import display_and_summarize_emails, summary
from one_drive import navigate_onedrive, format_combined_content, summarize_content_with_gemini, combined_content
from graph_api import generate_access_token

def process_onedrive_data():
    APP_ID = 'edf0be76-049c-4130-aa48-cad3cd75a2c9'
    SCOPES = ['Mail.Read', 'Files.Read', 'Notes.Read']

    access_token = generate_access_token(app_id=APP_ID, scopes=SCOPES)
    headers = {'Authorization': 'Bearer ' + access_token['access_token']}

    # Navigate OneDrive and extract content
    navigate_onedrive(headers, access_token, 7)
    formatted = "Summary of OneDrive Files:\n" + format_combined_content(combined_content)
    file_summary = summarize_content_with_gemini(formatted)

    # Display and summarize recent Outlook emails
    outlook_summary = display_and_summarize_emails(headers, cutoff_days=365)

    return outlook_summary + file_summary

@app.route('/')
def home():
    google_combined = fetch_and_process_emails()
    drive_data = process_drive_files()
    microsoft_combined = process_onedrive_data()
    
    combined_SQUARED = google_combined + drive_data + microsoft_combined

    # Convert newlines to <br> for proper HTML formatting
    formatted_output = combined_SQUARED.replace("\n", "<br>")

    return render_template("index.html", output=formatted_output)

if __name__ == '__main__':
    app.run(debug=False)  # Set debug=False to prevent unwanted restarts

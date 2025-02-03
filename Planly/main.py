'''from configparser import ConfigParser
import google.generativeai as genai
from gmail_service import Create_Service
from gmail import fetch_emails_in_date_ranges, get_message_content, get_message_metadata, batch_emails, summarize_combined_email_text
from drive_service import Create_Service_Drive
from drive import setup_whisper, setup_gemini, process_files, final_todo_list

# Set up the Gmail API and generative AI model
CLIENT_FILE = 'credentials.json'
API_NAME = 'gmail'
API_VERSION = 'v1'
SCOPES = ['https://mail.google.com/']

service = Create_Service(CLIENT_FILE, API_NAME, API_VERSION, SCOPES)

# Load API key from config file
config = ConfigParser()
config.read('credentials.ini')
api_key = config['API_KEY']['google_api_key']
genai.configure(api_key=api_key)

# Collect emails and their content
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

final_summary = "\n\n".join(batched_summaries)
#print(final_summary if final_summary else "No email content to summarize.")

CLIENT_SECRET_FILE = 'credentials.json'
API_NAME_DRIVE = 'drive'
API_VERSION_DRIVE = 'v3'
SCOPES_DRIVE = ['https://www.googleapis.com/auth/drive']
service, credentials = Create_Service_Drive(CLIENT_SECRET_FILE, API_NAME_DRIVE, API_VERSION_DRIVE, SCOPES_DRIVE)


if service and credentials:
    whisper_model = setup_whisper()
    setup_gemini(api_key="AIzaSyBrl4OwWlUfGzNjwo2brjNj73Z7jXop1oc")
    final_todo_list = process_files(service, credentials, whisper_model)

google_combined = final_summary + (final_todo_list)

from outlooks import display_and_summarize_emails, summary
from one_drive import navigate_onedrive, format_combined_content, summarize_content_with_gemini, combined_content
from graph_api import generate_access_token


if __name__ == '__main__':
    APP_ID = 'edf0be76-049c-4130-aa48-cad3cd75a2c9'
    SCOPES = ['Mail.Read', 'Files.Read', 'Notes.Read']
    GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'

    access_token = generate_access_token(app_id=APP_ID, scopes=SCOPES)
    headers = {
        'Authorization': 'Bearer ' + access_token['access_token']
    }

    # Navigate OneDrive and extract content
    navigate_onedrive(headers, access_token, 7)
    formatted = ("Summary of OneDrive Files:\n") + format_combined_content(combined_content)
    file_sum = (summarize_content_with_gemini(formatted))
    
    # Display and summarize recent emails with a cutoff date of 7 days
    outlooks = (display_and_summarize_emails(headers, cutoff_days=365))

#microsoft_combined = outlooks + file_sum

combined_SQUARED = google_combined'''


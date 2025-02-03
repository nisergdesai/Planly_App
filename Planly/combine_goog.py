from configparser import ConfigParser
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
emails = fetch_emails_in_date_ranges(service, days=3, chunk_size=20)
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
print(google_combined)
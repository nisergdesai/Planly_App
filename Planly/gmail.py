from gmail_service import Create_Service
import base64
from email import message_from_bytes
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from configparser import ConfigParser
import google.generativeai as genai
import time
import random

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

def fetch_emails_in_date_ranges(service, user_id='me', label_ids=['STARRED'], days=3, chunk_size=10):
    """
    Fetch emails in smaller date ranges to bypass API limitations.
    """
    now = datetime.utcnow()
    messages = []
    
    for i in range(0, days, chunk_size):
        if days > chunk_size:
            start_date = now - timedelta(days=i + chunk_size)
        else:
            start_date = now - timedelta(days=i + days)
        end_date = now - timedelta(days=i)
        query = f"after:{start_date.strftime('%Y/%m/%d')} before:{end_date.strftime('%Y/%m/%d')}"
        print(f"Querying emails with: {query}")
        
        page_token = None
        while True:
            response = retry_with_backoff(lambda: service.users().messages().list(
                userId=user_id,
                labelIds=label_ids,
                q=query,
                pageToken=page_token,
                maxResults=500
            ).execute())
            
            fetched_messages = response.get('messages', [])
            print(f"Fetched {len(fetched_messages)} messages in range {start_date} to {end_date}.")
            messages.extend(fetched_messages)
            page_token = response.get('nextPageToken')
            
            if not page_token:
                break
    
    print(f"Total emails fetched: {len(messages)}")
    return messages


def get_message_metadata(service, user_id='me', msg_id=''):
    """Retrieve metadata like the sender and date from the email."""
    try:
        msg = retry_with_backoff(lambda: service.users().messages().get(
            userId=user_id, id=msg_id, format='metadata', metadataHeaders=['From', 'Date']
        ).execute())
        
        headers = msg['payload']['headers']
        sender = next((header['value'] for header in headers if header['name'] == 'From'), 'unknown sender')
        date = next((header['value'] for header in headers if header['name'] == 'Date'), 'unknown date')
        
        try:
            formatted_date = datetime.strptime(date, '%a, %d %b %Y %H:%M:%S %z').strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            formatted_date = date
        
        return sender, formatted_date
    except Exception as error:
        print(f"An error occurred while retrieving metadata: {error}")
        return 'unknown sender', 'unknown date'

def get_message_content(service, user_id='me', msg_id=''):
    """Retrieve and decode the email message content, extracting HTML and plain text."""
    try:
        msg = retry_with_backoff(lambda: service.users().messages().get(
            userId=user_id, id=msg_id, format='raw'
        ).execute())
        
        msg_str = base64.urlsafe_b64decode(msg['raw'].encode('ASCII'))
        mime_msg = message_from_bytes(msg_str)
        
        html_content, text_content = None, None
        for part in mime_msg.walk():
            if part.get_content_type() == 'text/html':
                html_content = part.get_payload(decode=True).decode()
            elif part.get_content_type() == 'text/plain':
                text_content = part.get_payload(decode=True).decode()
        
        if html_content:
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.get_text()
        elif text_content:
            return text_content
        return 'No content found.'
    except Exception as error:
        print(f"An error occurred: {error}")
        return None

def batch_emails(email_texts, batch_size=10):
    """Split email texts into batches."""
    for i in range(0, len(email_texts), batch_size):
        yield email_texts[i:i + batch_size]

def summarize_combined_email_text(combined_text):
    """Summarize combined email text into actionable tasks."""
    prompt = (
    "You are going to be provided the text from multiple emails. "
    "Go through the entire text and use it to make a list of actionable tasks and important notes. "
    "For each task or note, include the following details in this format: "
    "<input type='checkbox'> for the checkbox, "
    "the **Action/Note**, "
    "**Requester**, "
    "**Date**, "
    "**Link** to the email. "
    "Organize the output by importance level (low, medium, high) and display each item in the following format:\n\n"
    "<ul>\n"
    "<li><input type='checkbox'> **Action/Note**: [task/note description] <br> **Requester**: [sender name] <br> **Date**: [sent date] <br> **Link**: [email link]</li>\n"
    "</ul>\n\n"
    "Here's the content:\n\n"
    f"{combined_text}"
    )
    return retry_with_backoff(lambda: genai.GenerativeModel('gemini-pro').generate_content(prompt).text)

# Collect emails and their content
'''emails = fetch_emails_in_date_ranges(service, days=40, chunk_size=20)
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
print(final_summary if final_summary else "No email content to summarize.")'''

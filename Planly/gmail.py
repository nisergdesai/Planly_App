'''from gmail_service import Create_Service
import base64
from email import message_from_bytes
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import random
from transformers import pipeline

# Set up the Gmail API
CLIENT_FILE = 'credentials.json'
API_NAME = 'gmail'
API_VERSION = 'v1'
SCOPES = ['https://mail.google.com/']

service = Create_Service(CLIENT_FILE, API_NAME, API_VERSION, SCOPES)

# Load the summarization model
summarizer = pipeline("summarization")

def retry_with_backoff(api_call, max_retries=5):
    """Retry logic with exponential backoff for API calls."""
    retries = 0
    while retries < max_retries:
        try:
            return api_call()
        except Exception as e:
            if "429" in str(e):
                wait_time = (2 ** retries) + random.uniform(0, 1)
                print(f"Rate limit reached. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
                retries += 1
            else:
                raise e
    raise Exception("Max retries reached")

def fetch_emails(service, user_id='me', label_ids=['STARRED'], days=3, chunk_size=10):
    """Fetch emails in smaller date ranges to bypass API limitations."""
    now = datetime.utcnow()
    messages = []
    
    for i in range(0, days, chunk_size):
        start_date = now - timedelta(days=i + chunk_size)
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
            
            messages.extend(response.get('messages', []))
            page_token = response.get('nextPageToken')
            if not page_token:
                break
    
    print(f"Total emails fetched: {len(messages)}")
    return messages

def get_email_details(service, user_id='me', msg_id=''):
    """Retrieve sender, date, and content from an email."""
    sender, date = "Unknown sender", "Unknown date"
    
    try:
        msg = retry_with_backoff(lambda: service.users().messages().get(
            userId=user_id, id=msg_id, format='raw'
        ).execute())
        
        msg_str = base64.urlsafe_b64decode(msg['raw'].encode('ASCII'))
        mime_msg = message_from_bytes(msg_str)
        
        for header in mime_msg._headers:
            if header[0] == "From":
                sender = header[1]
            elif header[0] == "Date":
                date = header[1]
        
        content = None
        for part in mime_msg.walk():
            if part.get_content_type() == 'text/html':
                content = BeautifulSoup(part.get_payload(decode=True).decode(), 'html.parser').get_text()
            elif part.get_content_type() == 'text/plain' and not content:
                content = part.get_payload(decode=True).decode()
        
        return sender, date, content.strip() if content else "No content found."
    except Exception as e:
        print(f"Error retrieving email: {e}")
        return sender, date, "Error extracting content"

def summarize_email(content):
    """Summarize email content using a transformer model."""
    try:
        word_count = len(content.split())

        # Set max_length dynamically (e.g., 30-40% of original text)
        max_len = min(150, max(50, int(word_count * 0.4)))

        if word_count > 50:  # Summarize only if email is long enough
            summary = summarizer(content, max_length=max_len, min_length=30, do_sample=False)
            return summary[0]['summary_text']
        return content  # Return original text if it's too short
    except Exception as e:
        print(f"Error summarizing email: {e}")
        return "Error summarizing content."


def process_emails(service, days=3):
    """Fetch, extract, summarize, and categorize emails."""
    emails = fetch_emails(service, days=days)
    summarized_emails = []
    
    for email in emails:
        sender, date, content = get_email_details(service, msg_id=email['id'])
        summary = summarize_email(content)
        summarized_emails.append({
            "Sender": sender,
            "Date": date,
            "Summary": summary
        })
    
    return summarized_emails

if __name__ == "__main__":
    summaries = process_emails(service, days=500)
    for email in summaries:
        print("\nEmail Summary:")
        print(f"From: {email['Sender']}")
        print(f"Date: {email['Date']}")
        print(f"Summary: {email['Summary']}")
'''
from gmail_service import Create_Service
import base64
from email import message_from_bytes
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from configparser import ConfigParser
import time
import random
from predict import predict_sentences  # Import from predict.py

# Set up the Gmail API and generative AI model
CLIENT_FILE = 'credentials.json'
API_NAME = 'gmail'
API_VERSION = 'v1'
SCOPES = ['https://mail.google.com/']

#service = Create_Service(CLIENT_FILE, API_NAME, API_VERSION, SCOPES)

# Load API key from config file
config = ConfigParser()
config.read('credentials.ini')
api_key = config['API_KEY']['google_api_key']

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

def fetch_emails_in_date_ranges(service, user_id='me', label_ids=['INBOX'], days=3, chunk_size=10):
    """Fetch emails in smaller date ranges to bypass API limitations."""
    now = datetime.utcnow()
    messages = []

    for i in range(0, days, chunk_size):
        actual_chunk_size = min(chunk_size, days - i)
        start_date = now - timedelta(days=i + actual_chunk_size)
        end_date = now - timedelta(days=i)

        query = f"after:{start_date.strftime('%Y/%m/%d')} before:{(end_date + timedelta(days=1)).strftime('%Y/%m/%d')}"
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
    """Retrieve metadata like the sender, date, and subject from the email."""
    try:
        msg = retry_with_backoff(lambda: service.users().messages().get(
            userId=user_id, id=msg_id, format='metadata', metadataHeaders=['From', 'Date', 'Subject']
        ).execute())

        headers = msg['payload']['headers']
        sender = next((header['value'] for header in headers if header['name'] == 'From'), 'unknown sender')
        date = next((header['value'] for header in headers if header['name'] == 'Date'), 'unknown date')
        subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')

        try:
            formatted_date = datetime.strptime(date, '%a, %d %b %Y %H:%M:%S %z').strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            formatted_date = date

        return sender, formatted_date, subject
    except Exception as error:
        print(f"An error occurred while retrieving metadata: {error}")
        return 'unknown sender', 'unknown date', 'No Subject'


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
        
        # Use BeautifulSoup to clean up HTML content
        if html_content:
            soup = BeautifulSoup(html_content, 'html.parser')
            # Remove unwanted tags (like ads, footers)
            for script in soup(["script", "style"]):
                script.decompose()
            text = soup.get_text(separator=' ')
        elif text_content:
            text = text_content
        else:
            return 'No content found.'

        # Further clean up the text content
        return clean_email_text(text)
    except Exception as error:
        print(f"An error occurred: {error}")
        return None

def clean_email_text(text):
    """Clean up the email text by removing unnecessary content."""
    # Remove excessive whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned_text = ' '.join(lines)
    # Optionally filter out common footer phrases
    footer_keywords = ['unsubscribe', 'no longer want to receive this email', 'this email was sent to']
    for keyword in footer_keywords:
        cleaned_text = cleaned_text.replace(keyword, '')
    return cleaned_text.strip()

# Collect emails and their content
'''emails = fetch_emails_in_date_ranges(service, days=15, chunk_size=10)
final_output = []

for email in emails:
    msg_id = email['id']
    try:
        # Fetch metadata and content separately
        sender, formatted_date = get_message_metadata(service, msg_id=msg_id)
        content = get_message_content(service, msg_id=msg_id)
        
        if content:
            # Summarize the content
            summary = predict_sentences(content)
            # Append metadata and summarized content to the final output
            email_link = f"https://mail.google.com/mail/u/0/#all/{msg_id}"
            final_output.append(f"Email from {sender} sent on {formatted_date} ({email_link}):\n{summary}\n")
    except Exception as e:
        print(f"Error processing email {msg_id}: {e}")

# Combine all outputs into a final string and print
final_output_cleaned = []

for output in final_output:
    # Clean up each output by stripping whitespace and replacing multiple newlines with a single newline
    cleaned_output = output.strip().replace('\n\n', '\n').replace('\n\n\n', '\n')
    final_output_cleaned.append(cleaned_output)

final_summary = "\n\n".join(final_output_cleaned)
if final_summary:  # Only print if there is content
    print(final_summary)
else:
    print("No emails found or processed.")
'''



#print(final_summary if final_summary else "No email content to summarize.")

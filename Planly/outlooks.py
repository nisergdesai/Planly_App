import requests
from bs4 import BeautifulSoup
from configparser import ConfigParser
from graph_api import generate_access_token
from datetime import datetime, timedelta
import time
import random
from predict import predict_sentences, predict_sentences_action_notes  # Import your sentence prediction function

GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'

# Load API key from config file
config = ConfigParser()
config.read('credentials.ini')
api_key = config['API_KEY']['google_api_key']

def retry_with_backoff(api_call, max_retries=5):
    """Retry logic with exponential backoff for API calls."""
    retries = 0
    while retries < max_retries:
        try:
            return api_call()  # Attempt the API call
        except requests.exceptions.RequestException as e:
            if "429" in str(e):  # Rate limit error
                wait_time = (2 ** retries) + random.uniform(0, 1)
                print(f"Rate limit reached. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
                retries += 1
            else:
                print(f"Error occurred: {e}. Retrying...")
                time.sleep(2 ** retries)  # Exponential backoff for other errors
                retries += 1
    raise Exception("Max retries reached. The operation failed.")

def display_and_summarize_emails(headers, cutoff_days=7):
    try:
        from datetime import datetime, timedelta
        import requests
        from bs4 import BeautifulSoup
        
        # Calculate the cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=cutoff_days)
        cutoff_date_str = cutoff_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        params = {
            '$select': 'id,subject,from,receivedDateTime,bodyPreview,body',
            '$filter': f"receivedDateTime ge {cutoff_date_str}"
        }

        # Retry the API call with backoff
        response = retry_with_backoff(lambda: requests.get(f'{GRAPH_API_ENDPOINT}/me/mailFolders/inbox/messages', headers=headers, params=params))
        response.raise_for_status()

        emails = response.json().get('value', [])
        if not emails:
            print("No emails found within the cutoff date.")
            return []

        outlook_emails = []

        for email in emails:
            email_id = email.get('id', 'Unknown ID')
            subject = email.get('subject', 'No Subject')
            sender = email.get('from', {}).get('emailAddress', {}).get('address', 'Unknown Sender')
            received_time = email.get('receivedDateTime', 'No Date')
            body_content = email.get('body', {}).get('content', 'No Content Available')

            # Format the received date to MM/DD/YY
            formatted_date = 'No Date'
            if received_time != 'No Date':
                date_object = datetime.fromisoformat(received_time[:-1])  # Remove trailing 'Z'
                formatted_date = date_object.strftime('%m/%d/%y')

            # Clean HTML from email body
            soup = BeautifulSoup(body_content, 'html.parser')
            clean_text = soup.get_text().strip()

            # Summarize only the email body
            summary = predict_sentences(clean_text) if clean_text else "No important content detected."

            # Construct email metadata
            email_metadata = {
                "id": email_id,
                "subject": subject.strip() or 'No Action',
                "sender": sender,
                "date": formatted_date,
                "summary": summary,
                "link": f"https://outlook.office.com/mail/inbox/id/{email_id}"
            }

            outlook_emails.append(email_metadata)

        return outlook_emails  # Return structured list of metadata

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"Other error occurred: {err}")

    return []


'''if __name__ == '__main__':
    APP_ID = 'edf0be76-049c-4130-aa48-cad3cd75a2c9'
    SCOPES = ['Mail.Read']

    try:
        access_token = generate_access_token(app_id=APP_ID, scopes=SCOPES)
        headers = {
            'Authorization': 'Bearer ' + access_token['access_token']
        }

        # Display and summarize recent emails with a cutoff date of 7 days
        print(display_and_summarize_emails(headers, cutoff_days=365))

    except Exception as e:
        print(f"Error retrieving access token: {e}")'''


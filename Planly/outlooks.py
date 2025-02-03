import requests
from bs4 import BeautifulSoup
from configparser import ConfigParser
import google.generativeai as genai
from graph_api import generate_access_token
from datetime import datetime, timedelta
import time
import random

GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'

# Configure Google Gemini API
config = ConfigParser()
config.read('credentials.ini')
api_key = config['API_KEY']['google_api_key']

# Configure Google Gemini with API Key
genai.configure(api_key=api_key)

# Select the appropriate model for summarization
model_gemini_pro = genai.GenerativeModel('gemini-pro')
summary = ""

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
        # Calculate the cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=cutoff_days)
        
        # Format cutoff_date in the required string format for Graph API
        cutoff_date_str = cutoff_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        params = {
            '$select': 'id,subject,from,receivedDateTime,bodyPreview,body',
            '$filter': f"receivedDateTime ge {cutoff_date_str}"  # Filter for emails received after the cutoff date
        }

        # Retry the API call with backoff
        response = retry_with_backoff(lambda: requests.get(f'{GRAPH_API_ENDPOINT}/me/mailFolders/inbox/messages', headers=headers, params=params))
        response.raise_for_status()

        emails = response.json().get('value', [])
        if not emails:
            print("No emails found within the cutoff date.")
            return

        all_email_bodies = ""

        for email in emails:
            email_id = email.get('id', 'Unknown ID')
            subject = email.get('subject', 'No Subject')
            sender = email.get('from', {}).get('emailAddress', {}).get('address', 'Unknown Sender')
            received_time = email.get('receivedDateTime', 'No Date')
            body_content = email.get('body', {}).get('content', 'No Content Available')

            # Format the received date to MM/DD/YY
            if received_time != 'No Date':
                date_object = datetime.fromisoformat(received_time[:-1])  # Remove the trailing 'Z'
                formatted_date = date_object.strftime('%m/%d/%y')  # Format to MM/DD/YY
            else:
                formatted_date = 'No Date'

            # Clean the HTML content
            soup = BeautifulSoup(body_content, 'html.parser')
            clean_text = soup.get_text()

            # Construct the email link
            email_link = f"https://outlook.office.com/mail/inbox/id/{email_id}"

            # Collect the cleaned email bodies
            all_email_bodies += (
                f"**Subject:** {subject.strip() or 'No Action'}\n"
                f"**Sender:** {sender}\n"
                f"**Date:** {formatted_date}\n"
                f"**Link:** {email_link}\n\n"
                f"{clean_text.strip()}\n\n"
            )

        # Summarize all email bodies using Gemini API
        if all_email_bodies:
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
            f"{all_email_bodies}"
            )
            # Retry the summarization API call with backoff
            response = retry_with_backoff(lambda: model_gemini_pro.generate_content(prompt))

            # Access the summary via 'text'
            summary = response.text
            return ("\nSummary of Outlook Emails:\n") + summary
            print(summary)
        else:
            print("No email bodies to summarize.")

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"Other error occurred: {err}")


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

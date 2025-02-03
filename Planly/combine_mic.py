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

microsoft_combined = outlooks + file_sum
print(microsoft_combined)
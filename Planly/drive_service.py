import pickle
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.auth.transport.requests import Request
import datetime

def Create_Service_Drive(client_secret_file, api_name, api_version, *scopes):
    print(client_secret_file, api_name, api_version, scopes, sep='-')
    CLIENT_SECRET_FILE = client_secret_file
    API_SERVICE_NAME = api_name
    API_VERSION = api_version
    SCOPES = [scope for scope in scopes[0]]  # Correctly format scopes
    print(SCOPES)

    cred = None
    pickle_file = f'token_{API_SERVICE_NAME}_{API_VERSION}.pickle'

    # Check if the pickle file with credentials already exists
    if os.path.exists(pickle_file):
        with open(pickle_file, 'rb') as token:
            cred = pickle.load(token)

    # If there are no valid credentials, authenticate the user
    if not cred or not cred.valid:
        if cred and cred.expired and cred.refresh_token:
            cred.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            
            # You can use run_local_server or run_console based on the environment
            cred = flow.run_local_server(port=0)  # Use a random available port

        # Save the credentials for the next run
        with open(pickle_file, 'wb') as token:
            pickle.dump(cred, token)

    try:
        service = build(API_SERVICE_NAME, API_VERSION, credentials=cred)
        print(f"{API_SERVICE_NAME} service created successfully")
        return service, cred  # Return both service and credentials
    except Exception as e:
        print('Unable to connect to the API service.')
        print(e)
        return None, None  # Return None for both if connection fails

def convert_to_RFC_datetime(year=1900, month=1, day=1, hour=0, minute=0):
    dt = datetime.datetime(year, month, day, hour, minute, 0).isoformat() + 'Z'
    return dt

# Example usage
'''if __name__ == "__main__":
    CLIENT_SECRET_FILE = 'path_to_your_client_secret.json'
    API_NAME = 'drive'
    API_VERSION = 'v3'
    SCOPES = ['https://www.googleapis.com/auth/drive']

    service, credentials = Create_Service_Drive(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)

    if service:
        print("Google Drive API service created successfully!")
    else:
        print("Failed to create the Google Drive API service.")'''

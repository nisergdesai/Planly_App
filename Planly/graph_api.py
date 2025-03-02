import webbrowser
from datetime import datetime
import json
import os
import msal

GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'
def generate_access_token(flow, app_id, scopes):
    access_token_cache = msal.SerializableTokenCache()

    # Read the token file
    if os.path.exists('ms_graph_api_token.json'):
        access_token_cache.deserialize(open("ms_graph_api_token.json", "r").read())
        token_detail = json.load(open('ms_graph_api_token.json',))
        token_detail_key = list(token_detail['AccessToken'].keys())[0]
        token_expiration = datetime.fromtimestamp(int(token_detail['AccessToken'][token_detail_key]['expires_on']))
        if datetime.now() > token_expiration:
            os.remove('ms_graph_api_token.json')
            access_token_cache = msal.SerializableTokenCache()
        else:
            saved_scopes = token_detail.get('Scopes', [])
            if set(saved_scopes) != set(scopes):
                os.remove('ms_graph_api_token.json')
                access_token_cache = msal.SerializableTokenCache()

    client = msal.PublicClientApplication(client_id=app_id, token_cache=access_token_cache)
    accounts = client.get_accounts()


    if accounts:
        token_response = client.acquire_token_silent(scopes, accounts[0])
        if not token_response or 'access_token' not in token_response:
            # Token is invalid or expired, prompt for re-authentication
            print('user_code: ' + flow['user_code'])
            token_response = client.acquire_token_by_device_flow(flow)
    else:
        # Authenticate as usual
        print('user_code: ' + flow['user_code'])
        token_response = client.acquire_token_by_device_flow(flow)

    # Save the new token and scopes
    with open('ms_graph_api_token.json', 'w') as _f:
        token_cache_data = json.loads(access_token_cache.serialize())
        token_cache_data['Scopes'] = scopes
        _f.write(json.dumps(token_cache_data, indent=2))
    print(flow['user_code'])
    return token_response  

def generate_user_code(app_id, scopes):
    access_token_cache = msal.SerializableTokenCache()

    # Read the token file
    if os.path.exists('ms_graph_api_token.json'):
        access_token_cache.deserialize(open("ms_graph_api_token.json", "r").read())
        token_detail = json.load(open('ms_graph_api_token.json',))
        token_detail_key = list(token_detail['AccessToken'].keys())[0]
        token_expiration = datetime.fromtimestamp(int(token_detail['AccessToken'][token_detail_key]['expires_on']))
        if datetime.now() > token_expiration:
            os.remove('ms_graph_api_token.json')
            access_token_cache = msal.SerializableTokenCache()
        else:
            saved_scopes = token_detail.get('Scopes', [])
            if set(saved_scopes) != set(scopes):
                os.remove('ms_graph_api_token.json')
                access_token_cache = msal.SerializableTokenCache()

    client = msal.PublicClientApplication(client_id=app_id, token_cache=access_token_cache)
    accounts = client.get_accounts()

    if accounts:
        token_response = client.acquire_token_silent(scopes, accounts[0])
        flow = client.initiate_device_flow(scopes=scopes)
        if not token_response or 'access_token' not in token_response:
            # Token is invalid or expired, prompt for re-authentication
            flow = client.initiate_device_flow(scopes=scopes)
            return flow
    else:
        # Authenticate as usual
        flow = client.initiate_device_flow(scopes=scopes)
        return flow

'''if __name__ == '__main__':
    APPLICATION_ID = 'edf0be76-049c-4130-aa48-cad3cd75a2c9'
    SCOPES = ['Mail.Read', 'Files.Read', 'Notes.Read']

    #result = generate_access_token(APPLICATION_ID, SCOPES)
    user_code = generate_user_code(APPLICATION_ID, SCOPES)
    print(user_code)
    #print(result['access_token'])
'''
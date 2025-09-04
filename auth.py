import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive.appdata']

def generate_token():
    """認証情報を取得し、token.jsonを生成する"""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("credentials.jsonが見つかりません。")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=8000)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            print("token.jsonが正常に生成されました。")
    else:
        print("token.jsonは既に存在し、有効です。")

if __name__ == '__main__':
    generate_token()

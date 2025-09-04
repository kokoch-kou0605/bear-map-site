from flask import Flask, render_template, request, jsonify, session
import uuid
import json
from datetime import datetime
from timezonefinder import TimezoneFinder
import pytz
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os

app = Flask(__name__)
app.secret_key = 'a_very_long_and_random_string_that_no_one_can_guess_12345'

CLIENT_ID = "395791546336-ll8vrl97u6iar765t6mg4i7i2ut4d3du.apps.googleusercontent.com"

tf = TimezoneFinder()

# 管理者のユーザーIDをここに設定してください
ADMIN_USER_ID = "117499766616149841879"

# Google Drive APIの設定
# アプリケーションデータフォルダにアクセスするためのスコープ
SCOPES = ['https://www.googleapis.com/auth/drive.appdata']

def get_drive_service():
    """認証情報を使用してGoogle Driveサービスを構築する"""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # ブラウザを開く代わりに、認証URLをコンソールに出力する
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            auth_url, _ = flow.authorization_url(prompt='consent')
            print(f'ブラウザで以下のURLを開いてください: {auth_url}')

            # ユーザーが認証コードを貼り付けるのを待つ
            auth_code = input('URLから認証コードを貼り付けてEnterを押してください: ')
            flow.fetch_token(code=auth_code)
            creds = flow.credentials
            
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('drive', 'v3', credentials=creds)

def find_file(drive_service, filename):
    """Google Driveから指定したファイル名を探す"""
    query = f"name='{filename}' and 'appDataFolder' in parents and trashed=false"
    results = drive_service.files().list(
        q=query,
        spaces='appDataFolder',
        fields='files(id, name)'
    ).execute()
    files = results.get('files', [])
    if files:
        return files[0]
    return None

def load_data_from_drive(drive_service):
    """Google Driveからデータを読み込む"""
    file_info = find_file(drive_service, 'data.json')
    if file_info:
        file_id = file_info.get('id')
        response = drive_service.files().get_media(fileId=file_id).execute()
        return json.loads(response.decode('utf-8'))
    return []

def save_data_to_drive(drive_service, data):
    """Google Driveにデータを保存する"""
    file_info = find_file(drive_service, 'data.json')
    
    # ファイルメタデータ
    file_metadata = {
        'name': 'data.json',
        'parents': ['appDataFolder']
    }
    
    # ファイルの内容
    media_body = json.dumps(data, indent=4)
    media = {'body': media_body, 'mimetype': 'application/json'}
    
    if file_info:
        # ファイルが既に存在する場合は更新
        file_id = file_info.get('id')
        drive_service.files().update(
            fileId=file_id,
            media_body=media
        ).execute()
    else:
        # ファイルが存在しない場合は新規作成
        drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

def get_local_time(lat, lng):
    timezone_str = tf.timezone_at(lng=lng, lat=lat)
    
    if timezone_str:
        try:
            timezone = pytz.timezone(timezone_str)
            local_time = datetime.now(timezone)
            return local_time.strftime('%Y年%m月%d日 %H時%M分%S秒')
        except pytz.UnknownTimeZoneError:
            pass

    jst = pytz.timezone('Asia/Tokyo')
    local_time = datetime.now(jst)
    return local_time.strftime('%Y年%m月%d日 %H時%M分%S秒')

@app.route('/')
def index():
    return render_template('index.html', CLIENT_ID=CLIENT_ID)

@app.route('/login', methods=['POST'])
def login():
    token = request.get_json().get('token')
    
    try:
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), CLIENT_ID)
        session['user_id'] = idinfo['sub']
        print("Logged in user ID:", idinfo.get('sub'))
        print("Logged in user email:", idinfo.get('email'))
        return jsonify({"success": True})
    except ValueError:
        return jsonify({"success": False, "error": "Invalid token"}), 400

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({"success": True})

@app.route('/check_login')
def check_login():
    logged_in = 'user_id' in session
    user_id = session.get('user_id') if logged_in else None
    return jsonify({"logged_in": logged_in, "user_id": user_id})

@app.route('/locations', methods=['GET', 'POST'])
def handle_locations():
    drive_service = get_drive_service()
    
    if request.method == 'POST':
        if 'user_id' not in session:
            return jsonify({"error": "Unauthorized"}), 401
            
        locations = load_data_from_drive(drive_service)
        data = request.get_json()
        
        data['id'] = str(uuid.uuid4())
        data['user_id'] = session['user_id']
        
        lat = data.get('lat')
        lng = data.get('lng')
        
        data['timestamp'] = get_local_time(lat, lng)

        locations.append(data)
        save_data_to_drive(drive_service, locations)
        
        return jsonify(data), 200

    elif request.method == 'GET':
        locations = load_data_from_drive(drive_service)
        return jsonify(locations), 200

@app.route('/locations/<string:location_id>', methods=['DELETE'])
def delete_location(location_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    is_admin = session['user_id'] == ADMIN_USER_ID

    drive_service = get_drive_service()
    locations = load_data_from_drive(drive_service)
    
    index_to_delete = -1
    for i, location in enumerate(locations):
        if location.get('id') == location_id:
            if is_admin or location.get('user_id') == session['user_id']:
                index_to_delete = i
                break
            else:
                return jsonify({"error": "You do not have permission to delete this location."}), 403
            
    if index_to_delete != -1:
        del locations[index_to_delete]
        save_data_to_drive(drive_service, locations)
        return jsonify({"message": "Location deleted successfully"}), 200
    else:
        return jsonify({"error": "Location not found"}), 404

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)


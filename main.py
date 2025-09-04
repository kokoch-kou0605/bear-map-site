from flask import Flask, request, jsonify, render_template
import json
import os

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

app = Flask(__name__)

# -------------------------
# Google Drive 認証処理
# -------------------------
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
CREDENTIALS_FILE = "credentials.json"  # Google Cloud から取得した認証情報

def get_drive_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("drive", "v3", credentials=creds)

# -------------------------
# Google Drive に保存する関数
# -------------------------
def save_reports_to_drive(report_data):
    """report_data を既存の JSON に追記して、Drive にアップロード"""
    local_file = "reports.json"

    # 既存データを読み込み
    if os.path.exists(local_file):
        with open(local_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []

    # 新しいデータを追加
    data.append(report_data)

    # ローカルに保存
    with open(local_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Google Drive にアップロード
    service = get_drive_service()

    # 同名ファイルが既にあるか確認
    response = service.files().list(q=f"name='{local_file}'", fields="files(id, name)").execute()
    files = response.get("files", [])

    if files:
        # 既存ファイルを更新
        file_id = files[0].get("id")
        media = MediaFileUpload(local_file, mimetype="application/json")
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        # 新規アップロード
        file_metadata = {"name": local_file, "mimeType": "application/json"}
        media = MediaFileUpload(local_file, mimetype="application/json")
        service.files().create(body=file_metadata, media_body=media, fields="id").execute()


# -------------------------
# ルーティング
# -------------------------
@app.route("/")
def index():
    return render_template("index.html")  # 通報フォームのHTML

@app.route("/report", methods=["POST"])
def report():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400

    # Drive に保存
    save_reports_to_drive(data)

    return jsonify({"message": "Report saved successfully!"})


if __name__ == "__main__":
    app.run(debug=True)

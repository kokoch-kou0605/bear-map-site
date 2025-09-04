from flask import Flask, render_template, request, jsonify, session
import uuid
import json
from datetime import datetime
from timezonefinder import TimezoneFinder
import pytz
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

app = Flask(__name__)
app.secret_key = 'a_very_long_and_random_string_that_no_one_can_guess_12345'

CLIENT_ID = "395791546336-2gegvqd4ion6f3jhvjjvjr1mo79mj295.apps.googleusercontent.com"

DATA_FILE = "data.json"
tf = TimezoneFinder()

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

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
    if request.method == 'POST':
        # POSTリクエスト（通報）はログインが必要
        if 'user_id' not in session:
            return jsonify({"error": "Unauthorized"}), 401
            
        locations = load_data()
        data = request.get_json()
        
        data['id'] = str(uuid.uuid4())
        data['user_id'] = session['user_id']
        
        lat = data.get('lat')
        lng = data.get('lng')
        
        data['timestamp'] = get_local_time(lat, lng)

        locations.append(data)
        save_data(locations)
        
        return jsonify(data), 200

    elif request.method == 'GET':
        # GETリクエスト（ピンの取得）は誰でもアクセス可能
        locations = load_data()
        return jsonify(locations), 200

@app.route('/locations/<string:location_id>', methods=['DELETE'])
def delete_location(location_id):
    # DELETEリクエスト（削除）はログインが必要
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    locations = load_data()
    
    index_to_delete = -1
    for i, location in enumerate(locations):
        if location.get('id') == location_id:
            if location.get('user_id') == session['user_id']:
                index_to_delete = i
                break
            else:
                return jsonify({"error": "You do not have permission to delete this location."}), 403
            
    if index_to_delete != -1:
        del locations[index_to_delete]
        save_data(locations)
        return jsonify({"message": "Location deleted successfully"}), 200
    else:
        return jsonify({"error": "Location not found"}), 404

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=81)

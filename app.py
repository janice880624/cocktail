import csv
import gspread
import random
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# 設定 Google Sheets API
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDENTIALS_FILE = "bartendingrecommendations-1180cc105542.json"
SPREADSHEET_ID = "1lU2VR1T9KyBGH-FLNjO4wTLvtH7uqh6CQ0481FVYgh8"

# 讀取 Excel 資料
EXCEL_FILE = "專題.xlsx"

def connect_sheet():
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID)

def load_cocktail_data():
    df = pd.read_csv("cocktails.csv")  # 改成讀取 CSV
    return df

# 根據使用者選擇篩選調酒ㄐ
def recommend_cocktail(concentration, alcohol_feel, taste, bubble):
    df = load_cocktail_data()

    filtered_df = df[
        (df["濃度"] == concentration) &
        (df["酒感"] == alcohol_feel) &
        (df["酸甜"] == taste) &
        (df["氣泡"] == bubble)
    ]

    if filtered_df.empty:
        filtered_df = df[
            (df["濃度"] == concentration) &
            (df["酸甜"] == taste)
        ]

    return filtered_df[["調酒名稱", "基酒-1", "基酒-2", "基酒-3", "基酒-4", "氣泡", "圖片位置"]].to_dict(orient="records")

@app.route('/')
def index():
    return redirect(url_for('login'))  # 🔹 預設先到登入頁

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # 🔹 未登入的話強制回 login
    return render_template("home.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')  # 瀏覽器直接訪問時顯示登入畫面
    
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({"success": False, "message": "Email is required"}), 400

        sheet = connect_sheet()
        users_worksheet = sheet.worksheet("Users")
        users = users_worksheet.get_all_records()

        user_exists = False
        for user in users:
            if user.get("email") == email:  # 避免 KeyError
                session['user_id'] = user.get("id")
                session['email'] = email
                session['name'] = user.get("name", "新用戶")
                user_exists = True
                break

        if not user_exists:
            # 🔍 如果找不到 email，新增至 Google Sheets
            new_user_id = len(users) + 1
            users_worksheet.append_row([new_user_id, email, "新用戶"])
            session['user_id'] = new_user_id
            session['email'] = email
            session['name'] = "新用戶"

        return jsonify({"success": True}), 200

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cocktails = []
    with open("cocktails.csv", newline='', encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            row = {key.strip(): value for key, value in row.items()}  # 去除欄位名稱前後的空格
            print(row)  # 🔍 檢查資料是否正確
            cocktails.append(row)

    return render_template('dashboard.html', name=session['name'], email=session['email'], cocktails=cocktails)

@app.route('/start-recommendation')
def start_recommendation():
    return render_template('cocktail_frontend.html')

@app.route('/history')
def history():
    if 'email' not in session:  # 🔹 確保未登入的使用者無法訪問
        return redirect(url_for('login'))

    user_email = session['email']  # 🔹 取得當前登入的使用者 Email
    sheet = connect_sheet()
    history_worksheet = sheet.worksheet("History")
    all_records = history_worksheet.get_all_values()  # 讀取所有紀錄

    user_records = [row for row in all_records if row[1] == user_email]  # 🔹 過濾出該使用者的紀錄（第2欄是 Email）

    return render_template("history.html", records=user_records)


@app.route('/recommend', methods=['POST'])
def recommend():
    data = request.get_json()
    concentration = data.get('concentration')
    alcohol_feel = data.get('alcohol_feel')
    taste = data.get('taste')
    bubble = data.get('bubble')
    weather = data.get('weather')

    recommendations = recommend_cocktail(concentration, alcohol_feel, taste, bubble)

    cocktails_data = []
    for cocktail in recommendations:
        cocktails_data.append({
            "調酒名稱": cocktail['調酒名稱'],
            "圖片位置": cocktail.get('圖片位置', 'default')  # 確保有預設值
        })

    return render_template('recommendation.html', cocktails=cocktails_data)





cocktail_by_weather = {
    "晴天": [
        {"name": "中國藍", "image": "/static/images/1.jpg"},
        {"name": "螺絲起子", "image": "/static/images/2.jpg"},
        {"name": "自由古巴", "image": "/static/images/3.jpg"},
        {"name": "威士忌可樂", "image": "/static/images/4.jpg"}
    ],
    "陰天": [
        {"name": "龍舌蘭日出", "image": "/static/images/5.jpg"},
        {"name": "馬頸", "image": "/static/images/6.jpg"},
        {"name": "Gin Buck", "image": "/static/images/7.jpg"}
    ],
    "雨天": [
        {"name": "Gin tonic", "image": "/static/images/8.jpg"},
        {"name": "野格炸彈", "image": "/static/images/9.jpg"},
        {"name": "鹹狗", "image": "/static/images/10.jpg"}
    ]
}


@app.route('/weather-recommendation', methods=['GET'])
def weather_recommendation():
    weather = request.args.get("weather")

    if weather not in cocktail_by_weather:
        return jsonify([])

    recommended_cocktails = cocktail_by_weather[weather]  # 直接回傳所有推薦的調酒

    return jsonify(recommended_cocktails)



@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('email', None)
    session.pop('name', None)
    return redirect(url_for('login'))

def handler(event, context):
    return app(event, context)

if __name__ == '__main__':
    app.run(debug=True)

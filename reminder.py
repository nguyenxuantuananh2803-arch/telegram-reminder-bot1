import requests
import json
from datetime import datetime, timedelta
import os

# Cấu hình từ GitHub Secrets
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
SHEET_ID = os.getenv('SHEET_ID')

# URL để lấy dữ liệu từ Google Sheets (dạng CSV)
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

def send_telegram_message(message):
    """Gửi tin nhắn qua Telegram Bot"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"Lỗi gửi tin nhắn: {e}")
        return None

def check_reminders():
    """Kiểm tra công việc cần nhắc hôm nay"""
    try:
        # Đọc dữ liệu từ Google Sheets
        response = requests.get(SHEET_URL)
        lines = response.text.strip().split('\n')
        
        if len(lines) < 2:
            print("Không có dữ liệu trong sheet")
            return
        
        # Bỏ qua dòng header
        headers = lines[0].split(',')
        data_rows = lines[1:]
        
        today = datetime.now().date()
        reminders = []
        
        for row in data_rows:
            cols = row.split(',')
            if len(cols) < 3:
                continue
                
            task = cols[0].strip()
            due_date_str = cols[1].strip()
            remind_before = int(cols[2].strip())
            
            # Chuyển đổi ngày
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            remind_date = due_date - timedelta(days=remind_before)
            
            # Kiểm tra nếu hôm nay là ngày cần nhắc
            if remind_date == today:
                # Kiểm tra trạng thái (nếu có cột status)
                status = cols[3].strip() if len(cols) > 3 else 'pending'
                if status.lower() != 'done':
                    reminders.append({
                        'task': task,
                        'due_date': due_date,
                        'days_before': remind_before
                    })
        
        # Gửi thông báo
        if reminders:
            message = "🔔 <b>NHẮC NHỞ CÔNG VIỆC HÔM NAY</b> 🔔\n\n"
            for r in reminders:
                message += f"📌 <b>{r['task']}</b>\n"
                message += f"   📅 Sẽ đến hạn vào: {r['due_date']}\n"
                message += f"   ⏰ Được nhắc trước: {r['days_before']} ngày\n\n"
            
            send_telegram_message(message)
            print(f"Đã gửi {len(reminders)} thông báo")
        else:
            print("Không có công việc nào cần nhắc hôm nay")
            
    except Exception as e:
        error_msg = f"❌ Lỗi kiểm tra: {str(e)}"
        print(error_msg)
        send_telegram_message(error_msg)

if __name__ == "__main__":
    check_reminders()

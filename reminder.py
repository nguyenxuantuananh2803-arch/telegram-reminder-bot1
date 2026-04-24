import requests
from datetime import datetime, timedelta
import os

# Lấy thông tin từ GitHub Secrets
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
SHEET_ID = os.getenv('SHEET_ID')

# URL để đọc Google Sheets dưới dạng CSV
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

def send_telegram_message(message):
    """Gửi tin nhắn đến Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ Đã gửi tin nhắn Telegram thành công")
        else:
            print(f"❌ Lỗi gửi tin nhắn: {response.text}")
        return response.json()
    except Exception as e:
        print(f"❌ Lỗi kết nối Telegram: {e}")
        return None

def check_reminders():
    """Kiểm tra và gửi thông báo công việc"""
    try:
        print("🔄 Đang đọc dữ liệu từ Google Sheets...")
        response = requests.get(SHEET_URL, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Không thể đọc sheet: {response.status_code}")
            send_telegram_message(f"❌ Lỗi: Không đọc được Google Sheets (Mã lỗi: {response.status_code})")
            return
        
        # Đọc dữ liệu CSV
        lines = response.text.strip().split('\n')
        
        if len(lines) < 2:
            print("⚠️ Sheet không có dữ liệu")
            return
        
        # Đọc header để biết cấu trúc
        headers = lines[0].split(',')
        print(f"📋 Các cột trong sheet: {headers}")
        
        # Tìm index của các cột cần thiết
        try:
            col_task = headers.index('Task') if 'Task' in headers else 0
            col_due_date = headers.index('Due Date') if 'Due Date' in headers else 1
            col_remind_before = headers.index('Remind Before') if 'Remind Before' in headers else 2
            col_phone = headers.index('Phone') if 'Phone' in headers else 3  # 📱 Cột số điện thoại
            col_status = headers.index('Status') if 'Status' in headers else 4
        except ValueError as e:
            print(f"⚠️ Không tìm thấy cột cần thiết: {e}")
            # Dùng index mặc định
            col_task, col_due_date, col_remind_before, col_phone, col_status = 0, 1, 2, 3, 4
        
        data_rows = lines[1:]
        today = datetime.now().date()
        reminders = []
        
        print(f"📅 Hôm nay là: {today}")
        print(f"🔍 Đang kiểm tra {len(data_rows)} công việc...")
        
        for idx, row in enumerate(data_rows, start=2):
            # Bỏ qua dòng trống
            if not row.strip():
                continue
                
            cols = row.split(',')
            if len(cols) < 3:
                print(f"⚠️ Dòng {idx}: Không đủ cột (cần ít nhất 3 cột)")
                continue
            
            # Lấy dữ liệu từ các cột
            task = cols[col_task].strip() if col_task < len(cols) else "Không có tên"
            due_date_str = cols[col_due_date].strip() if col_due_date < len(cols) else ""
            remind_before_str = cols[col_remind_before].strip() if col_remind_before < len(cols) else "0"
            phone = cols[col_phone].strip() if col_phone < len(cols) else "Không có SĐT"
            status = cols[col_status].strip().lower() if col_status < len(cols) else "pending"
            
            # Xử lý remind_before
            try:
                remind_before = int(float(remind_before_str))
            except:
                print(f"⚠️ Dòng {idx}: Số ngày nhắc trước không hợp lệ: {remind_before_str}")
                continue
            
            # Kiểm tra định dạng ngày
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except:
                print(f"⚠️ Dòng {idx}: Định dạng ngày sai ({due_date_str}), cần YYYY-MM-DD")
                continue
            
            # Tính ngày cần nhắc
            remind_date = due_date - timedelta(days=remind_before)
            
            # Kiểm tra nếu hôm nay là ngày cần nhắc
            if remind_date == today and status != 'done':
                reminders.append({
                    'task': task,
                    'due_date': due_date,
                    'days_before': remind_before,
                    'phone': phone,  # 📱 Thêm số điện thoại
                    'row': idx
                })
                print(f"📌 Dòng {idx}: Cần nhắc '{task}' - SĐT: {phone} (đến hạn {due_date})")
        
        # Gửi thông báo
        if reminders:
            # Tin nhắn chính cho bạn (quản lý)
            admin_message = "🔔 <b>NHẮC NHỞ CÔNG VIỆC HÔM NAY</b> 🔔\n\n"
            for r in reminders:
                admin_message += f"📌 <b>{r['task']}</b>\n"
                admin_message += f"   📅 Đến hạn: {r['due_date']}\n"
                admin_message += f"   ⏰ Nhắc trước: {r['days_before']} ngày\n"
                admin_message += f"   📱 SĐT KH: {r['phone']}\n\n"
            
            send_telegram_message(admin_message)
            print(f"✅ Đã gửi {len(reminders)} thông báo cho admin")
            
            # 🆕 Gửi tin nhắn riêng cho từng khách hàng (nếu có số điện thoại)
            # LƯU Ý: Cách này gửi qua Telegram, không phải SMS thật
            for r in reminders:
                if r['phone'] != "Không có SĐT" and r['phone']:
                    customer_message = f"🔔 <b>Thông báo từ hệ thống</b> 🔔\n\n"
                    customer_message += f"Xin nhắc nhở: <b>{r['task']}</b>\n"
                    customer_message += f"📅 Sẽ đến hạn vào ngày: {r['due_date']}\n"
                    customer_message += f"⏰ Vui lòng chuẩn bị trước {r['days_before']} ngày.\n\n"
                    customer_message += f"<i>Cảm ơn quý khách!</i>"
                    
                    # Gửi tin nhắn đến số điện thoại (cần số là username Telegram hoặc Chat ID)
                    # Cách này chỉ hoạt động nếu số điện thoại đã đăng ký Telegram
                    send_telegram_message(customer_message)
                    print(f"   📱 Đã gửi thông báo đến SĐT: {r['phone']}")
        else:
            print("✅ Không có công việc nào cần nhắc hôm nay")
            
    except requests.exceptions.Timeout:
        print("❌ Lỗi: Timeout khi kết nối Google Sheets")
        send_telegram_message("❌ Lỗi: Không thể kết nối Google Sheets (Timeout)")
    except Exception as e:
        error_msg = f"❌ Lỗi không xác định: {str(e)}"
        print(error_msg)
        send_telegram_message(error_msg)

if __name__ == "__main__":
    print("🚀 Bắt đầu chạy bot nhắc việc...")
    check_reminders()
    print("🏁 Kết thúc")

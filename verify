import os
import re
import telebot
import requests
from bs4 import BeautifulSoup
from flask import Flask
from threading import Thread
import logging
from urllib.parse import urljoin
import time
import base64
from io import BytesIO

# ============ লগিং ============
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ ওয়েব সার্ভার ============
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ BDRIS Bot is running with Captcha support!"

@app.route('/health')
def health():
    return "OK", 200

def run_web_server():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ============ টেলিগ্রাম বট ============
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("⚠️ BOT_TOKEN not set!")

bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

# ============ কনফিগারেশন ============
BASE_URL = "https://everify.bdris.gov.bd"
VERIFY_URL = "https://everify.bdris.gov.bd/UBRNVerification/Search"

session = requests.Session()

# ব্যবহারকারীর সেশন ডেটা সংরক্ষণ
user_sessions = {}

# ============ টোকেন ও ক্যাপচা সংগ্রহ ============
def get_initial_data():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        response = session.get(BASE_URL, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # টোকেন
        token = soup.find('input', {'name': '__RequestVerificationToken'})
        if token:
            token_value = token.get('value')
        else:
            token_value = None
        
        # ক্যাপচা ইমেজ URL
        captcha_img = soup.find('img', {'id': 'CaptchaImage'})
        if captcha_img:
            captcha_src = captcha_img.get('src')
            if captcha_src:
                captcha_url = urljoin(BASE_URL, captcha_src)
            else:
                captcha_url = None
        else:
            captcha_url = None
        
        return token_value, captcha_url
        
    except Exception as e:
        logger.error(f"❌ Initial data error: {e}")
        return None, None

def download_captcha_image(captcha_url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": BASE_URL + "/",
        }
        response = session.get(captcha_url, headers=headers, timeout=30)
        return response.content
    except Exception as e:
        logger.error(f"❌ Captcha download error: {e}")
        return None

# ============ জন্ম সনদ যাচাই ============
def verify_birth_certificate(ubrn, dob, captcha_text):
    try:
        token, _ = get_initial_data()
        if not token:
            return "⚠️ টোকেন পাওয়া যায়নি।"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": BASE_URL,
            "Referer": BASE_URL + "/",
        }
        
        # ✅ সঠিক ফর্ম ডেটা (আপনার স্ক্রিনশট থেকে)
        data = {
            "__RequestVerificationToken": token,
            "UBRN": ubrn,
            "BirthDate": dob,  # ⚠️ এখানে "DOB" না হয়ে "BirthDate"
            "CaptchaDeText": "",  # খালি রাখতে হবে
            "CaptchaInputText": captcha_text  # ব্যবহারকারীর দেওয়া ক্যাপচা
        }

        logger.info(f"🔍 Verifying: {ubrn}, {dob}")
        
        response = session.post(
            VERIFY_URL, 
            headers=headers, 
            data=data, 
            allow_redirects=True,
            timeout=30
        )
        
        logger.info(f"📡 Status: {response.status_code}")
        
        if response.status_code == 200:
            text = response.text.lower()
            
            if "not match" in text or "মিলেনি" in text:
                return "❌ **Not Match**\n\nসঠিক তথ্য পাওয়া যায়নি।"
            
            if "মিলেছে" in text or "found" in text or "সঠিক" in text:
                soup = BeautifulSoup(response.text, 'html.parser')
                info = {'name': 'পাওয়া যায়নি', 'father': 'পাওয়া যায়নি', 'mother': 'পাওয়া যায়নি'}
                
                for tag in soup.find_all(['td', 'th']):
                    if re.search(r'নাম|Name', tag.get_text(), re.I):
                        next_tag = tag.find_next(['td', 'th'])
                        if next_tag:
                            info['name'] = next_tag.get_text(strip=True)
                    elif re.search(r'পিতা|Father', tag.get_text(), re.I):
                        next_tag = tag.find_next(['td', 'th'])
                        if next_tag:
                            info['father'] = next_tag.get_text(strip=True)
                    elif re.search(r'মাতা|Mother', tag.get_text(), re.I):
                        next_tag = tag.find_next(['td', 'th'])
                        if next_tag:
                            info['mother'] = next_tag.get_text(strip=True)
                
                return f"""✅ **জন্ম সনদ সঠিক!** 🎉

👤 **নাম:** {info['name']}
👨 **পিতা:** {info['father']}
👩 **মাতা:** {info['mother']}
📋 **UBRN:** {ubrn}
📅 **জন্ম তারিখ:** {dob}

✅ তথ্য যাচাইকৃত।"""
            
            return "⚠️ **অস্পষ্ট উত্তর**। আবার চেষ্টা করুন।"
        else:
            return f"⚠️ সার্ভার ত্রুটি: {response.status_code}"
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return f"⚠️ ত্রুটি: {e}"

# ============ টেলিগ্রাম কমান্ড ============
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = """🎯 **BDRIS জন্ম সনদ যাচাই বট** 🇧🇩

আমি বাংলাদেশের জন্ম সনদ যাচাই করতে সাহায্য করি।

📌 **কীভাবে ব্যবহার করবেন:**
`/verify ১৭অঙ্কেরUBRN জন্মতারিখ`

📝 **উদাহরণ:**
`/verify 20053513211024127 2005-01-01`

⚠️ **সতর্কতা:**
• UBRN নম্বর ১৭ অঙ্কের হতে হবে
• তারিখ YYYY-MM-DD ফরম্যাটে দিন (যেমন: 2005-01-01)
• ক্যাপচা সমাধান করতে হবে

🤖 **ডেভেলপার:** @amarbaribot"""
    
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['verify'])
def verify_command(message):
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) != 3:
            bot.reply_to(message, 
                "⚠️ **সঠিক ফরম্যাট ব্যবহার করুন:**\n"
                "`/verify UBRN তারিখ`\n\n"
                "📌 উদাহরণ: `/verify 20053513211024127 2005-01-01`",
                parse_mode='Markdown')
            return
        
        ubrn = parts[1].strip()
        dob = parts[2].strip()
        
        if len(ubrn) != 17 or not ubrn.isdigit():
            bot.reply_to(message, "⚠️ UBRN নম্বর **১৭ অঙ্কের** হতে হবে।")
            return
        
        # ক্যাপচা ইমেজ সংগ্রহ
        processing_msg = bot.reply_to(message, "⏳ **ক্যাপচা সংগ্রহ করা হচ্ছে...**", parse_mode='Markdown')
        
        token, captcha_url = get_initial_data()
        if not captcha_url:
            bot.edit_message_text(
                "⚠️ ক্যাপচা সংগ্রহ করা যায়নি। দয়া করে আবার চেষ্টা করুন।",
                chat_id=message.chat.id,
                message_id=processing_msg.message_id
            )
            return
        
        captcha_img = download_captcha_image(captcha_url)
        if not captcha_img:
            bot.edit_message_text(
                "⚠️ ক্যাপচা ইমেজ ডাউনলোড করা যায়নি।",
                chat_id=message.chat.id,
                message_id=processing_msg.message_id
            )
            return
        
        # ক্যাপচা ইমেজ টেলিগ্রামে পাঠান
        bot.edit_message_text(
            "📸 **নিচের ক্যাপচা টাইপ করুন:**",
            chat_id=message.chat.id,
            message_id=processing_msg.message_id,
            parse_mode='Markdown'
        )
        
        bot.send_photo(message.chat.id, captcha_img)
        
        # ব্যবহারকারীর রেসপন্সের জন্য অপেক্ষা
        bot.send_message(
            message.chat.id,
            "⌨️ **ক্যাপচা টেক্সট লিখুন:**",
            parse_mode='Markdown'
        )
        
        # পরবর্তী মেসেজ ক্যাপচা হিসেবে নেওয়ার জন্য রেজিস্টার
        user_sessions[message.chat.id] = {'ubrn': ubrn, 'dob': dob, 'step': 'captcha'}
        
    except Exception as e:
        logger.error(f"❌ Command error: {e}")
        bot.reply_to(message, f"⚠️ ত্রুটি: {str(e)}")

@bot.message_handler(func=lambda message: True)
def handle_captcha_response(message):
    chat_id = message.chat.id
    
    if chat_id in user_sessions and user_sessions[chat_id].get('step') == 'captcha':
        session_data = user_sessions[chat_id]
        captcha_text = message.text.strip()
        
        if not captcha_text:
            bot.reply_to(message, "⚠️ দয়া করে ক্যাপচা টাইপ করুন।")
            return
        
        # যাচাই করা
        msg = bot.reply_to(message, "⏳ **যাচাই করা হচ্ছে...**", parse_mode='Markdown')
        
        result = verify_birth_certificate(
            session_data['ubrn'], 
            session_data['dob'], 
            captcha_text
        )
        
        bot.edit_message_text(
            result, 
            chat_id=chat_id, 
            message_id=msg.message_id,
            parse_mode='Markdown'
        )
        
        # সেশন ক্লিয়ার
        del user_sessions[chat_id]
    else:
        bot.reply_to(message, 
            "🤔 **আমি বুঝতে পারিনি।**\n\n"
            "📌 সাহায্যের জন্য `/help` বা `/start` লিখুন।\n"
            "📌 জন্ম সনদ যাচাই করতে `/verify UBRN তারিখ` লিখুন।",
            parse_mode='Markdown'
        )

# ============ মেইন ============
if __name__ == '__main__':
    logger.info("🚀 BDRIS Bot starting with Captcha support...")
    
    web_thread = Thread(target=run_web_server, daemon=True)
    web_thread.start()
    logger.info(f"🌐 Web server running on port {os.environ.get('PORT', 5000)}")
    
    logger.info("🤖 Bot polling started...")
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot polling error: {e}")
        raise

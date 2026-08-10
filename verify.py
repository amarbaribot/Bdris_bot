import os
import telebot
import requests
from bs4 import BeautifulSoup
from flask import Flask
from threading import Thread
import time
import logging

# ============ লগিং সেটআপ ============
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ ওয়েব সার্ভার (Render-এর পোর্ট সমস্যা সমাধানে) ============
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ BDRIS Birth Certificate Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

def run_web_server():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ============ টেলিগ্রাম বট ============
BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    logger.error("⚠️ BOT_TOKEN environment variable is not set!")
    raise ValueError("⚠️ BOT_TOKEN environment variable is not set!")

bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()  # Webhook সরিয়ে Polling ব্যবহারের জন্য

# ============ ওয়েবসাইট কনফিগারেশন ============
BASE_URL = "https://everify.bdris.gov.bd"
VERIFY_URL = "https://everify.bdris.gov.bd/UBRNVerification/Search"

session = requests.Session()

# ============ টোকেন সংগ্রহ ফাংশন ============
def get_initial_tokens():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        response = session.get(BASE_URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # টোকেন খোঁজা
        token_input = soup.find('input', {'name': '__RequestVerificationToken'})
        if token_input:
            token = token_input.get('value')
            logger.info("✅ Verification token collected successfully")
            return token
        
        # অথবা কুকি থেকে টোকেন খোঁজা
        for cookie in session.cookies:
            if cookie.name == '__RequestVerificationToken':
                logger.info("✅ Token found in cookies")
                return cookie.value
        
        logger.warning("⚠️ No verification token found")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Connection error: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return None

# ============ জন্ম সনদ যাচাই ফাংশন ============
def verify_birth_certificate(ubrn, dob):
    try:
        # টোকেন সংগ্রহ
        token = get_initial_tokens()
        if not token:
            return "⚠️ সার্ভার থেকে টোকেন সংগ্রহ করা যায়নি। দয়া করে কিছুক্ষণ পর চেষ্টা করুন।"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": BASE_URL,
            "Referer": BASE_URL + "/",
            "Connection": "keep-alive",
        }

        data = {
            "__RequestVerificationToken": token,
            "UBRN": ubrn,
            "DOB": dob
        }

        logger.info(f"🔍 Verifying UBRN: {ubrn}, DOB: {dob}")
        
        response = session.post(
            VERIFY_URL, 
            headers=headers, 
            data=data, 
            allow_redirects=True,
            timeout=30
        )
        
        logger.info(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            # সফল রেসপন্স চেক
            response_text = response.text.lower()
            
            if any(keyword in response_text for keyword in ['মিলেছে', 'পাওয়া গেছে', 'found', 'match', 'certificate', 'নিবন্ধন']):
                # নাম ইত্যাদি বের করার চেষ্টা
                soup = BeautifulSoup(response.text, 'html.parser')
                name_tag = soup.find('td', string=re.compile(r'নাম|Name', re.I))
                if name_tag:
                    value_tag = name_tag.find_next('td')
                    if value_tag:
                        name = value_tag.get_text(strip=True)
                        return f"✅ **জন্ম সনদ সঠিক!**\n\n👤 নাম: {name}\n\n💡 তথ্য যাচাইকৃত।"
                
                return "✅ **Birth Certificate Ok**\n\nআপনার জন্ম সনদ সঠিক।"
            else:
                return "❌ **Not Match**\n\nআপনার প্রদত্ত তথ্যের সাথে কোনো জন্ম সনদ মিলেনি।"
        else:
            return f"⚠️ সার্ভার ত্রুটি (স্ট্যাটাস: {response.status_code})। দয়া করে পরে চেষ্টা করুন।"
            
    except requests.exceptions.Timeout:
        return "⏰ সার্ভার থেকে উত্তর আসতে সময় বেশি লাগছে। দয়া করে আবার চেষ্টা করুন।"
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request error: {e}")
        return f"⚠️ সংযোগ সমস্যা: {str(e)}"
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return f"⚠️ অজানা ত্রুটি: {str(e)}"

# ============ টেলিগ্রাম কমান্ড হ্যান্ডলার ============
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = """🎯 **BDRIS জন্ম সনদ যাচাই বট** 🇧🇩

আমি বাংলাদেশের জন্ম সনদ যাচাই করতে সাহায্য করি।

📌 **কীভাবে ব্যবহার করবেন:**
`/verify ১৭অঙ্কেরUBRN জন্মতারিখ`

📝 **উদাহরণ:**
`/verify 12345678901234567 01/01/2000`

⚠️ **সতর্কতা:**
• UBRN নম্বর ১৭ অঙ্কের হতে হবে
• তারিখ dd/mm/yyyy ফরম্যাটে দিন
• শুধুমাত্র নিজের তথ্য যাচাই করুন

🤖 **ডেভেলপার:** @amarbaribot"""
    
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['verify'])
def verify_command(message):
    try:
        # কমান্ড থেকে ডেটা আলাদা করা
        parts = message.text.split(maxsplit=2)
        
        if len(parts) != 3:
            bot.reply_to(message, 
                "⚠️ **সঠিক ফরম্যাট ব্যবহার করুন:**\n"
                "`/verify UBRN তারিখ`\n\n"
                "📌 উদাহরণ: `/verify 12345678901234567 01/01/2000`",
                parse_mode='Markdown')
            return
        
        ubrn = parts[1].strip()
        dob = parts[2].strip()
        
        # মৌলিক যাচাই
        if len(ubrn) != 17 or not ubrn.isdigit():
            bot.reply_to(message, "⚠️ UBRN নম্বর **১৭ অঙ্কের** হতে হবে।")
            return
        
        # যদি UBRN ১৭ অঙ্কের না হয়
        if len(ubrn) > 17:
            ubrn = ubrn[:17]  # প্রথম ১৭ অঙ্ক নিন
            
        # প্রক্রিয়াকরণ শুরু
        processing_msg = bot.reply_to(message, "⏳ **যাচাই করা হচ্ছে...** দয়া করে অপেক্ষা করুন।", parse_mode='Markdown')
        
        # যাচাই করুন
        result = verify_birth_certificate(ubrn, dob)
        
        # উত্তর দিন
        bot.edit_message_text(
            result, 
            chat_id=message.chat.id, 
            message_id=processing_msg.message_id,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"❌ Command error: {e}")
        bot.reply_to(message, f"⚠️ ত্রুটি: {str(e)}")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, 
        "🤔 আমি বুঝতে পারিনি।\n\n"
        "📌 সাহায্যের জন্য `/help` বা `/start` লিখুন।\n"
        "📌 জন্ম সনদ যাচাই করতে `/verify UBRN তারিখ` লিখুন।")

# ============ মেইন ফাংশন ============
if __name__ == '__main__':
    logger.info("🚀 BDRIS Bot starting...")
    
    # ওয়েব সার্ভার চালু (Render-এর জন্য)
    web_thread = Thread(target=run_web_server, daemon=True)
    web_thread.start()
    logger.info(f"🌐 Web server running on port {os.environ.get('PORT', 5000)}")
    
    # বট চালু
    logger.info("🤖 Bot polling started...")
    
    try:
        # পোলিং শুরু
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot polling error: {e}")
        raise

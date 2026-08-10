import os
import re
import telebot
import requests
from bs4 import BeautifulSoup
from flask import Flask
from threading import Thread
import logging
import time

# ============ লগিং সেটআপ ============
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ ওয়েব সার্ভার ============
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
bot.remove_webhook()

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
        
        token_input = soup.find('input', {'name': '__RequestVerificationToken'})
        if token_input:
            token = token_input.get('value')
            logger.info("✅ Verification token collected successfully")
            return token
        
        for cookie in session.cookies:
            if cookie.name == '__RequestVerificationToken':
                logger.info("✅ Token found in cookies")
                return cookie.value
        
        logger.warning("⚠️ No verification token found")
        return None
        
    except Exception as e:
        logger.error(f"❌ Token error: {e}")
        return None

# ============ জন্ম সনদ যাচাই ফাংশন ============
def verify_birth_certificate(ubrn, dob):
    try:
        token = get_initial_tokens()
        if not token:
            return "⚠️ সার্ভার থেকে টোকেন সংগ্রহ করা যায়নি। দয়া করে কিছুক্ষণ পর চেষ্টা করুন।", None

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
        
        # ⚠️ রেসপন্সের সম্পূর্ণ HTML লগ করুন (ডিবাগের জন্য)
        logger.info(f"📄 Response length: {len(response.text)} characters")
        
        # ⚠️ চেক করুন: রেসপন্সে "Not Match" আছে কিনা
        response_lower = response.text.lower()
        
        # 🚨 সবচেয়ে গুরুত্বপূর্ণ: Not Match চেক করুন
        if "not match" in response_lower or "মিলেনি" in response_lower or "সঠিক নয়" in response_lower:
            logger.info("❌ Not Match detected")
            return "❌ **Not Match**\n\nআপনার প্রদত্ত তথ্যের সাথে কোনো জন্ম সনদ মিলেনি।\n\n💡 সম্ভাব্য কারণ:\n• UBRN নম্বর ভুল\n• জন্ম তারিখ ভুল\n• সনদটি ডাটাবেসে নেই", None
        
        # ✅ Match চেক করুন
        if any(keyword in response_lower for keyword in ['মিলেছে', 'পাওয়া গেছে', 'found', 'match', 'সঠিক']):
            logger.info("✅ Match detected")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # তথ্য সংগ্রহ
            name = "খুঁজে পাওয়া যায়নি"
            father = "খুঁজে পাওয়া যায়নি"
            mother = "খুঁজে পাওয়া যায়নি"
            
            # নাম খোঁজা
            name_patterns = [
                soup.find('td', string=re.compile(r'নাম', re.I)),
                soup.find('td', string=re.compile(r'Name', re.I)),
                soup.find('th', string=re.compile(r'নাম', re.I)),
                soup.find('th', string=re.compile(r'Name', re.I))
            ]
            
            for pattern in name_patterns:
                if pattern:
                    # next td বা th খোঁজা
                    next_elem = pattern.find_next('td')
                    if not next_elem:
                        next_elem = pattern.find_next('th')
                    if next_elem:
                        name = next_elem.get_text(strip=True)
                        break
            
            # পিতা খোঁজা
            father_tag = soup.find('td', string=re.compile(r'পিতা|Father', re.I))
            if father_tag:
                next_elem = father_tag.find_next('td')
                if not next_elem:
                    next_elem = father_tag.find_next('th')
                if next_elem:
                    father = next_elem.get_text(strip=True)
            
            # মাতা খোঁজা
            mother_tag = soup.find('td', string=re.compile(r'মাতা|Mother', re.I))
            if mother_tag:
                next_elem = mother_tag.find_next('td')
                if not next_elem:
                    next_elem = mother_tag.find_next('th')
                if next_elem:
                    mother = next_elem.get_text(strip=True)
            
            # তথ্য সংরক্ষণ
            info = {
                'name': name,
                'father': father,
                'mother': mother,
                'ubrn': ubrn,
                'dob': dob
            }
            
            return "✅ **জন্ম সনদ সঠিক!** 🎉", info
        
        # যদি কিছুই না পাওয়া যায়
        logger.warning("⚠️ Unknown response format")
        return "⚠️ **সার্ভার থেকে অস্পষ্ট উত্তর পাওয়া গেছে।**\n\nদয়া করে আবার চেষ্টা করুন।", None
            
    except Exception as e:
        logger.error(f"❌ Verification error: {e}")
        return f"⚠️ ত্রুটি: {str(e)}", None

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
        
        if len(ubrn) != 17 or not ubrn.isdigit():
            bot.reply_to(message, "⚠️ UBRN নম্বর **১৭ অঙ্কের** হতে হবে।")
            return
        
        processing_msg = bot.reply_to(message, "⏳ **যাচাই করা হচ্ছে...** দয়া করে অপেক্ষা করুন।", parse_mode='Markdown')
        
        result, info = verify_birth_certificate(ubrn, dob)
        
        if info:
            # সঠিক তথ্য পাওয়া গেলে বিস্তারিত দেখান
            response_text = f"""✅ **জন্ম সনদ সঠিক!** 🎉

👤 **নাম:** {info['name']}
👨 **পিতা:** {info['father']}
👩 **মাতা:** {info['mother']}
📋 **UBRN:** {info['ubrn']}
📅 **জন্ম তারিখ:** {info['dob']}

✅ তথ্য যাচাইকৃত।"""
            bot.edit_message_text(
                response_text, 
                chat_id=message.chat.id, 
                message_id=processing_msg.message_id,
                parse_mode='Markdown'
            )
        else:
            # Not Match বা ত্রুটি
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

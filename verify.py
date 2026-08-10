
import telebot
import requests
from bs4 import BeautifulSoup
import re

# আপনার টেলিগ্রাম বটের টোকেন দিন
BOT_TOKEN = "আপনার_টেলিগ্রাম_বট_টোকেন"
bot = telebot.TeleBot(BOT_TOKEN)

# ওয়েবসাইটের ঠিকানা
BASE_URL = "https://everify.bdris.gov.bd"
VERIFY_URL = "https://everify.bdris.gov.bd/UBRNVerification/Search"

# সেশন তৈরি করুন (কুকি ও হেডার সংরক্ষণের জন্য)
session = requests.Session()

# প্রথমে হোমপেজে GET অনুরোধ করুন (কুকি ও টোকেন পেতে)
def get_initial_tokens():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
        }
        response = session.get(BASE_URL, headers=headers)
        response.raise_for_status()
        
        # __RequestVerificationToken খুঁজে বের করা
        soup = BeautifulSoup(response.text, 'html.parser')
        token_input = soup.find('input', {'name': '__RequestVerificationToken'})
        if token_input:
            return token_input.get('value')
        else:
            # যদি না পাওয়া যায়, তবে কুকি থেকে বের করার চেষ্টা
            for cookie in session.cookies:
                if cookie.name == '__RequestVerificationToken':
                    return cookie.value
        return None
    except Exception as e:
        print(f"টোকেন পেতে সমস্যা: {e}")
        return None

# জন্ম নিবন্ধন যাচাই ফাংশন
def verify_birth_certificate(ubrn, dob):
    try:
        # ১. নতুন সেশন ও টোকেন সংগ্রহ
        token = get_initial_tokens()
        if not token:
            return "⚠️ প্রাথমিক টোকেন সংগ্রহ করা যায়নি।"

        # ২. POST অনুরোধের জন্য হেডার ও ডেটা প্রস্তুত
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": BASE_URL,
            "Referer": BASE_URL + "/",
            "Cache-Control": "max-age=0",
            "Upgrade-Insecure-Requests": "1"
        }

        # ফর্ম ডেটা (এটি সঠিক ফরম্যাটে দিতে হবে)
        data = {
            "__RequestVerificationToken": token,
            "UBRN": ubrn,  # ১৭ অঙ্কের নম্বর
            "DOB": dob     # তারিখের ফরম্যাট: dd/mm/yyyy অথবা সাইট যেভাবে নেয়
        }

        # ৩. POST অনুরোধ পাঠান
        response = session.post(VERIFY_URL, headers=headers, data=data, allow_redirects=True)
        
        # ৪. প্রতিক্রিয়া বিশ্লেষণ
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # সাফল্যের বার্তা খুঁজুন (সাইটের ডিজাইন অনুযায়ী পরিবর্তন করতে হবে)
            if "মিলেছে" in response.text or "পাওয়া গেছে" in response.text or "Birth Certificate" in response.text:
                # সফল হলে বিস্তারিত দেখান (যেমন নাম, পিতা-মাতা)
                name_tag = soup.find('td', string='নাম') or soup.find('td', string='Name')
                if name_tag:
                    value_tag = name_tag.find_next('td')
                    if value_tag:
                        return f"✅ জন্ম সনদ সঠিক।\n\nবিস্তারিত তথ্য:\n{value_tag.get_text(strip=True)}"
                return "✅ Birth Certificate Ok"
            else:
                return "❌ Not Match / জন্ম সনদ মিলেনি।"
        else:
            return f"⚠️ সার্ভার ত্রুটি (স্ট্যাটাস: {response.status_code})। আবার চেষ্টা করুন।"

    except requests.exceptions.RequestException as e:
        return f"⚠️ সংযোগ সমস্যা: {e}"
    except Exception as e:
        return f"⚠️ অজানা ত্রুটি: {e}"

# টেলিগ্রাম বট হ্যান্ডলার
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, 
        "🎯 **বাংলাদেশ জন্ম সনদ যাচাই বট**\n\n"
        "আপনার জন্ম সনদের ১৭ অঙ্কের UBRN নম্বর ও জন্ম তারিখ (dd/mm/yyyy) দিন।\n"
        "ফরম্যাট: `/verify 12345678901234567 01/01/2000`\n\n"
        "উদাহরণ: `/verify 12345678901234567 31/12/1990`",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['verify'])
def verify_command(message):
    try:
        # কমান্ড থেকে ডেটা আলাদা করা
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "⚠️ সঠিক ফরম্যাট ব্যবহার করুন:\n`/verify UBRN তারিখ`")
            return
        
        ubrn = parts[1].strip()
        dob = parts[2].strip()
        
        # মৌলিক যাচাই
        if len(ubrn) != 17 or not ubrn.isdigit():
            bot.reply_to(message, "⚠️ UBRN নম্বর ১৭ অঙ্কের হতে হবে।")
            return
        
        # যাচাই শুরু
        status_msg = bot.reply_to(message, "⏳ যাচাই করা হচ্ছে, দয়া করে অপেক্ষা করুন...")
        
        result = verify_birth_certificate(ubrn, dob)
        
        # উত্তর দিন
        bot.edit_message_text(result, chat_id=message.chat.id, message_id=status_msg.message_id)
    
    except Exception as e:
        bot.reply_to(message, f"⚠️ ত্রুটি: {str(e)}")

# বট চালু করুন
print("বট চালু হচ্ছে...")
bot.polling()

# বাংলাদেশ জন্ম সনদ যাচাই টেলিগ্রাম বট

একটি টেলিগ্রাম বট যা `everify.bdris.gov.bd` থেকে জন্ম সনদের তথ্য যাচাই করে।

## কমান্ডসমূহ
- `/start` - বট চালু করুন
- `/help` - সাহায্য দেখুন
- `/verify UBRN তারিখ` - জন্ম সনদ যাচাই করুন (যেমন: `/verify 12345678901234567 01/01/2000`)

## ডিপ্লয়মেন্ট
Render-এ ডিপ্লয় করতে:
1. এই রিপোজিটরি Render-এ সংযুক্ত করুন
2. Environment Variable হিসেবে `BOT_TOKEN` সেট করুন
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python bot.py`

## প্রযুক্তি
- Python 3.9+
- pyTelegramBotAPI
- Requests
- BeautifulSoup4
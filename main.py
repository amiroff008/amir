import telebot
import json
import os
import threading
import time
from telebot import types

API_TOKEN = '7510160668:AAFwLDIoSO9nQtc0fECKLUF5f5f_mSCZYww'
DEST_CHANNEL = -1002678267779
DEFAULT_CAPTION = "#meme\n𝗝𝗼𝗶𝗻 𝘂𝘀:\n@Rubi_Meme | روبی میم"
GROUP_ID = -1002372101814  # آیدی گروه برای ارسال پیام

OWNER_ID = 5910048772
ADMINS_FILE = "admins.json"
admins = set()

# وضعیت موقتی برای مدیریت اضافه/حذف
admin_actions = {}
media_to_send = {}

# ------------------ مدیریت فایل ادمین ------------------

def load_admins():
    if not os.path.exists(ADMINS_FILE):
        return {OWNER_ID}
    with open(ADMINS_FILE, "r") as f:
        return set(json.load(f))

def save_admins(admin_set):
    with open(ADMINS_FILE, "w") as f:
        json.dump(list(admin_set), f)

admins = load_admins()

# ------------------ راه‌اندازی ربات ------------------

bot = telebot.TeleBot(API_TOKEN)

@bot.message_handler(commands=['add', 'remove', 'list'])
def admin_control(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "شما اجازه استفاده از این دستور را ندارید.")
        return

    if message.text.startswith("/add"):
        admin_actions[message.from_user.id] = "add"
        bot.reply_to(message, "لطفاً آیدی عددی کاربر مورد نظر برای افزودن را ارسال کنید.")

    elif message.text.startswith("/remove"):
        admin_actions[message.from_user.id] = "remove"
        bot.reply_to(message, "لطفاً آیدی عددی کاربر مورد نظر برای حذف را ارسال کنید.")

    elif message.text.startswith("/list"):
        result = []
        for admin_id in admins:
            try:
                user = bot.get_chat(admin_id)
                if user.username:
                    display = f"@{user.username}"
                else:
                    name = (user.first_name or "") + " " + (user.last_name or "")
                    name = name.strip()
                    display = f"<a href='tg://user?id={admin_id}'>{name}</a>"
            except:
                display = "نامشخص"
            result.append(f"{admin_id} - {display}")
        bot.reply_to(message, "لیست ادمین‌های فعال:\n" + '\n'.join(result), parse_mode="HTML")

# ------------------ مدیریت ارسال آیدی بعد از /add یا /remove ------------------

@bot.message_handler(func=lambda m: m.from_user.id == OWNER_ID and m.text.isdigit())
def handle_admin_action(message):
    user_id = int(message.text)
    action = admin_actions.get(message.from_user.id)

    if not action:
        return  # اگر دستور قبلاً داده نشده بود، کاری نکن

    if action == "add":
        if user_id in admins:
            bot.reply_to(message, "این کاربر هم‌اکنون ادمین است.")
        else:
            admins.add(user_id)
            save_admins(admins)
            bot.reply_to(message, f"✅ کاربر {user_id} به لیست ادمین‌ها اضافه شد.")
    elif action == "remove":
        if user_id == OWNER_ID:
            bot.reply_to(message, "نمی‌توانید خودتان را حذف کنید.")
        elif user_id not in admins:
            bot.reply_to(message, "این کاربر ادمین نیست.")
        else:
            admins.remove(user_id)
            save_admins(admins)
            bot.reply_to(message, f"❌ کاربر {user_id} از لیست ادمین‌ها حذف شد.")

    admin_actions.pop(message.from_user.id, None)

# ------------------ مدیریت محتوای مجاز ------------------

@bot.message_handler(content_types=['photo', 'video', 'audio'])
def handle_media_content(message):
    if message.chat.type != "private":
        return

    if message.from_user.id not in admins:
        bot.reply_to(message, "شما اجازه استفاده از این ربات را ندارید.")
        return

    # ذخیره‌ی اطلاعات پست موقتاً
    media_to_send[message.from_user.id] = {
        'media': message,
        'caption_required': True
    }

    # ساخت دکمه‌های شیشه‌ای برای انتخاب کپشن
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("کپشن پیش‌فرض", callback_data="default_caption"))
    markup.add(types.InlineKeyboardButton("کپشن دلخواه", callback_data="custom_caption"))

    # درخواست انتخاب از کاربر
    bot.reply_to(message, "لطفاً انتخاب کنید که آیا می‌خواهید کپشن پیش‌فرض آپلود شود یا کپشن دلخواه خودتان را وارد کنید.", reply_markup=markup)

# ------------------ مدیریت انتخاب کپشن ------------------

@bot.callback_query_handler(func=lambda call: call.data in ['default_caption', 'custom_caption'])
def handle_caption_choice(call):
    user_id = call.from_user.id

    if user_id in media_to_send:
        media_info = media_to_send[user_id]
        media = media_info['media']

        if call.data == "default_caption":
            caption = DEFAULT_CAPTION
        else:
            bot.send_message(user_id, "لطفاً کپشن دلخواه خود را وارد کنید.")
            media_to_send[user_id]['caption_required'] = False  # علامت‌گذاری که باید منتظر کپشن دلخواه بمانیم
            bot.delete_message(call.message.chat.id, call.message.message_id)
            return

        if media.photo:
            bot.send_photo(DEST_CHANNEL, media.photo[-1].file_id, caption=caption)
        elif media.video:
            bot.send_video(DEST_CHANNEL, media.video.file_id, caption=caption)
        elif media.audio:
            bot.send_audio(DEST_CHANNEL, media.audio.file_id, caption=caption)

        bot.reply_to(call.message, "پست با موفقیت ارسال شد.")
        bot.delete_message(call.message.chat.id, call.message.message_id)

        media_to_send.pop(user_id, None)

# ------------------ دریافت کپشن دلخواه ------------------

@bot.message_handler(func=lambda message: message.from_user.id in media_to_send and not media_to_send[message.from_user.id]['caption_required'])
def handle_custom_caption(message):
    user_id = message.from_user.id
    caption = message.text.strip()

    media_info = media_to_send.pop(user_id, None)
    media = media_info['media']

    if media.photo:
        bot.send_photo(DEST_CHANNEL, media.photo[-1].file_id, caption=caption)
    elif media.video:
        bot.send_video(DEST_CHANNEL, media.video.file_id, caption=caption)
    elif media.audio:
        bot.send_audio(DEST_CHANNEL, media.audio.file_id, caption=caption)

    bot.reply_to(message, "پست با موفقیت ارسال شد.")
    bot.delete_message(message.chat.id, message.message_id)

# ------------------ ارسال خودکار پیام در گروه ------------------

def auto_send_dot():
    while True:
        try:
            bot.send_message(GROUP_ID, ".")
        except Exception as e:
            print(f"خطا در ارسال پیام: {e}")
        time.sleep(30)  # تغییر زمان از 45 ثانیه به 30 ثانیه

# شروع ترد ارسال خودکار پیام
threading.Thread(target=auto_send_dot, daemon=True).start()

# ------------------ شروع ربات ------------------

bot.polling()

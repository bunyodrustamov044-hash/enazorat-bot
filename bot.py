

import os
import json
import logging
import asyncio
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters,
    ContextTypes
)
from telegram.constants import ParseMode
import anthropic

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8603347074:AAHYWfN-gvW_NyJ9LZ3jfSbcTA-e_DUZLYE"
ADMIN_CHAT_ID = 8273323821
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

(
    CHOOSE_DEPARTMENT,
    ENTER_NAME,
    ENTER_PHONE,
    ENTER_REGION,
    CHOOSE_TYPE,
    ENTER_SUBJECT,
    ENTER_MESSAGE,
    CHOOSE_PRIORITY,
    CONFIRM,
    ADMIN_REPLY,
) = range(10)

messages_db = {}
message_counter = 0

def save_message(data: dict) -> str:
    global message_counter
    message_counter += 1
    msg_id = f"EN-{message_counter:06d}"
    data["id"] = msg_id
    data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["status"] = "yangi"
    messages_db[msg_id] = data
    return msg_id

def get_all_messages():
    return list(messages_db.values())

def get_message(msg_id: str):
    return messages_db.get(msg_id)

def update_message_status(msg_id: str, status: str):
    if msg_id in messages_db:
        messages_db[msg_id]["status"] = status

DEPARTMENTS = {
    "hokimiyat": "🏛️ Hokimiyat",
    "politsiya": "🚔 Politsiya",
    "talim": "🎓 Ta'lim",
    "soliq": "📋 Soliq",
    "tibbiyot": "🏥 Tibbiyot",
    "kommunal": "🔧 Kommunal",
}

TYPES = {
    "shikoyat": "😤 Shikoyat",
    "taklif": "💡 Taklif",
    "sorov": "❓ So'rov",
    "maqtov": "👏 Maqtov",
    "muammo": "⚠️ Muammo",
}

PRIORITIES = {
    "oddiy": "🟢 Oddiy",
    "muhim": "🟡 Muhim",
    "shoshilinch": "🔴 Shoshilinch",
}

REGIONS = [
    "Toshkent shahri", "Toshkent viloyati", "Samarqand viloyati",
    "Farg'ona viloyati", "Andijon viloyati", "Namangan viloyati",
    "Buxoro viloyati", "Xorazm viloyati", "Qashqadaryo viloyati",
    "Surxondaryo viloyati", "Jizzax viloyati", "Sirdaryo viloyati",
    "Navoiy viloyati", "Qoraqalpog'iston Respublikasi",
]

async def ai_analyze(text: str, msg_type: str) -> str:
    if not ANTHROPIC_API_KEY:
        return "AI tahlil uchun API kalit sozlanmagan."
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=500,
            messages=[{"role": "user", "content": f"Quyidagi fuqaro murojaatini o'zbek tilida qisqa tahlil qiling:\nTur: {msg_type}\nMatn: {text}\n\n1. Asosiy muammo nima?\n2. Ustuvorlik (past/o'rta/yuqori)?\n3. Tavsiya?"}]
        )
        return message.content[0].text
    except Exception as e:
        return f"AI tahlil amalga oshmadi: {str(e)[:100]}"

def make_dept_keyboard():
    buttons = []
    row = []
    for key, val in DEPARTMENTS.items():
        row.append(InlineKeyboardButton(val, callback_data=f"dept_{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

def make_type_keyboard():
    buttons = [[InlineKeyboardButton(v, callback_data=f"type_{k}")] for k, v in TYPES.items()]
    return InlineKeyboardMarkup(buttons)

def make_priority_keyboard():
    buttons = [[InlineKeyboardButton(v, callback_data=f"prio_{k}")] for k, v in PRIORITIES.items()]
    return InlineKeyboardMarkup(buttons)

def make_region_keyboard():
    buttons = []
    for i in range(0, len(REGIONS), 2):
        row = [KeyboardButton(REGIONS[i])]
        if i + 1 < len(REGIONS):
            row.append(KeyboardButton(REGIONS[i + 1]))
        buttons.append(row)
    buttons.append([KeyboardButton("🔙 Orqaga")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Murojaat yuborish", callback_data="new_complaint")],
        [InlineKeyboardButton("📋 Murojaatlarim", callback_data="my_complaints")],
        [InlineKeyboardButton("🔐 Admin panel", callback_data="admin_panel")],
    ])
    await update.message.reply_text(
        "🛡️ *eNazorat — Raqamli Nazorat Tizimi*\n\nFuqarolar va muassasalar o'rtasidagi ko'prik.\n\nQuyidagi bo'limdan birini tanlang:",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

async def new_complaint_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(
        "🏛️ *Qaysi bo'limga murojaat qilmoqchisiz?*",
        reply_markup=make_dept_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    return CHOOSE_DEPARTMENT

async def choose_department(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    dept = query.data.replace("dept_", "")
    context.user_data["department"] = dept
    await query.edit_message_text(
        f"✅ Bo'lim: *{DEPARTMENTS[dept]}*\n\n👤 *Ismingizni kiriting:*",
        parse_mode=ParseMode.MARKDOWN
    )
    return ENTER_NAME

async def enter_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("❌ To'liq ismingizni kiriting.")
        return ENTER_NAME
    context.user_data["name"] = name
    await update.message.reply_text(
        f"✅ Ism: *{name}*\n\n📞 *Telefon raqamingizni kiriting*\nO'tkazib yuborish: /skip",
        parse_mode=ParseMode.MARKDOWN
    )
    return ENTER_PHONE

async def enter_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "/skip":
        context.user_data["phone"] = "Kiritilmagan"
    else:
        context.user_data["phone"] = update.message.text.strip()
    await update.message.reply_text(
        "🏙️ *Viloyatingizni tanlang:*",
        reply_markup=make_region_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    return ENTER_REGION

async def enter_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    region = update.message.text.strip()
    if region == "🔙 Orqaga":
        await update.message.reply_text("📞 Telefon raqamingizni kiriting yoki /skip:")
        return ENTER_PHONE
    if region not in REGIONS:
        await update.message.reply_text("❌ Ro'yxatdan viloyat tanlang.")
        return ENTER_REGION
    context.user_data["region"] = region
    from telegram import ReplyKeyboardRemove
    await update.message.reply_text(
        f"✅ Viloyat: *{region}*\n\n📌 *Murojaat turini tanlang:*",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN
    )
    await update.message.reply_text("Turni tanlang:", reply_markup=make_type_keyboard())
    return CHOOSE_TYPE

async def choose_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg_type = query.data.replace("type_", "")
    context.user_data["msg_type"] = msg_type
    await query.edit_message_text(
        f"✅ Tur: *{TYPES[msg_type]}*\n\n✍️ *Mavzuni kiriting:*",
        parse_mode=ParseMode.MARKDOWN
    )
    return ENTER_SUBJECT

async def enter_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["subject"] = update.message.text.strip()
    await update.message.reply_text("💬 *Xabaringizni yozing* (max 1500 belgi):", parse_mode=ParseMode.MARKDOWN)
    return ENTER_MESSAGE

async def enter_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.strip()
    if len(msg) > 1500:
        await update.message.reply_text("❌ 1500 belgidan oshmasligi kerak.")
        return ENTER_MESSAGE
    context.user_data["message"] = msg
    await update.message.reply_text("⚡ *Ustuvorlik darajasini tanlang:*", reply_markup=make_priority_keyboard(), parse_mode=ParseMode.MARKDOWN)
    return CHOOSE_PRIORITY

async def choose_priority(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    priority = query.data.replace("prio_", "")
    context.user_data["priority"] = priority
    d = context.user_data
    summary = (
        f"📋 *Murojaatingizni tekshiring:*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {d.get('name')} | 📞 {d.get('phone')}\n"
        f"🏙️ {d.get('region')}\n"
        f"🏛️ {DEPARTMENTS.get(d.get('department',''))}\n"
        f"📌 {TYPES.get(d.get('msg_type',''))} | {PRIORITIES.get(priority)}\n"
        f"📝 {d.get('subject')}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💬 {d.get('message')}"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yuborish", callback_data="confirm_send"),
         InlineKeyboardButton("❌ Bekor", callback_data="cancel")]
    ])
    await query.edit_message_text(summary, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    return CONFIRM

async def confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏳ Yuborilmoqda...")
    await query.edit_message_text("🤖 AI tahlil qilinmoqda...")
    d = context.user_data.copy()
    d["user_id"] = query.from_user.id
    d["username"] = query.from_user.username or ""
    ai_text = await ai_analyze(d.get("message", ""), TYPES.get(d.get("msg_type", ""), ""))
    d["ai_analysis"] = ai_text
    msg_id = save_message(d)
    await query.edit_message_text(
        f"✅ *Xabar yuborildi!*\n\n🔖 Raqam: `{msg_id}`\n\n🤖 *AI Tahlil:*\n{ai_text}",
        parse_mode=ParseMode.MARKDOWN
    )
    if ADMIN_CHAT_ID:
        msg = messages_db[msg_id]
        admin_text = (
            f"🔔 *Yangi murojaat!*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🔖 #{msg_id}\n"
            f"👤 {msg.get('name')} | 📞 {msg.get('phone')}\n"
            f"🏙️ {msg.get('region')}\n"
            f"🏛️ {DEPARTMENTS.get(msg.get('department',''))}\n"
            f"📌 {TYPES.get(msg.get('msg_type',''))} | {PRIORITIES.get(msg.get('priority',''))}\n"
            f"📝 {msg.get('subject')}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💬 {msg.get('message')}\n\n"
            f"🤖 *AI:* {ai_text}"
        )
        admin_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Ko'rib chiqildi", callback_data=f"admin_seen_{msg_id}"),
             InlineKeyboardButton("🚨 Belgilash", callback_data=f"admin_flag_{msg_id}")],
            [InlineKeyboardButton("📩 Javob berish", callback_data=f"admin_reply_{msg_id}")]
        ])
        try:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text, reply_markup=admin_keyboard, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Admin xabar xatosi: {e}")
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("❌ Bekor qilindi.")
    else:
        await update.message.reply_text("❌ Bekor qilindi. /start bosing.")
    context.user_data.clear()
    return ConversationHandler.END

async def my_complaints_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_msgs = [m for m in get_all_messages() if m.get("user_id") == user_id]
    if not user_msgs:
        await query.edit_message_text("📭 Murojaatlaringiz yo'q.\n\n/start bosing.")
        return
    text = f"📋 *Murojaatlaringiz* ({len(user_msgs)} ta):\n\n"
    for m in user_msgs[-5:]:
        s = {"yangi": "🆕", "korib_chiqilgan": "✅", "belgilangan": "🚨"}.get(m.get("status","yangi"), "❓")
        text += f"{s} `{m['id']}` — {m.get('subject','-')} ({m.get('created_at','')[:10]})\n"
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

async def admin_panel_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_CHAT_ID:
        await query.edit_message_text("🔐 Siz admin emassiz.")
        return
    all_msgs = get_all_messages()
    yangi = sum(1 for m in all_msgs if m.get("status") == "yangi")
    text = (
        f"🛡️ *Admin Panel*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📨 Jami: {len(all_msgs)} | 🆕 Yangi: {yangi}\n\n"
        f"So'nggi murojaatlar:\n"
    )
    for m in list(reversed(all_msgs))[:5]:
        s = {"yangi": "🆕", "korib_chiqilgan": "✅", "belgilangan": "🚨"}.get(m.get("status","yangi"), "❓")
        text += f"{s} `{m['id']}` — {m.get('subject','-')[:30]}\n"
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

async def admin_seen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_CHAT_ID:
        await query.answer("Ruxsat yo'q!", show_alert=True)
        return
    await query.answer()
    msg_id = query.data.replace("admin_seen_", "")
    update_message_status(msg_id, "korib_chiqilgan")
    await query.edit_message_text(query.message.text + f"\n\n✅ Ko'rib chiqildi.", parse_mode=ParseMode.MARKDOWN)

async def admin_flag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_CHAT_ID:
        await query.answer("Ruxsat yo'q!", show_alert=True)
        return
    await query.answer()
    msg_id = query.data.replace("admin_flag_", "")
    update_message_status(msg_id, "belgilangan")
    await query.edit_message_text(query.message.text + f"\n\n🚨 Belgilandi.", parse_mode=ParseMode.MARKDOWN)

async def admin_reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_CHAT_ID:
        await query.answer("Ruxsat yo'q!", show_alert=True)
        return
    await query.answer()
    msg_id = query.data.replace("admin_reply_", "")
    context.user_data["reply_to_msg_id"] = msg_id
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"📩 *#{msg_id} uchun javob yozing:*\nBekor qilish: /cancel",
        parse_mode=ParseMode.MARKDOWN
    )
    return ADMIN_REPLY

async def admin_reply_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "/cancel":
        await update.message.reply_text("❌ Bekor qilindi.")
        return ConversationHandler.END
    msg_id = context.user_data.get("reply_to_msg_id")
    if not msg_id:
        await update.message.reply_text("❌ Xatolik.")
        return ConversationHandler.END
    reply_text = update.message.text.strip()
    msg = get_message(msg_id)
    if msg:
        msg["admin_reply"] = reply_text
        update_message_status(msg_id, "korib_chiqilgan")
        user_id = msg.get("user_id")
        if user_id:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📩 *Murojaatingizga javob keldi!*\n\n🔖 `{msg_id}`\n📝 {msg.get('subject','-')}\n\n💬 *Admin javobi:*\n{reply_text}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Foydalanuvchiga xabar xatosi: {e}")
        await update.message.reply_text(f"✅ Javob yuborildi!", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ Murojaat topilmadi.")
    context.user_data.clear()
    return ConversationHandler.END

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Tushunmadim. /start bosing.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    user_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(new_complaint_cb, pattern="^new_complaint$")],
        states={
            CHOOSE_DEPARTMENT: [CallbackQueryHandler(choose_department, pattern="^dept_")],
            ENTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_name)],
            ENTER_PHONE: [MessageHandler(filters.TEXT, enter_phone)],
            ENTER_REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_region)],
            CHOOSE_TYPE: [CallbackQueryHandler(choose_type, pattern="^type_")],
            ENTER_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_subject)],
            ENTER_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_message)],
            CHOOSE_PRIORITY: [CallbackQueryHandler(choose_priority, pattern="^prio_")],
            CONFIRM: [
                CallbackQueryHandler(confirm_send, pattern="^confirm_send$"),
                CallbackQueryHandler(cancel, pattern="^cancel$"),
            ],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern="^cancel$")],
    )

    admin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_reply_start, pattern="^admin_reply_")],
        states={
            ADMIN_REPLY: [MessageHandler(filters.TEXT, admin_reply_send)],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(user_conv)
    app.add_handler(admin_conv)
    app.add_handler(CallbackQueryHandler(my_complaints_cb, pattern="^my_complaints$"))
    app.add_handler(CallbackQueryHandler(admin_panel_cb, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin_seen, pattern="^admin_seen_"))
    app.add_handler(CallbackQueryHandler(admin_flag, pattern="^admin_flag_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    logger.info("🤖 eNazorat bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
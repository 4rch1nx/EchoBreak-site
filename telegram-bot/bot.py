import sqlite3
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8373273491:AAHKUfwPB2OYTfgejrz8Pbpim-NepdD--EU"

def init_db():
    conn = sqlite3.connect('keys.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS keys
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  key_value TEXT UNIQUE NOT NULL,
                  taken BOOLEAN DEFAULT FALSE,
                  taken_by TEXT,
                  taken_by_username TEXT,
                  taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    initial_keys = [
        "URru0x61",
        "URru0x62",
        "URru0x63",
        "URru0x64",
        "URru0x65",
        "URru0x66",
        "URru0x67",
        "URru0x68",
        "URru0x69",
        "URru0x6A"
    ]
    
    for key in initial_keys:
        try:
            c.execute("INSERT OR IGNORE INTO keys (key_value) VALUES (?)", (key,))
        except:
            pass
    
    conn.commit()
    conn.close()
    logger.info("Database initialized with keys")

def get_available_key(user_id, username):
    conn = sqlite3.connect('keys.db')
    c = conn.cursor()
    
    c.execute("SELECT key_value FROM keys WHERE taken_by = ?", (str(user_id),))
    existing_key = c.fetchone()
    
    if existing_key:
        conn.close()
        return None, "already_claimed"
    
    c.execute("SELECT key_value FROM keys WHERE taken = FALSE LIMIT 1")
    available_key = c.fetchone()
    
    if available_key:
        display_username = f"@{username}" if username else f"User {user_id}"
        c.execute("UPDATE keys SET taken = TRUE, taken_by = ?, taken_by_username = ? WHERE key_value = ?", 
                 (str(user_id), display_username, available_key[0]))
        conn.commit()
        conn.close()
        return available_key[0], "success"
    else:
        conn.close()
        return None, "no_keys"

def get_stats():
    conn = sqlite3.connect('keys.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM keys")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM keys WHERE taken = TRUE")
    taken = c.fetchone()[0]
    conn.close()
    return total, taken

def get_admin_stats():
    conn = sqlite3.connect('keys.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM keys")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM keys WHERE taken = TRUE")
    taken = c.fetchone()[0]
    available = total - taken
    
    c.execute("""
        SELECT key_value, taken_by_username, taken_at 
        FROM keys 
        WHERE taken = TRUE 
        ORDER BY taken_at DESC 
        LIMIT 10
    """)
    recent_keys = c.fetchall()
    
    c.execute("""
        SELECT taken_by_username, COUNT(*) 
        FROM keys 
        WHERE taken = TRUE 
        GROUP BY taken_by_username 
        ORDER BY COUNT(*) DESC
    """)
    user_distribution = c.fetchall()
    
    conn.close()
    
    return total, taken, available, recent_keys, user_distribution

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Привет {user.first_name}!\n\n"
        "Добро пожаловать в бот раздачи ключей!\n\n"
        "Используй /getkey чтобы получить бесплатный ключ для сайта.\n"
        "Каждый пользователь может получить только один ключ.\n\n"
        "Используй /status чтобы узнать статус раздачи."
    )

async def get_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username
    key, status = get_available_key(user.id, username)
    
    if status == "success":
        await update.message.reply_text(
            f"Поздравляем {user.first_name}!\n\n"
            f"Ваш ключ: `{key}`\n\n"
            "Скопируйте этот ключ и используйте его на нашем сайте!\n\n"
            "Спасибо за участие!",
            parse_mode='Markdown'
        )
        logger.info(f"Key {key} given to user {user.id} (@{username})")
        
    elif status == "already_claimed":
        conn = sqlite3.connect('keys.db')
        c = conn.cursor()
        c.execute("SELECT key_value FROM keys WHERE taken_by = ?", (str(user.id),))
        existing_key = c.fetchone()
        conn.close()
        
        if existing_key:
            await update.message.reply_text(
                f"Привет {user.first_name}!\n\n"
                f"Вы уже получили ключ: `{existing_key[0]}`\n\n"
                "Каждый пользователь может получить только один ключ.\n\n"
                "Если у вас есть проблемы, пожалуйста, обратитесь в [поддержку](https://echobreak.space/contact.html).",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"Привет {user.first_name}!\n\n"
                "Вы уже получили ключ ранее!\n\n"
                "Каждый пользователь может получить только один ключ."
            )
    else:
        await update.message.reply_text(
            "Извините! Все ключи уже розданы.\n\n"
            "У нас закончились ключи для этой раздачи.\n"
            "Пожалуйста, проверяйте позже для будущих раздач!"
        )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total, taken = get_stats()
    available = total - taken
    
    await update.message.reply_text(
        f"Статус раздачи ключей:\n\n"
        f"• Всего ключей: {total}\n"
        f"• Получено: {taken}\n"
        f"• Доступно: {available}\n\n"
        f"Используйте /getkey чтобы получить ключ."
    )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ADMIN_IDS = [5640730039, 5972150615]
    
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("У вас нет прав для этой команды.")
        return
    
    try:
        total, taken, available, recent_keys, user_distribution = get_admin_stats()
        
        message = "**АДМИН СТАТИСТИКА**\n\n"
        message += f"• Всего ключей: {total}\n"
        message += f"• Выдано: {taken}\n"
        message += f"• Доступно: {available}\n"
        message += f"• Заполненность: {(taken/total)*100:.1f}%\n\n"
        
        message += "👥 **Распределение по пользователям:**\n"
        for username, count in user_distribution[:10]:
            message += f"• {username}: {count} ключ(ей)\n"
        
        message += "\n**Последние выданные ключи:**\n"
        for key in recent_keys[:10]:
            key_value, username, taken_at = key
            short_time = taken_at.split(' ')[1][:8] if taken_at else 'N/A'
            message += f"• `{key_value}` → {username} в {short_time}\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin_stats: {e}")
        await update.message.reply_text("Ошибка при получении статистики.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ADMIN_IDS = [5640730039, 5972150615]

    help_text = "**Команды бота:**\n\n"
    help_text += "/start - Начать работу с ботом\n"
    help_text += "/getkey - Получить ключ\n"
    help_text += "/status - Статус раздачи\n"
    
    if user.id in ADMIN_IDS:
        help_text += "/admin - Админ статистика\n"
    
    help_text += "/help - Показать это сообщение\n\n"
    help_text += "Каждый пользователь может получить только один ключ.\n"
    help_text += "Если у вас есть проблемы, пожалуйста, обратитесь в [поддержку](https://echobreak.space/contact.html)."
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

def main():
    init_db()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("getkey", get_key))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("admin", admin_stats))
    application.add_handler(CommandHandler("help", help_command))
    
    logger.info("Starting Telegram bot...")
    print("Bot is running! Press Ctrl+C to stop.")
    
    application.run_polling()

if __name__ == '__main__':
    main()
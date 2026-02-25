from typing import Final 
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, ContextTypes, InlineQueryHandler, CommandHandler
from datetime import date, datetime, time 
import sqlite3

with open("token.txt", "r") as file:
    token = file.read().strip()
TOKEN: Final = token

bot_database: str = "birthdays_database.db"


def initiliaze_db():
    con = sqlite3.connect(bot_database)
    c = con.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS birthdays(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, name TEXT NOT NULL, month INTEGER NOT NULL, day INTEGER NOT NULL, year INTEGER)")
    con.commit()
    con.close()


def add_birthday(user_id, name, month, day, year=None) -> None: 
    con = sqlite3.connect(bot_database)
    c = con.cursor() 
    c.execute(
        "INSERT INTO birthdays (user_id, name, month, day, year) VALUES (?, ?, ?, ?, ?)",
        (user_id, name, month, day, year)
    )
    con.commit()
    con.close()
    

def get_birthdays(user_id):
    con = sqlite3.connect(bot_database)
    c = con.cursor() 
    c.execute(
        "SELECT id, name, month, day, year FROM birthdays WHERE user_id = ? ORDER BY month, day",
        (user_id,)
    )
    rows = c.fetchall()
    con.close()
    return rows 


def delete_birthday(user_id, birthday_id):
    con = sqlite3.connect(bot_database)
    c = con.cursor()
    c.execute(
        "DELETE FROM birthdays WHERE id = ? AND user_id = ?",
        (birthday_id, user_id)
    )
    deleted = c.rowcount > 0 
    con.commit() 
    con.close() 
    return deleted 


def get_all_birthdays():
    con = sqlite3.connect(bot_database)
    c = con.cursor() 
    c.execute("SELECT id, user_id, name, month, day, year FROM birthdays")
    rows = c.fetchall()
    con.close() 
    return rows 


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Это поможет тебе помнить др твоих друзей!")


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args 
    print(args)
    if len(args) < 2:
        await update.message.reply_text("Чтобы добавить день рождения: /add имя день-месяц\n"
                                        "Пример: /add Джэйк 25-12")
        return
    date_str = args[-1]
    name = "".join(args[:-1])
    
    
    try:
        if len(date_str.split("-")) == 3:
            d = datetime.strptime(date_str, "%d-%m-%Y")
            month, day, year = d.month, d.day, d.year
        else:
            d = datetime.strptime(date_str, "%d-%m")
            month, day, year = d.month, d.day, None
    except ValueError:
        await update.message.reply_text("не понимаю, что ты написал бро")
        return 
    
    user_id = update.effective_user.id
    add_birthday(user_id, name, month, day, year)
    await update.message.reply_text(f"День рождения {name} сохранён!")


async def list_birthdays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    rows = get_birthdays(user_id)
    
    if not rows:
        await update.message.reply_text("Ты не добавил ни один день рождения, давай добавляй")
        return 

    lines = []
    for row in rows: 
        birthday_id, name, month, day, year = row
        date_str = f"{day:02d}-{month:02d}"
        if year:
            date_str += f"-{year}"
        lines.append(f"{birthday_id}. {name} - {date_str}")
        
    await update.message.reply_text("Сохраненные дни рождения:\n" + "\n".join(lines))
    
    
async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args 
    if len(args) != 1:
        await update.message.reply_text("Использовать /delete айди(номер дня рождения в списке)")
        return 
    

    try:
        birthday_id = int(args[0])
    except ValueError:
        await update.message.reply_text("айди это номер дня рождения в списке")
        return 
    
    user_id = update.effective_user.id
    if delete_birthday(user_id, birthday_id):
        await update.message.reply_text("День рождения удалён")
    else:
        await update.message.reply_text("День рождения с этим айди не найден")


async def check_birthdays(context: ContextTypes.DEFAULT_TYPE):
    today = date.today()
    rows = get_all_birthdays()
    
    for row in rows:
        birthday_id, user_id, name, month, day, year = row 
        
        this_year_birthday = date(today.year, month, day)
        if this_year_birthday < today:
            next_birthday = date(today.year + 1, month, day)
        else:
            next_birthday = this_year_birthday
        
        days_until = (next_birthday - today).days
        
        if days_until == 7:
            try:
                await context.bot.send_message(
                    chat_id = user_id,
                    text = f"Напоминание: у {name} день рождения через неделю! 🎂"
                )
            except Exception as e:
                return
        # else:
        #     try:
        #         await context.bot.send_message(
        #             chat_id= user_id,
        #             text = "Ближайший день рождения находится более чем в 7 днях!"
        #         )
        #     except Exception as e:
        #         return



async def check_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Быстренько проверяю")
    await check_birthdays(context)


async def who_made_this_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Автор бота: @xdenside")


def main():
    initiliaze_db()
    
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add))
    application.add_handler(CommandHandler("list", list_birthdays))
    application.add_handler(CommandHandler("delete", delete))
    application.add_handler(CommandHandler("check", check_now))
    application.add_handler(CommandHandler("author", who_made_this_bot))
    
    job_queue = application.job_queue
    job_queue.run_daily(check_birthdays, time=time(hour=9, minute=0))
    
    application.run_polling(poll_interval = 3)


if __name__ == "__main__":
    main()
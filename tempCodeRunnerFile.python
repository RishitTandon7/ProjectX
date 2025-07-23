import os
from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, db
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import random
from dotenv import load_dotenv

load_dotenv()

# Initialize Flask
app = Flask(__name__)

# Initialize Firebase Admin SDK
cred = credentials.Certificate("ticktock-terror-firebase-adminsdk-fbsvc-0102de7b4c.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': os.getenv("FIREBASE_DB_URL")
})

# Telegram Bot Setup
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Send me a task (e.g., 'Read chapter 3'). I'll randomly check if you did it later!"
    )

async def save_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    task = update.message.text
    
    # Save to Firebase
    ref = db.reference(f'/users/{user_id}/tasks')
    new_task_ref = ref.push()
    new_task_ref.set({
        "task": task,
        "created_at": datetime.now().isoformat(),
        "completed": False
    })
    
    # Schedule random check (between 1 hour to 48 hours)
    delay = random.randint(3600, 172800)  # 1h-48h in seconds
    check_time = datetime.now() + timedelta(seconds=delay)
    
    scheduler.add_job(
        check_task,
        'date',
        run_date=check_time,
        args=[user_id, task]
    )
    
    await update.message.reply_text(f"✅ Saved! I'll ask you about '{task}' later... 😈")

async def check_task(user_id, task):
    # Send check message
    await application.bot.send_message(
        chat_id=user_id,
        text=f"⏰ DID YOU DO: '{task}'? Reply DONE or I'll ask again in 1 hour!"
    )
    
    # Reschedule if no reply
    scheduler.add_job(
        check_task,
        'date',
        run_date=datetime.now() + timedelta(hours=1),
        args=[user_id, task]
    )

async def handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.lower()
    
    if text == "done":
        # Mark as complete in Firebase
        ref = db.reference(f'/users/{user_id}/tasks')
        tasks = ref.get()
        
        if tasks:
            for task_id, task_data in tasks.items():
                if task_data['task'] in update.message.reply_to_message.text:
                    ref.child(task_id).update({"completed": True})
                    await update.message.reply_text("🎉 Good job! Task marked complete.")
                    return

# Set up handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_task))
application.add_handler(MessageHandler(filters.REPLY, handle_response))

# Webhook setup for production
@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.process_update(update)
    return "ok"

@app.route("/")
def home():
    return "Procrastination Bot is running!"

if __name__ == "__main__":
    try:
        # Start the Bot
        application.run_polling()
        # Start Flask
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        print(f"Error: {e}")
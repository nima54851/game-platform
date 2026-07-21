import os
from flask import Flask, request, jsonify
from phone_data import lookup_phone, get_db_stats

app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

@app.route("/")
def index():
    s = get_db_stats()
    return jsonify({"bot": "phone-lookup", **s})

@app.route("/health")
def health():
    return jsonify({"ok": True})

@app.route("/api/lookup/<phone>")
def api_lookup(phone):
    result = lookup_phone(phone)
    return jsonify(result)

if __name__ == "__main__":
    import threading
    if BOT_TOKEN:
        from telegram.ext import Application, CommandHandler, MessageHandler, filters
        from telegram.ext._application import Application
        
        async def run_bot():
            app_bot = Application.builder().token(BOT_TOKEN).build()
            from phone_data import lookup_phone
            async def handle_message(update, context):
                text = update.message.text.strip()
                r = lookup_phone(text)
                if r.get("error"):
                    await update.message.reply_text(f"❌ {r['error']}")
                else:
                    emoji = "📡" if "移动" in r.get("operator","") else "📶" if "联通" in r.get("operator","") else "📱"
                    msg = f"{emoji} {r['prefix']} {r['operator']}"
                    if r.get("province"): msg += f"\n{r['province']}"
                    if r.get("city"): msg += f" {r['city']}"
                    await update.message.reply_text(msg)
            app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            app_bot.add_handler(CommandHandler("start", lambda u,c: u.message.reply_text("📱 发送手机号查询归属地")))
            app_bot.add_handler(CommandHandler("help", lambda u,c: u.message.reply_text("发送手机号即可")))
            await app_bot.run_polling()
        
        from telegram.ext import Application
        t = threading.Thread(target=lambda: Application.builder().token(BOT_TOKEN).build().run_polling(), daemon=True)
        t.start()
    
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

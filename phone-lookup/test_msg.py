#!/usr/bin/env python3
import os, asyncio
from telegram.ext import Application

async def test():
    app = Application.builder().token(os.environ['BOT_TOKEN']).build()
    await app.initialize()
    me = await app.bot.get_me()
    print(f'BOT: @{me.username} | OK')
    # Clear any existing updates with a high offset
    updates = await app.bot.get_updates(timeout=5, read_timeout=8, write_timeout=8)
    print(f'Pending messages: {len(updates)}')
    for u in updates:
        m = u.message
        if m:
            print(f'  from={m.from_user.username or m.from_user.id} text={m.text}')
            # Reply directly
            await m.reply_text(f'✅ 收到消息: {m.text}')
    await app.shutdown()

BOT_TOKEN = '8979991426:AAEtgWjhF1KV_pJZVwzjk-ZE2_Yf1-W4RDU'
asyncio.run(test())

#!/usr/bin/env python3
import os, asyncio
from telegram.ext import Application

async def poll():
    app = Application.builder().token('8979991426:AAEtgWjhF1KV_pJZVwzjk-ZE2_Yf1-W4RDU').build()
    await app.initialize()
    me = await app.bot.get_me()
    print(f'BOT: @{me.username} - connected OK')
    try:
        updates = await app.bot.get_updates(timeout=3, read_timeout=5, write_timeout=5)
        print(f'Pending: {len(updates)}')
        for u in updates:
            m = u.message
            if m:
                uid = m.from_user.username or str(m.from_user.id)
                print(f'  [{u.update_id}] from={uid} text={m.text}')
    except Exception as e:
        print(f'ERROR: {type(e).__name__}: {e}')
    await app.shutdown()

asyncio.run(poll())

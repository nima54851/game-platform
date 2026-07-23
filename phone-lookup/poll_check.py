#!/usr/bin/env python3
import os, asyncio, sys
sys.path.insert(0, '.')
os.environ['BOT_TOKEN'] = os.environ.get('BOT_TOKEN', '')

from telegram.ext import Application

async def quick_check():
    app = Application.builder().token(os.environ['BOT_TOKEN']).build()
    await app.initialize()
    me = await app.bot.get_me()
    print('BOT: @' + me.username)
    updates = await app.bot.get_updates(timeout=3, read_timeout=5, write_timeout=5)
    print('Pending updates:', len(updates))
    for u in updates:
        msg = u.message
        uid = msg.from_user.username if msg and msg.from_user else '?'
        txt = msg.text if msg else 'n/a'
        print(f'  update_id={u.update_id} from={uid} text={txt}')
    await app.shutdown()

asyncio.run(quick_check())

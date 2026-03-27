import asyncio
import random
import os
from datetime import datetime
import pytz
from telethon import TelegramClient
from aiohttp import web  # 👈 Our fake storefront builder

# Твої ключі з my.telegram.org (заміни на свої)
API_ID = 1234567 # YOUR API ID 
API_HASH = 'your_hash_here'
BOT_USERNAME = 'target_bot_username'

client = TelegramClient('my_session', API_ID, API_HASH)

# Задаємо наш часовий пояс
KYIV_TZ = pytz.timezone('Europe/Kyiv')

# Час, коли бот має йти в атаку
TARGET_TIMES = ["07:59", "08:00", "08:01", "08:02", "08:03", "08:04", "08:05", "23:17"]

async def chill(min_s=0.5, max_s=1.5):
    """Штучна затримка для імітації людини"""
    await asyncio.sleep(random.uniform(min_s, max_s))

# --- NEW: The Fake Storefront ---
async def handle_ping(request):
    """Just a friendly wave to Render so they know we're alive."""
    return web.Response(text="Bot is awake and hunting for instructors! 🚙💨")

async def run_dummy_server():
    """Spins up the web server on the port Render gives us."""
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render assigns a dynamic port via environment variables. If running locally, defaults to 8080.
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"🌐 Fake storefront open on port {port}. Render is happy!")

# --- YOUR ORIGINAL BOT LOGIC ---
async def run_booking_logic():
    """Це твій основний алгоритм проходу по інструкторах"""
    print("🚀 Погнали! Стукаємо до бота...")
    
    async with client.conversation(BOT_USERNAME) as conv:
        await conv.send_message('/start')
        await conv.get_response()
        await chill()

        await conv.send_message('🚀 Записатися на заняття')
        await conv.get_response()
        await chill()

        await conv.send_message('🚙 Механіка')
        response = await conv.get_response()
        await chill()

        instructors = []
        if response.reply_markup and hasattr(response.reply_markup, 'rows'):
            for row in response.reply_markup.rows:
                for button in row.buttons:
                    instructors.append(button.text)
            
            if instructors:
                instructors = instructors[:-1] # Відкидаємо кнопку "Назад"

        print(f"👨‍🏫 Знайшли інструкторів: {instructors}")

        for instructor in instructors:
            print(f"➡️ Перевіряємо: {instructor}")
            await conv.send_message(instructor)
            inst_response = await conv.get_response()
            
            # Тут логіка перевірки вільних місць...
            
            await chill(1.0, 2.0)

            await conv.send_message('👨‍🏫 Обрати іншого інструктора')
            await conv.get_response()
            await chill()

async def main():
    # 1. Fire up the dummy server in the background so it runs alongside your bot
    asyncio.create_task(run_dummy_server())

    executed_times = set() 
    print("🕰 Засіли в засідці. Чекаємо на потрібний час за Києвом...")

    while True:
        now = datetime.now(KYIV_TZ)
        current_hm = now.strftime("%H:%M")

        if current_hm in TARGET_TIMES and current_hm not in executed_times:
            print(f"🔥 Час настав! Запускаємо цикл для {current_hm}")
            
            try:
                await run_booking_logic()
            except Exception as e:
                print(f"❌ Якась лажа під час виконання: {e}")
            
            executed_times.add(current_hm)
            print(f"✅ Цикл для {current_hm} завершено. Чекаємо далі.")

        if current_hm > "08:05" and "08:05" in executed_times:
            print("🏁 Всі спроби вичерпано. Бот йде відпочивати!")
            # We don't break here on Render, otherwise the whole app crashes and restarts.
            # We just let it keep looping and doing nothing until tomorrow.
            pass 

        await asyncio.sleep(1)

# Запуск
with client:
    client.loop.run_until_complete(main())
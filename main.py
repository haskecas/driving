import asyncio
import random
import os
import re
from datetime import datetime
import pytz
from telethon import TelegramClient
from aiohttp import web  # 👈 Our fake storefront builder
from telethon.errors import SessionPasswordNeededError
import requests
from telethon.sessions import StringSession

from config import *

#client = TelegramClient('my_session', API_ID, API_HASH)
client = TelegramClient(StringSession(SESSION_STR), API_ID, API_HASH)

# Задаємо наш часовий пояс
KYIV_TZ = pytz.timezone('Europe/Kyiv')

# Час, коли бот має йти в атаку
TARGET_TIMES = ["08:00"]
TIMES_CHECKED = 0
def is_valid_time(text):
    pattern = r"^(?:[01]\d|2[0-3]):[0-5]\d$"
    return bool(re.match(pattern, text))

def log_to_owner(text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": f"{USER_ID}", "text": f"{text}"})

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
async def run_booking_logic(current_hm):
    """Це твій основний алгоритм проходу по інструкторах"""
    print("🚀 Погнали! Стукаємо до бота...")
    
    async with client.conversation(BOT_USERNAME) as conv:
        global TIMES_CHECKED
        if TIMES_CHECKED % 10 == 0 or current_hm == "07:59": # бекенд бота може забути що він очікує інструктора від мене то час від часу перепочинатиму
            log_to_owner(f"Провірив {TIMES_CHECKED} раз {'+ записуємось на 08:00' if current_hm == '08:00' else ''}")
            await conv.send_message('/start')
            await conv.get_response()
            await chill()

            await conv.send_message('🚀 Записатися на заняття')
            await conv.get_response()
            await chill()

            await conv.send_message('🚙 Механіка')
            response = await conv.get_response()
        else:
            await conv.send_message('👨‍🏫 Обрати іншого інструктора')
            response = await conv.get_response()
        TIMES_CHECKED+=1
        instructors = []
        if response.reply_markup and hasattr(response.reply_markup, 'rows'):
            for row in response.reply_markup.rows:
                for button in row.buttons:
                    instructors.append(button.text)
            
            if instructors:
                instructors = instructors[:-1] # Відкидаємо кнопку "Назад"

        #print(f"👨‍🏫 Знайшли інструкторів: {instructors}")
        instructors = instructors
        for instructor in instructors:
            if TARGET_INSTRUCTOR_SURNAME.lower() not in instructor.lower(): # всіх не перевіряємо, бо не всі підходять, але робити хардкорну перевірку не вийде, бо окрім прізвища в тексті кнопки є рейтинг який міняється час від часу
                continue
            print(f"➡️ Перевіряємо: {instructor}")
            await conv.send_message(instructor)
            inst_response = await conv.get_response()
            #await chill()
            if "всі години зайняті на найближчі 14 днів" not in inst_response.text:
                print("Є година")
                await conv.send_message(inst_response.reply_markup.rows[0].buttons[0].text)
                inst_response = await conv.get_response()
                free_times = []
                bad_times = ["08:00", "09:00", "10:00", "11:00", "12:00"]
                for i in inst_response.reply_markup.rows:
                    for button in i.buttons:
                        if is_valid_time(button.text):
                            free_times.append(button.text)
                free_times = free_times[::-1]
                for i in free_times:
                    if i not in bad_times:
                        await conv.send_message(i)
                        time_response = await conv.get_response()
                        await chill(0.2, 0.2)
                        await conv.send_message("1 година")
                        await conv.get_response()
                        await chill(0.2, 0.2)
                        await conv.send_message("✅ Підтвердити")
                        log_to_owner("Записався‼️\n"*10)
                        break
            else:
                print("немає вільних годин")
            
            # await chill(1.0, 2.0)
            #
            # await conv.send_message('👨‍🏫 Обрати іншого інструктора')
            # await conv.get_response()
            # await chill()

async def main():
    global TIMES_CHECKED
    # 1. Fire up the dummy server in the background so it runs alongside your bot
    asyncio.create_task(run_dummy_server())

    executed_times = set() 
    print("🕰 Засіли в засідці. Чекаємо на потрібний час за Києвом...")

    while True:
        now = datetime.now(KYIV_TZ)
        current_hm = now.strftime("%H:%M")

        if current_hm == "00:00" and len(executed_times) > 0:
            executed_times.clear()
            TIMES_CHECKED = 0
            log_to_owner("Скинув всі лічильники")
            print("🌅 Новий день — чистий лист! Погнали по-новій!")

        if current_hm in TARGET_TIMES and current_hm not in executed_times and now.second >= 2: # if 1
            print(f"🔥 Час настав! Запускаємо цикл для {current_hm}")
            
            try:
                await run_booking_logic(current_hm)
            except Exception as e:
                print(f"❌ Якась лажа під час виконання: {e}")
            
            executed_times.add(current_hm)
            print(f"✅ Цикл для {current_hm} завершено. Чекаємо далі.")

        # if current_hm > "08:05" and "08:05" in executed_times:
        #     print("🏁 Всі спроби вичерпано. Бот йде відпочивати!")
        #     # We don't break here on Render, otherwise the whole app crashes and restarts.
        #     # We just let it keep looping and doing nothing until tomorrow.
        #     pass

        await asyncio.sleep(1)

# Запуск

def fill_times(interval=2):
    global TARGET_TIMES
    from datetime import datetime, timedelta

    start = datetime.strptime("00:00", "%H:%M")
    TARGET_TIMES = [
        (start + timedelta(minutes=interval * i)).strftime("%H:%M")
        for i in range((24 * 60) // interval )
    ]
    print(TARGET_TIMES)
    print(len(TARGET_TIMES))

fill_times(1)
with client:
    client.loop.run_until_complete(main())

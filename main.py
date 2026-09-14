import asyncio
import logging
import sqlite3
import sys
from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.text_decorations import html_decoration as hd

# ================= КОНФИГУРАЦИЯ =================

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  
ADMIN_ID = 6796608783
CHANNEL_ID = -1003237202237
CHANNEL_USERNAME = "plugmansliv"
CHANNEL_ID_2 = -1003354139532      
CHANNEL_USERNAME_2 = "aiogramacademy"  

AD_TEXT = """
<b>🔥 ХОСТИНГ APEXNODES: МОЩЬ И НАДЁЖНОСТЬ ПО УМНОЙ ЦЕНЕ! 🔥</b>

6 лет на рынке — и тысячи довольных клиентов знают: с ApexNodes можно не переживать за стабильность проектов. Мы держим планку и дарим вам максимальную производительность за минимальные деньги!

🚀 Что вы получаете с нами:
✅ Мощные серверы в Москве и Польше — выбирайте локацию, которая ближе к вашей аудитории, и обеспечьте минимальную задержку.
✅ Стабильная работа 24/7 — забудьте про простои и потерю клиентов.
✅ Оптимальные тарифы — платите только за то, что реально используете.
✅ Техническая поддержка, которая отвечает быстро и по делу.

А сейчас — особенный бонус для вас! 
При вводе промокода **plugman** — скидка **50%** на любой тариф! Это отличный шанс протестировать возможности ApexNodes или масштабировать свой проект с выгодой.

Не упустите возможность запустить свой проект на надёжной базе — начните уже сегодня!

👉 Воспользуйтесь промокодом plugman и получите скидку 50% прямо сейчас!
"""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)


def init_db():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    cursor.execute('CREATE TABLE IF NOT EXISTS stats (resource_code TEXT PRIMARY KEY, download_count INTEGER DEFAULT 0)')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resources (
            code TEXT PRIMARY KEY,
            type TEXT,
            title TEXT,
            desc TEXT,
            link TEXT,
            file_id TEXT,
            photo_id TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def log_download(code):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO stats (resource_code, download_count) VALUES (?, 1) ON CONFLICT(resource_code) DO UPDATE SET download_count = download_count + 1', (code,))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT resource_code, download_count FROM stats')
    rows = cursor.fetchall()
    conn.close()
    return dict(rows)

def get_all_users():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()
    return [user[0] for user in users]

def add_resource_to_db(data):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO resources (code, type, title, desc, link, file_id, photo_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (data['code'], data['type'], data['title'], data['desc'], data['link'], data['file_id'], data['photo_id']))
    conn.commit()
    conn.close()

def get_resource_by_code(code):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM resources WHERE code = ?', (code,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "code": row[0], "type": row[1], "title": row[2],
            "desc": row[3], "link": row[4], "file_id": row[5], "photo_id": row[6]
        }
    return None

def get_all_resources(filter_type="all"):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    if filter_type == "all":
        cursor.execute('SELECT code, title, type FROM resources')
    else:
        cursor.execute('SELECT code, title, type FROM resources WHERE type = ?', (filter_type,))
    rows = cursor.fetchall()
    conn.close()
    return rows

async def check_subscription(user_id: int, bot: Bot) -> bool:
    try:
        member1 = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        member2 = await bot.get_chat_member(chat_id=CHANNEL_ID_2, user_id=user_id)
        statuses = {"creator", "administrator", "member"}
        return member1.status in statuses and member2.status in statuses
    except:
        return False


async def log_message_middleware(handler, event: types.Message, data):
    user = event.from_user
    username = f"@{user.username}" if user.username else f"ID:{user.id}"
    text = event.text if event.text else "[media]"
    
    logging.info(f"📩 Message | User: {username} (ID: {user.id}) | Text: {text}")
    
    return await handler(event, data)


async def log_callback_middleware(handler, event: types.CallbackQuery, data):
    user = event.from_user
    username = f"@{user.username}" if user.username else f"ID:{user.id}"
    button_data = event.data
    
    logging.info(f"🔘 Callback | User: {username} (ID: {user.id}) | Button: {button_data}")
    
    return await handler(event, data)


dp = Dispatcher(storage=MemoryStorage())
router = Router()

router.message.middleware(log_message_middleware)
router.callback_query.middleware(log_callback_middleware)

dp.include_router(router)

class BroadcastState(StatesGroup):
    waiting_for_message = State()

class ResourceAdd(StatesGroup):
    waiting_for_code = State()
    waiting_for_type = State()
    waiting_for_title = State()
    waiting_for_desc = State()
    waiting_for_link = State()
    waiting_for_file = State()
    waiting_for_photo = State()

class SubscriptionCheck(StatesGroup):
    waiting_for_code = State()


@router.message(CommandStart())
async def command_start_handler(message: types.Message, command: CommandObject, bot: Bot):
    user_id = message.from_user.id
    add_user(user_id)
    
    args = command.args 

    if args and args.isdigit() and len(args) == 4:
        logging.info(f"User {user_id} used Deep Link for resource: {args}")
        await send_resource_logic(message, args, bot)
    else:
        logging.info(f"User {user_id} started bot normally.")
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📂 Список всех ресурсов", callback_data="filter_all")]])
        safe_name = hd.quote(message.from_user.first_name)
        await message.answer(
            f"Привет, {safe_name}!\n\n"
            "Я бот для выдачи ресурсов.\n"
            "🔸 Введи <b>4-значный код</b>.\n"
            "🔸 Или нажми кнопку ниже.",
            parse_mode="HTML",
            reply_markup=kb
        )


@router.message(Command("add"), F.from_user.id == ADMIN_ID)
async def add_resource_start(message: types.Message, state: FSMContext):
    await message.answer("➕ <b>Добавление нового ресурса</b>\n\nВведите 4-значный код (например, 1001):", parse_mode="HTML")
    await state.set_state(ResourceAdd.waiting_for_code)

@router.message(ResourceAdd.waiting_for_code, F.from_user.id == ADMIN_ID)
async def process_add_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    if not code.isdigit() or len(code) != 4:
        await message.answer("❌ Код должен состоять из 4 цифр. Попробуй снова.")
        return
    
    if get_resource_by_code(code):
        await message.answer(f"⚠️ Ресурс с кодом {code} уже существует и будет перезаписан.")
    
    await state.update_data(code=code)
    await message.answer("Введите тип ресурса:\n(варианты: <code>build</code>, <code>plugin</code>, <code>other</code>)", parse_mode="HTML")
    await state.set_state(ResourceAdd.waiting_for_type)

@router.message(ResourceAdd.waiting_for_type, F.from_user.id == ADMIN_ID)
async def process_add_type(message: types.Message, state: FSMContext):
    rtype = message.text.strip().lower()
    if rtype not in ["build", "plugin", "other"]:
        await message.answer("❌ Неверный тип. Введите: build, plugin или other.")
        return
    await state.update_data(type=rtype)
    await message.answer("Введите <b>НАЗВАНИЕ</b> (Title):", parse_mode="HTML")
    await state.set_state(ResourceAdd.waiting_for_title)

@router.message(ResourceAdd.waiting_for_title, F.from_user.id == ADMIN_ID)
async def process_add_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите <b>ОПИСАНИЕ</b> (Description).\nНапишите <code>skip</code> чтобы оставить пустым.", parse_mode="HTML")
    await state.set_state(ResourceAdd.waiting_for_desc)

@router.message(ResourceAdd.waiting_for_desc, F.from_user.id == ADMIN_ID)
async def process_add_desc(message: types.Message, state: FSMContext):
    text = message.text
    if text.lower() == 'skip': text = ""
    await state.update_data(desc=text)
    await message.answer("Введите <b>ССЫЛКУ</b> (Link).\nНапишите <code>skip</code> чтобы оставить пустой.", parse_mode="HTML")
    await state.set_state(ResourceAdd.waiting_for_link)

@router.message(ResourceAdd.waiting_for_link, F.from_user.id == ADMIN_ID)
async def process_add_link(message: types.Message, state: FSMContext):
    text = message.text
    if text.lower() == 'skip': text = ""
    await state.update_data(link=text)
    await message.answer("Отправьте <b>ФАЙЛ</b> (Document) для скачивания.\nНапишите <code>skip</code> чтобы пропустить.", parse_mode="HTML")
    await state.set_state(ResourceAdd.waiting_for_file)

@router.message(ResourceAdd.waiting_for_file, F.from_user.id == ADMIN_ID)
async def process_add_file(message: types.Message, state: FSMContext):
    file_id = ""
    if message.document:
        file_id = message.document.file_id
    elif message.text and message.text.lower() == 'skip':
        file_id = ""
    else:
        await message.answer("❌ Это не файл. Отправь документ или напиши skip.")
        return

    await state.update_data(file_id=file_id)
    await message.answer("Отправьте <b>КАРТИНКУ</b> (Photo) для поста.\nНапишите <code>skip</code> чтобы пропустить.", parse_mode="HTML")
    await state.set_state(ResourceAdd.waiting_for_photo)

@router.message(ResourceAdd.waiting_for_photo, F.from_user.id == ADMIN_ID)
async def process_add_photo(message: types.Message, state: FSMContext):
    photo_id = ""
    if message.photo:
        photo_id = message.photo[-1].file_id
    elif message.text and message.text.lower() == 'skip':
        photo_id = ""
    else:
        await message.answer("❌ Это не картинка. Отправь фото или напиши skip.")
        return

    data = await state.get_data()
    data['photo_id'] = photo_id
    
    add_resource_to_db(data)
    
    logging.info(f"Admin added resource {data['code']} ({data['title']})")
    await message.answer(f"✅ <b>Ресурс сохранен!</b>\nКод: <code>{data['code']}</code>\nНазвание: {data['title']}", parse_mode="HTML")
    await state.clear()


@router.message(Command("stats"), F.from_user.id == ADMIN_ID)
async def show_statistics(message: types.Message):
    stats_data = get_stats()
    resources_list = get_all_resources()

    if not stats_data:
        await message.answer("📊 Статистика пока пуста.")
        return

    text = "📊 <b>Статистика скачиваний:</b>\n\n"
    total = 0
    
    res_dict = {r[0]: r[1] for r in resources_list}

    for code, count in stats_data.items():
        title = res_dict.get(code, "Удаленный ресурс")
        text += f"🔹 <code>{code}</code> | {title}: <b>{count}</b>\n"
        total += count
    
    text += f"\n📈 <b>Всего выдано ресурсов: {total}</b>"
    logging.info("Admin requested statistics.")
    await message.answer(text, parse_mode="HTML")

@router.message(Command("sendmessage"), F.from_user.id == ADMIN_ID)
async def start_broadcast(message: types.Message, state: FSMContext):
    await message.answer("📢 <b>Режим рассылки.</b>\nОтправь сообщение.", parse_mode="HTML")
    await state.set_state(BroadcastState.waiting_for_message)

@router.message(BroadcastState.waiting_for_message, F.from_user.id == ADMIN_ID)
async def process_broadcast(message: types.Message, state: FSMContext):
    users = get_all_users()
    count, blocked = 0, 0
    status_msg = await message.answer(f"⏳ Рассылка на {len(users)}...")
    
    logging.info(f"Admin started broadcast to {len(users)} users.")
    
    for user_id in users:
        try:
            await message.copy_to(chat_id=user_id)
            count += 1
            await asyncio.sleep(0.05)
        except: blocked += 1
    
    logging.info(f"Broadcast finished. Success: {count}, Blocked: {blocked}")
    await status_msg.edit_text(f"✅ Готово!\nПолучили: {count}\nБлок: {blocked}")
    await state.clear()

@router.message(Command("sendads"), F.from_user.id == ADMIN_ID)
async def send_ads_broadcast(message: types.Message, bot: Bot):
    users = get_all_users()
    count, blocked = 0, 0
    status_msg = await message.answer(f"⏳ Отправка рекламы {len(users)} пользователям...")
    
    logging.info(f"Admin started ads broadcast to {len(users)} users.")
    
    kb_ad = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="СОЗДАТЬ СВОЙ СЕРВЕР", url="https://apexnodes.xyz/aff.php?aff=2")]
    ])
    
    for user_id in users:
        try:
            await bot.send_message(chat_id=user_id, text=AD_TEXT, parse_mode="HTML", reply_markup=kb_ad)
            count += 1
            await asyncio.sleep(0.05)
        except: blocked += 1
    
    logging.info(f"Ads broadcast finished. Success: {count}, Blocked: {blocked}")
    await status_msg.edit_text(f"✅ Готово!\n📢 Рекламу получили: {count}\n🚫 Заблокировали: {blocked}")

@router.callback_query(F.data.startswith("filter_"))
async def show_filtered_list(callback: types.CallbackQuery):
    category = callback.data.split("_")[1]
    resources = get_all_resources(category)

    text = f"<b>Список доступных ресурсов ({category}):</b>\n\n"
    if resources:
        for code, title, rtype in resources:
            text += f"🔹 <b>{title}</b> — Код: <code>{code}</code>\n"
    else:
        text += "<i>Пусто.</i>"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сборки", callback_data="filter_build"),
         InlineKeyboardButton(text="Плагины", callback_data="filter_plugin"),
         InlineKeyboardButton(text="Остальное", callback_data="filter_other")],
        [InlineKeyboardButton(text="📂 Показать всё", callback_data="filter_all")]
    ])
    
    logging.info(f"User {callback.from_user.id} viewed list filter: {category}")
    try: await callback.message.edit_text(text + "\n👇 Введи код ресурса.", parse_mode="HTML", reply_markup=kb)
    except: pass
    await callback.answer()

@router.callback_query(F.data.startswith("check_sub_"))
async def check_subscription_callback(callback: types.CallbackQuery, bot: Bot):
    code = callback.data.split("_", 2)[2]  # Извлекаем код из callback_data
    user_id = callback.from_user.id
    
    if await check_subscription(user_id, bot):
        await callback.answer("✅ Подписка подтверждена!", show_alert=True)
        logging.info(f"User {user_id} subscription confirmed for resource {code}")
        
        await send_resource_logic(callback.message, code, bot)
    else:
        await callback.answer("❌ Вы еще не подписаны на канал", show_alert=True)
        logging.info(f"User {user_id} subscription check failed for resource {code}")

async def send_subscription_request(message: types.Message, code: str):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подписаться на канал 1", url=f"https://t.me/{CHANNEL_USERNAME}")],
        [InlineKeyboardButton(text="✅ Подписаться на канал 2", url=f"https://t.me/{CHANNEL_USERNAME_2}")],
        [InlineKeyboardButton(text="🔄 Проверить подписку", callback_data=f"check_sub_{code}")]
    ])
    
    await message.answer(
        "📢 <b>Подпишитесь на оба канала перед получением ресурса!</b>",
        parse_mode="HTML",
        reply_markup=kb
    )

async def send_resource_logic(message: types.Message, code: str, bot: Bot):
    user_id = message.from_user.id
    if not await check_subscription(user_id, bot):
        await send_subscription_request(message, code)
        return
    
    resource = get_resource_by_code(code)
    
    if resource:
        log_download(code)
        logging.info(f"User {message.from_user.id} received resource {code}")

        caption = f"📦 <b>{resource['title']}</b>\n\n{resource['desc']}\n\n⬇️ Способы загрузки:"
        
        kb_rows = []
        if resource['link']:
            kb_rows.append([InlineKeyboardButton(text="☁️ Скачать по ссылке", url=resource['link'])])
        
        kb = InlineKeyboardMarkup(inline_keyboard=kb_rows) if kb_rows else None
        
        if resource["photo_id"]:
            await message.answer_photo(photo=resource["photo_id"], caption=caption, parse_mode="HTML", reply_markup=kb)
        else:
            await message.answer(caption, parse_mode="HTML", reply_markup=kb)
        
        if resource['file_id']:
            await bot.send_chat_action(chat_id=message.chat.id, action="upload_document")
            try:
                await message.answer_document(document=resource['file_id'], caption="📂 Файл из Telegram")
            except Exception as e:
                logging.error(f"Error sending file for {code}: {e}")
                await message.answer("⚠️ Ошибка отправки файла.")
        
        await asyncio.sleep(1)
        kb_ad = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="СОЗДАТЬ СВОЙ СЕРВЕР", url="https://apexnodes.xyz/aff.php?aff=2")]
        ])
        await message.answer(AD_TEXT, parse_mode="HTML", reply_markup=kb_ad)
    else:
        logging.warning(f"User {message.from_user.id} requested unknown code {code}")
        await message.answer("❌ Ресурс не найден.")

@router.message(F.text)
async def get_resource_text(message: types.Message, bot: Bot):
    code = message.text.strip()
    if code.isdigit() and len(code) == 4:
        await send_resource_logic(message, code, bot)

async def main():
    init_db() 
    bot = Bot(token=BOT_TOKEN)
    print("Бот запущен! Логи пишутся в bot.log")
    logging.info("Bot started.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
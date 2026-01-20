import aiosqlite
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

TOKEN = "8440171842:AAFwfNKtK-Y8u-JZ3334TzDK9RRtRoVYZcY"
REPORT_CHAT_ID = -1002720457461  # ID группы BuildingReports

bot = Bot(TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# ───────── БАЗА ДАННЫХ ─────────
async def init_db():
    async with aiosqlite.connect("reports.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            user_id INTEGER,
            nickname TEXT,
            build TEXT,
            money INTEGER,
            cd TEXT,
            date TEXT
        )
        """)
        await db.commit()

# ───────── FSM ─────────
class Report(StatesGroup):
    nickname = State()
    build = State()
    cd = State()
    proof = State()

# ───────── КНОПКИ ─────────
main_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add("📋 Сдать отчёт", "🏗 Взятие строек")
main_kb.add("🏆 Недельный рейтинг", "📊 Мой банк")

build_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
build_kb.add("🏗 Средняя", "🏢 Высокая")

take_build_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
take_build_kb.add("🏢 Высокая", "🏗 Средняя")
take_build_kb.add("⬅️ Назад")

high_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
high_kb.add("Арзамас", "Лыткарино")
high_kb.add("Южный", "Нижегородск")
high_kb.add("⬅️ Назад")

mid_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
mid_kb.add("Гарель 1", "Гарель 2")
mid_kb.add("Батырево 1", "Батырево 2")
mid_kb.add("⬅️ Назад")

# ───────── СТАРТ ─────────
@dp.message_handler(commands="start")
async def start(msg: types.Message):
    await msg.answer(
        "🏗 BLACK RUSSIA\n"
        "Строительная компания\n\n"
        "Выберите действие:",
        reply_markup=main_kb
    )

# ───────── ОТЧЁТ ─────────
@dp.message_handler(text="📋 Сдать отчёт")
async def report_start(msg: types.Message):
    await msg.answer("👤 Введите NickName:")
    await Report.nickname.set()

@dp.message_handler(state=Report.nickname)
async def set_nick(msg: types.Message, state: FSMContext):
    await state.update_data(nick=msg.text)
    await msg.answer("🏗 Выберите вид стройки:", reply_markup=build_kb)
    await Report.build.set()

@dp.message_handler(state=Report.build)
async def set_build(msg: types.Message, state: FSMContext):
    money = 250000 if "Средняя" in msg.text else 400000
    await state.update_data(build=msg.text, money=money)
    await msg.answer("⏱ Укажите время КД:")
    await Report.cd.set()

@dp.message_handler(state=Report.cd)
async def set_cd(msg: types.Message, state: FSMContext):
    await state.update_data(cd=msg.text)
    await msg.answer("📸 Отправьте скриншот:")
    await Report.proof.set()

@dp.message_handler(content_types=types.ContentType.PHOTO, state=Report.proof)
async def finish_report(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    date = datetime.now().isoformat()

    async with aiosqlite.connect("reports.db") as db:
        await db.execute(
            "INSERT INTO reports VALUES (?,?,?,?,?,?)",
            (msg.from_user.id, data["nick"], data["build"], data["money"], data["cd"], date)
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT SUM(money) FROM reports WHERE user_id=?",
            (msg.from_user.id,)
        )
        total = (await cursor.fetchone())[0]

    caption = (
        "🏗 BLACK RUSSIA | ОТЧЁТ\n\n"
        f"👤 NickName: {data['nick']}\n"
        f"{data['build']}\n"
        f"⏱ КД: {data['cd']}\n"
        f"💰 Заработок: {data['money']:,} вирт\n"
        f"🏦 Общий банк: {total:,} вирт"
    )

    await bot.send_photo(REPORT_CHAT_ID, msg.photo[-1].file_id, caption=caption)
    await msg.answer("✅ Отчёт принят!", reply_markup=main_kb)
    await state.finish()

# ───────── МОЙ БАНК ─────────
@dp.message_handler(text="📊 Мой банк")
async def my_bank(msg: types.Message):
    async with aiosqlite.connect("reports.db") as db:
        cursor = await db.execute(
            "SELECT SUM(money) FROM reports WHERE user_id=?",
            (msg.from_user.id,)
        )
        total = (await cursor.fetchone())[0]

    if total is None:
        await msg.answer("❌ У вас нет отчётов.")
    else:
        await msg.answer(f"🏦 Ваш общий банк:\n💰 {total:,} вирт")

# ───────── НЕДЕЛЬНЫЙ РЕЙТИНГ ─────────
@dp.message_handler(text="🏆 Недельный рейтинг")
async def weekly_rating(msg: types.Message):
    week = (datetime.now() - timedelta(days=7)).isoformat()

    async with aiosqlite.connect("reports.db") as db:
        cursor = await db.execute("""
        SELECT nickname, SUM(money) FROM reports
        WHERE date >= ?
        GROUP BY nickname
        ORDER BY SUM(money) DESC
        LIMIT 10
        """, (week,))
        rows = await cursor.fetchall()

    text = "🏆 НЕДЕЛЬНЫЙ РЕЙТИНГ\n\n"
    for i, row in enumerate(rows, 1):
        text += f"{i}. {row[0]} — {row[1]:,} вирт\n"

    await msg.answer(text)

# ───────── ВЗЯТИЕ СТРОЕК ─────────
@dp.message_handler(text="🏗 Взятие строек")
async def take_build(msg: types.Message):
    await msg.answer("Выберите тип стройки:", reply_markup=take_build_kb)

@dp.message_handler(text="🏢 Высокая")
async def high_build(msg: types.Message):
    await msg.answer("🏢 Высокая стройка:", reply_markup=high_kb)

@dp.message_handler(text="🏗 Средняя")
async def mid_build(msg: types.Message):
    await msg.answer("🏗 Средняя стройка:", reply_markup=mid_kb)

BUILD_MESSAGES = {
    "Арзамас": "взял г.Арзамас /gps 7>3>1",
    "Лыткарино": "взял г.Лыткарино /gps 7>3>2",
    "Южный": "взял г.Южный /gps 7>3>3",
    "Нижегородск": "взял г.Нижегородск /gps 7>3>4",
    "Гарель 1": "взял пгт. Гарель 1 /gps 7>2>3",
    "Гарель 2": "взял пгт. Гарель 2 /gps 7>2>4",
    "Батырево 1": "взял пгт. Батырево 1 /gps 7>2>1",
    "Батырево 2": "взял пгт. Батырево 2 /gps 7>2>2",
}

@dp.message_handler(lambda m: m.text in BUILD_MESSAGES)
async def send_build(msg: types.Message):
    await bot.send_message(REPORT_CHAT_ID, BUILD_MESSAGES[msg.text])
    await msg.answer("✅ Стройка взята!", reply_markup=main_kb)

@dp.message_handler(text="⬅️ Назад")
async def back(msg: types.Message):
    await msg.answer("Главное меню:", reply_markup=main_kb)

# ───────── ЗАПУСК ─────────
if __name__ == "__main__":
    executor.start_polling(dp, on_startup=init_db)

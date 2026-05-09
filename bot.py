import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

# ===== НАСТРОЙКИ =====
BOT_TOKEN = "8597592634:AAE-yzoBERU6wjSZO5P03VdrB2Y9jGOYG44"
ADMIN_CHAT_ID = "8746312387"

# ===== СОСТОЯНИЯ ДЛЯ СБОРА ДАННЫХ =====
class OrderState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()

# ===== ИНИЦИАЛИЗАЦИЯ =====
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# ===== КОМАНДА /START =====
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer(
        "🐔 *Добро пожаловать в Balapan chicken!* 🐔\n\n"
        "Вы сделали заказ на нашем сайте.\n"
        "Пожалуйста, укажите ваши данные для доставки.\n\n"
        "✏️ *Введите ваше имя:*",
        parse_mode="Markdown"
    )
    await OrderState.waiting_for_name.set()


# ===== ПОЛУЧЕНИЕ ИМЕНИ =====
@dp.message_handler(state=OrderState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    
    if len(name) < 2:
        await message.answer("❌ Пожалуйста, введите корректное имя (минимум 2 символа):")
        return
    
    await state.update_data(name=name)
    
    await message.answer(
        f"✅ {name}, спасибо!\n\n"
        "📞 Теперь укажите ваш *номер телефона*:\n"
        "Например: +996 700 123 456",
        parse_mode="Markdown"
    )
    await OrderState.waiting_for_phone.set()


# ===== ПОЛУЧЕНИЕ ТЕЛЕФОНА =====
@dp.message_handler(state=OrderState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    
    if len(phone) < 10:
        await message.answer("❌ Пожалуйста, введите корректный номер телефона (минимум 10 цифр):")
        return
    
    await state.update_data(phone=phone)
    
    await message.answer(
        f"📞 Номер: {phone}\n\n"
        "🏠 Теперь укажите *адрес доставки*:\n"
        "Улица, дом, квартира, подъезд, этаж",
        parse_mode="Markdown"
    )
    await OrderState.waiting_for_address.set()


# ===== ПОЛУЧЕНИЕ АДРЕСА =====
@dp.message_handler(state=OrderState.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    address = message.text.strip()
    
    if len(address) < 5:
        await message.answer("❌ Пожалуйста, введите полный адрес:")
        return
    
    user_data = await state.get_data()
    name = user_data.get("name")
    phone = user_data.get("phone")
    
    # Формируем заказ для администратора
    order_text = f"""
🆕 *НОВЫЙ ЗАКАЗ!* 🆕
──────────────────
👤 *Имя:* {name}
📞 *Телефон:* {phone}
🏠 *Адрес:* {address}
──────────────────
⏱️ *Время:* {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
──────────────────
💬 Свяжитесь с клиентом для подтверждения.
    """
    
    # Отправляем заказ администратору
    await bot.send_message(
        ADMIN_CHAT_ID,
        order_text,
        parse_mode="Markdown"
    )
    
    # Подтверждение клиенту
    await message.answer(
        "✅ *ЗАКАЗ ПРИНЯТ!* ✅\n\n"
        f"👤 {name}, мы получили ваш заказ.\n"
        f"📞 Свяжемся с вами по номеру: {phone}\n"
        f"🏠 Доставим по адресу: {address}\n\n"
        "🍗 *Спасибо, что выбрали Balapan chicken!*\n"
        "⏱️ Ожидайте звонка в ближайшее время.\n\n"
        "✨ Хорошего дня! ✨",
        parse_mode="Markdown"
    )
    
    await state.finish()


# ===== КОМАНДА /CANCEL =====
@dp.message_handler(commands=['cancel'])
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "❌ Оформление заказа отменено.\n\n"
        "Вы можете начать заново командой /start"
    )


# ===== КОМАНДА /HELP =====
@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    await message.answer(
        "🐔 *Balapan chicken - Помощь* 🐔\n\n"
        "/start - Начать оформление заказа\n"
        "/cancel - Отменить оформление заказа\n"
        "/help - Показать это сообщение\n\n"
        "📞 По вопросам: +996 XXX XXX XXX",
        parse_mode="Markdown"
    )


# ===== ЗАПУСК БОТА =====
if __name__ == "__main__":
    print("🤖 Бот Balapan chicken запущен!")
    print(f"📨 Заказы будут приходить в чат: {ADMIN_CHAT_ID}")
    executor.start_polling(dp, skip_updates=True)
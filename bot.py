import asyncio
import json
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

# Временное хранилище заказов (в памяти)
pending_orders = {}


# ===== КОМАНДА /START =====
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message, state: FSMContext):
    # Проверяем, есть ли параметр с заказом
    args = message.text.split()
    order_data = None
    
    if len(args) > 1 and args[1].startswith("order_"):
        order_id = args[1].replace("order_", "")
        # Сохраняем ID заказа в сессию
        await state.update_data(order_id=order_id)
        
        await message.answer(
            "🐔 *Добро пожаловать в Balapan chicken!* 🐔\n\n"
            "✅ *Мы получили ваш заказ с сайта!*\n\n"
            "Пожалуйста, укажите ваши данные для доставки.\n\n"
            "✏️ *Введите ваше имя:*",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "🐔 *Добро пожаловать в Balapan chicken!* 🐔\n\n"
            "Вы можете оформить заказ на нашем сайте.\n"
            "Чтобы начать оформление, нажмите кнопку 'Оформить заказ' на сайте.\n\n"
            "📞 По вопросам: +996 XXX XXX XXX",
            parse_mode="Markdown"
        )
        return
    
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
    order_id = user_data.get("order_id", "не указан")
    
    # Формируем заказ для администратора
    order_text = f"""
🆕 *НОВЫЙ ЗАКАЗ!* 🆕
──────────────────
🆔 *ID заказа:* {order_id}
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
        "Вы можете начать заново через сайт, нажав 'Оформить заказ'"
    )


# ===== КОМАНДА /HELP =====
@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    await message.answer(
        "🐔 *Balapan chicken - Помощь* 🐔\n\n"
        "1️⃣ Оформите заказ на нашем сайте\n"
        "2️⃣ Перейдите в бота для подтверждения\n"
        "3️⃣ Укажите имя, телефон и адрес\n"
        "4️⃣ Дождитесь звонка оператора\n\n"
        "📞 По вопросам: +996 XXX XXX XXX",
        parse_mode="Markdown"
    )


# ===== ЗАПУСК БОТА =====
if __name__ == "__main__":
    print("🤖 Бот Balapan chicken запущен!")
    print(f"📨 Заказы будут приходить в чат: {ADMIN_CHAT_ID}")
    executor.start_polling(dp, skip_updates=True)
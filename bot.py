import asyncio
import json
import threading
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from flask import Flask
import os

# ===== НАСТРОЙКИ (ЗАПОЛНЕНО ВАШИМИ ДАННЫМИ) =====
BOT_TOKEN = "8597592634:AAE-yzoBERU6wjSZO5P03VdrB2Y9jGOYG44"
ADMIN_CHAT_ID = "8746312387"

# ===== СОСТОЯНИЯ ДЛЯ СБОРА ДАННЫХ =====
class OrderState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_payment = State()

# ===== ИНИЦИАЛИЗАЦИЯ =====
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# ===== ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ДАННЫХ ЗАКАЗА ИЗ ССЫЛКИ =====
def parse_order_data(text):
    """Извлекает данные заказа из ссылки /start order_ID_JSON"""
    try:
        # Проверяем, есть ли order_ в тексте
        if 'order_' not in text:
            print("❌ Нет order_ в тексте")
            return None, None
        
        # Берём всё после order_
        parts = text.split('order_')
        if len(parts) < 2:
            print("❌ Нет данных после order_")
            return None, None
        
        order_part = parts[1]
        print(f"📦 order_part: {order_part[:100]}")
        
        # Находим первый underscore (разделитель между ID и JSON)
        first_underscore = order_part.find('_')
        if first_underscore == -1:
            # НЕТ JSON, значит заказ не передан — возвращаем None (НЕ показываем тестовое блюдо)
            print("❌ Нет JSON данных в ссылке")
            return None, None
        
        order_id = order_part[:first_underscore]
        json_part = order_part[first_underscore + 1:]
        
        print(f"🆔 ID заказа: {order_id}")
        print(f"📋 JSON часть: {json_part[:100]}")
        
        order_data = json.loads(json_part)
        return order_id, order_data
        
    except Exception as e:
        print(f"❌ Ошибка парсинга: {e}")
        return None, None


# ===== КОМАНДА /START =====
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message, state: FSMContext):
    text = message.text
    print(f"📨 Получена команда: {text}")
    
    order_id, order_data = parse_order_data(text)
    
    if order_data:
        print(f"✅ Заказ найден! ID: {order_id}")
        await state.update_data(order_id=order_id, order_data=order_data)
        
        items_text = ""
        for item in order_data.get('items', []):
            items_text += f"🍗 {item['title']} × {item['quantity']} = {item['sum']} ₽\n"
        
        total = order_data.get('total', 0)
        
        await message.answer(
            f"🐔 *Добро пожаловать в Balapan chicken!* 🐔\n\n"
            f"✅ *Мы получили ваш заказ с сайта!*\n\n"
            f"📋 *Ваш заказ:*\n"
            f"──────────────────\n"
            f"{items_text}"
            f"──────────────────\n"
            f"💰 *ИТОГО:* {total} ₽\n"
            f"──────────────────\n\n"
            f"✏️ *Пожалуйста, укажите ваши данные для доставки:*\n\n"
            f"📝 *Введите ваше имя:*",
            parse_mode="Markdown"
        )
        await OrderState.waiting_for_name.set()
    else:
        print("❌ Заказ не найден, показываем обычное приветствие")
        await message.answer(
            "🐔 *Добро пожаловать в Balapan chicken!* 🐔\n\n"
            "Вы можете оформить заказ на нашем сайте.\n"
            "Чтобы начать оформление, нажмите кнопку 'Оформить заказ' на сайте.\n\n"
            "📞 По вопросам: +996 XXX XXX XXX",
            parse_mode="Markdown"
        )


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
    
    await state.update_data(address=address)
    
    await message.answer(
        "💰 *Выберите способ оплаты:*\n\n"
        "1️⃣ *Наличными* при получении\n"
        "2️⃣ *Картой* при получении (терминал)\n"
        "3️⃣ *Онлайн-оплата* (перевод на карту)\n\n"
        "📝 *Введите номер способа оплаты (1, 2 или 3):*",
        parse_mode="Markdown"
    )
    await OrderState.waiting_for_payment.set()


# ===== ПОЛУЧЕНИЕ СПОСОБА ОПЛАТЫ =====
@dp.message_handler(state=OrderState.waiting_for_payment)
async def process_payment(message: types.Message, state: FSMContext):
    payment_choice = message.text.strip()
    
    payment_methods = {
        "1": "💰 Наличными при получении",
        "2": "💳 Картой при получении (терминал)",
        "3": "🏦 Онлайн-перевод на карту"
    }
    
    if payment_choice not in payment_methods:
        await message.answer("❌ Пожалуйста, введите 1, 2 или 3:")
        return
    
    payment_method = payment_methods[payment_choice]
    await state.update_data(payment=payment_method)
    
    user_data = await state.get_data()
    name = user_data.get("name")
    phone = user_data.get("phone")
    address = user_data.get("address")
    order_data = user_data.get("order_data", {})
    order_id = user_data.get("order_id", "не указан")
    
    items_text = ""
    for item in order_data.get('items', []):
        items_text += f"🍗 {item['title']} × {item['quantity']} = {item['sum']} ₽\n"
    
    total = order_data.get('total', 0)
    
    order_text = f"""
🆕 *НОВЫЙ ЗАКАЗ!* 🆕
──────────────────
🆔 *ID заказа:* {order_id}
──────────────────
📋 *БЛЮДА:*
{items_text}
──────────────────
💰 *ИТОГО:* {total} ₽
──────────────────
👤 *Имя:* {name}
📞 *Телефон:* {phone}
🏠 *Адрес:* {address}
💳 *Оплата:* {payment_method}
──────────────────
⏱️ *Время:* {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
──────────────────
💬 Свяжитесь с клиентом для подтверждения.
    """
    
    await bot.send_message(ADMIN_CHAT_ID, order_text, parse_mode="Markdown")
    
    await message.answer(
        "✅ *ЗАКАЗ ПРИНЯТ!* ✅\n\n"
        f"👤 {name}, мы получили ваш заказ.\n\n"
        f"📋 *Ваш заказ:*\n"
        f"{items_text}\n"
        f"💰 *Итого:* {total} ₽\n"
        f"💳 *Оплата:* {payment_method}\n\n"
        f"📞 Свяжемся с вами по номеру: {phone}\n"
        f"🏠 Доставим по адресу: {address}\n\n"
        "🍗 *Спасибо, что выбрали Balapan chicken!*\n"
        "⏱️ Ожидайте звонка в ближайшее время.",
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
        "4️⃣ Выберите способ оплаты\n"
        "5️⃣ Дождитесь звонка оператора\n\n"
        "📞 По вопросам: +996 XXX XXX XXX",
        parse_mode="Markdown"
    )


# ===== FLASK-СЕРВЕР ДЛЯ RENDER =====
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Balapan chicken bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=10000)


# ===== ЗАПУСК БОТА И ВЕБ-СЕРВЕРА =====
if __name__ == "__main__":
    print("🤖 Бот Balapan chicken запущен!")
    print(f"📨 Заказы будут приходить в чат: {ADMIN_CHAT_ID}")
    
    # Запускаем Flask-сервер в отдельном потоке
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    
    # Запускаем бота
    executor.start_polling(dp, skip_updates=True)
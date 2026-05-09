import asyncio
import json
import threading
from urllib.parse import unquote
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from flask import Flask
import os
import re

# ===== НАСТРОЙКИ =====
BOT_TOKEN = "8597592634:AAE-yzoBERU6wjSZO5P03VdrB2Y9jGOYG44"
ADMIN_CHAT_ID = "8746312387"

# ===== СОСТОЯНИЯ =====
class OrderState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_payment = State()

# ===== ИНИЦИАЛИЗАЦИЯ =====
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

pending_orders = {}


def save_pending_order(user_id, order_id, order_data):
    pending_orders[user_id] = {
        'order_id': order_id,
        'order_data': order_data,
        'timestamp': datetime.now()
    }


def get_pending_order(user_id):
    return pending_orders.get(user_id)


def clear_pending_order(user_id):
    if user_id in pending_orders:
        del pending_orders[user_id]


# ===== ИСПРАВЛЕННАЯ ФУНКЦИЯ ПАРСИНГА =====
def parse_start_data(text):
    """Извлекает данные из ссылки /start order_ID_JSON"""
    try:
        print(f"🔍 Парсинг: {text[:200]}")
        
        if not text or not text.startswith('/start'):
            print("❌ Не команда /start")
            return None, None
        
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            print("❌ Нет параметров")
            return None, None
        
        param = parts[1].strip()
        print(f"📦 Параметр: {param[:200]}")
        
        # Ищем order_ЦИФРЫ_ЛЮБЫЕ_СИМВОЛЫ
        match = re.search(r'order_(\d+)_(.+)', param)
        if not match:
            print("❌ Нет совпадения с order_..._...")
            return None, None
        
        order_id = match.group(1)
        encoded_json = match.group(2)
        print(f"🆔 ID: {order_id}")
        print(f"📦 Закодированный JSON: {encoded_json[:100]}")
        
        try:
            decoded_json = unquote(encoded_json)
            print(f"📋 Декодированный JSON: {decoded_json[:150]}")
        except Exception as e:
            print(f"❌ Ошибка декодирования URL: {e}")
            return None, None
        
        try:
            order_data = json.loads(decoded_json)
            print(f"✅ JSON распарсен успешно!")
            return order_id, order_data
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON: {e}")
            try:
                decoded_json2 = unquote(decoded_json)
                order_data = json.loads(decoded_json2)
                print("✅ Успех после повторного декодирования!")
                return order_id, order_data
            except Exception as e2:
                print(f"❌ Повторная попытка не удалась: {e2}")
                return None, None
        
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None, None


# ===== КОМАНДА /START =====
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text
    
    print(f"📨 /start от {user_id}: {text[:100]}")
    
    order_id, order_data = parse_start_data(text)
    
    if order_data:
        print(f"✅ Заказ получен! ID: {order_id}")
        save_pending_order(user_id, order_id, order_data)
        await show_order(message, state, order_data)
        return
    
    pending = get_pending_order(user_id)
    if pending:
        print(f"✅ Найден сохранённый заказ для {user_id}")
        order_data = pending['order_data']
        clear_pending_order(user_id)
        await show_order(message, state, order_data)
        return
    
    print("❌ Заказ не найден")
    await message.answer(
        "🐔 *Добро пожаловать в Balapan chicken!* 🐔\n\n"
        "Вы можете оформить заказ на нашем сайте.\n"
        "Чтобы начать оформление, нажмите кнопку 'Оформить заказ' на сайте.\n\n"
        "📞 По вопросам: +996 XXX XXX XXX",
        parse_mode="Markdown"
    )


async def show_order(message: types.Message, state: FSMContext, order_data):
    items_text = ""
    for item in order_data.get('items', []):
        items_text += f"🍗 {item['title']} × {item['quantity']} = {item['sum']} ₽\n"
    
    total = order_data.get('total', 0)
    
    await state.update_data(order_data=order_data)
    
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


@dp.message_handler(state=OrderState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Введите корректное имя (минимум 2 символа):")
        return
    await state.update_data(name=name)
    await message.answer(
        f"✅ {name}, спасибо!\n\n📞 Теперь укажите ваш *номер телефона*:\nНапример: +996 700 123 456",
        parse_mode="Markdown"
    )
    await OrderState.waiting_for_phone.set()


@dp.message_handler(state=OrderState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    if len(phone) < 10:
        await message.answer("❌ Введите корректный номер телефона (минимум 10 цифр):")
        return
    await state.update_data(phone=phone)
    await message.answer(
        f"📞 Номер: {phone}\n\n🏠 Теперь укажите *адрес доставки*:\nУлица, дом, квартира, подъезд, этаж",
        parse_mode="Markdown"
    )
    await OrderState.waiting_for_address.set()


@dp.message_handler(state=OrderState.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    address = message.text.strip()
    if len(address) < 5:
        await message.answer("❌ Введите полный адрес:")
        return
    await state.update_data(address=address)
    await message.answer(
        "💰 *Выберите способ оплаты:*\n\n1️⃣ Наличными при получении\n2️⃣ Картой при получении\n3️⃣ Онлайн-перевод\n\n📝 Введите 1, 2 или 3:",
        parse_mode="Markdown"
    )
    await OrderState.waiting_for_payment.set()


@dp.message_handler(state=OrderState.waiting_for_payment)
async def process_payment(message: types.Message, state: FSMContext):
    payment_choice = message.text.strip()
    payment_methods = {
        "1": "💰 Наличными при получении",
        "2": "💳 Картой при получении",
        "3": "🏦 Онлайн-перевод на карту"
    }
    if payment_choice not in payment_methods:
        await message.answer("❌ Введите 1, 2 или 3:")
        return
    
    payment_method = payment_methods[payment_choice]
    await state.update_data(payment=payment_method)
    
    user_data = await state.get_data()
    name = user_data.get("name")
    phone = user_data.get("phone")
    address = user_data.get("address")
    order_data = user_data.get("order_data", {})
    
    items_text = ""
    for item in order_data.get('items', []):
        items_text += f"🍗 {item['title']} × {item['quantity']} = {item['sum']} ₽\n"
    total = order_data.get('total', 0)
    
    order_text = f"""
🆕 *НОВЫЙ ЗАКАЗ!* 🆕
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
        f"👤 {name}, мы получили ваш заказ.\n"
        f"📞 Свяжемся с вами по номеру: {phone}\n"
        f"🏠 Доставим по адресу: {address}\n\n"
        "🍗 *Спасибо, что выбрали Balapan chicken!*\n"
        "⏱️ Ожидайте звонка в ближайшее время.",
        parse_mode="Markdown"
    )
    
    await state.finish()


@dp.message_handler(commands=['cancel'])
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("❌ Оформление заказа отменено.")


@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    await message.answer(
        "🐔 *Balapan chicken - Помощь* 🐔\n\n"
        "/start - Начать оформление\n"
        "/cancel - Отменить\n"
        "/help - Помощь",
        parse_mode="Markdown"
    )


app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Balapan chicken bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=10000)


if __name__ == "__main__":
    print("🤖 Бот Balapan chicken запущен!")
    print(f"📨 Заказы будут приходить в чат: {ADMIN_CHAT_ID}")
    
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    
    executor.start_polling(dp, skip_updates=True)
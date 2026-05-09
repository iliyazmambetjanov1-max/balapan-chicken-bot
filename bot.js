const { Telegraf, session } = require('telegraf');

// ===== НАСТРОЙКИ =====
const BOT_TOKEN = '8597592634:AAE-yzoBERU6wjSZO5P03VdrB2Y9jGOYG44';
const ADMIN_CHAT_ID = '8746312387';

// Создаём бота
const bot = new Telegraf(BOT_TOKEN);

// Включаем сессии для хранения данных пользователя
bot.use(session());

// Хранилище заказов (в памяти, для простоты)
const orders = new Map();

// ===== КОМАНДА /START =====
bot.start(async (ctx) => {
    // Инициализируем сессию пользователя
    ctx.session = { step: 'waiting_for_name' };
    
    await ctx.replyWithMarkdown(
        '🐔 *Добро пожаловать в Balapan chicken!* 🐔\n\n' +
        'Вы сделали заказ на нашем сайте.\n' +
        'Пожалуйста, укажите ваши данные для доставки.\n\n' +
        '✏️ *Введите ваше имя:*'
    );
});

// ===== ОБРАБОТКА ВСЕХ ТЕКСТОВЫХ СООБЩЕНИЙ =====
bot.on('text', async (ctx) => {
    // Если нет сессии - создаём
    if (!ctx.session) {
        ctx.session = {};
    }
    
    const step = ctx.session.step;
    const text = ctx.message.text.trim();
    
    // === ШАГ 1: ПОЛУЧЕНИЕ ИМЕНИ ===
    if (step === 'waiting_for_name') {
        if (text.length < 2) {
            await ctx.reply('❌ Пожалуйста, введите корректное имя (минимум 2 символа):');
            return;
        }
        
        ctx.session.name = text;
        ctx.session.step = 'waiting_for_phone';
        
        await ctx.replyWithMarkdown(
            `✅ ${text}, спасибо!\n\n` +
            '📞 Теперь укажите ваш *номер телефона*:\n' +
            'Например: +996 700 123 456'
        );
        return;
    }
    
    // === ШАГ 2: ПОЛУЧЕНИЕ ТЕЛЕФОНА ===
    if (step === 'waiting_for_phone') {
        if (text.length < 10) {
            await ctx.reply('❌ Пожалуйста, введите корректный номер телефона (минимум 10 цифр):');
            return;
        }
        
        ctx.session.phone = text;
        ctx.session.step = 'waiting_for_address';
        
        await ctx.replyWithMarkdown(
            `📞 Номер: ${text}\n\n` +
            '🏠 Теперь укажите *адрес доставки*:\n' +
            'Улица, дом, квартира, подъезд, этаж'
        );
        return;
    }
    
    // === ШАГ 3: ПОЛУЧЕНИЕ АДРЕСА ===
    if (step === 'waiting_for_address') {
        if (text.length < 5) {
            await ctx.reply('❌ Пожалуйста, введите полный адрес:');
            return;
        }
        
        const name = ctx.session.name;
        const phone = ctx.session.phone;
        const address = text;
        const now = new Date();
        const time = now.toLocaleString('ru-RU');
        
        // Формируем текст заказа для администратора
        const orderText =
            '🆕 *НОВЫЙ ЗАКАЗ!* 🆕\n' +
            '──────────────────\n' +
            `👤 *Имя:* ${name}\n` +
            `📞 *Телефон:* ${phone}\n` +
            `🏠 *Адрес:* ${address}\n` +
            '──────────────────\n' +
            `⏱️ *Время:* ${time}\n` +
            '──────────────────\n' +
            '💬 Свяжитесь с клиентом для подтверждения.';
        
        // Отправляем заказ администратору
        try {
            await bot.telegram.sendMessage(ADMIN_CHAT_ID, orderText, { parse_mode: 'Markdown' });
        } catch (err) {
            console.error('Ошибка отправки администратору:', err.message);
            await ctx.reply('⚠️ Произошла ошибка при отправке заказа. Пожалуйста, попробуйте позже.');
            ctx.session.step = null;
            return;
        }
        
        // Подтверждение клиенту
        await ctx.replyWithMarkdown(
            '✅ *ЗАКАЗ ПРИНЯТ!* ✅\n\n' +
            `👤 ${name}, мы получили ваш заказ.\n` +
            `📞 Свяжемся с вами по номеру: ${phone}\n` +
            `🏠 Доставим по адресу: ${address}\n\n` +
            '🍗 *Спасибо, что выбрали Balapan chicken!*\n' +
            '⏱️ Ожидайте звонка в ближайшее время.\n\n' +
            '✨ Хорошего дня! ✨'
        );
        
        // Очищаем сессию
        ctx.session.step = null;
        return;
    }
    
    // Если пользователь ввел что-то не в процессе заказа
    if (!step) {
        await ctx.replyWithMarkdown(
            '🐔 *Balapan chicken*\n\n' +
            'Чтобы оформить заказ, отправьте команду /start\n\n' +
            'Доступные команды:\n' +
            '/start - Начать оформление заказа\n' +
            '/cancel - Отменить оформление\n' +
            '/help - Помощь'
        );
    }
});

// ===== КОМАНДА /CANCEL =====
bot.command('cancel', async (ctx) => {
    if (ctx.session) {
        ctx.session.step = null;
    }
    await ctx.reply('❌ Оформление заказа отменено.\n\nВы можете начать заново командой /start');
});

// ===== КОМАНДА /HELP =====
bot.help(async (ctx) => {
    await ctx.replyWithMarkdown(
        '🐔 *Balapan chicken - Помощь* 🐔\n\n' +
        '/start - Начать оформление заказа\n' +
        '/cancel - Отменить оформление заказа\n' +
        '/help - Показать это сообщение\n\n' +
        '📞 По вопросам: +996 XXX XXX XXX'
    );
});

// ===== ЗАПУСК БОТА =====
bot.launch()
    .then(() => {
        console.log('🤖 Бот Balapan chicken запущен!');
        console.log(`📨 Заказы будут приходить в чат: ${ADMIN_CHAT_ID}`);
    })
    .catch((err) => {
        console.error('Ошибка при запуске бота:', err);
    });

// Обработка завершения процесса
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
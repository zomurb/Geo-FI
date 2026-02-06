import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram.constants import ParseMode

from config import BOT_TOKEN, ERROR_PARSING, ERROR_GENERIC
from parser import parse_input
from visualizer import plot_function, plot_geometry, plot_parametric, plot_polar, plot_3d

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Квадратичная", callback_data='ex_quad'),
            InlineKeyboardButton("Синусоида", callback_data='ex_sin')
        ],
        [
            InlineKeyboardButton("Окружность", callback_data='ex_circle'),
            InlineKeyboardButton("Примеры", callback_data='help_examples')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "👋 Привет! Я математический бот-визуализатор.\n\n"
        "Я умею:\n"
        "📈 Строить графики функций (например, `y = x^2`)\n"
        "🟢 Рисовать геометрические фигуры (например, `круг r=5`)\n\n"
        "Просто отправь мне формулу или выбери пример ниже!"
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def get_chat_id_and_reply(update: Update, text: str, reply_markup=None):
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)


async def get_message_target(update: Update):
    """Returns the message object to reply to, regardless of update type."""
    if update.message:
        return update.message
    elif update.callback_query:
        return update.callback_query.message
    return None

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 *Справка*\n\n"
        "*Алгебра:*\n"
        "Отправь формулу, например:\n"
        "`y = x^2`\n"
        "`y = sin(x) + cos(x)`\n"
        "`y = 2*x + 1; y = -x + 5` (несколько графиков)\n\n"
        "*Геометрия:*\n"
        "`круг r=5`\n"
        "`треугольник a=3 b=4 c=5`\n"
        "`прямоугольник a=5 b=3`\n"
        "`эллипс a=4 b=2`\n"
    )
    target_msg = await get_message_target(update)
    if target_msg:
        await target_msg.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def examples_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    examples_text = (
        "💡 *Примеры команд:*\n\n"
        "1. `y = x^2` (Парабола)\n"
        "2. `y = sin(x) * x` (Затухающие колебания)\n"
        "3. `y = 1/x` (Гипербола)\n"
        "4. `круг r=10`\n"
        "5. `треугольник a=3 b=4 c=5`\n"
        "6. `прямоугольник width=10 height=5`"
    )
    target_msg = await get_message_target(update)
    if target_msg:
        await target_msg.reply_text(examples_text, parse_mode=ParseMode.MARKDOWN)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text:
        return

    status_msg = await update.message.reply_text("⏳ Строю график...")

    try:
        # 1. Parse
        parse_result = parse_input(text)
        
        if parse_result['type'] == 'error':
            await status_msg.edit_text(f"❌ {parse_result['message']}")
            return

        # 2. Visualize
        img_buffer = None
        caption = ""
        
        if parse_result['type'] == 'function':
            img_buffer = plot_function(parse_result['data'])
            caption = f"📊 График по запросу: `{text}`"
            
        elif parse_result['type'] == 'parametric':
            img_buffer = plot_parametric(parse_result['data'])
            caption = f"➰ Параметрический график: `{parse_result['raw']}`"

        elif parse_result['type'] == 'polar':
            img_buffer = plot_polar(parse_result)
            caption = f"🌀 Полярный график: `{parse_result['raw']}`" # Curly loop for spiral?

        elif parse_result['type'] == '3d':
            img_buffer = plot_3d(parse_result)
            caption = f"🧊 3D График: `{parse_result['raw']}`"

        elif parse_result['type'] == 'geometry':
            img_buffer = plot_geometry(parse_result)
            caption = f"📐 Фигура по запросу: `{text}`"

        # 3. Send
        if img_buffer:
            await update.message.reply_photo(photo=img_buffer, caption=caption, parse_mode=ParseMode.MARKDOWN)
            await status_msg.delete()
        else:
             await status_msg.edit_text("❌ Не удалось построить изображение.")

    except Exception as e:
        logging.error(f"Error handling message: {e}")
        await status_msg.edit_text(f"❌ Произошла внутренняя ошибка: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    text_to_process = ""
    
    if data == 'ex_quad':
        text_to_process = "y = x^2"
    elif data == 'ex_sin':
        text_to_process = "y = sin(x)"
    elif data == 'ex_circle':
        text_to_process = "круг r=5"
    elif data == 'help_examples':
        await examples_command(update, context) 
        return
    if text_to_process:
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"Выбрано: {text_to_process}")
        
        status_msg = await context.bot.send_message(chat_id=query.message.chat_id, text="⏳ Строю график...")
        try:
            parse_result = parse_input(text_to_process)
            img_buffer = None
            if parse_result['type'] == 'function':
                img_buffer = plot_function(parse_result['data'])
            elif parse_result['type'] == 'parametric':
                img_buffer = plot_parametric(parse_result['data'])
            elif parse_result['type'] == 'polar':
                img_buffer = plot_polar(parse_result)
            elif parse_result['type'] == '3d':
                img_buffer = plot_3d(parse_result)
            elif parse_result['type'] == 'geometry':
                img_buffer = plot_geometry(parse_result)
            
            if img_buffer:
                await context.bot.send_photo(chat_id=query.message.chat_id, photo=img_buffer, caption=f"Преcет: `{text_to_process}`", parse_mode=ParseMode.MARKDOWN)
                await status_msg.delete()
        except Exception as e:
             await status_msg.edit_text(f"Error: {e}")

if __name__ == '__main__':
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN not found in .env")
        exit(1)
        
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("examples", examples_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Generic text handler
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("Bot is running...")
    application.run_polling()

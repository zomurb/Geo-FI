import logging
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram.constants import ParseMode

from config import (
    BOT_TOKEN,
    ERROR_PARSING,
    ERROR_GENERIC,
    ALGEBRA_SOLVE_TEMPLATE,
    ALGEBRA_DIFF_TEMPLATE,
    ALGEBRA_INTEGRATE_TEMPLATE,
    EXPLAIN_TEMPLATE,
    DEFAULT_3D_ELEV,
    DEFAULT_3D_AZIM,
    DEFAULT_3D_RANGE,
    DEFAULT_3D_GRID,
    DEFAULT_3D_MODE,
)
from parser import parse_input
from visualizer import plot_function, plot_geometry, plot_parametric, plot_polar, plot_3d

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

MAX_TG = 4000


def _truncate(s: str, n: int = MAX_TG) -> str:
    if s is None:
        return ""
    if len(s) <= n:
        return s
    return s[: n - 30] + "\n\n…(сообщение обрезано — начало сохранено.)"


def _default_plot3d_state():
    return {
        "elev": float(DEFAULT_3D_ELEV),
        "azim": float(DEFAULT_3D_AZIM),
        "range": float(DEFAULT_3D_RANGE),
        "grid": int(DEFAULT_3D_GRID),
        "mode": str(DEFAULT_3D_MODE),
        "contour_base": False,
    }


def _plot3d_keyboard_rows():
    return [
        [
            InlineKeyboardButton("elev +", callback_data="3d_e+"),
            InlineKeyboardButton("elev −", callback_data="3d_e-"),
            InlineKeyboardButton("azim +", callback_data="3d_a+"),
            InlineKeyboardButton("azim −", callback_data="3d_a-"),
        ],
        [
            InlineKeyboardButton("зум+", callback_data="3d_zi"),
            InlineKeyboardButton("зум−", callback_data="3d_zo"),
            InlineKeyboardButton("сброс 3D", callback_data="3d_rs"),
        ],
        [
            InlineKeyboardButton("surface", callback_data="3d_ms"),
            InlineKeyboardButton("wire", callback_data="3d_mw"),
            InlineKeyboardButton("surface+wire", callback_data="3d_mb"),
            InlineKeyboardButton("контур zmin", callback_data="3d_mc"),
        ],
    ]


def _base_keyboard_rows():
    return [
        [
            InlineKeyboardButton("Показать формулы", callback_data="show_formulas"),
            InlineKeyboardButton("Показать шаги", callback_data="show_steps"),
        ],
        [
            InlineKeyboardButton("Преобразовать фигуру", callback_data="transform_hint"),
            InlineKeyboardButton("Похожая задача", callback_data="generate_task"),
        ],
    ]


def _build_keyboard(include_3d=False):
    rows = list(_base_keyboard_rows())
    if include_3d:
        rows.extend(_plot3d_keyboard_rows())
    return InlineKeyboardMarkup(rows)


def _apply_3d_callback(data: str, st: dict) -> bool:
    if data == "3d_e+":
        st["elev"] = min(89.0, float(st.get("elev", DEFAULT_3D_ELEV)) + 12.0)
    elif data == "3d_e-":
        st["elev"] = max(-89.0, float(st.get("elev", DEFAULT_3D_ELEV)) - 12.0)
    elif data == "3d_a+":
        st["azim"] = (float(st.get("azim", DEFAULT_3D_AZIM)) + 18.0) % 360.0
    elif data == "3d_a-":
        st["azim"] = (float(st.get("azim", DEFAULT_3D_AZIM)) - 18.0) % 360.0
    elif data == "3d_zi":
        st["range"] = max(0.35, float(st.get("range", DEFAULT_3D_RANGE)) * 0.78)
    elif data == "3d_zo":
        st["range"] = min(22.0, float(st.get("range", DEFAULT_3D_RANGE)) * 1.28)
    elif data == "3d_ms":
        st["mode"] = "surface"
    elif data == "3d_mw":
        st["mode"] = "wireframe"
    elif data == "3d_mb":
        st["mode"] = "both"
    elif data == "3d_mc":
        st["contour_base"] = not bool(st.get("contour_base", False))
    elif data == "3d_rs":
        st.clear()
        st.update(_default_plot3d_state())
    else:
        return False
    st["grid"] = int(max(18, min(110, st.get("grid", DEFAULT_3D_GRID))))
    return True


def _refresh_context_cache(context: ContextTypes.DEFAULT_TYPE, text: str, pr: dict) -> None:
    """Кэш для кнопок: формулы и шаги, зависят от типа last_parse_result."""
    context.user_data["last_input"] = text
    context.user_data["last_parse_result"] = pr
    formulas = pr.get("formula_help") or ""
    steps = pr.get("steps_text") or ""
    if (not formulas) or (not steps):
        df, ds = _derive_help_from_parse(text, pr)
        if not formulas:
            formulas = df
        if not steps:
            steps = ds
    context.user_data["last_formula_help"] = formulas
    context.user_data["last_step_help"] = steps


def _derive_help_from_parse(text: str, pr: dict) -> tuple:
    t = pr.get("type")
    fml = None
    st = None
    if t == "function":
        try:
            import sympy as _sp
            parts = [f"• y = {_sp.pretty(e, use_unicode=True)}" for e in pr.get("data", [])]
        except Exception:
            parts = [str(p) for p in pr.get("data", [])]
        fml = "График: на отрезке x ∈ [-10, 10] строим y = f(x).\n" + "\n".join(parts)
        st = (
            "1) Парсер читает формулу(ы) как выражения от x.\n"
            "2) Считаем значения f(x) на сетке из 1000 точек.\n"
            "3) Между соседними точками при |Δy/Δx| > порога вставляем разрыв (как у асимптот).\n"
            f"4) Ваш запрос: {text!r}."
        )
    elif t == "parametric":
        fml = f"Параметр t: {pr.get('raw', '')} — x(t), y(t) задают кривую на плоскости."
        st = (
            "1) t пробегает от -10 до 10.\n"
            "2) Считаем (x(t), y(t)) и соединяем точки.\n"
            f"3) Запрос: {text!r}."
        )
    elif t == "polar":
        fml = "Полярные координаты: x = r(θ)cos(θ), y = r(θ)sin(θ), угол θ от 0 до 4π."
        st = "1) Находим r как функцию угла.\n2) Переводим в декартовы координаты и строим кривую.\n" + f"3) {text!r}."
    elif t == "3d":
        fml = (
            "Поверхность z = f(x, y) на прямоугольной сетке; z = f(x,y); цвет по высоте z.\n"
            "Под картинкой — кнопки: камера (elev/azim), зум окна, режим surface/wire/both, контур у zmin, сброс."
        )
        st = (
            "1) Сетка по x,y, считаем z = f(x,y).\n"
            "2) Рисуем surface и/или wireframe; опционально контур на «полу».\n"
            "3) Камера: view_init(elev, azim). Зум: меняется полуинтервал R по осям x,y.\n"
            f"4) Запрос: {text!r}."
        )
    elif t == "geometry":
        sh = pr.get("shape", "")
        fml = {
            "circle": "Окружность: площадь πR², длина 2πR; центр из запроса.",
            "triangle": "Треугольник по сторонам: площадь по формуле Герона; вершины строим по теореме косинусов.",
            "triangle_points": "По трём точкам: площадь многоугольника (для треугольника) и центры (G, I, O) по координатам.",
            "line_points": "Прямая через две точки: y − y₁ = k(x − x₁), если не вертикаль; длина отрезка — расстояние между точками.",
            "polygon_points": "Площадь многоугольника по «шнуровке’ (trapezoid); периметр — сумма сторон.",
            "rectangle": "Прямоугольник: площадь a·b, периметр 2(a+b).",
            "ellipse": "Эллипс: площадь πab (полуоси a, b), периметр оценка Рамануджана в тексте к фигуре.",
        }.get(sh, "Геометрия: стандартные формулы плоскости для данной фигуры.")
        tr = pr.get("transformations") or []
        if tr:
            fml += "\nПреобразования применяются в порядке: сдвиг → (на ваше усмотрение комбинировать) rotate/scale/reflect."
        st = f"1) Распознана фигура: {sh}.\n2) Считаем вершины/параметры и рисуем с подписями.\n3) {text!r}."
    else:
        fml = st = ""
    return fml or "Нет стандартного текста — см. ответ бота.", st or f"См. последний ответ. Запрос: {text!r}."


def _transform_hint_for(pr: dict, last_text: str) -> str:
    if pr.get("type") != "geometry":
        return (
            "Преобразования (сдвиг, поворот, масштаб, отражение) работают с геометрией. "
            "Сначала отправь, например: многоугольник (0,0),(2,0),(1,1), "
            "а справа от `|` — rotate=15 translate dx=1 dy=0"
        )
    sh = pr.get("shape", "")
    base = (last_text or "").split("|", 1)[0].strip()
    ex = f"{base} | rotate=20 translate dx=1 dy=0" if base else "многоугольник (0,0),(2,0),(1,2) | rotate=20 scale=1.1"
    if sh in ("polygon_points", "triangle_points"):
        return f"К той же фигуре достаточно добавить хвост после `|`. Пример (на основе твоего запроса):\n{ex}"
    if sh in ("line_points",):
        return "Для отрезка/прямой: поверни точки, как многоугольник из 2 вершин нельзя — используй `многоугольник` или `треугольник` с вершинами, либо примени преобразование вручную, скопировав координаты в многоугольник."
    return f"Попробуй: {ex}"


def _similar_task_suggestion(pr: dict) -> str:
    t = pr.get("type")
    if t == "algebra":
        op = pr.get("operation")
        if op == "solve":
            return "Похожее: реши: 2*x^2 - 3*x - 2 = 0"
        if op == "diff":
            return "Похожее: diff: sin(x) * x"
        if op == "integrate":
            return "Похожее: интеграл: 1/x"
        if op == "explain":
            return "Похожее: объясни: x^2 - 2*x - 3"
    if t == "function":
        return "Похожее: y = tan(x) / (x+1)   или  y = 2*x^2 - 3*x; y = -x+1"
    if t == "3d":
        return "Похожее: z = sin(sqrt(x^2+y^2))   или  z = 4 - x^2 - y^2"
    if t == "parametric":
        return "Похожее: x = t*cos(t), y = t*sin(t)"
    if t == "polar":
        return "Похожее: r = 1 + 0.5*cos(3*t)"
    if t == "geometry":
        sh = pr.get("shape")
        if sh == "triangle_points":
            return "Похожее: треугольник A(1,1) B(4,0) C(2,3)"
        if sh == "circle":
            return "Похожее: круг центр(-1,2) r=3"
        return "Похожее: многоугольник (0,0),(2,0),(2,1),(0,1)"
    return "Попробуй: реши: x+2=5  или  z = x^2 + y^2"


def _format_algebra_message(pr: dict) -> str:
    op = pr.get("operation")
    res = pr.get("result")
    steps = pr.get("steps_text", "") or ""
    if op == "solve":
        head = ALGEBRA_SOLVE_TEMPLATE.format(result=res)
    elif op == "diff":
        head = ALGEBRA_DIFF_TEMPLATE.format(result=res)
    elif op == "integrate":
        head = ALGEBRA_INTEGRATE_TEMPLATE.format(result=res)
    elif op == "explain":
        ro = res
        head = EXPLAIN_TEMPLATE.format(
            expr=ro.get("expr"),
            roots=ro.get("roots"),
            derivative=ro.get("derivative"),
        )
    else:
        head = str(res)
    block = f"{head}\n\n{steps}".strip()
    return _truncate(block)


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
        "👋 Привет! Я Геомма, математический бот-визуализатор.\n\n"
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
        "📖 *Подробная справка*\n\n"
        "Я Геомма, математический бот, поддерживающий построение графиков и геометрических фигур.\n\n"
        "🔢 *Алгебра (Графики)*\n"
        "• Функция 2D: просто отправьте формулу, например: `y = x^2`\n"
        "• Несколько функций: разделите их: `y = x; y = x^2`\n"
        "• Параметрические кривые: `x = cos(t), y = sin(t)`\n"
        "• Полярные координаты: `r = 1 + cos(t)`\n"
        "• Решение уравнений: `реши: x^2 - 4 = 0`\n\n"
        "🧊 *Графики 3D*\n"
        "• Например: `z = x^2 + y^2` (можно вращать и менять зум)\n\n"
        "📐 *Геометрия*\n"
        "• Окружность: `круг r=5`\n"
        "• Треугольник: `треугольник a=3 b=4 c=5` или `треугольник (0,0),(3,0),(0,4)`\n"
        "• Прямоугольник: `прямоугольник a=5 b=3`\n\n"
        "⚙️ *Преобразования*\n"
        "• Добавьте `|` в конце: `треугольник a=3 b=4 c=5 | rotate=45`\n\n"
        "Выберите нужное действие ниже:"
    )
    keyboard = [
        [
            InlineKeyboardButton("🚀 Начать", callback_data='help_start'),
            InlineKeyboardButton("💡 Примеры", callback_data='help_examples')
        ],
        [
            InlineKeyboardButton("💬 Оставить отзыв / предложение", callback_data='help_feedback')
        ]
    ]
    target_msg = await get_message_target(update)
    if target_msg:
        await target_msg.reply_text(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['awaiting_feedback'] = True
    text = "📝 Оставьте свой отзыв или предложение следующим сообщением.\nМы обязательно всё прочитаем!"
    target_msg = await get_message_target(update)
    if target_msg:
        await target_msg.reply_text(text)

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

    if context.user_data.get('awaiting_feedback'):
        context.user_data['awaiting_feedback'] = False
        await update.message.reply_text("✅ Спасибо за ваш отзыв! Мы учтём его в будущих обновлениях.")
        return

    status_msg = await update.message.reply_text("⏳ Строю график...")

    try:
        # 1. Parse
        parse_result = parse_input(text)
        
        if parse_result['type'] == 'error':
            await status_msg.edit_text(f"❌ {ERROR_PARSING}\n{parse_result['message']}")
            return

        _refresh_context_cache(context, text, parse_result)

        # 2. Visualize
        img_buffer = None
        caption = ""
        keyboard = _build_keyboard()
        
        if parse_result['type'] == 'function':
            img_buffer = await asyncio.to_thread(plot_function, parse_result['data'])
            caption = f"📊 График по запросу: {text}"
            
        elif parse_result['type'] == 'parametric':
            img_buffer = await asyncio.to_thread(plot_parametric, parse_result['data'])
            caption = f"➰ Параметрический график: {parse_result['raw']}"

        elif parse_result['type'] == 'polar':
            img_buffer = await asyncio.to_thread(plot_polar, parse_result)
            caption = f"🌀 Полярный график: {parse_result['raw']}"

        elif parse_result['type'] == '3d':
            context.user_data["plot3d"] = _default_plot3d_state()
            st = context.user_data["plot3d"]
            img_buffer = await asyncio.to_thread(
                plot_3d,
                parse_result,
                elev=st["elev"],
                azim=st["azim"],
                range_val=st["range"],
                grid_n=st["grid"],
                mode=st["mode"],
                contour_base=st["contour_base"],
            )
            caption = f"🧊 3D График: {parse_result['raw']}"
            keyboard = _build_keyboard(include_3d=True)

        elif parse_result['type'] == 'geometry':
            img_buffer = await asyncio.to_thread(plot_geometry, parse_result)
            caption = f"📐 Фигура по запросу: {text}"
        elif parse_result['type'] == 'algebra':
            response = _format_algebra_message(parse_result)
            await status_msg.edit_text(response, reply_markup=keyboard)
            return

        # 3. Send
        if img_buffer:
            await update.message.reply_photo(photo=img_buffer, caption=caption, reply_markup=keyboard)
            await status_msg.delete()
        else:
            await status_msg.edit_text(f"❌ {ERROR_GENERIC}")

    except Exception as e:
        logging.error(f"Error handling message: {e}")
        await status_msg.edit_text(f"❌ {ERROR_GENERIC}")

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
    elif data == 'help_start':
        await start(update, context)
        return
    elif data == 'help_feedback':
        await feedback_command(update, context)
        return
    elif data == "show_formulas":
        f = context.user_data.get("last_formula_help")
        if not f:
            pr = context.user_data.get("last_parse_result")
            t = context.user_data.get("last_input", "")
            if pr:
                f, _ = _derive_help_from_parse(t, pr)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=_truncate(f or "Сначала отправьте любую задачу боту — тогда здесь появятся формулы для последнего ответа."),
        )
        return
    elif data == "show_steps":
        s = context.user_data.get("last_step_help")
        if not s:
            pr = context.user_data.get("last_parse_result")
            t = context.user_data.get("last_input", "")
            if pr:
                _, s = _derive_help_from_parse(t, pr)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=_truncate(s or "Сначала отправьте задачу — по шагам расписывается последний успешный запрос."),
        )
        return
    elif data == "transform_hint":
        pr = context.user_data.get("last_parse_result") or {}
        last = context.user_data.get("last_input", "")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=_truncate(_transform_hint_for(pr, last)),
        )
        return
    elif data == "generate_task":
        pr = context.user_data.get("last_parse_result") or {}
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=_similar_task_suggestion(pr),
        )
        return
    elif data.startswith("3d_"):
        pr = context.user_data.get("last_parse_result") or {}
        if pr.get("type") != "3d":
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Сначала отправьте 3D: z = f(x, y), например: z = x^2 + y^2",
            )
            return
        st = context.user_data.get("plot3d")
        if st is None:
            st = _default_plot3d_state()
            context.user_data["plot3d"] = st
        if not _apply_3d_callback(data, st):
            return
        status_msg = await context.bot.send_message(chat_id=query.message.chat_id, text="⏳ Пересчёт 3D...")
        try:
            img_buffer = await asyncio.to_thread(
                plot_3d,
                pr,
                elev=st["elev"],
                azim=st["azim"],
                range_val=st["range"],
                grid_n=st["grid"],
                mode=st["mode"],
                contour_base=st["contour_base"],
            )
            cap = (
                f"🧊 3D: {pr.get('raw', '')}\n"
                f"elev={st['elev']:.0f}° azim={st['azim']:.0f}° | окно ±{st['range']:.2f} | "
                f"сетка {st['grid']} | {st['mode']} | контур_у_основания={st['contour_base']}"
            )
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=img_buffer,
                caption=cap,
                reply_markup=_build_keyboard(include_3d=True),
            )
            await status_msg.delete()
        except Exception as e:
            logging.error(f"3d callback: {e}")
            await status_msg.edit_text(f"❌ {ERROR_GENERIC}")
        return
    if text_to_process:
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"Выбрано: {text_to_process}")
        
        status_msg = await context.bot.send_message(chat_id=query.message.chat_id, text="⏳ Строю график...")
        try:
            parse_result = parse_input(text_to_process)
            if parse_result['type'] == 'error':
                await status_msg.edit_text(f"❌ {ERROR_PARSING}\n{parse_result['message']}")
                return
            _refresh_context_cache(context, text_to_process, parse_result)
            img_buffer = None
            if parse_result['type'] == 'function':
                img_buffer = await asyncio.to_thread(plot_function, parse_result['data'])
            elif parse_result['type'] == 'parametric':
                img_buffer = await asyncio.to_thread(plot_parametric, parse_result['data'])
            elif parse_result['type'] == 'polar':
                img_buffer = await asyncio.to_thread(plot_polar, parse_result)
            elif parse_result['type'] == '3d':
                context.user_data["plot3d"] = _default_plot3d_state()
                st = context.user_data["plot3d"]
                img_buffer = await asyncio.to_thread(
                    plot_3d,
                    parse_result,
                    elev=st["elev"],
                    azim=st["azim"],
                    range_val=st["range"],
                    grid_n=st["grid"],
                    mode=st["mode"],
                    contour_base=st["contour_base"],
                )
            elif parse_result['type'] == 'geometry':
                img_buffer = await asyncio.to_thread(plot_geometry, parse_result)
            
            if img_buffer:
                kbd = _build_keyboard(include_3d=(parse_result.get("type") == "3d"))
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=img_buffer,
                    caption=f"Пресет: {text_to_process}",
                    reply_markup=kbd,
                )
                await status_msg.delete()
            else:
                await status_msg.edit_text(f"❌ {ERROR_GENERIC}")
        except Exception as e:
            logging.error(f"Error handling button: {e}")
            await status_msg.edit_text(f"❌ {ERROR_GENERIC}")

async def post_init(app: Application):
    await app.bot.set_my_commands([
        BotCommand("start", "Запустить бота"),
        BotCommand("help", "Подробная справка"),
        BotCommand("examples", "Примеры команд"),
        BotCommand("feedback", "Оставить отзыв или предложение")
    ])

if __name__ == '__main__':
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN not found in .env")
        exit(1)
        
    application = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("examples", examples_command))
    application.add_handler(CommandHandler("feedback", feedback_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Generic text handler
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("Bot is running...")
    application.run_polling()

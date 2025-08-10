import json
import os
import asyncio
import random
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, Message
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

with open("civs.json", "r", encoding="utf-8") as f:
    all_civs = set(json.load(f))

players = []
player_bans = {}
player_choices = {}
bans = set()
sent_messages = []
num_players = 0
ban_stage = False
ban_queue = []
ban_message: Message = None
MAX_BANS_PER_PLAYER = 2
CIVS_PER_PLAYER = 3
WORLD_AGE = None
SEA_LEVEL = None

# 🚀 Старт игры — сброс и запуск меню выбора
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global players, player_bans, player_choices, bans, num_players, ban_stage, ban_queue, ban_message, sent_messages
    # Reset game state
    players = []
    player_bans = {}
    player_choices = {}
    bans = set()
    num_players = 0
    ban_stage = False
    ban_queue = []
    ban_message = None
    # Clear tracked messages
    sent_messages.clear()

    # Welcome message and instructions
    chat_id = update.message.chat.id
    if update.message.chat.type == "private":
        sent = await context.bot.send_message(chat_id=chat_id, text=(
            "👋 Добро пожаловать, залетай в наш телеграм-чат для игры с проверенными цивилизаторами.\n"
            "👉 https://t.me/+z2TNnnTy2qs2Mzhi 🔥\n\n"
            "А ещё там я помогу с банами и пиками. Просто нажми /start в этой группе."
        ))
        sent_messages.append(sent)

    # Prompt for number of players
    keyboard = [
        [InlineKeyboardButton(str(i), callback_data=f"players|{i}") for i in range(1, 7)]
    ]
    sent = await context.bot.send_message(chat_id=chat_id, text="🔄 Игра сброшена.\nВыберите количество игроков:", reply_markup=InlineKeyboardMarkup(keyboard))
    sent_messages.append(sent)

# 🔘 Обработка кнопок автобана
async def handle_autoban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bans
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat.id

    if data == "autoban1_yes":
        bans.update(["Spain", "Venice"])
    if data.startswith("autoban1_"):
        # Ask second stage autoban question
        keyboard = [[InlineKeyboardButton("Да", callback_data="autoban2_yes"), InlineKeyboardButton("Нет", callback_data="autoban2_no")]]
        sent = await context.bot.send_message(chat_id=chat_id, text="Добавить ли Данию, Вавилон, Корею и Полинезию в автобан?", reply_markup=InlineKeyboardMarkup(keyboard))
        sent_messages.append(sent)
    elif data == "autoban2_yes":
        bans.update(["Denmark", "Babylon", "Korea", "Polynesia"])
        # Ask for number of bans per player
        keyboard = [[InlineKeyboardButton(str(i), callback_data=f"bans|{i}") for i in range(1, 6)]]
        sent = await context.bot.send_message(chat_id=chat_id, text="Выберите количество банов на игрока:", reply_markup=InlineKeyboardMarkup(keyboard))
        sent_messages.append(sent)
    elif data == "autoban2_no":
        # Ask for number of bans per player
        keyboard = [[InlineKeyboardButton(str(i), callback_data=f"bans|{i}") for i in range(1, 6)]]
        sent = await context.bot.send_message(chat_id=chat_id, text="Выберите количество банов на игрока:", reply_markup=InlineKeyboardMarkup(keyboard))
        sent_messages.append(sent)

# ⚙️ Обработка выбора игроков, банов и пиков
async def setup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global num_players, MAX_BANS_PER_PLAYER, CIVS_PER_PLAYER, players, player_bans, bans, player_choices, ban_stage
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat.id

    if data.startswith("players|"):
        # Number of players selected
        num_players = int(data.split("|")[1])
        # Ask about autoban Spain and Venice
        keyboard = [[InlineKeyboardButton("Да", callback_data="autoban1_yes"), InlineKeyboardButton("Нет", callback_data="autoban1_no")]]
        sent = await context.bot.send_message(chat_id=chat_id, text="Добавить ли Испанию и Венецию в автобан?", reply_markup=InlineKeyboardMarkup(keyboard))
        sent_messages.append(sent)

    elif data.startswith("bans|"):
        # Number of bans per player selected
        MAX_BANS_PER_PLAYER = int(data.split("|")[1])
        keyboard = [[InlineKeyboardButton(str(i), callback_data=f"picks|{i}") for i in range(1, 6)]]
        sent = await context.bot.send_message(chat_id=chat_id, text="Выберите количество наций на выбор:", reply_markup=InlineKeyboardMarkup(keyboard))
        sent_messages.append(sent)

    elif data.startswith("picks|"):
        # Number of picks per player selected
        CIVS_PER_PLAYER = int(data.split("|")[1])
        # Ask about random world settings
        keyboard = [[InlineKeyboardButton("Да", callback_data="worldsettings_yes"), InlineKeyboardButton("Нет", callback_data="worldsettings_no")]]
        text = ("💡 Только пацаны с нетрадиционной ориентацией играют всё время на 3 млрд и низком уровне моря.\n"
                "Хочешь, я зарандомлю вам эти настройки?")
        sent = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        sent_messages.append(sent)
        return  # Wait for world settings response

async def handle_worldsettings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global WORLD_AGE, SEA_LEVEL
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat.id

    if data == "worldsettings_yes":
        WORLD_AGE = random.choice(["3 миллиарда лет", "4 миллиарда лет"])
        SEA_LEVEL = random.choice(["Низкий", "Средний"])
    else:
        WORLD_AGE = "по умолчанию"
        SEA_LEVEL = "по умолчанию"

    # Prompt players to join
    keyboard = [[InlineKeyboardButton("🎮 ИГРАЮ", callback_data="join")]]
    text = (f"🎮 Игра будет на {num_players} игроков.\n"
            f"Каждому по {MAX_BANS_PER_PLAYER} бана и {CIVS_PER_PLAYER} нации на выбор.\n"
            "Нажми кнопку ниже, чтобы присоединиться.")
    sent = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))
    sent_messages.append(sent)

# ➕ Присоединение к игре
async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user.username
    chat_id = query.message.chat.id

    if not user:
        sent = await context.bot.send_message(chat_id=chat_id, text="У тебя нет username в Telegram. Установи его, чтобы участвовать.")
        sent_messages.append(sent)
        return

    global ban_stage

    if num_players == 0:
        sent = await context.bot.send_message(chat_id=chat_id, text="Сначала введите количество игроков.")
        sent_messages.append(sent)
        return

    if user in players:
        sent = await context.bot.send_message(chat_id=chat_id, text=f"@{user}, ты уже в игре.")
        sent_messages.append(sent)
        return

    if len(players) >= num_players:
        sent = await context.bot.send_message(chat_id=chat_id, text="Максимальное количество игроков уже в игре.")
        sent_messages.append(sent)
        return

    # Add player
    players.append(user)
    sent = await context.bot.send_message(chat_id=chat_id, text=f"✅ @{user} присоединился ({len(players)}/{num_players})")
    sent_messages.append(sent)

    # If all players joined, start ban process
    if len(players) == num_players:
        sent = await context.bot.send_message(chat_id=chat_id, text="✅ Все игроки заняли свои места.")
        sent_messages.append(sent)
        await start_ban_process(update, context)

# 🔁 Запуск очереди банов
async def start_ban_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ban_queue, ban_stage
    ban_stage = True
    # Prepare ban queue (each player repeats for number of bans)
    ban_queue = [p for p in players] * MAX_BANS_PER_PLAYER

    # Determine chat id
    if hasattr(update, 'message') and update.message:
        chat_id = update.message.chat.id
    else:
        chat_id = update.callback_query.message.chat.id

    # Prepare list of autobanned civs for display
    autoban_list = []
    if "Spain" in bans:
        autoban_list.append("Spain")
    if "Venice" in bans:
        autoban_list.append("Venice")
    for civ in ["Denmark", "Babylon", "Korea", "Polynesia"]:
        if civ in bans:
            autoban_list.append(civ)

    # Send game settings summary
    text = f"🎮 *Настройки игры:*\n👥 Игроков: {num_players}\n"
    text += "👤 Список: " + ", ".join(f"@{p}" for p in players) + "\n"
    text += f"🚫 Автобан: {', '.join(autoban_list) if autoban_list else 'нет'}\n"
    text += f"❌ Банов на игрока: {MAX_BANS_PER_PLAYER}\n"
    text += f"🎯 Наций на выбор: {CIVS_PER_PLAYER}\n\n"
    text += f"🌍 Возраст мира: {WORLD_AGE}\n"
    text += f"🌊 Уровень моря: {SEA_LEVEL}\n\n"
    text += "📌 Ознакомьтесь с настройками — через 5 секунд начнется фаза банов."
    sent = await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
    sent_messages.append(sent)

    # Wait and start ban phase
    await asyncio.sleep(5)
    sent = await context.bot.send_message(chat_id=chat_id, text="🚫 Начинается фаза банов цивилизаций. Удачи! 🎲")
    sent_messages.append(sent)
    await next_ban_turn(update, context)

async def next_ban_turn(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    global ban_queue, ban_message

    # Determine chat id
    if hasattr(update_or_query, "message") and update_or_query.message:
        chat_id = update_or_query.message.chat.id
    elif hasattr(update_or_query, "callback_query") and update_or_query.callback_query:
        chat_id = update_or_query.callback_query.message.chat.id
    else:
        raise ValueError("Невозможно определить chat_id")

    # If no more bans, proceed to assignment
    if not ban_queue:
        sent = await context.bot.send_message(chat_id=chat_id, text="✅ Все цивилизации забанены. Распределяем нации...")
        sent_messages.append(sent)
        await assign_civs(update_or_query, context)
        return

    # Next ban: current player is first in queue
    current_player = ban_queue.pop(0)
    available = sorted(list(all_civs - bans))

    # Build ban choices keyboard
    keyboard = []
    row = []
    for i, civ in enumerate(available):
        row.append(InlineKeyboardButton(civ, callback_data=f"ban|{current_player}|{civ}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    # Add a dummy button indicating whose turn it is
    keyboard.append([InlineKeyboardButton(f"‼️ @{current_player.upper()} ➤ ВЫБИРАЕТ БАН ‼️", callback_data="none")])

    # Send ban prompt
    sent = await context.bot.send_message(chat_id=chat_id, text=f"🚫 @{current_player}, выбери цивилизацию для бана:", reply_markup=InlineKeyboardMarkup(keyboard))
    ban_message = sent

# ✅ Обработка кнопки бана
async def handle_ban_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bans, player_bans, ban_message
    query = update.callback_query
    await query.answer()
    data = query.data
    if not data.startswith("ban|"):
        return
    _, expected_user, civ = data.split("|")
    actual_user = query.from_user.username
    chat_id = query.message.chat.id

    if actual_user != expected_user:
        await query.answer("⛔ Сейчас не твой ход", show_alert=True)
        return
    if civ in bans:
        await query.answer("Эта нация уже забанена", show_alert=True)
        return

    # Ban the civ
    bans.add(civ)
    player_bans.setdefault(actual_user, []).append(civ)

    # Delete the ban prompt message
    try:
        await ban_message.delete()
    except Exception:
        pass

    # Acknowledge ban
    sent = await context.bot.send_message(chat_id=chat_id, text=f"✅ @{actual_user} забанил {civ}")
    sent_messages.append(sent)

    # Continue to next ban turn
    await next_ban_turn(update, context)

# 🎯 Распределение наций и финальный вывод
async def assign_civs(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    # Determine chat id
    if hasattr(update_or_query, "message") and update_or_query.message:
        chat_id = update_or_query.message.chat.id
    else:
        chat_id = update_or_query.callback_query.message.chat.id

    # Assign civs to players
    available_civs = list(all_civs - bans)
    random.shuffle(available_civs)
    for player in players:
        picks = available_civs[:CIVS_PER_PLAYER]
        player_choices[player] = picks
        del available_civs[:CIVS_PER_PLAYER]

    # Thinking message
    sent = await context.bot.send_message(chat_id=chat_id, text="⌛ Дайте мне 5 секунд, я думаю...")
    sent_messages.append(sent)
    await asyncio.sleep(5)

    # Prepare final summary message
    lines = []
    lines.append("🎮 *Финальные настройки игры:*")
    lines.append(f"👥 Игроков: {num_players}")
    lines.append("👤 Список: " + ", ".join(f"@{p}" for p in players))

    # Autobans list for final
    autoban_list = []
    if "Spain" in bans: autoban_list.append("Spain")
    if "Venice" in bans: autoban_list.append("Venice")
    for civ in ["Denmark", "Babylon", "Korea", "Polynesia"]:
        if civ in bans: autoban_list.append(civ)
    lines.append(f"🚫 Автобан: {', '.join(autoban_list) if autoban_list else '—'}")

    lines.append(f"❌ Банов на игрока: {MAX_BANS_PER_PLAYER}")
    lines.append(f"🎯 Наций на выбор: {CIVS_PER_PLAYER}")
    lines.append("")
    lines.append(f"🌍 Возраст мира: {WORLD_AGE}")
    lines.append(f"🌊 Уровень моря: {SEA_LEVEL}")
    lines.append("")

    # Ban phase summary
    lines.append("🛡️ *Фаза банов:*")
    for player in players:
        bans_list = player_bans.get(player, [])
        lines.append(f"🔻 @{player} → {', '.join(bans_list) if bans_list else '—'}")
    lines.append("")

    # Picks phase summary
    lines.append("🎯 *Фаза пиков:*")
    for player in players:
        picks = player_choices.get(player, [])
        lines.append(f"✅ @{player} → {', '.join(picks) if picks else '—'}")
    lines.append("")
    lines.append("🏁 Удачной игры!")

    # Delete intermediate messages
    for msg in sent_messages:
        try:
            await context.bot.delete_message(chat_id=msg.chat.id, message_id=msg.message_id)
        except Exception:
            pass
    sent_messages.clear()

    # Send final summary
    await context.bot.send_message(chat_id=chat_id, text="\n".join(lines), parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """📖 *Civ5 Picker Бот — инструкция:*

1️⃣ Напиши /start — бот сбросит текущую игру и начнёт настройку.
2️⃣ Укажи количество игроков, автобаны, число банов и пиков.
3️⃣ Нажми 🎮 ИГРАЮ, чтобы войти в список игроков.
4️⃣ После набора игроков появится окно с настройками, затем начнётся фаза банов.
5️⃣ После банов каждый игрок получит свои варианты наций.

❗ У всех участников должен быть *username* в Telegram.
🔁 Повторный запуск — /start
❓ Справка — /h"""
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Неизвестная команда. Напиши /start или /h для помощи.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("h", help_command))
    app.add_handler(CallbackQueryHandler(handle_worldsettings, pattern="^worldsettings_"))
    app.add_handler(CallbackQueryHandler(join, pattern="^join$"))
    app.add_handler(CallbackQueryHandler(handle_autoban, pattern="^autoban[12]?_"))
    app.add_handler(CallbackQueryHandler(setup_callback, pattern=r"^(players|bans|picks)\|"))
    app.add_handler(CallbackQueryHandler(handle_ban_callback, pattern=r"^ban\|"))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\+$"), join))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))
    app.run_polling()

"""
Shadow Hunters — Complete Handlers
All commands: profile, stats, upgrade, daily, quests, gate, dungeon,
battle (PvP), gacha, inventory, hunters, weapons, equip, team, shop,
buy, top, pvp_top, guild, skills — with Pokemon-style interactive battle UI.
"""

import asyncio
import random
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import config
import database.db as db
from database.player_crud import (
    get_or_create_player, get_player, update_player,
    add_exp, claim_daily, upgrade_stat,
    get_leaderboard, get_pvp_leaderboard,
    get_inventory, add_to_inventory,
    update_quest_progress, generate_daily_quests,
    recalculate, get_exp_required, get_rank,
)
from systems.dungeon import (
    start_dungeon_session, build_battle_text,
    process_dungeon_action, DUNGEON_SESSIONS,
)
from systems.gacha import do_hunter_summon, do_weapon_summon, format_hunter_result, format_weapon_result
from battles.engine import (
    player_to_combatant, run_pvp, Combatant,
    run_pve, monster_to_combatant,
)
from systems.skills import (
    ALL_SKILLS, DEFAULT_SKILLS, RARITY_COLORS,
    get_unlocked_skills, get_skill, format_skill_card, RANK_ORDER,
)

router = Router()

# ─── FSM STATES ───────────────────────────────────────────────────────────────

class BattleState(StatesGroup):
    in_battle   = State()
    in_dungeon  = State()

class GuildState(StatesGroup):
    creating = State()

# ─── ACTIVE BATTLES (in-memory) ───────────────────────────────────────────────
# { chat_id: { attacker_id, defender_id, atk_combatant, dfn_combatant, round, log } }
ACTIVE_BATTLES: dict = {}

# ─── HELPERS ──────────────────────────────────────────────────────────────────

RANK_EMOJIS = config.RANK_EMOJIS

def hp_bar(hp, max_hp, width=10):
    ratio = max(0, hp / max_hp) if max_hp > 0 else 0
    filled = int(ratio * width)
    bar = "█" * filled + "░" * (width - filled)
    if ratio > 0.6:   color = "🟩"
    elif ratio > 0.3: color = "🟨"
    else:             color = "🟥"
    return f"{color}[{bar}]"

def rank_emoji(rank): return RANK_EMOJIS.get(rank, "⬛")

async def banned_check(msg: Message, player: dict) -> bool:
    if player and player.get("is_banned"):
        await msg.answer("🚫 You are banned from Shadow Hunters.")
        return True
    return False

def skill_buttons(equipped: list, available_skills: list) -> InlineKeyboardMarkup:
    """Build inline keyboard with player's 4 equipped skills."""
    buttons = []
    for sid in equipped[:4]:
        sk = ALL_SKILLS.get(sid)
        if sk:
            buttons.append(InlineKeyboardButton(
                text=f"{sk['name']} (💧{sk['mana_cost']})",
                callback_data=f"battle_skill:{sid}"
            ))
    if len(buttons) % 2 != 0:
        buttons.append(InlineKeyboardButton(text="⚡ Basic Attack", callback_data="battle_skill:basic"))
    rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    if not rows:
        rows = [[InlineKeyboardButton(text="⚡ Basic Attack", callback_data="battle_skill:basic")]]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def gate_buttons() -> InlineKeyboardMarkup:
    gates = list(config.GATE_CONFIG.keys())
    rows = []
    for i in range(0, len(gates), 2):
        row = []
        for g in gates[i:i+2]:
            cfg = config.GATE_CONFIG[g]
            row.append(InlineKeyboardButton(
                text=f"{cfg['emoji']} {g} (⚡{cfg['stamina_cost']})",
                callback_data=f"gate_enter:{g}"
            ))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="❌ Cancel", callback_data="gate_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def confirm_buttons(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Confirm", callback_data=f"confirm:{action}"),
        InlineKeyboardButton(text="❌ Cancel",  callback_data="cancel"),
    ]])

# ─── /start ───────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if player.get("is_banned"):
        await msg.answer("🚫 You are banned.")
        return

    re = rank_emoji(player["rank"])
    text = (
        f"╔══════════════════════╗\n"
        f"   🌑 <b>SHADOW HUNTERS ONLINE</b> 🌑\n"
        f"╚══════════════════════╝\n\n"
        f"🩸 <b>Hunter Awakened!</b>\n\n"
        f"🧿 Hunter: <b>{msg.from_user.first_name}</b>\n"
        f"🆔 ID: <code>{msg.from_user.id}</code>\n\n"
        f"{re} Rank: <b>{player['rank']}-Rank Hunter</b>\n"
        f"⚔️ Combat Power: <b>{player['combat_power']:,}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🌌 <i>The gates have cracked open.\n"
        f"Monsters pour into our world.\n"
        f"Only hunters can stop them.\n\n"
        f"You have awakened your power.\n"
        f"Rise, Shadow Hunter.</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 <b>Starter Stats</b>\n"
        f"💪 Strength: <b>{player['strength']}</b>  "
        f"⚡ Agility: <b>{player['agility']}</b>\n"
        f"🎯 Precision: <b>{player['precision']}</b>  "
        f"🧠 Intelligence: <b>{player['intelligence']}</b>\n"
        f"❤️ Vitality: <b>{player['vitality']}</b>  "
        f"🛡 Endurance: <b>{player['endurance']}</b>\n"
        f"🍀 Luck: <b>{player['luck']}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎁 <b>Starter Rewards</b>\n"
        f"💰 Coins: <b>1,000</b>\n"
        f"🎫 Tickets: <b>5</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🗡 <i>\"I alone level up.\"</i>\n\n"
        f"Type /help to begin your journey."
    )
    await msg.answer(text, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())

# ─── /help ────────────────────────────────────────────────────────────────────

@router.message(Command("help"))
async def cmd_help(msg: Message):
    text = (
        "╔══════════════════════╗\n"
        "   🌑 <b>SHADOW HUNTERS COMMANDS</b> 🌑\n"
        "╚══════════════════════╝\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👤 <b>PROFILE</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "/profile — View your hunter card\n"
        "/stats — Detailed stat breakdown\n"
        "/upgrade — Spend stat points\n"
        "/daily — Claim daily rewards\n"
        "/quests — View daily quests\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚔️ <b>COMBAT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "/gate — Enter a gate (PvE)\n"
        "/dungeon — Dungeon shortcut\n"
        "/battle @user — Challenge a hunter\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🌑 <b>SKILLS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "/skills — View all your skills\n"
        "/skill_equip &lt;id&gt; &lt;slot 1-4&gt; — Equip skill\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎰 <b>GACHA</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "/hunter_royale — Summon hunters\n"
        "/weapon_royale — Summon weapons\n"
        "/pity — Check pity counter\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎒 <b>INVENTORY</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "/inventory — All items\n"
        "/hunters — Your hunters\n"
        "/weapons — Your weapons\n"
        "/equip &lt;weapon_name&gt; — Equip weapon\n"
        "/team — View team\n"
        "/team_add &lt;hunter_name&gt; — Add to team\n"
        "/team_remove &lt;hunter_name&gt; — Remove\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💰 <b>ECONOMY</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "/shop — Item shop\n"
        "/buy &lt;item&gt; — Purchase item\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🏆 <b>RANKINGS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "/top — Power leaderboard\n"
        "/pvp_top — PvP leaderboard\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚔️ <b>GUILD</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "/guild — View your guild\n"
        "/guild_create &lt;name&gt; — Create guild\n"
        "/guild_join &lt;name&gt; — Join guild\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🗡 <i>\"Arise.\"</i>"
    )
    await msg.answer(text, parse_mode="HTML")

# ─── /profile ─────────────────────────────────────────────────────────────────

@router.message(Command("profile"))
async def cmd_profile(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    re = rank_emoji(player["rank"])
    exp_req = get_exp_required(player["level"])
    exp_bar_filled = int((player["exp"] / exp_req) * 12) if exp_req > 0 else 12
    exp_bar = "▓" * exp_bar_filled + "░" * (12 - exp_bar_filled)
    hp_b = hp_bar(player["max_hp"], player["max_hp"])
    cp = player["combat_power"]

    equipped_weapon = "None"
    if player.get("equipped_weapon_id"):
        w = await db.weapons().find_one({"_id": player["equipped_weapon_id"]})
        if w: equipped_weapon = w["name"]

    # Skills
    equipped_skills = player.get("equipped_skills", DEFAULT_SKILLS[:2])
    skill_names = []
    for sid in equipped_skills[:4]:
        sk = ALL_SKILLS.get(sid)
        if sk: skill_names.append(sk["name"])
    skill_str = " · ".join(skill_names) if skill_names else "None"

    text = (
        f"╔══════════════════════╗\n"
        f"      🌑 <b>HUNTER PROFILE</b> 🌑\n"
        f"╚══════════════════════╝\n\n"
        f"🧿 <b>{player['hunter_name']}</b>\n"
        f"{re} Rank: <b>{player['rank']}-Rank</b> | 🎖 Level: <b>{player['level']}</b>\n\n"
        f"⚡ <b>Combat Power: {cp:,}</b>\n\n"
        f"❤️ HP: <b>{player['max_hp']:,}</b>  🔮 Mana: <b>{player['max_mana']:,}</b>\n\n"
        f"📈 EXP: [{exp_bar}] {player['exp']:,}/{exp_req:,}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💪 STR <b>{player['strength']}</b>  ⚡ AGI <b>{player['agility']}</b>  🎯 PRE <b>{player['precision']}</b>\n"
        f"🧠 INT <b>{player['intelligence']}</b>  ❤️ VIT <b>{player['vitality']}</b>  🛡 END <b>{player['endurance']}</b>  🍀 LCK <b>{player['luck']}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚔️ Weapon: <b>{equipped_weapon}</b>\n"
        f"🌑 Skills: <i>{skill_str}</i>\n"
        f"🔷 Stat Points: <b>{player['stat_points']}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Coins: <b>{player['coins']:,}</b>  🎫 Tickets: <b>{player['tickets']}</b>\n"
        f"⚡ Stamina: <b>{player['stamina']}/{player['max_stamina']}</b>\n\n"
        f"🏆 PvP: <b>{player['pvp_wins']}W</b> / <b>{player['pvp_losses']}L</b>\n"
        f"🗡 Dungeons: <b>{player['dungeon_clears']}</b> cleared"
    )

    # Try to show profile image from favourite hunter in team
    profile_image = None
    team_ids = player.get("team_slots", [])
    if team_ids:
        best = await db.hunters().find_one({"_id": team_ids[0]})
        if best and best.get("image_file_id"):
            profile_image = best["image_file_id"]

    if profile_image:
        await msg.answer_photo(photo=profile_image, caption=text, parse_mode="HTML")
    else:
        await msg.answer(text, parse_mode="HTML")

# ─── /stats ───────────────────────────────────────────────────────────────────

@router.message(Command("stats"))
async def cmd_stats(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    re = rank_emoji(player["rank"])
    text = (
        f"╔══════════════════════╗\n"
        f"     ⚡ <b>HUNTER STATS</b> ⚡\n"
        f"╚══════════════════════╝\n\n"
        f"🧿 <b>{player['hunter_name']}</b> {re} {player['rank']}-Rank  Lv.<b>{player['level']}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💪 Strength     <b>{player['strength']:>5}</b>\n"
        f"⚡ Agility      <b>{player['agility']:>5}</b>\n"
        f"🎯 Precision    <b>{player['precision']:>5}</b>\n"
        f"🧠 Intelligence <b>{player['intelligence']:>5}</b>\n"
        f"❤️ Vitality     <b>{player['vitality']:>5}</b>\n"
        f"🛡 Endurance    <b>{player['endurance']:>5}</b>\n"
        f"🍀 Luck         <b>{player['luck']:>5}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚔️ Combat Power: <b>{player['combat_power']:,}</b>\n"
        f"❤️ Max HP:       <b>{player['max_hp']:,}</b>\n"
        f"🔮 Max Mana:     <b>{player['max_mana']:,}</b>\n\n"
        f"🔷 Stat Points Available: <b>{player['stat_points']}</b>\n\n"
        f"<i>Use /upgrade &lt;stat&gt; &lt;points&gt; to allocate.</i>\n"
        f"Stats: str agility precision intelligence vitality endurance luck"
    )
    await msg.answer(text, parse_mode="HTML")

# ─── /upgrade ─────────────────────────────────────────────────────────────────

@router.message(Command("upgrade"))
async def cmd_upgrade(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    args = msg.text.split()[1:]
    if len(args) < 2:
        await msg.answer(
            "🔷 <b>STAT UPGRADE</b>\n\n"
            f"Available points: <b>{player['stat_points']}</b>\n\n"
            "Usage: <code>/upgrade &lt;stat&gt; &lt;points&gt;</code>\n\n"
            "Stats: <code>strength agility precision intelligence vitality endurance luck</code>",
            parse_mode="HTML"
        )
        return

    stat, *rest = args
    try:
        points = int(rest[0])
    except ValueError:
        await msg.answer("❌ Points must be a number.")
        return

    if points <= 0:
        await msg.answer("❌ Points must be positive.")
        return

    result = await upgrade_stat(msg.from_user.id, player, stat.lower(), points)
    if not result["success"]:
        await msg.answer(result["message"], parse_mode="Markdown")
        return

    await msg.answer(
        f"✅ <b>Stat Upgraded!</b>\n\n"
        f"📊 <b>{stat.capitalize()}</b> → <b>{result['new_value']}</b>\n"
        f"🔷 Remaining Points: <b>{player['stat_points'] - points}</b>",
        parse_mode="HTML"
    )

# ─── /daily ───────────────────────────────────────────────────────────────────

@router.message(Command("daily"))
async def cmd_daily(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    result = await claim_daily(msg.from_user.id, player)
    if not result["success"]:
        await msg.answer(
            f"⏳ <b>Already Claimed!</b>\n\n{result['message']}\n\nCome back tomorrow, hunter.",
            parse_mode="HTML"
        )
        return

    # Regenerate quests
    await generate_daily_quests(msg.from_user.id)

    await msg.answer(
        f"╔══════════════════════╗\n"
        f"    🌅 <b>DAILY REWARDS CLAIMED!</b> 🌅\n"
        f"╚══════════════════════╝\n\n"
        f"🧿 <b>{player['hunter_name']}</b>, your rewards:\n\n"
        f"💰 Coins: <b>+{result['coins']:,}</b>\n"
        f"🎫 Tickets: <b>+{result['tickets']}</b>\n"
        f"⚡ Stamina: <b>+{result['stamina']}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 New quests generated! Use /quests\n\n"
        f"🗡 <i>A hunter who rests is a hunter who wins.</i>",
        parse_mode="HTML"
    )

# ─── /quests ──────────────────────────────────────────────────────────────────

@router.message(Command("quests"))
async def cmd_quests(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    now = datetime.utcnow()
    quests = await db.quests().find(
        {"user_id": msg.from_user.id, "quest_type": "daily", "expires_at": {"$gt": now}}
    ).to_list(length=10)

    if not quests:
        await generate_daily_quests(msg.from_user.id)
        quests = await db.quests().find(
            {"user_id": msg.from_user.id, "quest_type": "daily", "expires_at": {"$gt": now}}
        ).to_list(length=10)

    lines = [
        "╔══════════════════════╗\n"
        "    📋 <b>DAILY QUESTS</b> 📋\n"
        "╚══════════════════════╝\n"
    ]
    for q in quests:
        pct = int((q["progress"] / q["target"]) * 10)
        bar = "▓" * pct + "░" * (10 - pct)
        status = "✅" if q["completed"] else "🔲"
        lines.append(
            f"\n{status} <b>{q['description']}</b>\n"
            f"   [{bar}] {q['progress']}/{q['target']}\n"
            f"   🏆 <b>{q['reward_coins']:,}</b>💰  "
            f"<b>{q['reward_exp']:,}</b>✨  "
            f"<b>{q['reward_tickets']}</b>🎫"
        )

    lines.append("\n\n━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("⏰ <i>Resets daily at midnight UTC</i>")
    await msg.answer("\n".join(lines), parse_mode="HTML")

# ─── /gate (Pokemon-style interactive dungeon) ────────────────────────────────

@router.message(Command("gate", "dungeon"))
async def cmd_gate(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    text = (
        f"╔══════════════════════╗\n"
        f"    🌀 <b>GATE SELECTION</b> 🌀\n"
        f"╚══════════════════════╝\n\n"
        f"🧿 Hunter: <b>{player['hunter_name']}</b>\n"
        f"⚡ Stamina: <b>{player['stamina']}/{player['max_stamina']}</b>\n"
        f"🎖 Rank: <b>{player['rank']}</b>  Lv.<b>{player['level']}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⬇️ <b>Select a gate to enter:</b>"
    )
    await msg.answer(
        text, parse_mode="HTML",
        reply_markup=gate_buttons()
    )

def dungeon_skill_buttons(equipped: list, p_mana: int) -> InlineKeyboardMarkup:
    """Skill buttons for dungeon battles."""
    from systems.skills import ALL_SKILLS
    buttons = []
    for sid in equipped[:4]:
        sk = ALL_SKILLS.get(sid)
        if sk:
            can_use = p_mana >= sk["mana_cost"]
            label = f"{sk['name']} [{sk['mana_cost']}💧]" if can_use else f"🔒 {sk['name']}"
            buttons.append(InlineKeyboardButton(
                text=label,
                callback_data=f"dg_skill:{sid}" if can_use else "dg_nomana"
            ))
    buttons.append(InlineKeyboardButton(text="⚔️ Basic Attack", callback_data="dg_skill:basic"))
    rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(text="🏃 Flee", callback_data="dg_flee")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@router.callback_query(F.data.startswith("gate_enter:"))
async def cb_gate_enter(cb: CallbackQuery):
    gate_type = cb.data.split(":", 1)[1]
    player = await get_player(cb.from_user.id)
    if not player:
        await cb.answer("Register first with /start", show_alert=True)
        return

    DUNGEON_SESSIONS.pop(cb.from_user.id, None)

    await cb.message.edit_text(
        f"🌀 <b>Entering {gate_type}...</b>\n\n⚔️ Summoning monsters...",
        parse_mode="HTML"
    )

    result = await start_dungeon_session(player, gate_type)
    if not result["success"]:
        await cb.message.edit_text(
            f"❌ <b>Cannot Enter Gate</b>\n\n{result['message']}",
            parse_mode="HTML"
        )
        return

    session = result["session"]
    text, image_id = build_battle_text(session, "⚔️ <b>Battle Start!</b> Choose your action:")
    equipped = player.get("equipped_skills", DEFAULT_SKILLS[:2])
    kbd = dungeon_skill_buttons(equipped, session["p_comb"].mana)

    if image_id:
        await cb.message.delete()
        await cb.message.answer_photo(
            photo=image_id,
            caption=text,
            parse_mode="HTML",
            reply_markup=kbd
        )
    else:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kbd)

@router.callback_query(F.data == "dg_nomana")
async def cb_dg_nomana(cb: CallbackQuery):
    await cb.answer("❌ Not enough mana for this skill!", show_alert=True)

@router.callback_query(F.data == "dg_flee")
async def cb_dg_flee(cb: CallbackQuery):
    DUNGEON_SESSIONS.pop(cb.from_user.id, None)
    try:
        await cb.message.edit_text(
            "🏃 <b>You fled from the dungeon!</b>\n\nStamina was consumed. Use /gate to try again.",
            parse_mode="HTML"
        )
    except:
        await cb.message.edit_caption(
            caption="🏃 <b>You fled from the dungeon!</b>\n\nUse /gate to try again.",
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("dg_skill:"))
async def cb_dg_skill(cb: CallbackQuery):
    skill_id = cb.data.split(":", 1)[1]
    user_id = cb.from_user.id

    if user_id not in DUNGEON_SESSIONS:
        try:
            await cb.message.edit_text(
                "❌ No active dungeon session.\n\nUse /gate to enter a new dungeon.",
                parse_mode="HTML"
            )
        except:
            await cb.message.edit_caption(
                caption="❌ No active dungeon session.\n\nUse /gate to enter.",
                parse_mode="HTML"
            )
        return

    result = await process_dungeon_action(user_id, skill_id)
    session = DUNGEON_SESSIONS.get(user_id)
    player = session["player"] if session else None
    equipped = player.get("equipped_skills", DEFAULT_SKILLS[:2]) if player else DEFAULT_SKILLS[:2]

    if result["done"]:
        try:
            await cb.message.edit_text(result["message"], parse_mode="HTML")
        except:
            await cb.message.edit_caption(caption=result["message"], parse_mode="HTML")
    else:
        text = result["text"]
        image_id = result.get("image")
        kbd = dungeon_skill_buttons(equipped, result["session"]["p_comb"].mana)

        if image_id:
            # If current message is already a photo, edit caption
            if cb.message.photo:
                await cb.message.edit_caption(caption=text, parse_mode="HTML", reply_markup=kbd)
            else:
                await cb.message.delete()
                await cb.message.answer_photo(photo=image_id, caption=text, parse_mode="HTML", reply_markup=kbd)
        else:
            try:
                await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kbd)
            except:
                await cb.message.edit_caption(caption=text, parse_mode="HTML", reply_markup=kbd)

    await cb.answer()

@router.callback_query(F.data == "gate_cancel")
async def cb_gate_cancel(cb: CallbackQuery):
    await cb.message.edit_text("❌ Gate entry cancelled.")

# ─── /battle @user (Pokemon-style interactive PvP) ────────────────────────────

@router.message(Command("battle"))
async def cmd_battle(msg: Message, state: FSMContext):
    if not msg.reply_to_message and not msg.entities:
        await msg.answer(
            "⚔️ <b>PvP BATTLE</b>\n\n"
            "Reply to a hunter's message or tag them:\n"
            "<code>/battle @username</code>\n\n"
            "🗡 Challenge another hunter to a duel!",
            parse_mode="HTML"
        )
        return

    # Resolve target
    target_user = None
    if msg.reply_to_message:
        target_user = msg.reply_to_message.from_user
    else:
        for ent in msg.entities or []:
            if ent.type == "mention":
                uname = msg.text[ent.offset+1:ent.offset+ent.length]
                target = await db.players().find_one({"username": uname})
                if target:
                    class FakeUser:
                        id = target["user_id"]
                        first_name = target.get("hunter_name", uname)
                    target_user = FakeUser()
                break

    if not target_user:
        await msg.answer("❌ Could not find that hunter. They must have used /start first.")
        return

    if target_user.id == msg.from_user.id:
        await msg.answer("🤔 You can't battle yourself, Shadow Hunter!")
        return

    atk_player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    dfn_player = await get_player(target_user.id)

    if not dfn_player:
        await msg.answer("❌ That hunter hasn't registered yet!")
        return
    if atk_player.get("is_banned") or dfn_player.get("is_banned"):
        await msg.answer("❌ A banned player cannot participate in battles.")
        return

    # Build combatants
    atk_comb = player_to_combatant(atk_player)
    dfn_comb = player_to_combatant(dfn_player)

    chat_id = msg.chat.id
    ACTIVE_BATTLES[chat_id] = {
        "attacker_id": msg.from_user.id,
        "defender_id": target_user.id,
        "atk": atk_comb,
        "dfn": dfn_comb,
        "turn": msg.from_user.id,
        "round": 1,
        "log": [],
        "atk_player": atk_player,
        "dfn_player": dfn_player,
        "msg_id": None,
    }

    e1 = config.ELEMENT_EMOJIS.get(atk_comb.element, "⚪")
    e2 = config.ELEMENT_EMOJIS.get(dfn_comb.element, "⚪")

    equipped_atk = atk_player.get("equipped_skills", DEFAULT_SKILLS[:2])
    text = _battle_status_text(
        atk_comb, dfn_comb, atk_player["hunter_name"], dfn_player["hunter_name"],
        e1, e2, 1, f"⚔️ <b>{atk_player['hunter_name']}</b> challenges <b>{dfn_player['hunter_name']}</b> to a duel!"
    )
    kbd = skill_buttons(equipped_atk, [])
    sent = await msg.answer(text, parse_mode="HTML", reply_markup=kbd)
    ACTIVE_BATTLES[chat_id]["msg_id"] = sent.message_id
    await state.set_state(BattleState.in_battle)

def _battle_status_text(atk, dfn, atk_name, dfn_name, e1, e2, rnd, last_action=""):
    a_bar = hp_bar(atk.hp, atk.max_hp)
    d_bar = hp_bar(dfn.hp, dfn.max_hp)
    a_mana_pct = int((atk.mana / atk.max_mana) * 10) if atk.max_mana > 0 else 0
    d_mana_pct = int((dfn.mana / dfn.max_mana) * 10) if dfn.max_mana > 0 else 0
    a_mana_bar = "🔵" * a_mana_pct + "⚫" * (10 - a_mana_pct)
    d_mana_bar = "🔵" * d_mana_pct + "⚫" * (10 - d_mana_pct)
    return (
        f"╔══════════════════════╗\n"
        f"    🩸 <b>PvP BATTLE</b> — Round {rnd} 🩸\n"
        f"╚══════════════════════╝\n\n"
        f"{e1} 🧿 <b>{atk_name}</b>\n"
        f"❤️ {a_bar}\n"
        f"    <b>{max(0,atk.hp):,}/{atk.max_hp:,} HP</b>\n"
        f"🔮 [{a_mana_bar}] <b>{atk.mana}/{atk.max_mana}</b>\n\n"
        f"<b>⚔️  VS  ⚔️</b>\n\n"
        f"{e2} 🧿 <b>{dfn_name}</b>\n"
        f"❤️ {d_bar}\n"
        f"    <b>{max(0,dfn.hp):,}/{dfn.max_hp:,} HP</b>\n"
        f"🔮 [{d_mana_bar}] <b>{dfn.mana}/{dfn.max_mana}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{last_action}"
    )

@router.callback_query(F.data.startswith("battle_skill:"))
async def cb_battle_skill(cb: CallbackQuery, state: FSMContext):
    chat_id = cb.message.chat.id
    battle = ACTIVE_BATTLES.get(chat_id)

    if not battle:
        await cb.answer("No active battle!", show_alert=True)
        return

    if cb.from_user.id != battle["turn"]:
        await cb.answer("⏳ It's not your turn!", show_alert=True)
        return

    skill_id = cb.data.split(":", 1)[1]
    atk_id = battle["attacker_id"]
    dfn_id = battle["defender_id"]

    is_attacker = cb.from_user.id == atk_id
    attacker: Combatant = battle["atk"] if is_attacker else battle["dfn"]
    defender: Combatant = battle["dfn"] if is_attacker else battle["atk"]
    atk_name = battle["atk_player"]["hunter_name"] if is_attacker else battle["dfn_player"]["hunter_name"]
    dfn_name = battle["dfn_player"]["hunter_name"] if is_attacker else battle["atk_player"]["hunter_name"]

    # Determine skill
    use_skill = False
    skill_txt = ""
    damage_mult = 1.0
    mana_cost = 0

    if skill_id != "basic":
        sk = ALL_SKILLS.get(skill_id)
        if sk and attacker.mana >= sk["mana_cost"]:
            use_skill = True
            skill_txt = sk["name"]
            damage_mult = sk["damage_multiplier"]
            mana_cost = sk["mana_cost"]
        else:
            await cb.answer("❌ Not enough mana!", show_alert=True)
            return

    # Calculate damage
    from battles.engine import calc_damage
    dmg, crit, dodged, note = calc_damage(attacker, defender, use_skill)

    if use_skill:
        attacker.mana -= mana_cost
        dmg = int(dmg * damage_mult)

    action_text = ""
    if dodged:
        action_text = f"💨 <b>{dfn_name}</b> evaded the attack!"
    else:
        actual = defender.take_damage(dmg)
        attacker.mana = min(attacker.max_mana, attacker.mana + 15)
        crit_txt = "💥 <b>CRITICAL HIT!</b> " if crit else ""
        skill_display = f"🌑 <b>{skill_txt}</b>! " if use_skill else "⚔️ Basic Attack! "
        action_text = (
            f"{skill_display}{note}{crit_txt}\n"
            f"🗡 <b>{atk_name}</b> deals <b>{actual:,} DMG</b> → <b>{dfn_name}</b>"
        )

    battle["round"] += 1

    # Check win
    e1 = config.ELEMENT_EMOJIS.get(battle["atk"].element, "⚪")
    e2 = config.ELEMENT_EMOJIS.get(battle["dfn"].element, "⚪")
    atk_p_name = battle["atk_player"]["hunter_name"]
    dfn_p_name = battle["dfn_player"]["hunter_name"]

    if not defender.alive() or battle["round"] > 20:
        # Battle over
        if not defender.alive():
            winner_id = cb.from_user.id
            loser_id  = dfn_id if is_attacker else atk_id
            winner_name = atk_name
            loser_name  = dfn_name
        else:
            # Decide by HP ratio
            a_ratio = battle["atk"].hp / battle["atk"].max_hp
            d_ratio = battle["dfn"].hp / battle["dfn"].max_hp
            if a_ratio >= d_ratio:
                winner_id, winner_name = atk_id, atk_p_name
                loser_id,  loser_name  = dfn_id, dfn_p_name
            else:
                winner_id, winner_name = dfn_id, dfn_p_name
                loser_id,  loser_name  = atk_id, atk_p_name

        # Rewards
        coins_won = random.randint(200, 500)
        await db.players().update_one({"user_id": winner_id}, {"$inc": {"pvp_wins": 1, "coins": coins_won}})
        await db.players().update_one({"user_id": loser_id},  {"$inc": {"pvp_losses": 1}})
        await update_quest_progress(winner_id, "win_pvp", 1)

        result_text = (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{action_text}\n\n"
            f"╔══════════════════════╗\n"
            f"   🏆 <b>BATTLE RESULT</b> 🏆\n"
            f"╚══════════════════════╝\n\n"
            f"🥇 <b>{winner_name}</b> wins the duel!\n"
            f"💀 <b>{loser_name}</b> has been defeated!\n\n"
            f"💰 Winner earns: <b>+{coins_won:,} coins</b>"
        )
        del ACTIVE_BATTLES[chat_id]
        await state.clear()
        await cb.message.edit_text(result_text, parse_mode="HTML")
        return

    # Switch turn
    battle["turn"] = dfn_id if is_attacker else atk_id
    next_player_data = battle["dfn_player"] if is_attacker else battle["atk_player"]
    next_equipped = next_player_data.get("equipped_skills", DEFAULT_SKILLS[:2])

    status = _battle_status_text(
        battle["atk"], battle["dfn"], atk_p_name, dfn_p_name,
        e1, e2, battle["round"], action_text
    )
    kbd = skill_buttons(next_equipped, [])
    await cb.message.edit_text(status, parse_mode="HTML", reply_markup=kbd)
    await cb.answer()

# ─── /skills ──────────────────────────────────────────────────────────────────

@router.message(Command("skills"))
async def cmd_skills(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    unlocked = get_unlocked_skills(player["rank"], player["level"])
    equipped = player.get("equipped_skills", DEFAULT_SKILLS[:2])

    lines = [
        "╔══════════════════════╗\n"
        "    🌑 <b>SKILL COMPENDIUM</b> 🌑\n"
        "╚══════════════════════╝\n\n"
        f"🧿 <b>{player['hunter_name']}</b> — {player['rank']}-Rank\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🗡 <b>Equipped Skills</b> (max 4):\n"
    ]

    for i, sid in enumerate(equipped[:4], 1):
        sk = ALL_SKILLS.get(sid)
        if sk:
            rc = RARITY_COLORS.get(sk["rarity"], "⬜")
            lines.append(f"  {i}. {rc} <b>{sk['name']}</b> — 💧{sk['mana_cost']} mana")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("📖 <b>Unlocked Skills:</b>\n")

    for sk in unlocked:
        rc = RARITY_COLORS.get(sk["rarity"], "⬜")
        equipped_mark = "✅" if sk["id"] in equipped else "  "
        lines.append(
            f"{equipped_mark} {rc} <b>{sk['name']}</b> [<code>{sk['id']}</code>]\n"
            f"     ⚔️ {sk['type']} | 💥 x{sk['damage_multiplier']} | 💧{sk['mana_cost']}\n"
            f"     <i>{sk['description']}</i>\n"
        )

    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("📌 <code>/skill_equip &lt;skill_id&gt; &lt;slot 1-4&gt;</code>")
    await msg.answer("\n".join(lines), parse_mode="HTML")

@router.message(Command("skill_equip"))
async def cmd_skill_equip(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    args = msg.text.split()[1:]
    if len(args) < 2:
        await msg.answer(
            "📌 <b>Equip Skill</b>\n\nUsage: <code>/skill_equip &lt;skill_id&gt; &lt;slot 1-4&gt;</code>\n\n"
            "Example: <code>/skill_equip shadow_extraction 1</code>",
            parse_mode="HTML"
        )
        return

    skill_id = args[0].lower()
    try:
        slot = int(args[1]) - 1
        assert 0 <= slot <= 3
    except (ValueError, AssertionError):
        await msg.answer("❌ Slot must be 1, 2, 3, or 4.")
        return

    sk = ALL_SKILLS.get(skill_id)
    if not sk:
        await msg.answer(f"❌ Unknown skill: <code>{skill_id}</code>. Use /skills to see available IDs.", parse_mode="HTML")
        return

    # Check unlock requirements
    req_rank_idx = RANK_ORDER.index(sk["rank_required"]) if sk["rank_required"] in RANK_ORDER else 0
    player_rank_idx = RANK_ORDER.index(player["rank"]) if player["rank"] in RANK_ORDER else 0
    if player_rank_idx < req_rank_idx or player["level"] < sk["level_required"]:
        await msg.answer(
            f"🔒 <b>Skill Locked!</b>\n\n"
            f"Requires: {sk['rank_required']}-Rank & Level {sk['level_required']}\n"
            f"You are: {player['rank']}-Rank Lv.{player['level']}",
            parse_mode="HTML"
        )
        return

    equipped = list(player.get("equipped_skills", DEFAULT_SKILLS[:2]))
    while len(equipped) < 4:
        equipped.append(None)

    equipped[slot] = skill_id
    equipped = [e for e in equipped if e is not None]

    await update_player(msg.from_user.id, {"equipped_skills": equipped})
    rc = RARITY_COLORS.get(sk["rarity"], "⬜")
    await msg.answer(
        f"✅ <b>Skill Equipped!</b>\n\n"
        f"{rc} <b>{sk['name']}</b> → Slot <b>{slot+1}</b>\n\n"
        f"⚔️ Type: {sk['type']} | 💥 Power: x{sk['damage_multiplier']}\n"
        f"💧 Mana Cost: {sk['mana_cost']}",
        parse_mode="HTML"
    )

# ─── /hunter_royale ───────────────────────────────────────────────────────────

@router.message(Command("hunter_royale"))
async def cmd_hunter_royale(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    args = msg.text.split()[1:]
    count = 10 if args and args[0] == "10" else 1
    cost = count

    if player["tickets"] < cost:
        await msg.answer(
            f"🎫 <b>HUNTER ROYALE</b>\n\n"
            f"Need <b>{cost}</b> 🎫 tickets.\n"
            f"You have: <b>{player['tickets']}</b>\n\n"
            f"Get more with /daily!",
            parse_mode="HTML"
        )
        return

    result = await do_hunter_summon(player, count)
    text = format_hunter_result(result)
    await msg.answer(text, parse_mode="Markdown")

# ─── /weapon_royale ───────────────────────────────────────────────────────────

@router.message(Command("weapon_royale"))
async def cmd_weapon_royale(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    args = msg.text.split()[1:]
    count = 10 if args and args[0] == "10" else 1

    result = await do_weapon_summon(player, count)
    text = format_weapon_result(result)
    await msg.answer(text, parse_mode="Markdown")

# ─── /pity ────────────────────────────────────────────────────────────────────

@router.message(Command("pity"))
async def cmd_pity(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    hp = player.get("hunter_pity", 0)
    wp = player.get("weapon_pity", 0)
    h_bar_f = int(hp / config.HUNTER_PITY * 10)
    w_bar_f = int(wp / config.WEAPON_PITY * 10)

    await msg.answer(
        f"🎰 <b>PITY COUNTER</b>\n\n"
        f"🧿 <b>Hunter Royale</b>\n"
        f"   [{'▓'*h_bar_f}{'░'*(10-h_bar_f)}] {hp}/{config.HUNTER_PITY}\n"
        f"   ⭐ S-Rank guaranteed at {config.HUNTER_PITY} pulls\n\n"
        f"⚔️ <b>Weapon Royale</b>\n"
        f"   [{'▓'*w_bar_f}{'░'*(10-w_bar_f)}] {wp}/{config.WEAPON_PITY}\n"
        f"   ⭐ S-Rank guaranteed at {config.WEAPON_PITY} pulls",
        parse_mode="HTML"
    )

# ─── /inventory ───────────────────────────────────────────────────────────────

@router.message(Command("inventory"))
async def cmd_inventory(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    items = await get_inventory(msg.from_user.id)
    if not items:
        await msg.answer(
            "🎒 <b>INVENTORY</b>\n\n"
            "Your inventory is empty.\n\n"
            "Enter gates and summon hunters to collect items!",
            parse_mode="HTML"
        )
        return

    by_type: dict = {}
    for item in items:
        t = item.get("item_type", "misc")
        by_type.setdefault(t, []).append(item)

    type_icons = {"hunter": "🧿", "weapon": "⚔️", "material": "💎", "ticket": "🎫", "misc": "📦"}
    lines = ["╔══════════════════════╗\n   🎒 <b>INVENTORY</b>\n╚══════════════════════╝\n"]

    for t, icon in type_icons.items():
        if t not in by_type: continue
        lines.append(f"\n{icon} <b>{t.upper()}S</b>")
        for item in by_type[t][:10]:
            qty = item.get("quantity", 1)
            lines.append(f"  • <b>{item['item_name']}</b>" + (f" ×{qty}" if qty > 1 else ""))

    lines.append(f"\n━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"💰 Coins: <b>{player['coins']:,}</b>  🎫 Tickets: <b>{player['tickets']}</b>")
    await msg.answer("\n".join(lines), parse_mode="HTML")

# ─── /hunters ─────────────────────────────────────────────────────────────────

@router.message(Command("hunters"))
async def cmd_hunters(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    items = await get_inventory(msg.from_user.id, "hunter")
    if not items:
        await msg.answer(
            "🧿 <b>YOUR HUNTERS</b>\n\n"
            "No hunters summoned yet!\n\n"
            "Use /hunter_royale to summon hunters.",
            parse_mode="HTML"
        )
        return

    lines = ["╔══════════════════════╗\n   🧿 <b>YOUR HUNTERS</b>\n╚══════════════════════╝\n"]
    for item in items[:15]:
        h = await db.hunters().find_one({"_id": item["item_id"]}) if item.get("item_id") else None
        if h:
            re = rank_emoji(h.get("rank", "E"))
            elem = config.ELEMENT_EMOJIS.get(h.get("element", "None"), "⚪")
            cls = config.CLASS_EMOJIS.get(h.get("hunter_class", "Fighter"), "⚔️")
            lines.append(f"\n{re} <b>{h['name']}</b>  {elem} {cls}\n"
                         f"   CP: <b>{h.get('combat_power',0):,}</b>  ATK: <b>{h.get('attack',0):,}</b>")
        else:
            lines.append(f"\n🧿 <b>{item['item_name']}</b>")

    await msg.answer("\n".join(lines), parse_mode="HTML")

# ─── /weapons ─────────────────────────────────────────────────────────────────

@router.message(Command("weapons"))
async def cmd_weapons(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    items = await get_inventory(msg.from_user.id, "weapon")
    if not items:
        await msg.answer(
            "⚔️ <b>YOUR WEAPONS</b>\n\n"
            "No weapons found!\n\n"
            "Use /weapon_royale to forge weapons.",
            parse_mode="HTML"
        )
        return

    lines = ["╔══════════════════════╗\n   ⚔️ <b>YOUR WEAPONS</b>\n╚══════════════════════╝\n"]
    equipped_id = str(player.get("equipped_weapon_id", ""))

    for item in items[:15]:
        w = await db.weapons().find_one({"_id": item.get("item_id")}) if item.get("item_id") else None
        if w:
            re = rank_emoji(w.get("rank", "C"))
            elem = config.ELEMENT_EMOJIS.get(w.get("element", "None"), "⚪")
            eq_mark = " ✅" if str(w.get("_id", "")) == equipped_id else ""
            lines.append(
                f"\n{re} <b>{w['name']}</b>{eq_mark}\n"
                f"   {elem} DMG: <b>{w.get('damage',0):,}</b>  Crit: <b>{w.get('crit_rate',0.1)*100:.0f}%</b>"
            )
        else:
            lines.append(f"\n⚔️ <b>{item['item_name']}</b>")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("Use /equip &lt;weapon name&gt; to equip")
    await msg.answer("\n".join(lines), parse_mode="HTML")

# ─── /equip ───────────────────────────────────────────────────────────────────

@router.message(Command("equip"))
async def cmd_equip(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    args = msg.text.split(None, 1)[1:]
    if not args:
        await msg.answer("Usage: <code>/equip &lt;weapon name&gt;</code>", parse_mode="HTML")
        return

    weapon_name = args[0].strip()
    weapon = await db.weapons().find_one({"name": {"$regex": weapon_name, "$options": "i"}})
    if not weapon:
        await msg.answer(f"❌ Weapon <b>{weapon_name}</b> not found in database.", parse_mode="HTML")
        return

    # Check inventory
    inv = await get_inventory(msg.from_user.id, "weapon")
    owned_ids = [str(i.get("item_id", "")) for i in inv]
    if str(weapon["_id"]) not in owned_ids:
        await msg.answer(f"❌ You don't own <b>{weapon['name']}</b>.", parse_mode="HTML")
        return

    await update_player(msg.from_user.id, {"equipped_weapon_id": weapon["_id"]})
    re = rank_emoji(weapon.get("rank", "C"))
    elem = config.ELEMENT_EMOJIS.get(weapon.get("element", "None"), "⚪")
    await msg.answer(
        f"✅ <b>Weapon Equipped!</b>\n\n"
        f"{re} <b>{weapon['name']}</b>\n"
        f"{elem} DMG: <b>{weapon.get('damage',0):,}</b>  Crit: <b>{weapon.get('crit_rate',0.1)*100:.0f}%</b>",
        parse_mode="HTML"
    )

# ─── /team ────────────────────────────────────────────────────────────────────

@router.message(Command("team"))
async def cmd_team(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    team_ids = player.get("team_slots", [])
    if not team_ids:
        await msg.answer(
            "👥 <b>YOUR TEAM</b>\n\n"
            "Your team is empty!\n\n"
            "Use /team_add &lt;hunter name&gt; to add hunters.\n"
            f"Max team size: <b>{config.MAX_TEAM_SIZE}</b>",
            parse_mode="HTML"
        )
        return

    lines = [f"╔══════════════════════╗\n   👥 <b>YOUR TEAM</b> ({len(team_ids)}/{config.MAX_TEAM_SIZE})\n╚══════════════════════╝\n"]
    for hid in team_ids:
        h = await db.hunters().find_one({"_id": hid})
        if h:
            re = rank_emoji(h.get("rank", "E"))
            elem = config.ELEMENT_EMOJIS.get(h.get("element", "None"), "⚪")
            lines.append(f"\n{re} <b>{h['name']}</b>  {elem}\n   CP: <b>{h.get('combat_power',0):,}</b>  Skill: <b>{h.get('skill_name','—')}</b>")

    await msg.answer("\n".join(lines), parse_mode="HTML")

@router.message(Command("team_add"))
async def cmd_team_add(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    args = msg.text.split(None, 1)[1:]
    if not args:
        await msg.answer("Usage: <code>/team_add &lt;hunter name&gt;</code>", parse_mode="HTML")
        return

    hunter = await db.hunters().find_one({"name": {"$regex": args[0].strip(), "$options": "i"}})
    if not hunter:
        await msg.answer(f"❌ Hunter not found.", parse_mode="HTML")
        return

    inv = await get_inventory(msg.from_user.id, "hunter")
    owned_ids = [str(i.get("item_id", "")) for i in inv]
    if str(hunter["_id"]) not in owned_ids:
        await msg.answer(f"❌ You don't own <b>{hunter['name']}</b>.", parse_mode="HTML")
        return

    team = list(player.get("team_slots", []))
    if len(team) >= config.MAX_TEAM_SIZE:
        await msg.answer(f"❌ Team is full! ({config.MAX_TEAM_SIZE}/{config.MAX_TEAM_SIZE})\nRemove a hunter with /team_remove first.")
        return
    if hunter["_id"] in team:
        await msg.answer(f"❌ <b>{hunter['name']}</b> is already in your team.", parse_mode="HTML")
        return

    team.append(hunter["_id"])
    await update_player(msg.from_user.id, {"team_slots": team})
    await msg.answer(
        f"✅ <b>{hunter['name']}</b> added to team!\n"
        f"Team: <b>{len(team)}/{config.MAX_TEAM_SIZE}</b>",
        parse_mode="HTML"
    )

@router.message(Command("team_remove"))
async def cmd_team_remove(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    args = msg.text.split(None, 1)[1:]
    if not args:
        await msg.answer("Usage: <code>/team_remove &lt;hunter name&gt;</code>", parse_mode="HTML")
        return

    hunter = await db.hunters().find_one({"name": {"$regex": args[0].strip(), "$options": "i"}})
    team = list(player.get("team_slots", []))

    if not hunter or hunter["_id"] not in team:
        await msg.answer("❌ That hunter is not in your team.", parse_mode="HTML")
        return

    team.remove(hunter["_id"])
    await update_player(msg.from_user.id, {"team_slots": team})
    await msg.answer(
        f"✅ <b>{hunter['name']}</b> removed from team.\n"
        f"Team: <b>{len(team)}/{config.MAX_TEAM_SIZE}</b>",
        parse_mode="HTML"
    )

# ─── /shop ────────────────────────────────────────────────────────────────────

@router.message(Command("shop"))
async def cmd_shop(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    await msg.answer(
        f"╔══════════════════════╗\n"
        f"    💰 <b>SHADOW MARKET</b> 💰\n"
        f"╚══════════════════════╝\n\n"
        f"Your balance: <b>{player['coins']:,}</b> 💰  <b>{player['tickets']}</b> 🎫\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎫 <b>Hunter Ticket</b>       — <b>500</b> 💰\n"
        f"   Use: /buy ticket\n\n"
        f"⚡ <b>Stamina Potion</b>      — <b>200</b> 💰\n"
        f"   Restore 50 stamina\n"
        f"   Use: /buy stamina\n\n"
        f"💎 <b>Hunter Shard ×5</b>    — <b>300</b> 💰\n"
        f"   Gacha material\n"
        f"   Use: /buy shard\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🗡 <i>\"Spend wisely, hunter.\"</i>",
        parse_mode="HTML"
    )

@router.message(Command("buy"))
async def cmd_buy(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    args = msg.text.split()[1:]
    if not args:
        await msg.answer("Usage: <code>/buy &lt;ticket|stamina|shard&gt;</code>", parse_mode="HTML")
        return

    item = args[0].lower()
    SHOP = {
        "ticket":  {"cost": 500,  "desc": "🎫 Hunter Ticket"},
        "stamina": {"cost": 200,  "desc": "⚡ Stamina Potion"},
        "shard":   {"cost": 300,  "desc": "💎 Hunter Shard ×5"},
    }
    if item not in SHOP:
        await msg.answer("❌ Unknown item. Check /shop for available items.")
        return

    shop_item = SHOP[item]
    if player["coins"] < shop_item["cost"]:
        await msg.answer(
            f"❌ Not enough coins!\nNeed: <b>{shop_item['cost']:,}</b> 💰\nYours: <b>{player['coins']:,}</b> 💰",
            parse_mode="HTML"
        )
        return

    updates = {"coins": player["coins"] - shop_item["cost"]}
    if item == "ticket":
        updates["tickets"] = player["tickets"] + 1
    elif item == "stamina":
        updates["stamina"] = min(player["max_stamina"], player["stamina"] + 50)
    elif item == "shard":
        await add_to_inventory(msg.from_user.id, "material", "shard_1", "Hunter Shard 💎", 5)

    await update_player(msg.from_user.id, updates)
    await msg.answer(
        f"✅ <b>Purchase Successful!</b>\n\n"
        f"{shop_item['desc']} bought!\n"
        f"💰 Remaining: <b>{updates['coins']:,}</b>",
        parse_mode="HTML"
    )

# ─── /top ─────────────────────────────────────────────────────────────────────

@router.message(Command("top"))
async def cmd_top(msg: Message):
    leaders = await get_leaderboard(10)
    lines = [
        "╔══════════════════════╗\n"
        "   🏆 <b>POWER RANKINGS</b> 🏆\n"
        "╚══════════════════════╝\n"
    ]
    medals = ["🥇", "🥈", "🥉"] + ["⚔️"] * 7
    for i, p in enumerate(leaders):
        re = rank_emoji(p.get("rank", "E"))
        lines.append(
            f"\n{medals[i]} <b>#{i+1}</b> {re} <b>{p['hunter_name']}</b>\n"
            f"   Lv.<b>{p['level']}</b>  CP: <b>{p['combat_power']:,}</b>"
        )
    await msg.answer("\n".join(lines), parse_mode="HTML")

@router.message(Command("pvp_top"))
async def cmd_pvp_top(msg: Message):
    leaders = await get_pvp_leaderboard(10)
    lines = [
        "╔══════════════════════╗\n"
        "   🥊 <b>PvP RANKINGS</b> 🥊\n"
        "╚══════════════════════╝\n"
    ]
    medals = ["🥇", "🥈", "🥉"] + ["⚔️"] * 7
    for i, p in enumerate(leaders):
        re = rank_emoji(p.get("rank", "E"))
        total = p["pvp_wins"] + p.get("pvp_losses", 0)
        wr = int(p["pvp_wins"] / total * 100) if total > 0 else 0
        lines.append(
            f"\n{medals[i]} <b>#{i+1}</b> {re} <b>{p['hunter_name']}</b>\n"
            f"   🏆 <b>{p['pvp_wins']}W</b> / <b>{p.get('pvp_losses',0)}L</b>  WR: <b>{wr}%</b>"
        )
    await msg.answer("\n".join(lines), parse_mode="HTML")

# ─── /guild ───────────────────────────────────────────────────────────────────

@router.message(Command("guild"))
async def cmd_guild(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    if not player.get("guild_id"):
        await msg.answer(
            "⚔️ <b>GUILD</b>\n\n"
            "You are not in a guild.\n\n"
            "• <code>/guild_create &lt;name&gt;</code> — Create a new guild\n"
            "• <code>/guild_join &lt;name&gt;</code> — Join an existing guild",
            parse_mode="HTML"
        )
        return

    guild = await db.guilds().find_one({"_id": player["guild_id"]}) if hasattr(db, 'guilds') else None
    if not guild:
        await msg.answer("⚔️ Your guild could not be found. It may have been disbanded.", parse_mode="HTML")
        return

    members = await db.players().count_documents({"guild_id": guild["_id"]})
    await msg.answer(
        f"╔══════════════════════╗\n"
        f"     ⚔️ <b>GUILD INFO</b> ⚔️\n"
        f"╚══════════════════════╝\n\n"
        f"🏰 <b>{guild['name']}</b>\n"
        f"👤 Members: <b>{members}</b>\n"
        f"⭐ Founded: <b>{guild.get('created_at', '—')}</b>\n\n"
        f"<i>{guild.get('description', 'No description.')}</i>",
        parse_mode="HTML"
    )

@router.message(Command("guild_create"))
async def cmd_guild_create(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    if player.get("guild_id"):
        await msg.answer("❌ You're already in a guild! Leave first to create one.")
        return

    args = msg.text.split(None, 1)[1:]
    if not args:
        await msg.answer("Usage: <code>/guild_create &lt;guild name&gt;</code>", parse_mode="HTML")
        return

    name = args[0].strip()[:30]
    existing = await db.guilds().find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
    if existing:
        await msg.answer(f"❌ Guild <b>{name}</b> already exists!", parse_mode="HTML")
        return

    cost = 2000
    if player["coins"] < cost:
        await msg.answer(
            f"❌ Creating a guild costs <b>{cost:,}</b> 💰\nYou have: <b>{player['coins']:,}</b>",
            parse_mode="HTML"
        )
        return

    result = await db.guilds().insert_one({
        "name": name,
        "owner_id": msg.from_user.id,
        "description": "A new guild of shadow hunters.",
        "created_at": datetime.utcnow(),
    })
    await update_player(msg.from_user.id, {
        "guild_id": result.inserted_id,
        "coins": player["coins"] - cost,
    })
    await msg.answer(
        f"🏰 <b>Guild Created!</b>\n\n"
        f"⚔️ <b>{name}</b>\n"
        f"👑 You are the Guild Master!\n\n"
        f"Share the guild name so others can join with:\n"
        f"<code>/guild_join {name}</code>",
        parse_mode="HTML"
    )

@router.message(Command("guild_join"))
async def cmd_guild_join(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if await banned_check(msg, player): return

    if player.get("guild_id"):
        await msg.answer("❌ You're already in a guild!")
        return

    args = msg.text.split(None, 1)[1:]
    if not args:
        await msg.answer("Usage: <code>/guild_join &lt;guild name&gt;</code>", parse_mode="HTML")
        return

    name = args[0].strip()
    guild = await db.guilds().find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
    if not guild:
        await msg.answer(f"❌ Guild <b>{name}</b> not found.", parse_mode="HTML")
        return

    await update_player(msg.from_user.id, {"guild_id": guild["_id"]})
    await msg.answer(
        f"✅ <b>Joined {guild['name']}!</b>\n\n"
        f"Welcome to the guild, <b>{player['hunter_name']}</b>!",
        parse_mode="HTML"
    )

# ─── FALLBACK ─────────────────────────────────────────────────────────────────

@router.message(F.text.startswith("/"))
async def unknown_command(msg: Message):
    await msg.answer(
        "❓ Unknown command.\n\nUse /help to see all available commands.",
        parse_mode="HTML"
    )

from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from database.player_crud import (
    get_or_create_player, update_stamina, claim_daily, upgrade_stat,
    get_inventory, generate_daily_quests, update_player, get_leaderboard, get_pvp_leaderboard
)
from systems.dungeon import enter_dungeon
from systems.gacha import do_hunter_summon, do_weapon_summon, format_hunter_result, format_weapon_result
from battles.engine import player_to_combatant, run_pvp
import database.db as db
import config
import asyncio
import time

router = Router()
_pvp_cd = {}
_dng_cd = {}
_summon_cd = {}


def main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👤 Profile"), KeyboardButton(text="⚔️ Gate")],
        [KeyboardButton(text="🎰 Hunter Royale"), KeyboardButton(text="🗡️ Weapon Royale")],
        [KeyboardButton(text="👥 Team"), KeyboardButton(text="🎒 Inventory")],
        [KeyboardButton(text="🏆 Top"), KeyboardButton(text="📋 Quests")],
        [KeyboardButton(text="🎁 Daily"), KeyboardButton(text="🏪 Shop")],
    ], resize_keyboard=True)


# ─── START ────────────────────────────────────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username)
    await msg.answer(
        f"⚫ **SHADOW HUNTERS ONLINE** ⚫\n{'━'*28}\n\n"
        f"Welcome, **{player['hunter_name']}**.\n\n"
        f"The gates have opened.\n"
        f"Monsters pour through the rifts.\n"
        f"Only the strongest survive.\n\n"
        f"You awaken as **E-Rank Hunter**.\n"
        f"Combat Power: **{player['combat_power']:,}**\n\n"
        f"_\"I alone level up.\"_\n\n{'━'*28}\n"
        f"Use /help to see all commands.",
        reply_markup=main_kb()
    )


# ─── PROFILE ──────────────────────────────────────────────────────────────────

@router.message(Command("profile"))
@router.message(F.text == "👤 Profile")
async def cmd_profile(msg: Message):
    player = await get_or_create_player(msg.from_user.id, msg.from_user.username)
    player = await update_stamina(player)

    inv = await get_inventory(msg.from_user.id, "hunter")
    rank_emoji = config.RANK_EMOJIS.get(player["rank"], "⬛")
    exp_req = int(100 * (1.35 ** (player["level"] - 1)))
    exp_fill = int((player["exp"] / max(1, exp_req)) * 10)
    exp_bar = "█" * exp_fill + "░" * (10 - exp_fill)
    sta_fill = int((player["stamina"] / player["max_stamina"]) * 10)
    sta_bar = "⚡" * sta_fill + "○" * (10 - sta_fill)

    weapon_text = "None"
    if player.get("equipped_weapon_id"):
        w = await db.weapons().find_one({"_id": player["equipped_weapon_id"]})
        if w: weapon_text = f"{w['name']} [{w['rank']}]"

    await msg.answer(
        f"{'━'*28}\n👤 **HUNTER PROFILE**\n{'━'*28}\n\n"
        f"🏷️ Name: **{player['hunter_name']}**\n"
        f"{rank_emoji} Rank: **{player['rank']}**\n"
        f"⭐ Level: **{player['level']}**\n"
        f"✨ EXP: [{exp_bar}] {player['exp']:,}/{exp_req:,}\n"
        f"⚡ Stamina: [{sta_bar}] {player['stamina']}/{player['max_stamina']}\n\n"
        f"💰 Coins: **{player['coins']:,}** | 🎫 Tickets: **{player['tickets']}**\n\n"
        f"{'─'*26}\n⚔️ **STATS**\n{'─'*26}\n"
        f"💪 STR: **{player['strength']}** | 🏃 AGI: **{player['agility']}**\n"
        f"🎯 PRE: **{player['precision']}** | 🧠 INT: **{player['intelligence']}**\n"
        f"❤️ VIT: **{player['vitality']}** | 🛡️ END: **{player['endurance']}**\n"
        f"🍀 LCK: **{player['luck']}** | 📊 Points: **{player['stat_points']}**\n\n"
        f"⚡ Combat Power: **{player['combat_power']:,}**\n"
        f"❤️ Max HP: **{player['max_hp']:,}**\n\n"
        f"⚔️ Weapon: **{weapon_text}**\n"
        f"👥 Hunters: **{len(inv)}** collected\n\n"
        f"🏆 PvP: **{player['pvp_wins']}W / {player['pvp_losses']}L**\n"
        f"🚪 Dungeons: **{player['dungeon_clears']}** cleared\n"
        f"👹 Bosses: **{player['boss_kills']}** killed\n{'━'*28}"
    )


# ─── DAILY ────────────────────────────────────────────────────────────────────

@router.message(Command("daily"))
@router.message(F.text == "🎁 Daily")
async def cmd_daily(msg: Message):
    player = await get_or_create_player(msg.from_user.id)
    result = await claim_daily(msg.from_user.id, player)
    if result["success"]:
        await msg.answer(
            f"🎁 **DAILY REWARD CLAIMED!**\n{'━'*26}\n\n"
            f"💰 Coins: **+{result['coins']:,}**\n"
            f"🎫 Tickets: **+{result['tickets']}**\n"
            f"⚡ Stamina: **+{result['stamina']}**\n\n"
            f"_Come back tomorrow!_"
        )
    else:
        await msg.answer(result["message"])


# ─── STATS ────────────────────────────────────────────────────────────────────

@router.message(Command("stats"))
async def cmd_stats(msg: Message):
    player = await get_or_create_player(msg.from_user.id)
    await msg.answer(
        f"📊 **STAT ALLOCATION**\n{'━'*26}\n\n"
        f"Available Points: **{player['stat_points']}** ⭐\n\n"
        f"💪 Strength: **{player['strength']}** → ATK damage\n"
        f"🏃 Agility: **{player['agility']}** → Speed + Dodge\n"
        f"🎯 Precision: **{player['precision']}** → Accuracy + Crit\n"
        f"🧠 Intelligence: **{player['intelligence']}** → Mana + Skills\n"
        f"❤️ Vitality: **{player['vitality']}** → Max HP\n"
        f"🛡️ Endurance: **{player['endurance']}** → Defense\n"
        f"🍀 Luck: **{player['luck']}** → Drops + Crit\n\n"
        f"**Usage:** `/upgrade strength 5`"
    )


@router.message(Command("upgrade"))
async def cmd_upgrade(msg: Message):
    args = msg.text.split()[1:] if msg.text else []
    if len(args) < 2:
        await msg.answer("❓ **Usage:** `/upgrade <stat> <points>`\nExample: `/upgrade strength 5`")
        return
    try:
        points = int(args[1])
        if points <= 0: raise ValueError
    except ValueError:
        await msg.answer("❌ Points must be a positive number!")
        return

    player = await get_or_create_player(msg.from_user.id)
    result = await upgrade_stat(msg.from_user.id, player, args[0].lower(), points)

    if result["success"]:
        await msg.answer(f"✅ **{args[0].capitalize()}** → **{result['new_value']}**\nRemaining points: **{player['stat_points'] - points}**")
    else:
        await msg.answer(result["message"])


# ─── GATE / DUNGEON ───────────────────────────────────────────────────────────

@router.message(Command("gate"))
@router.message(F.text == "⚔️ Gate")
async def cmd_gate(msg: Message):
    player = await get_or_create_player(msg.from_user.id)
    player = await update_stamina(player)
    lines = [f"🌀 **GATE SELECTION**\n{'━'*26}\n⚡ Stamina: **{player['stamina']}/{player['max_stamina']}**\n"]

    for name, cfg in config.GATE_CONFIG.items():
        can = player["level"] >= cfg["min_level"] and player["stamina"] >= cfg["stamina_cost"]
        s = "✅" if can else "🔒"
        lock = f" | 🔒 Lv.{cfg['min_level']}+" if player["level"] < cfg["min_level"] else ""
        lines.append(f"{s} {cfg['emoji']} **{name}**\n   ⚡ Cost: {cfg['stamina_cost']}{lock}")

    lines.append(f"\n{'━'*26}\nUse: `/dungeon <gate name>`\nExample: `/dungeon E Gate`")
    await msg.answer("\n".join(lines))


@router.message(Command("dungeon"))
async def cmd_dungeon(msg: Message):
    args = msg.text.split(None, 2)
    if len(args) < 2:
        await msg.answer("❓ **Usage:** `/dungeon <gate type>`\nExample: `/dungeon E Gate`\n\nUse /gate to see all gates.")
        return

    gate_type = " ".join(args[1:]).strip()
    uid = msg.from_user.id

    if time.time() - _dng_cd.get(uid, 0) < 30:
        remaining = int(30 - (time.time() - _dng_cd.get(uid, 0)))
        await msg.answer(f"⏳ Cooldown! Wait **{remaining}s**")
        return

    await msg.answer(f"🌀 **Entering {gate_type}...**\n⚔️ Prepare for battle!\n\n_\"Even the darkness cannot stop my rise.\"_")

    player = await get_or_create_player(uid)
    player = await update_stamina(player)
    result = await enter_dungeon(player, gate_type)

    if not result["success"]:
        await msg.answer(result["message"])
        return

    _dng_cd[uid] = time.time()
    log = result["log"]
    chunk, size = [], 0
    for line in log:
        chunk.append(line)
        size += len(line)
        if size >= 3500:
            await msg.answer("\n".join(chunk))
            await asyncio.sleep(0.3)
            chunk, size = [], 0
    if chunk:
        await msg.answer("\n".join(chunk))


# ─── PvP ──────────────────────────────────────────────────────────────────────

@router.message(Command("battle"))
async def cmd_battle(msg: Message):
    uid = msg.from_user.id
    if time.time() - _pvp_cd.get(uid, 0) < 60:
        await msg.answer(f"⏳ PvP cooldown! Wait **{int(60 - (time.time() - _pvp_cd.get(uid,0)))}s**")
        return

    defender = None
    if msg.entities:
        for e in msg.entities:
            if e.type == "text_mention" and e.user:
                defender = await get_or_create_player(e.user.id, e.user.username)
                break

    if not defender:
        await msg.answer("❓ **Usage:** `/battle @username`\nMention a player to challenge them!")
        return
    if defender["user_id"] == uid:
        await msg.answer("❌ You can't battle yourself!")
        return

    attacker = await get_or_create_player(uid, msg.from_user.username)

    atk_weapon = None
    if attacker.get("equipped_weapon_id"):
        atk_weapon = await db.weapons().find_one({"_id": attacker["equipped_weapon_id"]})

    def_weapon = None
    if defender.get("equipped_weapon_id"):
        def_weapon = await db.weapons().find_one({"_id": defender["equipped_weapon_id"]})

    atk_team, def_team = [], []
    for hid in attacker.get("team_slots", []):
        h = await db.hunters().find_one({"_id": hid})
        if h: atk_team.append(h)
    for hid in defender.get("team_slots", []):
        h = await db.hunters().find_one({"_id": hid})
        if h: def_team.append(h)

    a = player_to_combatant(attacker, atk_weapon, atk_team)
    d = player_to_combatant(defender, def_weapon, def_team)
    result = run_pvp(a, d)

    if result.victory:
        await update_player(uid, {"pvp_wins": attacker["pvp_wins"] + 1, "coins": attacker["coins"] + 200})
        await update_player(defender["user_id"], {"pvp_losses": defender["pvp_losses"] + 1})
    else:
        await update_player(defender["user_id"], {"pvp_wins": defender["pvp_wins"] + 1})
        await update_player(uid, {"pvp_losses": attacker["pvp_losses"] + 1, "coins": max(0, attacker["coins"] - 50)})

    _pvp_cd[uid] = time.time()

    log_text = "\n".join(result.log)
    if len(log_text) <= 4096:
        await msg.answer(log_text)
    else:
        chunks = [result.log[i:i+25] for i in range(0, len(result.log), 25)]
        for chunk in chunks:
            await msg.answer("\n".join(chunk))
            await asyncio.sleep(0.3)

    reward = f"\n🏆 **{attacker['hunter_name']}** wins! +200 💰" if result.victory else f"\n🏆 **{defender['hunter_name']}** wins!"
    await msg.answer(reward)


# ─── GACHA ────────────────────────────────────────────────────────────────────

@router.message(Command("hunter_royale"))
@router.message(F.text == "🎰 Hunter Royale")
async def cmd_hunter_royale(msg: Message):
    args = msg.text.split() if msg.text else []
    count = 10 if len(args) > 1 and args[1].lower() in ("x10", "10") else 1
    uid = msg.from_user.id

    if time.time() - _summon_cd.get(f"h{uid}", 0) < 5:
        await msg.answer("⏳ Cooldown!")
        return

    await msg.answer(f"🎰 **HUNTER ROYALE** — {'x10' if count==10 else 'x1'}\n🌀 Summoning...\n_\"Arise!\"_")
    player = await get_or_create_player(uid)
    result = await do_hunter_summon(player, count)
    _summon_cd[f"h{uid}"] = time.time()
    await msg.answer(format_hunter_result(result))


@router.message(Command("weapon_royale"))
@router.message(F.text == "🗡️ Weapon Royale")
async def cmd_weapon_royale(msg: Message):
    args = msg.text.split() if msg.text else []
    count = 10 if len(args) > 1 and args[1].lower() in ("x10", "10") else 1
    uid = msg.from_user.id

    if time.time() - _summon_cd.get(f"w{uid}", 0) < 5:
        await msg.answer("⏳ Cooldown!")
        return

    await msg.answer(f"⚔️ **WEAPON ROYALE** — {'x10' if count==10 else 'x1'}\n💰 Cost: {300*count:,} coins\n🔥 Forging...")
    player = await get_or_create_player(uid)
    result = await do_weapon_summon(player, count)
    _summon_cd[f"w{uid}"] = time.time()
    await msg.answer(format_weapon_result(result))


# ─── INVENTORY ────────────────────────────────────────────────────────────────

@router.message(Command("inventory"))
@router.message(F.text == "🎒 Inventory")
async def cmd_inventory(msg: Message):
    player = await get_or_create_player(msg.from_user.id)
    items = await get_inventory(msg.from_user.id)
    hunters = [i for i in items if i["item_type"] == "hunter"]
    weapons = [i for i in items if i["item_type"] == "weapon"]
    mats = [i for i in items if i["item_type"] == "material"]

    await msg.answer(
        f"🎒 **INVENTORY** — {player['hunter_name']}\n{'━'*26}\n\n"
        f"👥 Hunters: **{len(hunters)}**\n"
        f"⚔️ Weapons: **{len(weapons)}**\n"
        f"💎 Materials: **{sum(m.get('quantity',1) for m in mats)}**\n"
        f"🎫 Tickets: **{player['tickets']}**\n"
        f"💰 Coins: **{player['coins']:,}**\n\n"
        f"Use /hunters — View hunter collection\n"
        f"Use /weapons — View weapon collection"
    )


@router.message(Command("hunters"))
async def cmd_hunters(msg: Message):
    items = await get_inventory(msg.from_user.id, "hunter")
    if not items:
        await msg.answer("👥 No hunters yet! Use /hunter_royale to summon 🎰")
        return

    lines = [f"👥 **HUNTER COLLECTION** [{len(items)}]\n{'━'*26}\n"]
    for inv in items[:12]:
        h = await db.hunters().find_one({"_id": inv["item_id"]}) if inv.get("item_id") else None
        if h:
            re = config.RANK_EMOJIS.get(h.get("rank","E"),"⬛")
            ee = config.ELEMENT_EMOJIS.get(h.get("element","None"),"⚪")
            ce = config.CLASS_EMOJIS.get(h.get("hunter_class","Fighter"),"⚔️")
            lines.append(f"{re} **{h['name']}** [{h.get('rank','?')}]\n   {ce}{h.get('hunter_class','?')} | {ee}{h.get('element','?')} | CP:{h.get('combat_power',0):,}")
        else:
            lines.append(f"• **{inv['item_name']}**")

    if len(items) > 12: lines.append(f"\n_...and {len(items)-12} more_")
    lines.append(f"\n{'━'*26}\nUse /team to build your team")
    await msg.answer("\n".join(lines))


@router.message(Command("weapons"))
async def cmd_weapons(msg: Message):
    player = await get_or_create_player(msg.from_user.id)
    items = await get_inventory(msg.from_user.id, "weapon")
    if not items:
        await msg.answer("⚔️ No weapons yet! Use /weapon_royale 🎰")
        return

    lines = [f"⚔️ **WEAPON COLLECTION** [{len(items)}]\n{'━'*26}\n"]
    for inv in items[:12]:
        w = await db.weapons().find_one({"_id": inv["item_id"]}) if inv.get("item_id") else None
        if w:
            re = config.RANK_EMOJIS.get(w.get("rank","C"),"⬛")
            ee = config.ELEMENT_EMOJIS.get(w.get("element","None"),"⚪")
            eq = " 🔱 EQUIPPED" if str(player.get("equipped_weapon_id","")) == str(w.get("_id","")) else ""
            lines.append(f"{re} **{w['name']}** [{w.get('rank','?')}]{eq}\n   {ee} DMG:{w.get('damage',0):,} | Crit:{w.get('crit_rate',0.1)*100:.0f}%")
        else:
            lines.append(f"• **{inv['item_name']}**")

    lines.append(f"\n{'━'*26}\nUse `/equip <name>` to equip")
    await msg.answer("\n".join(lines))


@router.message(Command("equip"))
async def cmd_equip(msg: Message):
    args = msg.text.split(None, 1)
    if len(args) < 2:
        await msg.answer("❓ **Usage:** `/equip <weapon name>`")
        return

    items = await get_inventory(msg.from_user.id, "weapon")
    found = next((i for i in items if i["item_name"].lower() == args[1].strip().lower()), None)

    if not found:
        await msg.answer(f"❌ **{args[1]}** not in your inventory!")
        return

    w = await db.weapons().find_one({"_id": found["item_id"]}) if found.get("item_id") else None
    await update_player(msg.from_user.id, {"equipped_weapon_id": found.get("item_id")})
    wname = w["name"] if w else found["item_name"]
    wrank = w.get("rank","?") if w else "?"
    await msg.answer(f"✅ **{wname}** [{wrank}] equipped!")


# ─── TEAM ─────────────────────────────────────────────────────────────────────

@router.message(Command("team"))
@router.message(F.text == "👥 Team")
async def cmd_team(msg: Message):
    player = await get_or_create_player(msg.from_user.id)
    slots = player.get("team_slots", [])

    if not slots:
        await msg.answer("👥 **TEAM EMPTY**\n\nUse `/team_add <hunter name>` to add hunters!\nFirst collect hunters via /hunter_royale")
        return

    lines = [f"👥 **ACTIVE TEAM** ({len(slots)}/5)\n{'━'*26}\n"]
    for i, hid in enumerate(slots):
        h = await db.hunters().find_one({"_id": hid})
        if h:
            re = config.RANK_EMOJIS.get(h.get("rank","E"),"⬛")
            lines.append(f"**Slot {i+1}:** {re} **{h['name']}**\n   CP: {h.get('combat_power',0):,} | {h.get('element','?')}")

    lines.append(f"\n{'─'*24}\n/team_add <name> | /team_remove <name>")
    await msg.answer("\n".join(lines))


@router.message(Command("team_add"))
async def cmd_team_add(msg: Message):
    args = msg.text.split(None, 1)
    if len(args) < 2:
        await msg.answer("❓ `/team_add <hunter name>`")
        return

    player = await get_or_create_player(msg.from_user.id)
    slots = player.get("team_slots", [])

    if len(slots) >= 5:
        await msg.answer("❌ Team full! (5/5)\nRemove one with `/team_remove <name>`")
        return

    items = await get_inventory(msg.from_user.id, "hunter")
    found = next((i for i in items if i["item_name"].lower() == args[1].strip().lower()), None)
    if not found:
        await msg.answer(f"❌ **{args[1]}** not in your collection!")
        return

    hid = found.get("item_id")
    if hid in slots:
        await msg.answer(f"❌ **{found['item_name']}** is already on your team!")
        return

    slots.append(hid)
    await update_player(msg.from_user.id, {"team_slots": slots})
    await msg.answer(f"✅ **{found['item_name']}** added! Team: **{len(slots)}/5**")


@router.message(Command("team_remove"))
async def cmd_team_remove(msg: Message):
    args = msg.text.split(None, 1)
    if len(args) < 2:
        await msg.answer("❓ `/team_remove <hunter name>`")
        return

    player = await get_or_create_player(msg.from_user.id)
    slots = player.get("team_slots", [])
    items = await get_inventory(msg.from_user.id, "hunter")
    found = next((i for i in items if i["item_name"].lower() == args[1].strip().lower()), None)

    if not found or found.get("item_id") not in slots:
        await msg.answer(f"❌ **{args[1]}** is not on your team!")
        return

    slots.remove(found["item_id"])
    await update_player(msg.from_user.id, {"team_slots": slots})
    await msg.answer(f"✅ **{found['item_name']}** removed! Team: **{len(slots)}/5**")


# ─── QUESTS ───────────────────────────────────────────────────────────────────

@router.message(Command("quests"))
@router.message(F.text == "📋 Quests")
async def cmd_quests(msg: Message):
    from datetime import datetime
    uid = msg.from_user.id
    await get_or_create_player(uid)

    cursor = db.quests().find({"user_id": uid, "expires_at": {"$gt": datetime.utcnow()}})
    quests = await cursor.to_list(length=10)

    if not quests:
        await generate_daily_quests(uid)
        cursor = db.quests().find({"user_id": uid, "expires_at": {"$gt": datetime.utcnow()}})
        quests = await cursor.to_list(length=10)

    lines = [f"📋 **DAILY QUESTS**\n{'━'*26}\n"]
    for q in quests:
        fill = int((q["progress"] / q["target"]) * 8)
        bar = "█" * fill + "░" * (8 - fill)
        status = "✅ DONE" if q["completed"] else f"[{bar}] {q['progress']}/{q['target']}"
        reward = f"💰{q['reward_coins']} ✨{q['reward_exp']}"
        if q.get("reward_tickets"): reward += f" 🎫{q['reward_tickets']}"
        lines.append(f"{'─'*24}\n{q['description']}\n{status}\nReward: {reward}")

    lines.append(f"\n{'━'*26}\n_Resets daily at midnight UTC_")
    await msg.answer("\n".join(lines))


# ─── LEADERBOARD ──────────────────────────────────────────────────────────────

@router.message(Command("top"))
@router.message(F.text == "🏆 Top")
async def cmd_top(msg: Message):
    players = await get_leaderboard(10)
    lines = [f"🏆 **TOP HUNTERS**\n{'━'*26}\n_Ranked by Combat Power_\n"]
    medals = ["🥇","🥈","🥉"]
    for i, p in enumerate(players):
        re = config.RANK_EMOJIS.get(p.get("rank","E"),"⬛")
        medal = medals[i] if i < 3 else f"**#{i+1}**"
        lines.append(f"{medal} **{p['hunter_name']}** {re}\n   ⚡ CP:{p.get('combat_power',0):,} | Lv.{p.get('level',1)} | 🏆{p.get('pvp_wins',0)}W")
    await msg.answer("\n".join(lines))


# ─── SHOP ─────────────────────────────────────────────────────────────────────

@router.message(Command("shop"))
@router.message(F.text == "🏪 Shop")
async def cmd_shop(msg: Message):
    player = await get_or_create_player(msg.from_user.id)
    await msg.answer(
        f"🏪 **SHADOW MARKET**\n{'━'*26}\n"
        f"💰 Coins: **{player['coins']:,}** | 🎫 Tickets: **{player['tickets']}**\n\n"
        f"**🎫 Hunter Ticket** — 800 💰\n   For Hunter Royale summons\n   `/buy ticket`\n\n"
        f"**⚡ Stamina Potion** — 300 💰\n   Restore 50 stamina\n   `/buy stamina`\n\n"
        f"**💎 Shard Pack x5** — 500 💰\n   Hunter crafting materials\n   `/buy shards`\n\n"
        f"{'━'*26}\n_Use `/buy <item>` to purchase_"
    )


@router.message(Command("buy"))
async def cmd_buy(msg: Message):
    args = msg.text.split()
    if len(args) < 2:
        await msg.answer("❓ `/buy <item>`\nItems: ticket, stamina, shards")
        return

    item = args[1].lower()
    player = await get_or_create_player(msg.from_user.id)
    uid = msg.from_user.id

    ITEMS = {
        "ticket": {"cost": 800, "name": "Hunter Ticket 🎫"},
        "stamina": {"cost": 300, "name": "Stamina Potion ⚡"},
        "shards": {"cost": 500, "name": "Shard Pack x5 💎"},
    }

    if item not in ITEMS:
        await msg.answer("❌ Unknown item! Use: ticket, stamina, shards")
        return

    info = ITEMS[item]
    if player["coins"] < info["cost"]:
        await msg.answer(f"❌ Need **{info['cost']:,}** 💰! You have **{player['coins']:,}**")
        return

    new_coins = player["coins"] - info["cost"]
    updates = {"coins": new_coins}

    if item == "ticket":
        updates["tickets"] = player["tickets"] + 1
        effect = "🎫 Tickets: +1"
    elif item == "stamina":
        new_sta = min(player["max_stamina"], player["stamina"] + 50)
        updates["stamina"] = new_sta
        effect = f"⚡ Stamina restored: +{new_sta - player['stamina']}"
    else:
        await add_to_inventory(uid, "material", "shard_1", "Hunter Shard 💎", 5)
        effect = "💎 5 Hunter Shards added to inventory"

    await update_player(uid, updates)
    await msg.answer(f"✅ **{info['name']}** purchased!\n💰 Spent: **{info['cost']:,}**\n{effect}")


# ─── HELP ─────────────────────────────────────────────────────────────────────

@router.message(Command("help"))
async def cmd_help(msg: Message):
    await msg.answer(
        f"📖 **SHADOW HUNTERS COMMANDS**\n{'━'*28}\n\n"
        f"👤 **Profile**\n"
        f"/profile /stats /upgrade /daily /quests\n\n"
        f"⚔️ **Combat**\n"
        f"/gate /dungeon /battle\n\n"
        f"🎰 **Gacha**\n"
        f"/hunter_royale /weapon_royale /pity\n\n"
        f"🎒 **Inventory**\n"
        f"/inventory /hunters /weapons /equip\n/team /team_add /team_remove\n\n"
        f"💰 **Economy**\n"
        f"/shop /buy /daily\n\n"
        f"🏆 **Rankings**\n"
        f"/top /pvp_top\n\n"
        f"⚔️ **Guild**\n"
        f"/guild /guild_create /guild_join\n{'━'*28}"
    )

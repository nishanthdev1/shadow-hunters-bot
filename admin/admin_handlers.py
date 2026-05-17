from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import database.db as db
import config

router = Router()

def is_admin(uid): return uid in config.ADMIN_IDS

def parse(text: str) -> dict:
    fields = {}
    for line in text.strip().splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fields[k.strip().lower().replace(" ","_")] = v.strip()
    return fields


@router.message(Command("addmonster"))
async def cmd_addmonster(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("❌ Admin only!")
        return

    if "\n" not in msg.text:
        await msg.answer(
            "👹 **ADD MONSTER**\n\n"
            "Send /addmonster with data:\n\n"
            "```\nName: Iron Golem\nRank: E\nType: Normal\n"
            "HP: 500\nAttack: 80\nDefense: 40\nSpeed: 50\n"
            "Element: Earth\nGate Rank: E\nDrop EXP: 100\n"
            "Drop Coins: 50\nSkill: Stone Slam\n```\n\n"
            "Types: Normal, Elite, Boss, Mythic\n"
            "Gate Ranks: E D C B A S SS"
        )
        return

    fields = parse(msg.text.split("\n",1)[1])
    image_id = None
    if msg.reply_to_message and msg.reply_to_message.photo:
        image_id = msg.reply_to_message.photo[-1].file_id

    required = ["name","hp","attack","defense","speed"]
    missing = [f for f in required if f not in fields]
    if missing:
        await msg.answer(f"❌ Missing: **{', '.join(missing)}**")
        return

    try:
        doc = {
            "name": fields["name"],
            "rank": fields.get("rank","E"),
            "monster_type": fields.get("type","Normal"),
            "hp": int(fields["hp"]),
            "attack": int(fields["attack"]),
            "defense": int(fields["defense"]),
            "speed": int(fields["speed"]),
            "element": fields.get("element","None"),
            "skills": [{"name": fields["skill"], "multiplier": 2.0}] if "skill" in fields else [],
            "drop_exp": int(fields.get("drop_exp",100)),
            "drop_coins": int(fields.get("drop_coins",50)),
            "gate_rank": fields.get("gate_rank", fields.get("rank","E")),
            "spawn_weight": int(fields.get("spawn_weight",100)),
            "image_file_id": image_id,
            "special_drops": [],
        }
        result = await db.monsters().insert_one(doc)
        await msg.answer(
            f"✅ **Monster Added!**\n\n"
            f"👹 **{doc['name']}** [{doc['rank']}]\n"
            f"Type: {doc['monster_type']} | Element: {doc['element']}\n"
            f"HP: {doc['hp']:,} | ATK: {doc['attack']:,}\n"
            f"Gate: {doc['gate_rank']} | EXP: {doc['drop_exp']:,}\n"
            f"ID: `{result.inserted_id}`"
        )
    except Exception as e:
        await msg.answer(f"❌ Error: `{e}`")


@router.message(Command("addhunter"))
async def cmd_addhunter(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("❌ Admin only!")
        return

    if "\n" not in msg.text:
        await msg.answer(
            "👥 **ADD HUNTER**\n\n"
            "```\nName: Shadow Sovereign\nRank: SS\nClass: Assassin\n"
            "Element: Dark\nHP: 45000\nAttack: 8500\nDefense: 3500\n"
            "Speed: 420\nSkill: Void Step\nSkill Multiplier: 2.5\n"
            "Passive: Shadow Form\nCombat Power: 12500\n```"
        )
        return

    fields = parse(msg.text.split("\n",1)[1])
    image_id = None
    if msg.reply_to_message and msg.reply_to_message.photo:
        image_id = msg.reply_to_message.photo[-1].file_id

    required = ["name","rank","class","element","hp","attack","defense","speed","combat_power"]
    missing = [f for f in required if f not in fields]
    if missing:
        await msg.answer(f"❌ Missing: **{', '.join(missing)}**")
        return

    existing = await db.hunters().find_one({"name": fields["name"]})
    if existing:
        await msg.answer(f"❌ Hunter **{fields['name']}** already exists!")
        return

    try:
        doc = {
            "name": fields["name"],
            "rank": fields["rank"],
            "hunter_class": fields["class"],
            "element": fields["element"],
            "hp": int(fields["hp"]),
            "attack": int(fields["attack"]),
            "defense": int(fields["defense"]),
            "speed": int(fields["speed"]),
            "skill_name": fields.get("skill","Hunter Strike"),
            "skill_multiplier": float(fields.get("skill_multiplier",1.5)),
            "passive_name": fields.get("passive",""),
            "combat_power": int(fields["combat_power"]),
            "image_file_id": image_id,
            "is_event_exclusive": False,
        }
        result = await db.hunters().insert_one(doc)
        re = config.RANK_EMOJIS.get(doc["rank"],"⬛")
        await msg.answer(
            f"✅ **Hunter Added!**\n\n"
            f"{re} **{doc['name']}** [{doc['rank']}]\n"
            f"{doc['hunter_class']} | {doc['element']}\n"
            f"ATK: {doc['attack']:,} | CP: {doc['combat_power']:,}\n"
            f"Skill: **{doc['skill_name']}** (x{doc['skill_multiplier']})\n"
            f"ID: `{result.inserted_id}`"
        )
    except Exception as e:
        await msg.answer(f"❌ Error: `{e}`")


@router.message(Command("add_weapon"))
async def cmd_add_weapon(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("❌ Admin only!")
        return

    if "\n" not in msg.text:
        await msg.answer(
            "⚔️ **ADD WEAPON**\n\n"
            "```\nName: Demon King's Dagger\nRank: SS\nDamage: 5200\n"
            "Durability: 900\nPrecision: 85\nCrit Rate: 0.25\n"
            "Element: Dark\nPassive: Shadow Amplify\n```"
        )
        return

    fields = parse(msg.text.split("\n",1)[1])
    image_id = None
    if msg.reply_to_message and msg.reply_to_message.photo:
        image_id = msg.reply_to_message.photo[-1].file_id

    required = ["name","rank","damage"]
    missing = [f for f in required if f not in fields]
    if missing:
        await msg.answer(f"❌ Missing: **{', '.join(missing)}**")
        return

    existing = await db.weapons().find_one({"name": fields["name"]})
    if existing:
        await msg.answer(f"❌ Weapon **{fields['name']}** already exists!")
        return

    try:
        doc = {
            "name": fields["name"],
            "rank": fields["rank"],
            "damage": int(fields["damage"]),
            "durability": int(fields.get("durability",500)),
            "precision": int(fields.get("precision",50)),
            "crit_rate": float(fields.get("crit_rate",0.10)),
            "element": fields.get("element","None"),
            "passive_name": fields.get("passive",""),
            "passive_description": fields.get("passive_description",""),
            "image_file_id": image_id,
        }
        result = await db.weapons().insert_one(doc)
        re = config.RANK_EMOJIS.get(doc["rank"],"⬛")
        await msg.answer(
            f"✅ **Weapon Added!**\n\n"
            f"{re} **{doc['name']}** [{doc['rank']}]\n"
            f"DMG: {doc['damage']:,} | Crit: {doc['crit_rate']*100:.0f}%\n"
            f"Element: {doc['element']}\n"
            f"Passive: {doc['passive_name'] or 'None'}\n"
            f"ID: `{result.inserted_id}`"
        )
    except Exception as e:
        await msg.answer(f"❌ Error: `{e}`")


@router.message(Command("adminpanel"))
async def cmd_adminpanel(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("❌ Admin only!")
        return

    p = await db.players().count_documents({})
    m = await db.monsters().count_documents({})
    h = await db.hunters().count_documents({})
    w = await db.weapons().count_documents({})

    await msg.answer(
        f"🛡️ **ADMIN PANEL**\n{'━'*26}\n\n"
        f"👤 Players: **{p}**\n"
        f"👹 Monsters: **{m}**\n"
        f"👥 Hunters: **{h}**\n"
        f"⚔️ Weapons: **{w}**\n\n"
        f"{'─'*24}\n"
        f"/addmonster — Add monster\n"
        f"/addhunter — Add hunter\n"
        f"/add_weapon — Add weapon\n"
        f"/give <id> <coins/tickets> <amount>\n"
        f"/ban <user_id>\n"
        f"{'━'*26}"
    )


@router.message(Command("give"))
async def cmd_give(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("❌ Admin only!")
        return

    args = msg.text.split()
    if len(args) < 4:
        await msg.answer("Usage: /give <user_id> <coins|tickets|gems> <amount>")
        return

    try:
        uid = int(args[1])
        resource = args[2].lower()
        amount = int(args[3])
    except ValueError:
        await msg.answer("❌ Invalid arguments")
        return

    if resource not in ("coins","tickets","gems"):
        await msg.answer("❌ Resource must be: coins, tickets, gems")
        return

    result = await db.players().update_one(
        {"user_id": uid},
        {"$inc": {resource: amount}}
    )
    if result.matched_count:
        await msg.answer(f"✅ Gave **{amount} {resource}** to user **{uid}**")
    else:
        await msg.answer(f"❌ Player {uid} not found")


@router.message(Command("ban"))
async def cmd_ban(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("❌ Admin only!")
        return

    args = msg.text.split()
    if len(args) < 2:
        await msg.answer("Usage: /ban <user_id>")
        return

    try:
        uid = int(args[1])
    except ValueError:
        await msg.answer("❌ Invalid user ID")
        return

    await db.players().update_one({"user_id": uid}, {"$set": {"is_banned": True}})
    await msg.answer(f"✅ Player **{uid}** banned.")

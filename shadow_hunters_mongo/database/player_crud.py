"""
Player database operations using MongoDB.
"""

from datetime import datetime, timedelta
import database.db as db
import config
import random


# ─── DEFAULT PLAYER ───────────────────────────────────────────────────────────

def default_player(user_id: int, username: str = None) -> dict:
    return {
        "user_id": user_id,
        "username": username or "",
        "hunter_name": f"Hunter_{str(user_id)[-4:]}",
        "level": 1,
        "exp": 0,
        "coins": config.STARTING_COINS,
        "gems": 0,
        "tickets": config.STARTING_TICKETS,
        "stamina": config.STARTING_STAMINA,
        "max_stamina": config.MAX_STAMINA,
        "rank": "E",
        # Stats
        "strength": 10,
        "agility": 10,
        "precision": 10,
        "intelligence": 10,
        "vitality": 10,
        "endurance": 10,
        "luck": 5,
        "stat_points": 0,
        # Combat
        "max_hp": 1000,
        "max_mana": 500,
        "combat_power": 100,
        # Equipment
        "equipped_weapon_id": None,
        "team_slots": [],
        # Progress
        "dungeon_clears": 0,
        "pvp_wins": 0,
        "pvp_losses": 0,
        "monsters_killed": 0,
        "boss_kills": 0,
        "total_damage": 0,
        # Gacha pity
        "hunter_pity": 0,
        "weapon_pity": 0,
        # Meta
        "guild_id": None,
        "is_banned": False,
        "last_daily": None,
        "last_stamina_regen": datetime.utcnow(),
        "created_at": datetime.utcnow(),
        "last_active": datetime.utcnow(),
    }


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def calc_combat_power(p: dict) -> int:
    return (
        p["strength"] * 3 + p["agility"] * 2 +
        p["precision"] * 2 + p["intelligence"] * 2 +
        p["vitality"] * 2 + p["endurance"] + p["luck"] +
        p["level"] * 10
    )

def calc_max_hp(p: dict) -> int:
    return 1000 + p["vitality"] * 80 + p["endurance"] * 40 + p["level"] * 50

def calc_max_mana(p: dict) -> int:
    return 500 + p["intelligence"] * 50 + p["level"] * 20

def get_exp_required(level: int) -> int:
    return int(100 * (1.35 ** (level - 1)))

def get_rank(level: int) -> str:
    rank = "E"
    for r, threshold in config.RANK_THRESHOLDS.items():
        if level >= threshold:
            rank = r
    return rank

def recalculate(p: dict) -> dict:
    p["max_hp"] = calc_max_hp(p)
    p["max_mana"] = calc_max_mana(p)
    p["combat_power"] = calc_combat_power(p)
    p["rank"] = get_rank(p["level"])
    return p


# ─── CRUD ─────────────────────────────────────────────────────────────────────

async def get_or_create_player(user_id: int, username: str = None) -> dict:
    player = await db.players().find_one({"user_id": user_id})
    if not player:
        player = default_player(user_id, username)
        player = recalculate(player)
        await db.players().insert_one(player)
        await generate_daily_quests(user_id)
    return player


async def get_player(user_id: int) -> dict:
    return await db.players().find_one({"user_id": user_id})


async def update_player(user_id: int, updates: dict):
    await db.players().update_one(
        {"user_id": user_id},
        {"$set": updates}
    )


async def update_stamina(player: dict) -> dict:
    now = datetime.utcnow()
    last = player.get("last_stamina_regen", now)
    minutes = (now - last).total_seconds() / 60
    gained = int(minutes / 5)

    if gained > 0 and player["stamina"] < player["max_stamina"]:
        new_stamina = min(player["max_stamina"], player["stamina"] + gained)
        await update_player(player["user_id"], {
            "stamina": new_stamina,
            "last_stamina_regen": now,
        })
        player["stamina"] = new_stamina
        player["last_stamina_regen"] = now
    return player


async def add_exp(user_id: int, player: dict, exp: int) -> dict:
    result = {"leveled_up": False, "levels_gained": 0, "new_level": player["level"]}
    player["exp"] += exp

    while player["exp"] >= get_exp_required(player["level"]):
        player["exp"] -= get_exp_required(player["level"])
        player["level"] += 1
        player["stat_points"] += 5
        result["leveled_up"] = True
        result["levels_gained"] += 1

    old_rank = player["rank"]
    player = recalculate(player)
    result["new_level"] = player["level"]

    if player["rank"] != old_rank:
        result["rank_up"] = player["rank"]

    await update_player(user_id, {
        "exp": player["exp"],
        "level": player["level"],
        "stat_points": player["stat_points"],
        "max_hp": player["max_hp"],
        "max_mana": player["max_mana"],
        "combat_power": player["combat_power"],
        "rank": player["rank"],
    })
    return result


async def claim_daily(user_id: int, player: dict) -> dict:
    now = datetime.utcnow()
    last = player.get("last_daily")

    if last and (now - last).total_seconds() < 86400:
        remaining = timedelta(seconds=86400) - (now - last)
        h = int(remaining.total_seconds() // 3600)
        m = int((remaining.total_seconds() % 3600) // 60)
        return {"success": False, "message": f"⏳ Come back in **{h}h {m}m**"}

    new_coins = player["coins"] + config.DAILY_REWARD_COINS
    new_tickets = player["tickets"] + config.DAILY_REWARD_TICKETS
    new_stamina = min(player["max_stamina"], player["stamina"] + 50)

    await update_player(user_id, {
        "coins": new_coins,
        "tickets": new_tickets,
        "stamina": new_stamina,
        "last_daily": now,
    })
    return {
        "success": True,
        "coins": config.DAILY_REWARD_COINS,
        "tickets": config.DAILY_REWARD_TICKETS,
        "stamina": 50,
    }


async def upgrade_stat(user_id: int, player: dict, stat: str, points: int) -> dict:
    valid = ["strength", "agility", "precision", "intelligence", "vitality", "endurance", "luck"]
    if stat not in valid:
        return {"success": False, "message": f"❌ Invalid stat! Choose: {', '.join(valid)}"}
    if player["stat_points"] < points:
        return {"success": False, "message": f"❌ Not enough stat points! You have **{player['stat_points']}**"}

    player[stat] += points
    player["stat_points"] -= points
    player = recalculate(player)

    await update_player(user_id, {
        stat: player[stat],
        "stat_points": player["stat_points"],
        "max_hp": player["max_hp"],
        "max_mana": player["max_mana"],
        "combat_power": player["combat_power"],
    })
    return {"success": True, "stat": stat, "new_value": player[stat]}


async def get_leaderboard(limit: int = 10) -> list:
    cursor = db.players().find(
        {"is_banned": False},
        {"hunter_name": 1, "level": 1, "rank": 1, "combat_power": 1, "pvp_wins": 1}
    ).sort("combat_power", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_pvp_leaderboard(limit: int = 10) -> list:
    cursor = db.players().find(
        {"is_banned": False},
        {"hunter_name": 1, "rank": 1, "pvp_wins": 1, "pvp_losses": 1}
    ).sort("pvp_wins", -1).limit(limit)
    return await cursor.to_list(length=limit)


# ─── INVENTORY ────────────────────────────────────────────────────────────────

async def add_to_inventory(user_id: int, item_type: str, item_id: str, item_name: str, qty: int = 1):
    existing = await db.inventory().find_one({
        "user_id": user_id, "item_type": item_type, "item_id": item_id
    })
    if existing and item_type != "weapon":
        await db.inventory().update_one(
            {"_id": existing["_id"]},
            {"$inc": {"quantity": qty}}
        )
    else:
        await db.inventory().insert_one({
            "user_id": user_id,
            "item_type": item_type,
            "item_id": item_id,
            "item_name": item_name,
            "quantity": qty,
            "obtained_at": datetime.utcnow(),
        })


async def get_inventory(user_id: int, item_type: str = None) -> list:
    query = {"user_id": user_id}
    if item_type:
        query["item_type"] = item_type
    cursor = db.inventory().find(query).sort("obtained_at", -1)
    return await cursor.to_list(length=200)


# ─── QUESTS ───────────────────────────────────────────────────────────────────

QUEST_TEMPLATES = [
    {"key": "clear_dungeons", "desc": "🚪 Clear 3 dungeons", "target": 3,
     "coins": 300, "exp": 200, "tickets": 1},
    {"key": "defeat_monsters", "desc": "⚔️ Defeat 15 monsters", "target": 15,
     "coins": 200, "exp": 150, "tickets": 0},
    {"key": "win_pvp", "desc": "🥊 Win 2 PvP battles", "target": 2,
     "coins": 500, "exp": 300, "tickets": 1},
    {"key": "summon_hunters", "desc": "🎰 Summon 3 hunters", "target": 3,
     "coins": 150, "exp": 100, "tickets": 0},
]


async def generate_daily_quests(user_id: int):
    tomorrow = datetime.utcnow().replace(hour=0, minute=0, second=0) + timedelta(days=1)
    await db.quests().delete_many({"user_id": user_id, "quest_type": "daily"})

    selected = random.sample(QUEST_TEMPLATES, 3)
    docs = []
    for t in selected:
        docs.append({
            "user_id": user_id,
            "quest_type": "daily",
            "key": t["key"],
            "description": t["desc"],
            "target": t["target"],
            "progress": 0,
            "completed": False,
            "reward_coins": t["coins"],
            "reward_exp": t["exp"],
            "reward_tickets": t["tickets"],
            "expires_at": tomorrow,
        })
    await db.quests().insert_many(docs)


async def update_quest_progress(user_id: int, key: str, increment: int = 1) -> list:
    now = datetime.utcnow()
    cursor = db.quests().find({
        "user_id": user_id, "key": key,
        "completed": False, "expires_at": {"$gt": now}
    })
    quests = await cursor.to_list(length=10)
    completed = []

    for q in quests:
        new_progress = min(q["target"], q["progress"] + increment)
        is_done = new_progress >= q["target"]
        await db.quests().update_one(
            {"_id": q["_id"]},
            {"$set": {"progress": new_progress, "completed": is_done}}
        )
        if is_done:
            completed.append(q)
    return completed

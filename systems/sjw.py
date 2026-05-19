"""
Sung Jin-Woo System
- SJW is every player's permanent main hunter
- Rank auto-upgrades based on player level
- Each rank has a custom image set by admin via /set_sjw_image <rank>
- /hunters shows SJW as (MAIN) at the top
"""
import database.db as db
import config

SJW_RANK_LEVELS = {
    "E":  1,
    "D":  10,
    "C":  25,
    "B":  45,
    "A":  70,
    "S":  100,
    "SS": 150,
}

SJW_RANK_TITLES = {
    "E":  "The Weakest Hunter",
    "D":  "Awakened Hunter",
    "C":  "Rising Shadow",
    "B":  "Shadow Warrior",
    "A":  "Shadow Sovereign",
    "S":  "Shadow Monarch Candidate",
    "SS": "☠️ Shadow Monarch",
}

SJW_RANK_STATS = {
    "E":  {"attack": 135,  "hp": 2000,   "cp": 135},
    "D":  {"attack": 600,  "hp": 8000,   "cp": 1800},
    "C":  {"attack": 2500, "hp": 30000,  "cp": 15000},
    "B":  {"attack": 6000, "hp": 80000,  "cp": 50000},
    "A":  {"attack": 15000,"hp": 200000, "cp": 150000},
    "S":  {"attack": 50000,"hp": 600000, "cp": 500000},
    "SS": {"attack": 99999,"hp": 999999, "cp": 1000000},
}

RANK_ORDER = ["E", "D", "C", "B", "A", "S", "SS"]


async def get_sjw_rank(player_level: int) -> str:
    """Get current SJW rank based on player level."""
    current = "E"
    for rank, min_level in SJW_RANK_LEVELS.items():
        if player_level >= min_level:
            current = rank
    return current


async def get_sjw_image(rank: str) -> str | None:
    """Get Sung Jin-Woo image for a specific rank from DB."""
    doc = await db.settings().find_one({"key": f"sjw_image_{rank}"})
    return doc["value"] if doc else None


async def set_sjw_image(rank: str, file_id: str):
    """Save Sung Jin-Woo rank image to DB."""
    await db.settings().update_one(
        {"key": f"sjw_image_{rank}"},
        {"$set": {"key": f"sjw_image_{rank}", "value": file_id}},
        upsert=True
    )


async def get_sjw_card(player: dict) -> dict:
    """Get full SJW card data for a player."""
    rank = await get_sjw_rank(player["level"])
    image = await get_sjw_image(rank)
    stats = SJW_RANK_STATS.get(rank, SJW_RANK_STATS["E"])
    title = SJW_RANK_TITLES.get(rank, "Hunter")
    rank_info = config.SUNG_JINWOO_RANKS.get(rank, {})
    emoji = rank_info.get("emoji", "⬛")

    return {
        "rank": rank,
        "title": title,
        "emoji": emoji,
        "image": image,
        "stats": stats,
    }


async def get_royale_image(banner_type: str) -> str | None:
    """Get hunter/weapon royale banner image."""
    doc = await db.settings().find_one({"key": f"royale_image_{banner_type}"})
    return doc["value"] if doc else None


async def set_royale_image(banner_type: str, file_id: str):
    """Save royale banner image."""
    await db.settings().update_one(
        {"key": f"royale_image_{banner_type}"},
        {"$set": {"key": f"royale_image_{banner_type}", "value": file_id}},
        upsert=True
    )


async def get_fav_hunter(user_id: int) -> dict | None:
    """Get user's favourite hunter set via /fav."""
    doc = await db.settings().find_one({"key": f"fav_{user_id}"})
    if not doc:
        return None
    return await db.hunters().find_one({"_id": doc["hunter_id"]})


async def set_fav_hunter(user_id: int, hunter_id):
    """Set user's favourite hunter."""
    await db.settings().update_one(
        {"key": f"fav_{user_id}"},
        {"$set": {"key": f"fav_{user_id}", "hunter_id": hunter_id}},
        upsert=True
    )

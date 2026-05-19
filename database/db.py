"""
MongoDB connection using Motor (async MongoDB driver).
No Redis, no PostgreSQL — just MongoDB Atlas.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger
import config

# Global client
_client: AsyncIOMotorClient = None
_db = None


async def connect_db():
    """Connect to MongoDB Atlas."""
    global _client, _db
    _client = AsyncIOMotorClient(config.MONGODB_URL)
    _db = _client[config.DB_NAME]

    # Create indexes for fast queries
    await _db.players.create_index("user_id", unique=True)
    await _db.players.create_index("combat_power")
    await _db.players.create_index("pvp_wins")
    await _db.hunters.create_index("name", unique=True)
    await _db.weapons.create_index("name", unique=True)
    await _db.monsters.create_index("gate_rank")
    await _db.guilds.create_index("name")

    logger.info("✅ Connected to MongoDB Atlas!")


async def close_db():
    """Close MongoDB connection."""
    global _client
    if _client:
        _client.close()
        logger.info("✅ MongoDB connection closed.")


def get_db():
    """Get database instance."""
    return _db


# ─── COLLECTION SHORTCUTS ─────────────────────────────────────────────────────

def players():
    return _db.players

def hunters():
    return _db.hunters

def weapons():
    return _db.weapons

def monsters():
    return _db.monsters

def guilds():
    return _db.guilds

def inventory():
    return _db.inventory

def dungeon_runs():
    return _db.dungeon_runs

def pvp_battles():
    return _db.pvp_battles

def quests():
    return _db.quests

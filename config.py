import os
from dotenv import load_dotenv

load_dotenv()

# ─── BOT ──────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "123456789").strip("[]").split(",")))

# ─── MONGODB ──────────────────────────────────────────────────────────────────
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = "shadow_hunters"

# ─── GAME SETTINGS ────────────────────────────────────────────────────────────
STARTING_COINS = 1000
STARTING_TICKETS = 5
STARTING_STAMINA = 100
MAX_STAMINA = 100
DAILY_REWARD_COINS = 500
DAILY_REWARD_TICKETS = 2
MAX_TEAM_SIZE = 5

# ─── COMBAT ───────────────────────────────────────────────────────────────────
BASE_CRIT_CHANCE = 0.10
BASE_DODGE_CHANCE = 0.05
CRIT_MULTIPLIER = 1.75

# ─── GACHA RATES ──────────────────────────────────────────────────────────────
HUNTER_RATES = {
    "E":  65.0,
    "D":  17.0,
    "C":  17.0,
    "B":  10.0,
    "A":   5.0,
    "S":   2.0,
    "SS":  1.0,
}
WEAPON_RATES = {
    "E":  65.0,
    "D":  17.0,
    "C":  17.0,
    "B":  10.0,
    "A":   5.0,
    "S":   2.0,
    "SS":  1.0,
}
HUNTER_PITY = 80
WEAPON_PITY = 90

# ─── RANK THRESHOLDS ──────────────────────────────────────────────────────────
RANK_THRESHOLDS = {
    "E": 0,
    "D": 10,
    "C": 25,
    "B": 45,
    "A": 70,
    "S": 100,
    "SS": 150,
    "National": 200,
}

RANK_EMOJIS = {
    "E": "⬛", "D": "🟫", "C": "🟩",
    "B": "🟦", "A": "🟪", "S": "🟨",
    "SS": "🔶", "National": "🔱",
}

ELEMENT_EMOJIS = {
    "Fire": "🔥", "Water": "💧", "Wind": "🌪️",
    "Earth": "🌍", "Light": "✨", "Dark": "🌑",
    "Lightning": "⚡", "Ice": "❄️", "None": "⚪",
}

ELEMENT_ADVANTAGES = {
    "Fire": "Wind", "Wind": "Earth",
    "Earth": "Lightning", "Lightning": "Water",
    "Water": "Fire", "Light": "Dark",
    "Dark": "Light", "Ice": "Fire",
}

CLASS_EMOJIS = {
    "Tank": "🛡️", "Mage": "🔮", "Assassin": "🗡️",
    "Healer": "💚", "Summoner": "👻",
    "Fighter": "👊", "Ranger": "🏹",
}

GATE_CONFIG = {
    "E Gate": {"rank": "E", "min_level": 1, "stamina_cost": 10, "emoji": "🚪"},
    "D Gate": {"rank": "D", "min_level": 10, "stamina_cost": 15, "emoji": "🚪"},
    "C Gate": {"rank": "C", "min_level": 25, "stamina_cost": 20, "emoji": "🌀"},
    "B Gate": {"rank": "B", "min_level": 45, "stamina_cost": 25, "emoji": "🌀"},
    "A Gate": {"rank": "A", "min_level": 70, "stamina_cost": 35, "emoji": "💜"},
    "S Gate": {"rank": "S", "min_level": 100, "stamina_cost": 50, "emoji": "🔴"},
    "Red Gate": {"rank": "S", "min_level": 120, "stamina_cost": 60, "emoji": "🔴"},
    "Double Dungeon": {"rank": "SS", "min_level": 150, "stamina_cost": 80, "emoji": "⚫"},
}

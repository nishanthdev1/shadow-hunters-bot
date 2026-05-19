"""
Sung Jin-Woo Skill System
Players unlock skills as they level up and can equip 4 active skills.
"""

# ─── ALL SKILLS ───────────────────────────────────────────────────────────────

ALL_SKILLS = {
    # ── BEGINNER (E-D Rank) ──
    "sprint": {
        "id": "sprint",
        "name": "⚡ Sprint",
        "type": "Active",
        "rank_required": "E",
        "level_required": 1,
        "description": "Temporary speed boost. Dodge chance +20% for 1 turn.",
        "damage_multiplier": 1.0,
        "effect": "dodge_boost",
        "mana_cost": 15,
        "rarity": "Common",
        "color": "⬜",
    },
    "vital_strike": {
        "id": "vital_strike",
        "name": "🗡️ Vital Strike",
        "type": "Active",
        "rank_required": "E",
        "level_required": 1,
        "description": "Basic critical attack targeting vital points.",
        "damage_multiplier": 1.8,
        "effect": "crit_boost",
        "mana_cost": 20,
        "rarity": "Common",
        "color": "⬜",
    },
    "stealth": {
        "id": "stealth",
        "name": "🌑 Stealth",
        "type": "Passive",
        "rank_required": "E",
        "level_required": 5,
        "description": "Reduces enemy detection. Dodge +10% permanently.",
        "damage_multiplier": 1.0,
        "effect": "passive_dodge",
        "mana_cost": 0,
        "rarity": "Common",
        "color": "⬜",
    },
    "dagger_mastery": {
        "id": "dagger_mastery",
        "name": "⚔️ Dagger Mastery",
        "type": "Passive",
        "rank_required": "E",
        "level_required": 8,
        "description": "Increases dagger damage. ATK +15% permanently.",
        "damage_multiplier": 1.15,
        "effect": "passive_atk",
        "mana_cost": 0,
        "rarity": "Common",
        "color": "⬜",
    },

    # ── INTERMEDIATE (C-B Rank) ──
    "bloodlust": {
        "id": "bloodlust",
        "name": "🩸 Bloodlust",
        "type": "Debuff",
        "rank_required": "C",
        "level_required": 25,
        "description": "Fear aura weakens all enemies. Enemy ATK -25%.",
        "damage_multiplier": 1.5,
        "effect": "enemy_atk_down",
        "mana_cost": 35,
        "rarity": "Rare",
        "color": "🟩",
    },
    "quick_slash": {
        "id": "quick_slash",
        "name": "💨 Quick Slash",
        "type": "Active",
        "rank_required": "D",
        "level_required": 15,
        "description": "Rapid multi-hit combo. 3 hits at reduced damage.",
        "damage_multiplier": 2.2,
        "effect": "multi_hit",
        "mana_cost": 30,
        "rarity": "Rare",
        "color": "🟩",
    },
    "assassination": {
        "id": "assassination",
        "name": "☠️ Assassination",
        "type": "Active",
        "rank_required": "C",
        "level_required": 25,
        "description": "Bonus damage from blind spot. Guaranteed crit.",
        "damage_multiplier": 2.8,
        "effect": "guaranteed_crit",
        "mana_cost": 45,
        "rarity": "Rare",
        "color": "🟩",
    },
    "dash": {
        "id": "dash",
        "name": "💫 Dash",
        "type": "Movement",
        "rank_required": "D",
        "level_required": 12,
        "description": "Blink-speed movement. Speed +50% for 1 turn.",
        "damage_multiplier": 1.3,
        "effect": "speed_boost",
        "mana_cost": 25,
        "rarity": "Rare",
        "color": "🟩",
    },

    # ── ADVANCED (A-S Rank) ──
    "rulers_authority": {
        "id": "rulers_authority",
        "name": "👑 Ruler's Authority",
        "type": "Active",
        "rank_required": "A",
        "level_required": 70,
        "description": "Telekinesis — lift and crush enemies dealing massive damage.",
        "damage_multiplier": 3.5,
        "effect": "telekinesis",
        "mana_cost": 60,
        "rarity": "Epic",
        "color": "🟦",
    },
    "shadow_extraction": {
        "id": "shadow_extraction",
        "name": "🌑 Shadow Extraction",
        "type": "Monarch Skill",
        "rank_required": "S",
        "level_required": 100,
        "description": "Extract shadows from fallen enemies to fight for you.",
        "damage_multiplier": 4.0,
        "effect": "shadow_summon",
        "mana_cost": 80,
        "rarity": "Legendary",
        "color": "🟪",
    },
    "mutilate": {
        "id": "mutilate",
        "name": "💀 Mutilate",
        "type": "Active",
        "rank_required": "B",
        "level_required": 45,
        "description": "Devastating combo attack dealing extreme damage.",
        "damage_multiplier": 3.8,
        "effect": "devastate",
        "mana_cost": 70,
        "rarity": "Epic",
        "color": "🟦",
    },
    "dominators_touch": {
        "id": "dominators_touch",
        "name": "✋ Dominator's Touch",
        "type": "Active",
        "rank_required": "S",
        "level_required": 100,
        "description": "Force manipulation — obliterate enemy defenses.",
        "damage_multiplier": 3.2,
        "effect": "defense_break",
        "mana_cost": 65,
        "rarity": "Legendary",
        "color": "🟪",
    },
    "shadow_storage": {
        "id": "shadow_storage",
        "name": "🌀 Shadow Storage",
        "type": "Utility",
        "rank_required": "A",
        "level_required": 75,
        "description": "Store shadow army in dimension. Team power +30%.",
        "damage_multiplier": 1.5,
        "effect": "team_boost",
        "mana_cost": 50,
        "rarity": "Epic",
        "color": "🟦",
    },

    # ── SHADOW MONARCH ──
    "shadow_monarch_authority": {
        "id": "shadow_monarch_authority",
        "name": "⚫ Shadow Monarch Authority",
        "type": "Ultimate",
        "rank_required": "SS",
        "level_required": 150,
        "description": "Full control over all shadows. Massive damage + fear aura.",
        "damage_multiplier": 6.0,
        "effect": "monarch_aura",
        "mana_cost": 120,
        "rarity": "Mythic",
        "color": "🔴",
    },
    "shadow_exchange": {
        "id": "shadow_exchange",
        "name": "🌑 Shadow Exchange",
        "type": "Movement",
        "rank_required": "SS",
        "level_required": 150,
        "description": "Instantly teleport to shadow position, striking from behind.",
        "damage_multiplier": 4.5,
        "effect": "teleport_strike",
        "mana_cost": 90,
        "rarity": "Mythic",
        "color": "🔴",
    },
    "dragon_fear": {
        "id": "dragon_fear",
        "name": "🐉 Dragon Fear",
        "type": "Aura",
        "rank_required": "National",
        "level_required": 200,
        "description": "Massive intimidation aura. All enemy stats -50%.",
        "damage_multiplier": 5.0,
        "effect": "mass_debuff",
        "mana_cost": 100,
        "rarity": "Mythic",
        "color": "🔴",
    },
    "army_summon": {
        "id": "army_summon",
        "name": "👹 Army Summon",
        "type": "Summon",
        "rank_required": "National",
        "level_required": 200,
        "description": "Summon entire shadow army. Devastating team assault.",
        "damage_multiplier": 7.0,
        "effect": "shadow_army",
        "mana_cost": 150,
        "rarity": "Mythic",
        "color": "🔴",
    },
    "monarch_domain": {
        "id": "monarch_domain",
        "name": "♾️ Monarch Domain",
        "type": "Ultimate",
        "rank_required": "National",
        "level_required": 200,
        "description": "Massive stat amplification. All stats x2 for battle.",
        "damage_multiplier": 8.0,
        "effect": "stat_amplify",
        "mana_cost": 200,
        "rarity": "Monarch",
        "color": "🏆",
    },
}

# Default starting skills for new players
DEFAULT_SKILLS = ["vital_strike", "sprint"]

# Rank order for comparisons
RANK_ORDER = ["E", "D", "C", "B", "A", "S", "SS", "National"]

RARITY_COLORS = {
    "Common": "⬜",
    "Rare": "🟩",
    "Epic": "🟦",
    "Legendary": "🟪",
    "Mythic": "🔴",
    "Monarch": "🏆",
}


def get_unlocked_skills(player_rank: str, player_level: int) -> list:
    """Get all skills the player can unlock based on rank and level."""
    unlocked = []
    rank_idx = RANK_ORDER.index(player_rank) if player_rank in RANK_ORDER else 0

    for skill_id, skill in ALL_SKILLS.items():
        req_rank = skill["rank_required"]
        req_level = skill["level_required"]
        req_rank_idx = RANK_ORDER.index(req_rank) if req_rank in RANK_ORDER else 0

        if rank_idx >= req_rank_idx and player_level >= req_level:
            unlocked.append(skill)

    return unlocked


def get_skill(skill_id: str) -> dict:
    return ALL_SKILLS.get(skill_id)


def format_skill_card(skill: dict) -> str:
    rarity_color = RARITY_COLORS.get(skill["rarity"], "⬜")
    type_emoji = {
        "Active": "⚔️",
        "Passive": "🛡️",
        "Debuff": "💀",
        "Movement": "💨",
        "Monarch Skill": "👑",
        "Utility": "🔧",
        "Ultimate": "💥",
        "Aura": "🌟",
        "Summon": "👹",
    }.get(skill["type"], "✨")

    return (
        f"{rarity_color} <b>{skill['name']}</b>\n"
        f"   {type_emoji} {skill['type']} | 💧 {skill['mana_cost']} Mana\n"
        f"   ⚡ Power: x{skill['damage_multiplier']} | {skill['rarity']}\n"
        f"   📖 {skill['description']}"
    )

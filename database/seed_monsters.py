"""
Auto-seed default monsters for all gate ranks.
Called on bot startup if DB is empty.
"""
import database.db as db

DEFAULT_MONSTERS = [
    # ── E GATE ──
    {"name": "Goblin Scout", "rank": "E", "monster_type": "Normal", "hp": 400, "attack": 60, "defense": 20, "speed": 45, "element": "None", "gate_rank": "E", "drop_exp": 80, "drop_coins": 40, "spawn_weight": 100, "skills": [{"name": "Scratch", "multiplier": 1.3}], "image_file_id": None},
    {"name": "Iron Golem", "rank": "E", "monster_type": "Normal", "hp": 700, "attack": 80, "defense": 50, "speed": 25, "element": "Earth", "gate_rank": "E", "drop_exp": 120, "drop_coins": 60, "spawn_weight": 80, "skills": [{"name": "Stone Slam", "multiplier": 1.5}], "image_file_id": None},
    {"name": "Dire Wolf", "rank": "E", "monster_type": "Normal", "hp": 500, "attack": 90, "defense": 15, "speed": 70, "element": "None", "gate_rank": "E", "drop_exp": 100, "drop_coins": 50, "spawn_weight": 90, "skills": [{"name": "Feral Bite", "multiplier": 1.4}], "image_file_id": None},
    {"name": "Dungeon Cerberus", "rank": "E", "monster_type": "Boss", "hp": 1800, "attack": 150, "defense": 60, "speed": 55, "element": "Fire", "gate_rank": "E", "drop_exp": 350, "drop_coins": 200, "spawn_weight": 30, "skills": [{"name": "Hellfire Bite", "multiplier": 2.0}], "image_file_id": None},

    # ── D GATE ──
    {"name": "Orc Warrior", "rank": "D", "monster_type": "Normal", "hp": 1200, "attack": 180, "defense": 80, "speed": 40, "element": "Earth", "gate_rank": "D", "drop_exp": 200, "drop_coins": 100, "spawn_weight": 100, "skills": [{"name": "Brutal Cleave", "multiplier": 1.6}], "image_file_id": None},
    {"name": "Shadow Bat", "rank": "D", "monster_type": "Normal", "hp": 900, "attack": 160, "defense": 40, "speed": 90, "element": "Dark", "gate_rank": "D", "drop_exp": 180, "drop_coins": 90, "spawn_weight": 90, "skills": [{"name": "Darkness Shroud", "multiplier": 1.5}], "image_file_id": None},
    {"name": "Stone Troll", "rank": "D", "monster_type": "Elite", "hp": 2500, "attack": 220, "defense": 120, "speed": 30, "element": "Earth", "gate_rank": "D", "drop_exp": 400, "drop_coins": 200, "spawn_weight": 50, "skills": [{"name": "Rock Crush", "multiplier": 1.8}], "image_file_id": None},
    {"name": "Dungeon Lizard King", "rank": "D", "monster_type": "Boss", "hp": 4000, "attack": 300, "defense": 150, "speed": 60, "element": "Fire", "gate_rank": "D", "drop_exp": 800, "drop_coins": 450, "spawn_weight": 25, "skills": [{"name": "Blazing Tail", "multiplier": 2.2}], "image_file_id": None},

    # ── C GATE ──
    {"name": "Dark Knight", "rank": "C", "monster_type": "Normal", "hp": 3500, "attack": 450, "defense": 200, "speed": 80, "element": "Dark", "gate_rank": "C", "drop_exp": 500, "drop_coins": 250, "spawn_weight": 100, "skills": [{"name": "Shadow Slash", "multiplier": 1.8}], "image_file_id": None},
    {"name": "Frost Wyrm", "rank": "C", "monster_type": "Elite", "hp": 5000, "attack": 550, "defense": 250, "speed": 65, "element": "Ice", "gate_rank": "C", "drop_exp": 700, "drop_coins": 350, "spawn_weight": 60, "skills": [{"name": "Blizzard Breath", "multiplier": 2.0}], "image_file_id": None},
    {"name": "Demon General Baran", "rank": "C", "monster_type": "Boss", "hp": 12000, "attack": 800, "defense": 400, "speed": 90, "element": "Lightning", "gate_rank": "C", "drop_exp": 2000, "drop_coins": 1000, "spawn_weight": 20, "skills": [{"name": "Thunder Spear", "multiplier": 2.8}], "image_file_id": None},

    # ── B GATE ──
    {"name": "Skeleton Archer", "rank": "B", "monster_type": "Normal", "hp": 6000, "attack": 800, "defense": 300, "speed": 110, "element": "Dark", "gate_rank": "B", "drop_exp": 900, "drop_coins": 450, "spawn_weight": 100, "skills": [{"name": "Bone Arrow", "multiplier": 1.9}], "image_file_id": None},
    {"name": "Flame Golem", "rank": "B", "monster_type": "Elite", "hp": 9000, "attack": 1000, "defense": 500, "speed": 50, "element": "Fire", "gate_rank": "B", "drop_exp": 1200, "drop_coins": 600, "spawn_weight": 60, "skills": [{"name": "Magma Fist", "multiplier": 2.2}], "image_file_id": None},
    {"name": "Ice Elf Commander", "rank": "B", "monster_type": "Boss", "hp": 22000, "attack": 1500, "defense": 700, "speed": 130, "element": "Ice", "gate_rank": "B", "drop_exp": 4000, "drop_coins": 2000, "spawn_weight": 20, "skills": [{"name": "Frozen Domain", "multiplier": 3.0}], "image_file_id": None},

    # ── A GATE ──
    {"name": "Winged Dragon", "rank": "A", "monster_type": "Elite", "hp": 18000, "attack": 2200, "defense": 900, "speed": 140, "element": "Wind", "gate_rank": "A", "drop_exp": 2500, "drop_coins": 1200, "spawn_weight": 70, "skills": [{"name": "Storm Wing", "multiplier": 2.5}], "image_file_id": None},
    {"name": "Demon Noble", "rank": "A", "monster_type": "Elite", "hp": 22000, "attack": 2800, "defense": 1100, "speed": 120, "element": "Dark", "gate_rank": "A", "drop_exp": 3000, "drop_coins": 1500, "spawn_weight": 60, "skills": [{"name": "Void Rend", "multiplier": 2.8}], "image_file_id": None},
    {"name": "Architect of Death", "rank": "A", "monster_type": "Boss", "hp": 55000, "attack": 4000, "defense": 1800, "speed": 160, "element": "Dark", "gate_rank": "A", "drop_exp": 9000, "drop_coins": 5000, "spawn_weight": 15, "skills": [{"name": "Necrotic Eruption", "multiplier": 3.5}], "image_file_id": None},

    # ── S GATE ──
    {"name": "Igris the Bloody Red", "rank": "S", "monster_type": "Boss", "hp": 150000, "attack": 12000, "defense": 5000, "speed": 300, "element": "Dark", "gate_rank": "S", "drop_exp": 25000, "drop_coins": 15000, "spawn_weight": 40, "skills": [{"name": "Red Knight Charge", "multiplier": 4.0}], "image_file_id": None},
    {"name": "Beru the Ant King", "rank": "S", "monster_type": "Boss", "hp": 200000, "attack": 18000, "defense": 7000, "speed": 400, "element": "Dark", "gate_rank": "S", "drop_exp": 35000, "drop_coins": 20000, "spawn_weight": 25, "skills": [{"name": "Venom Assault", "multiplier": 4.5}], "image_file_id": None},

    # ── SS / Double Dungeon ──
    {"name": "Monarchs' Shadow", "rank": "SS", "monster_type": "Mythic", "hp": 500000, "attack": 50000, "defense": 20000, "speed": 600, "element": "Dark", "gate_rank": "SS", "drop_exp": 100000, "drop_coins": 60000, "spawn_weight": 20, "skills": [{"name": "Monarch's Wrath", "multiplier": 6.0}], "image_file_id": None},
    {"name": "Antares the Destruction", "rank": "SS", "monster_type": "Mythic", "hp": 999999, "attack": 99999, "defense": 40000, "speed": 800, "element": "Fire", "gate_rank": "SS", "drop_exp": 250000, "drop_coins": 150000, "spawn_weight": 10, "skills": [{"name": "Apocalypse Nova", "multiplier": 8.0}], "image_file_id": None},
]


async def seed_if_empty():
    """Seed monsters only if collection is empty."""
    count = await db.monsters().count_documents({})
    if count == 0:
        await db.monsters().insert_many(DEFAULT_MONSTERS)
        return len(DEFAULT_MONSTERS)
    return 0

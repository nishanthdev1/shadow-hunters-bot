import random
import database.db as db
from battles.engine import player_to_combatant, monster_to_combatant, run_pve
from database.player_crud import add_exp, add_to_inventory, update_quest_progress, update_player
import config


async def enter_dungeon(player: dict, gate_type: str) -> dict:
    gate = config.GATE_CONFIG.get(gate_type)
    if not gate:
        return {"success": False, "message": "❌ Unknown gate type."}

    if player["level"] < gate["min_level"]:
        return {"success": False, "message": f"❌ Need level **{gate['min_level']}** for {gate_type}. You are level **{player['level']}**."}

    if player["stamina"] < gate["stamina_cost"]:
        return {"success": False, "message": f"❌ Not enough stamina! Need **{gate['stamina_cost']}** ⚡\nYours: **{player['stamina']}/{player['max_stamina']}**"}

    # Deduct stamina
    user_id = player["user_id"]
    await update_player(user_id, {"stamina": player["stamina"] - gate["stamina_cost"]})

    # Get weapon
    weapon = None
    if player.get("equipped_weapon_id"):
        weapon = await db.weapons().find_one({"_id": player["equipped_weapon_id"]})

    # Get team
    team = []
    for hid in player.get("team_slots", [])[:5]:
        h = await db.hunters().find_one({"_id": hid})
        if h: team.append(h)

    p_combatant = player_to_combatant(player, weapon, team)

    # Spawn monsters
    monsters = await spawn_monsters(gate["rank"])
    if not monsters:
        return {"success": False, "message": "❌ No monsters found! Admin needs to add monsters with /addmonster"}

    full_log = [
        f"{gate['emoji']} **{gate_type.upper()}** {gate['emoji']}\n"
        f"🗡️ **{player['hunter_name']}** (Lv.{player['level']})\n"
        f"{'━'*26}\n"
        f"⚡ {len(monsters)} monsters ahead!\n"
    ]

    total_exp = 0
    total_coins = 0
    total_dmg = 0
    kills = 0
    loot = []
    success = True
    boss_killed = False

    for i, monster in enumerate(monsters):
        is_boss = (i == len(monsters) - 1)
        if is_boss:
            full_log.append(f"\n👹 **BOSS: {monster['name']}!**")

        m_combatant = monster_to_combatant(monster)
        if is_boss:
            m_combatant.hp = int(m_combatant.hp * 1.5)
            m_combatant.max_hp = m_combatant.hp
            m_combatant.attack = int(m_combatant.attack * 1.3)

        result = run_pve(p_combatant, m_combatant)
        full_log.extend(result.log)
        total_dmg += result.player_damage

        if result.victory:
            kills += 1
            total_exp += monster.get("drop_exp", 100)
            total_coins += monster.get("drop_coins", 50)
            if is_boss:
                total_exp = int(total_exp * 1.5)
                total_coins = int(total_coins * 2)
                boss_killed = True

            dropped = await roll_loot(monster, is_boss)
            loot.extend(dropped)
            p_combatant.hp = min(p_combatant.max_hp, p_combatant.hp + int(p_combatant.max_hp * 0.10))
        else:
            success = False
            total_exp = int(total_exp * 0.25)
            total_coins = int(total_coins * 0.25)
            break

    # Apply rewards
    updates = {
        "coins": player["coins"] + total_coins,
        "total_damage": player.get("total_damage", 0) + total_dmg,
        "monsters_killed": player.get("monsters_killed", 0) + kills,
    }
    if success:
        updates["dungeon_clears"] = player.get("dungeon_clears", 0) + 1
    if boss_killed:
        updates["boss_kills"] = player.get("boss_kills", 0) + 1

    await update_player(user_id, updates)

    for item in loot:
        await add_to_inventory(user_id, item["type"], item["id"], item["name"], item.get("qty", 1))

    level_result = await add_exp(user_id, player, total_exp)

    if kills > 0:
        await update_quest_progress(user_id, "defeat_monsters", kills)
    if success:
        await update_quest_progress(user_id, "clear_dungeons", 1)

    summary = build_summary(success, total_exp, total_coins, loot, level_result, kills, boss_killed)
    full_log.append(summary)

    return {"success": True, "victory": success, "log": full_log, "exp": total_exp, "coins": total_coins, "loot": loot, "level_up": level_result}


async def spawn_monsters(gate_rank: str, count: int = 4) -> list:
    cursor = db.monsters().find({"gate_rank": gate_rank})
    available = await cursor.to_list(length=50)

    if not available:
        fallback = {"D": "E", "C": "D", "B": "C", "A": "B", "S": "A", "SS": "S"}.get(gate_rank)
        if fallback:
            cursor = db.monsters().find({"gate_rank": fallback})
            available = await cursor.to_list(length=50)

    if not available: return []

    weights = [m.get("spawn_weight", 100) for m in available]
    selected = random.choices(available, weights=weights, k=min(count * 2, len(available) * 3))

    bosses = [m for m in available if m.get("monster_type") in ("Boss", "Mythic")]
    regular = [m for m in selected if m.get("monster_type") not in ("Boss", "Mythic")]

    final = regular[:count - 1]
    final.append(random.choice(bosses) if bosses else random.choice(selected))
    return final


async def roll_loot(monster: dict, is_boss: bool) -> list:
    drops = []
    if random.random() < (0.15 if is_boss else 0.03):
        drops.append({"type": "ticket", "id": "ticket_0", "name": "Hunter Ticket 🎫", "qty": 1})
    if is_boss and random.random() < 0.25:
        w = await db.weapons().find_one({"rank": {"$in": ["C", "B", "A"]}})
        if w:
            drops.append({"type": "weapon", "id": str(w["_id"]), "name": w["name"]})
    if random.random() < (0.20 if is_boss else 0.05):
        drops.append({"type": "material", "id": "shard_1", "name": "Hunter Shard 💎", "qty": random.randint(1, 3)})
    return drops


def build_summary(victory, exp, coins, loot, level_result, kills, boss_killed) -> str:
    lines = [f"\n{'━'*26}", "📊 **DUNGEON SUMMARY**", f"{'━'*26}"]
    lines.append("✅ **CLEARED!**" if victory else "❌ **FAILED**")
    lines.append(f"⚔️ Monsters: **{kills}**")
    if boss_killed: lines.append("👹 Boss: ✅ Defeated")
    lines.append(f"\n💰 Coins: **+{coins:,}**")
    lines.append(f"✨ EXP: **+{exp:,}**")
    if loot:
        lines.append("\n🎁 **Drops:**")
        for item in loot:
            lines.append(f"  • {item['name']}" + (f" x{item.get('qty',1)}" if item.get('qty',1) > 1 else ""))
    if level_result.get("leveled_up"):
        lines.append(f"\n🎉 **LEVEL UP!** → Lv.**{level_result['new_level']}**")
        lines.append(f"   +5 Stat Points!")
    if level_result.get("rank_up"):
        lines.append(f"🔱 **RANK UP!** → **{level_result['rank_up']}**!")
    return "\n".join(lines)

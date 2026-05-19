"""
Dungeon System — Pokemon-style turn-based battle with image support.
"""
import random
import database.db as db
from battles.engine import player_to_combatant, monster_to_combatant, Combatant
from database.player_crud import add_exp, add_to_inventory, update_quest_progress, update_player
import config

# ─── HP BAR ───────────────────────────────────────────────────────────────────

def hp_bar(hp, max_hp, width=10):
    ratio = max(0, hp / max_hp) if max_hp > 0 else 0
    filled = int(ratio * width)
    bar = "█" * filled + "░" * (width - filled)
    if ratio > 0.6:   color = "🟩"
    elif ratio > 0.3: color = "🟨"
    else:             color = "🔴"
    return f"{color}[{bar}]"

# ─── DUNGEON SESSIONS (in-memory) ────────────────────────────────────────────
DUNGEON_SESSIONS: dict = {}

# ─── START DUNGEON ────────────────────────────────────────────────────────────

async def start_dungeon_session(player: dict, gate_type: str) -> dict:
    gate = config.GATE_CONFIG.get(gate_type)
    if not gate:
        return {"success": False, "message": "❌ Unknown gate type."}

    if player["level"] < gate["min_level"]:
        return {"success": False, "message": (
            f"❌ Need level <b>{gate['min_level']}</b> for {gate_type}.\n"
            f"You are level <b>{player['level']}</b>."
        )}

    if player["stamina"] < gate["stamina_cost"]:
        return {"success": False, "message": (
            f"❌ Not enough stamina!\n"
            f"Need <b>{gate['stamina_cost']}</b> ⚡  Yours: <b>{player['stamina']}/{player['max_stamina']}</b>"
        )}

    await update_player(player["user_id"], {"stamina": player["stamina"] - gate["stamina_cost"]})

    weapon = None
    if player.get("equipped_weapon_id"):
        weapon = await db.weapons().find_one({"_id": player["equipped_weapon_id"]})

    team = []
    for hid in player.get("team_slots", [])[:5]:
        h = await db.hunters().find_one({"_id": hid})
        if h: team.append(h)

    p_comb = player_to_combatant(player, weapon, team)

    monsters = await spawn_monsters(gate["rank"])
    if not monsters:
        await update_player(player["user_id"], {"stamina": player["stamina"]})
        return {"success": False, "message": "❌ No monsters found! Use /addmonster to add some."}

    uid = player["user_id"]
    DUNGEON_SESSIONS[uid] = {
        "gate_type": gate_type,
        "gate": gate,
        "player": player,
        "p_comb": p_comb,
        "monsters": monsters,
        "current_idx": 0,
        "m_comb": None,
        "total_exp": 0,
        "total_coins": 0,
        "kills": 0,
        "loot": [],
        "boss_killed": False,
    }

    return {"success": True, "session": DUNGEON_SESSIONS[uid]}


def build_battle_text(session: dict, last_action: str = "") -> tuple:
    """Returns (text, image_file_id) for the battle screen."""
    gate = session["gate"]
    p = session["player"]
    p_comb: Combatant = session["p_comb"]
    monsters = session["monsters"]
    idx = session["current_idx"]
    total = len(monsters)
    monster = monsters[idx]
    is_boss = (idx == total - 1)

    # Init m_comb for this monster if not yet done
    m_comb: Combatant = session.get("m_comb")
    if m_comb is None:
        m_comb = monster_to_combatant(monster)
        if is_boss:
            m_comb.hp = int(m_comb.hp * 1.5)
            m_comb.max_hp = m_comb.hp
            m_comb.attack = int(m_comb.attack * 1.3)
        session["m_comb"] = m_comb

    m_elem = config.ELEMENT_EMOJIS.get(monster.get("element", "None"), "⚪")
    p_elem = config.ELEMENT_EMOJIS.get(p_comb.element, "⚪")
    rank_em = config.RANK_EMOJIS.get(monster.get("rank", "E"), "⬛")
    boss_tag = " 👹 <b>BOSS!</b>" if is_boss else ""

    p_hp_bar  = hp_bar(p_comb.hp,  p_comb.max_hp)
    m_hp_bar  = hp_bar(m_comb.hp,  m_comb.max_hp)

    # Mana bar
    p_mana_pct = int((p_comb.mana / p_comb.max_mana) * 10) if p_comb.max_mana > 0 else 0
    p_mana_bar = "🔵" * p_mana_pct + "⚫" * (10 - p_mana_pct)

    text = (
        f"{gate['emoji']} <b>{session['gate_type'].upper()}</b>  [{idx+1}/{total}]{boss_tag}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{m_elem} {rank_em} <b>{monster['name']}</b>\n"
        f"❤️ {m_hp_bar}\n"
        f"    <b>{max(0, m_comb.hp):,} / {m_comb.max_hp:,} HP</b>\n"
        f"⚔️ ATK: <b>{m_comb.attack:,}</b>  🛡 DEF: <b>{m_comb.defense:,}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{p_elem} 🧿 <b>{p['hunter_name']}</b>  Lv.<b>{p['level']}</b>\n"
        f"❤️ {p_hp_bar}\n"
        f"    <b>{max(0, p_comb.hp):,} / {p_comb.max_hp:,} HP</b>\n"
        f"🔮 [{p_mana_bar}]  <b>{p_comb.mana}/{p_comb.max_mana}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    if last_action:
        text += f"\n{last_action}"

    image_id = monster.get("image_file_id")
    return text, image_id


async def spawn_monsters(gate_rank: str, count: int = 4) -> list:
    cursor = db.monsters().find({"gate_rank": gate_rank})
    available = await cursor.to_list(length=50)

    if not available:
        fallback = {"D": "E", "C": "D", "B": "C", "A": "B", "S": "A", "SS": "S"}.get(gate_rank)
        if fallback:
            cursor = db.monsters().find({"gate_rank": fallback})
            available = await cursor.to_list(length=50)

    if not available:
        return []

    weights = [m.get("spawn_weight", 100) for m in available]
    selected = random.choices(available, weights=weights, k=min(count * 2, len(available) * 3))

    bosses  = [m for m in available if m.get("monster_type") in ("Boss", "Mythic")]
    regular = [m for m in selected  if m.get("monster_type") not in ("Boss", "Mythic")]

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


async def process_dungeon_action(user_id: int, skill_id: str) -> dict:
    """Process one combat turn. Returns updated screen data."""
    from systems.skills import ALL_SKILLS
    from battles.engine import calc_damage

    session = DUNGEON_SESSIONS.get(user_id)
    if not session:
        return {"done": True, "message": "❌ No active dungeon. Use /gate to start."}

    p_comb: Combatant = session["p_comb"]
    monsters = session["monsters"]
    idx = session["current_idx"]
    monster = monsters[idx]
    is_boss = (idx == len(monsters) - 1)
    m_comb: Combatant = session["m_comb"]

    # ── Player attacks ──
    use_skill = False
    skill_txt = ""
    damage_mult = 1.0
    mana_cost = 0

    if skill_id != "basic":
        sk = ALL_SKILLS.get(skill_id)
        if sk and p_comb.mana >= sk["mana_cost"]:
            use_skill = True
            skill_txt = sk["name"]
            damage_mult = sk["damage_multiplier"]
            mana_cost = sk["mana_cost"]

    # Deduct mana BEFORE attack
    if use_skill:
        p_comb.mana = max(0, p_comb.mana - mana_cost)

    dmg, crit, dodged, note = calc_damage(p_comb, m_comb, use_skill)
    if use_skill:
        dmg = int(dmg * damage_mult)

    p_action = ""
    if dodged:
        p_action = f"💨 <b>{monster['name']}</b> evaded your attack!"
    else:
        actual = m_comb.take_damage(dmg)
        # Regen small mana after basic attack only
        if not use_skill:
            p_comb.mana = min(p_comb.max_mana, p_comb.mana + 10)
        crit_txt = " 💥 <b>CRITICAL!</b>" if crit else ""
        sk_display = f"🌑 <b>{skill_txt}</b>!" if use_skill else "⚔️ <b>Basic Attack!</b>"
        p_action = (
            f"{sk_display}{crit_txt}\n"
            f"🗡 You deal <b>{actual:,} DMG</b> to {monster['name']}\n"
            f"   {note}"
        )

    # ── Check monster dead ──
    if not m_comb.alive():
        session["kills"] += 1
        session["total_exp"] += monster.get("drop_exp", 100)
        session["total_coins"] += monster.get("drop_coins", 50)
        if is_boss:
            session["total_exp"] = int(session["total_exp"] * 1.5)
            session["total_coins"] = int(session["total_coins"] * 2)
            session["boss_killed"] = True

        dropped = await roll_loot(monster, is_boss)
        session["loot"].extend(dropped)
        # Small HP heal between fights
        p_comb.hp = min(p_comb.max_hp, p_comb.hp + int(p_comb.max_hp * 0.10))

        session["current_idx"] += 1
        if session["current_idx"] >= len(monsters):
            return await finish_dungeon(user_id, True, p_action + f"\n✅ <b>{monster['name']}</b> defeated!")
        else:
            session["m_comb"] = None  # Reset for next monster
            next_monster = monsters[session["current_idx"]]
            text, img = build_battle_text(session, p_action + f"\n✅ <b>{monster['name']}</b> defeated! ➡️ Next enemy!")
            return {"done": False, "text": text, "image": img, "session": session}

    # ── Monster counter-attacks ──
    m_use_skill = m_comb.mana >= 30 and random.random() < 0.35
    m_dmg, m_crit, m_dodged, m_note = calc_damage(m_comb, p_comb, m_use_skill)
    if m_use_skill:
        m_comb.mana = max(0, m_comb.mana - 30)
        m_dmg = int(m_dmg * (m_comb.skill_multiplier or 1.5))
    else:
        m_comb.mana = min(m_comb.max_mana, m_comb.mana + 10)

    m_action = ""
    if m_dodged:
        m_action = f"💨 You evaded <b>{monster['name']}</b>'s attack!"
    else:
        m_actual = p_comb.take_damage(m_dmg)
        m_crit_txt = " 💥 <b>CRITICAL!</b>" if m_crit else ""
        m_sk = f"💀 <b>{m_comb.skill_name}</b>!" if m_use_skill else "🗡 <b>Monster Attacks!</b>"
        m_action = (
            f"{m_sk}{m_crit_txt}\n"
            f"☠️ {monster['name']} deals <b>{m_actual:,} DMG</b> to you"
        )

    if not p_comb.alive():
        return await finish_dungeon(user_id, False, p_action + "\n\n" + m_action)

    full_action = p_action + "\n\n" + m_action
    text, img = build_battle_text(session, full_action)
    return {"done": False, "text": text, "image": img, "session": session}


async def finish_dungeon(user_id: int, victory: bool, last_action: str = "") -> dict:
    session = DUNGEON_SESSIONS.pop(user_id, {})
    if not session:
        return {"done": True, "message": "Session expired."}

    player = session["player"]
    total_exp    = session["total_exp"]   if victory else int(session["total_exp"]   * 0.25)
    total_coins  = session["total_coins"] if victory else int(session["total_coins"] * 0.25)
    kills        = session["kills"]
    loot         = session["loot"]
    boss_killed  = session["boss_killed"]

    updates = {
        "coins":            player["coins"] + total_coins,
        "total_damage":     player.get("total_damage", 0) + session["p_comb"].max_hp,
        "monsters_killed":  player.get("monsters_killed", 0) + kills,
    }
    if victory:    updates["dungeon_clears"] = player.get("dungeon_clears", 0) + 1
    if boss_killed: updates["boss_kills"]   = player.get("boss_kills", 0) + 1

    await update_player(user_id, updates)
    for item in loot:
        await add_to_inventory(user_id, item["type"], item["id"], item["name"], item.get("qty", 1))

    level_result = await add_exp(user_id, player, total_exp)

    if kills > 0:   await update_quest_progress(user_id, "defeat_monsters", kills)
    if victory:     await update_quest_progress(user_id, "clear_dungeons", 1)

    result_text = (
        f"{last_action}\n\n"
        f"╔══════════════════════╗\n"
        f"  {'🏆 DUNGEON CLEARED!' if victory else '💀 DUNGEON FAILED'}\n"
        f"╚══════════════════════╝\n\n"
        f"{'✅ Victory!' if victory else '❌ Defeated...'}\n"
        f"⚔️ Monsters slain: <b>{kills}</b>\n"
    )
    if boss_killed:
        result_text += "👹 Boss: ✅ <b>Defeated!</b>\n"
    result_text += f"\n💰 Coins: <b>+{total_coins:,}</b>\n✨ EXP: <b>+{total_exp:,}</b>\n"
    if loot:
        result_text += "\n🎁 <b>Drops:</b>\n"
        for item in loot:
            qty = item.get("qty", 1)
            result_text += f"  • {item['name']}" + (f" ×{qty}" if qty > 1 else "") + "\n"
    if level_result.get("leveled_up"):
        result_text += f"\n🎉 <b>LEVEL UP!</b> → Lv.<b>{level_result['new_level']}</b>  +5 Stat Points!\n"
    if level_result.get("rank_up"):
        result_text += f"🔱 <b>RANK UP!</b> → <b>{level_result['rank_up']}-Rank!</b>\n"

    return {"done": True, "victory": victory, "message": result_text}

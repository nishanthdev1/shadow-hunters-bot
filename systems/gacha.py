import random
import database.db as db
from database.player_crud import add_to_inventory, update_player
import config


def roll_rarity(rates: dict, pity: int, pity_max: int, pity_rank: str = "S") -> str:
    if pity >= pity_max: return pity_rank
    roll = random.uniform(0, 100)
    cum = 0.0
    for rank, chance in rates.items():
        cum += chance
        if roll <= cum: return rank
    return list(rates.keys())[-1]


async def do_hunter_summon(player: dict, count: int = 1) -> dict:
    if player["tickets"] < count:
        return {"success": False, "message": f"❌ Need **{count}** 🎫 tickets! You have **{player['tickets']}**"}

    await update_player(player["user_id"], {"tickets": player["tickets"] - count})
    results = []
    pity = player.get("hunter_pity", 0)
    RANK_ORDER = ["C", "B", "A", "S", "SS", "National"]
    highest = "C"

    for _ in range(count):
        rarity = roll_rarity(config.HUNTER_RATES, pity, config.HUNTER_PITY, "S")
        h_list = await db.hunters().find({"rank": rarity}).to_list(length=50)
        if not h_list:
            h_list = await db.hunters().find().to_list(length=50)

        if not h_list:
            results.append({"rarity": rarity, "hunter": None})
            pity += 1
            continue

        hunter = random.choice(h_list)
        await add_to_inventory(player["user_id"], "hunter", str(hunter["_id"]), hunter["name"])

        if RANK_ORDER.index(rarity) > RANK_ORDER.index(highest):
            highest = rarity
        pity = 0 if rarity in ("S", "SS", "National") else pity + 1
        results.append({"rarity": rarity, "hunter": hunter})

    await update_player(player["user_id"], {"hunter_pity": pity})
    return {"success": True, "results": results, "highest": highest, "count": count}


async def do_weapon_summon(player: dict, count: int = 1) -> dict:
    cost = 300 * count
    if player["coins"] < cost:
        return {"success": False, "message": f"❌ Need **{cost:,}** 💰 coins! You have **{player['coins']:,}**"}

    await update_player(player["user_id"], {"coins": player["coins"] - cost})
    results = []
    pity = player.get("weapon_pity", 0)
    RANK_ORDER = ["C", "B", "A", "S", "SS", "SSR", "Mythic"]
    highest = "C"

    for _ in range(count):
        rarity = roll_rarity(config.WEAPON_RATES, pity, config.WEAPON_PITY, "S")
        w_list = await db.weapons().find({"rank": rarity}).to_list(length=50)
        if not w_list:
            w_list = await db.weapons().find().to_list(length=50)

        if not w_list:
            results.append({"rarity": rarity, "weapon": None})
            pity += 1
            continue

        weapon = random.choice(w_list)
        await add_to_inventory(player["user_id"], "weapon", str(weapon["_id"]), weapon["name"])

        if RANK_ORDER.index(rarity) > RANK_ORDER.index(highest):
            highest = rarity
        pity = 0 if rarity in ("S", "SS", "SSR", "Mythic") else pity + 1
        results.append({"rarity": rarity, "weapon": weapon})

    await update_player(player["user_id"], {"weapon_pity": pity})
    return {"success": True, "results": results, "highest": highest, "count": count}


def format_hunter_result(result: dict) -> str:
    if not result["success"]: return result["message"]
    STYLES = {
        "C": ("⬜", "C-Class"), "B": ("🟦", "B-Class"),
        "A": ("🟣", "A-Class"), "S": ("🌟", "★ S-Class ★"),
        "SS": ("💫", "✦✦ SS-Class ✦✦"), "National": ("🔱", "♦ NATIONAL ♦"),
    }
    highest = result["highest"]
    if highest in ("SS", "National"): header = "🔥✨ **RARE PULL!** ✨🔥\n" + "═"*26 + "\n\n"
    elif highest == "S": header = "⭐ **S-CLASS PULL!** ⭐\n" + "═"*26 + "\n\n"
    else: header = "🎰 **HUNTER ROYALE** 🎰\n" + "═"*26 + "\n\n"

    lines = [header]
    for r in result["results"]:
        icon, label = STYLES.get(r["rarity"], ("⬜", r["rarity"]))
        h = r.get("hunter")
        if h:
            elem = config.ELEMENT_EMOJIS.get(h.get("element","None"), "⚪")
            cls = config.CLASS_EMOJIS.get(h.get("hunter_class","Fighter"), "⚔️")
            lines.append(f"{icon} **[{label}]** {cls} **{h['name']}**\n   {elem} {h.get('element','?')} | CP: **{h.get('combat_power',0):,}**")
        else:
            lines.append(f"{icon} **[{label}]** — No hunters added yet!")

    lines.append(f"\n{'═'*26}\n📦 Added to inventory!")
    return "\n".join(lines)


def format_weapon_result(result: dict) -> str:
    if not result["success"]: return result["message"]
    STYLES = {
        "C": ("🔵", "C-Rank"), "B": ("🟢", "B-Rank"), "A": ("🟣", "A-Rank"),
        "S": ("🌟", "★ S-Rank ★"), "SS": ("💫", "✦ SS-Rank ✦"),
        "SSR": ("🔶", "✦✦ SSR ✦✦"), "Mythic": ("🔱", "⚡ MYTHIC ⚡"),
    }
    highest = result["highest"]
    if highest in ("Mythic", "SSR"): header = "⚡🔱 **MYTHIC PULL!** 🔱⚡\n" + "═"*26 + "\n\n"
    elif highest == "SS": header = "💫 **SS-RANK!** 💫\n" + "═"*26 + "\n\n"
    else: header = "⚔️ **WEAPON ROYALE** ⚔️\n" + "═"*26 + "\n\n"

    lines = [header]
    for r in result["results"]:
        icon, label = STYLES.get(r["rarity"], ("⚪", r["rarity"]))
        w = r.get("weapon")
        if w:
            elem = config.ELEMENT_EMOJIS.get(w.get("element","None"), "⚪")
            lines.append(f"{icon} **[{label}]** **{w['name']}**\n   {elem} DMG: **{w.get('damage',0):,}** | Crit: **{w.get('crit_rate',0.1)*100:.0f}%**")
        else:
            lines.append(f"{icon} **[{label}]** — No weapons added yet!")

    lines.append(f"\n{'═'*26}\n📦 Added to inventory!")
    return "\n".join(lines)

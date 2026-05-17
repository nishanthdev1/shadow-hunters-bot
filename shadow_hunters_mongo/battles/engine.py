"""
Core Battle Engine — PvE and PvP combat.
"""

import random
from dataclasses import dataclass, field
import config


@dataclass
class Combatant:
    name: str
    hp: int
    max_hp: int
    attack: int
    defense: int
    speed: int
    element: str = "None"
    crit_chance: float = 0.10
    dodge_chance: float = 0.05
    skill_name: str = "Basic Attack"
    skill_multiplier: float = 1.5
    mana: int = 100
    max_mana: int = 100

    def alive(self): return self.hp > 0

    def take_damage(self, dmg: int) -> int:
        actual = max(1, dmg - self.defense)
        self.hp = max(0, self.hp - actual)
        return actual

    def hp_bar(self) -> str:
        ratio = self.hp / self.max_hp
        filled = int(ratio * 10)
        bar = "█" * filled + "░" * (10 - filled)
        color = "🟩" if ratio > 0.6 else "🟨" if ratio > 0.3 else "🟥"
        return f"{color}[{bar}]"


@dataclass
class BattleResult:
    victory: bool
    winner: str
    loser: str
    rounds: int
    log: list
    player_damage: int
    enemy_damage: int


def elem_bonus(atk_elem: str, def_elem: str) -> float:
    adv = config.ELEMENT_ADVANTAGES.get(atk_elem)
    if adv == def_elem: return 1.35
    dis = config.ELEMENT_ADVANTAGES.get(def_elem)
    if dis == atk_elem: return 0.75
    return 1.0


def calc_damage(attacker: Combatant, defender: Combatant, skill: bool = False):
    if random.random() < defender.dodge_chance:
        return 0, False, True, ""

    base = attacker.attack * (attacker.skill_multiplier if skill else 1.0)
    elem = elem_bonus(attacker.element, defender.element)
    base *= elem
    crit = random.random() < attacker.crit_chance
    if crit: base *= config.CRIT_MULTIPLIER
    base *= random.uniform(0.9, 1.1)

    note = "⚡ Element Advantage! " if elem > 1 else ("🛡️ Resisted. " if elem < 1 else "")
    return int(base), crit, False, note


def run_pve(player: Combatant, monster: Combatant) -> BattleResult:
    log = []
    rounds = 0
    p_dmg = 0
    m_dmg = 0

    e1 = config.ELEMENT_EMOJIS.get(player.element, "⚪")
    e2 = config.ELEMENT_EMOJIS.get(monster.element, "⚪")
    log.append(f"⚔️ **{player.name}** {e1} VS **{monster.name}** {e2}\n{'━'*26}")

    p_first = player.speed >= monster.speed

    while player.alive() and monster.alive() and rounds < 20:
        rounds += 1
        log.append(f"\n🔄 **Round {rounds}**")

        order = [(player, monster), (monster, player)] if p_first else [(monster, player), (player, monster)]

        for (atk, dfn) in order:
            if not atk.alive() or not dfn.alive(): break
            use_skill = atk.mana >= 30 and random.random() < 0.30
            dmg, crit, dodged, note = calc_damage(atk, dfn, use_skill)

            if dodged:
                log.append(f"  {atk.name} attacks → 💨 **EVADED!**")
                continue

            if use_skill: atk.mana -= 30
            actual = dfn.take_damage(dmg)

            if atk == player: p_dmg += actual
            else: m_dmg += actual

            skill_txt = f"💠 **{atk.skill_name}**! " if use_skill else ""
            crit_txt = "🔥 **CRITICAL!** " if crit else ""
            log.append(
                f"  {skill_txt}{note}{crit_txt}\n"
                f"  {atk.name} ⚔️ **{actual:,}** dmg\n"
                f"  {dfn.name} HP: {dfn.hp_bar()} **{max(0,dfn.hp):,}/{dfn.max_hp:,}**"
            )
            atk.mana = min(atk.max_mana, atk.mana + 15)

        if not monster.alive() or not player.alive(): break

    victory = player.alive() and not monster.alive()
    if not victory and player.alive():
        victory = (player.hp / player.max_hp) > (monster.hp / monster.max_hp)

    log.append(f"\n{'═'*26}")
    if victory:
        log.append(f"🏆 **VICTORY!** {player.name} wins!")
    else:
        log.append(f"💀 **DEFEATED!** {player.name} has fallen...")

    return BattleResult(victory, player.name if victory else monster.name,
                        monster.name if victory else player.name, rounds, log, p_dmg, m_dmg)


def run_pvp(atk: Combatant, dfn: Combatant) -> BattleResult:
    log = []
    rounds = 0
    a_dmg = 0
    d_dmg = 0

    e1 = config.ELEMENT_EMOJIS.get(atk.element, "⚪")
    e2 = config.ELEMENT_EMOJIS.get(dfn.element, "⚪")
    log.append(f"🥊 **PvP BATTLE**\n{e1} **{atk.name}** VS {e2} **{dfn.name}**\n{'━'*26}")

    first = atk if atk.speed >= dfn.speed else dfn
    second = dfn if first == atk else atk

    while atk.alive() and dfn.alive() and rounds < 15:
        rounds += 1
        log.append(f"\n🔄 **Round {rounds}**")

        for (a, d) in [(first, second), (second, first)]:
            if not a.alive() or not d.alive(): break
            use_skill = a.mana >= 30 and random.random() < 0.35
            dmg, crit, dodged, note = calc_damage(a, d, use_skill)

            if dodged:
                log.append(f"  {a.name} → 💨 **EVADED!**")
                continue

            if use_skill: a.mana -= 30
            actual = d.take_damage(dmg)
            if a == atk: a_dmg += actual
            else: d_dmg += actual

            skill_txt = f"💠 **{a.skill_name}**! " if use_skill else ""
            crit_txt = "🔥 **CRIT!** " if crit else ""
            log.append(
                f"  {skill_txt}{note}{crit_txt}\n"
                f"  {a.name} ⚔️ **{actual:,}** → {d.name}\n"
                f"  {d.name} HP: {d.hp_bar()} **{max(0,d.hp):,}/{d.max_hp:,}**"
            )
            a.mana = min(a.max_mana, a.mana + 20)

    atk_won = atk.alive() and not dfn.alive()
    if atk.alive() and dfn.alive():
        atk_won = (atk.hp / atk.max_hp) >= (dfn.hp / dfn.max_hp)
    elif not atk.alive():
        atk_won = False

    winner = atk if atk_won else dfn
    loser = dfn if atk_won else atk
    log.append(f"\n{'═'*26}\n🏆 **{winner.name}** wins the duel!")

    return BattleResult(atk_won, winner.name, loser.name, rounds, log, a_dmg, d_dmg)


def player_to_combatant(p: dict, weapon: dict = None, team: list = None) -> Combatant:
    attack = p["strength"] * 15 + p["precision"] * 5 + p["level"] * 10
    element = "None"
    crit_bonus = 0

    if weapon:
        attack += weapon.get("damage", 0)
        element = weapon.get("element", "None")
        crit_bonus = weapon.get("crit_rate", 0)

    if team:
        attack += sum(h.get("attack", 0) for h in team) // max(1, len(team)) // 4
        if element == "None" and team:
            element = team[0].get("element", "None")

    skill_name = "Shadow Strike"
    skill_mult = 2.0
    if team:
        best = max(team, key=lambda h: h.get("combat_power", 0))
        skill_name = best.get("skill_name", "Shadow Strike")
        skill_mult = best.get("skill_multiplier", 2.0)

    return Combatant(
        name=p["hunter_name"],
        hp=p["max_hp"], max_hp=p["max_hp"],
        attack=attack,
        defense=p["endurance"] * 8 + p["vitality"] * 5,
        speed=p["agility"] * 10 + p["level"] * 2,
        element=element,
        crit_chance=config.BASE_CRIT_CHANCE + p["luck"] * 0.005 + crit_bonus,
        dodge_chance=config.BASE_DODGE_CHANCE + p["agility"] * 0.003,
        skill_name=skill_name,
        skill_multiplier=skill_mult,
        mana=p["max_mana"], max_mana=p["max_mana"],
    )


def monster_to_combatant(m: dict) -> Combatant:
    skills = m.get("skills", [])
    skill_name = skills[0]["name"] if skills else "Monster Assault"
    skill_mult = skills[0].get("multiplier", 1.8) if skills else 1.8

    return Combatant(
        name=m["name"],
        hp=m["hp"], max_hp=m["hp"],
        attack=m["attack"],
        defense=m["defense"],
        speed=m["speed"],
        element=m.get("element", "None"),
        crit_chance=0.08, dodge_chance=0.04,
        skill_name=skill_name, skill_multiplier=skill_mult,
        mana=200, max_mana=200,
    )

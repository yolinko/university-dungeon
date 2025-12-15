import json
import random
import os
from i18n import i18n


class Buff:
    def __init__(self, data):
        self.id = data["id"]
        # i18n 적용
        self.name = i18n.get(f"buffs.{self.id}.name")
        if self.name == f"buffs.{self.id}.name":  # 번역이 없으면 기본값 사용
            self.name = data["name"]

        self.description = i18n.get(f"buffs.{self.id}.desc")
        if self.description == f"buffs.{self.id}.desc":
            self.description = data["description"]

        self.effect_type = data["effect_type"]
        self.data = data


class BuffManager:
    def __init__(self, data_path="data/buffs.json"):
        self.buffs = []
        self.load_buffs(data_path)

    def load_buffs(self, path):
        if not os.path.exists(path):
            print(f"Buffs file not found: {path}")
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    self.buffs.append(Buff(item))
            print(f"Loaded {len(self.buffs)} buffs.")
        except Exception as e:
            print(f"Error loading buffs: {e}")

    def get_random_buffs(self, amount=3):
        if len(self.buffs) < amount:
            return self.buffs
        return random.sample(self.buffs, amount)

    def apply_buff(self, player, buff):
        print(f"Applying buff: {buff.name}")

        if buff.effect_type == "stat":
            stat = buff.data.get("stat")
            value = buff.data.get("value")
            if stat and value is not None:
                if stat in player.stats:
                    player.stats[stat] += value
                elif stat == "max_hp":
                    player.stats["max_hp"] += value
                    player.hp += value  # 증가된 양만큼 회복
                elif stat == "dash_cooldown":
                    player.stats["dash_cooldown"] = max(
                        0.1, player.stats["dash_cooldown"] + value
                    )

                # 특수 버프에 대한 보조 능력치 처리
                if "stat2" in buff.data:
                    stat2 = buff.data.get("stat2")
                    value2 = buff.data.get("value2")
                    if stat2 == "max_hp":
                        player.stats["max_hp"] += value2
                        player.hp += value2

        elif buff.effect_type == "heal":
            heal_amount = buff.data.get("value", 0)
            player.hp = min(player.stats["max_hp"], player.hp + heal_amount)

        elif buff.effect_type == "gold":
            amount = buff.data.get("value", 0)
            player.gold += amount

        elif buff.effect_type == "relic":
            relic_id = buff.data.get("relic_id")
            if not hasattr(player, "passive_relics"):
                player.passive_relics = []
            player.passive_relics.append(relic_id)

        elif buff.effect_type == "special":
            stat = buff.data.get("stat")
            value = buff.data.get("value")
            penalty_stat = buff.data.get("penalty_stat")
            penalty_value = buff.data.get("penalty_value")

            if stat in player.stats:
                player.stats[stat] += value
            if penalty_stat in player.stats:
                player.stats[penalty_stat] += penalty_value

        elif buff.effect_type == "random":
            # 무작위 능력치 상승
            stats = ["damage", "speed", "max_hp"]
            s = random.choice(stats)
            if s == "damage":
                player.stats["damage"] += 5
            elif s == "speed":
                player.stats["speed"] += 20
            elif s == "max_hp":
                player.stats["max_hp"] += 20
                player.hp += 20

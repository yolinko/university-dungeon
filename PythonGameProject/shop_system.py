import random
from i18n import i18n


class ShopItem:
    def __init__(self, item_id, price, effect_type, data):
        self.id = item_id
        self.price = price
        self.effect_type = effect_type
        self.data = data

        # i18n 지원
        self.name = i18n.get(f"shop.{self.id}.name")
        if self.name == f"shop.{self.id}.name":
            self.name = data.get("name", "Unknown Item")

        self.description = i18n.get(f"shop.{self.id}.desc")
        if self.description == f"shop.{self.id}.desc":
            self.description = data.get("description", "No description.")


class ShopManager:
    def __init__(self):
        self.items = []
        self.init_default_items()

    def init_default_items(self):
        self.items = [
            ShopItem(
                "health_potion",
                50,
                "heal",
                {
                    "value": 30,
                    "name": "Health Potion",
                    "description": "Restores 30 HP.",
                },
            ),
            ShopItem(
                "damage_up",
                100,
                "stat",
                {
                    "stat": "damage",
                    "value": 2,
                    "name": "Damage Up",
                    "description": "Increases damage by 2.",
                },
            ),
            ShopItem(
                "speed_up",
                80,
                "stat",
                {
                    "stat": "speed",
                    "value": 10,
                    "name": "Speed Up",
                    "description": "Increases movement speed by 10.",
                },
            ),
            ShopItem(
                "max_hp_up",
                120,
                "stat",
                {
                    "stat": "max_hp",
                    "value": 20,
                    "name": "Max HP Up",
                    "description": "Increases Max HP by 20.",
                },
            ),
            ShopItem(
                "full_heal",
                150,
                "heal_full",
                {"name": "Full Restore", "description": "Fully restores HP."},
            ),
        ]

    def get_shop_items(self, level, count=3):
        return random.sample(self.items, min(count, len(self.items)))

    def buy_item(self, player, item):
        if player.gold >= item.price:
            player.gold -= item.price
            self.apply_item_effect(player, item)
            return True
        return False

    def apply_item_effect(self, player, item):
        if item.effect_type == "heal":
            heal_amount = item.data.get("value", 0)
            player.hp = min(player.stats["max_hp"], player.hp + heal_amount)
        elif item.effect_type == "heal_full":
            player.hp = player.stats["max_hp"]
        elif item.effect_type == "stat":
            stat = item.data.get("stat")
            value = item.data.get("value")
            if stat in player.stats:
                player.stats[stat] += value
                if stat == "max_hp":
                    player.hp += value  # 최대 체력 증가

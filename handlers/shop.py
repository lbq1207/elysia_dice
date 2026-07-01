"""
商店系统业务逻辑
"""

import random
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime

logger = logging.getLogger("elysia_dice.shop")

# 全局分群开关：True=按群隔离数据, False=全局共享数据
SEPARATE_BY_GROUP = True

# 商品定义：{全称: (价格, 描述, [简称列表])}
ITEMS_DB: Dict[str, tuple] = {
    "蒸蛋": (6, "滑滑嫩嫩的蒸蛋", ["蒸蛋"]),
    "薯条": (12, "该去码头整点薯条了", ["薯条"]),
    "培根": (16, "香煎培根，肉香四溢", ["培根"]),
    "早餐面包": (20, "软糯的早餐面包", ["面包"]),
    "冰镇西瓜": (24, "解渴的冰镇西瓜", ["西瓜"]),
    "草莓蛋糕": (28, "爱莉最喜欢的蛋糕之一", ["蛋糕"]),
    "速冻饺子": (36, "爱莉在黄金庭院的回忆", ["饺子"]),
    "芋泥奶茶": (39, "美好相遇，为你都可", ["奶茶"]),
}

# 构建快速查找索引：简称 -> (全称, 价格)
ITEM_ALIASES: Dict[str, Tuple[str, int]] = {}
for full_name, (price, desc, aliases) in ITEMS_DB.items():
    ITEM_ALIASES[full_name] = (full_name, price)
    for alias in aliases:
        ITEM_ALIASES[alias] = (full_name, price)

# 抽奖奖池定义
LOTTERY_POOL = [
    (31, "currency", (3, 16), "花花"),
    (20, "currency", (17, 30), "花花"),
    (5, "currency", (31, 50), "花花"),
    (10, "item", "蒸蛋", "蒸蛋"),
    (10, "item", "薯条", "薯条"),
    (10, "item", "培根", "培根"),
    (4, "item", "早餐面包", "面包"),
    (4, "item", "冰镇西瓜", "西瓜"),
    (2, "item", "草莓蛋糕", "蛋糕"),
    (2, "item", "速冻饺子", "饺子"),
    (2, "item", "芋泥奶茶", "奶茶"),
]

LOTTERY_FREE = 0
LOTTERY_HALF = 8
LOTTERY_FULL = 16


def _make_key(user_id: str, group_id: str = "") -> str:
    """生成存储key"""
    if SEPARATE_BY_GROUP and group_id:
        return f"{group_id}:{user_id}"
    return user_id


class ShopManager:
    """商店管理器"""

    def __init__(self):
        self.daily_lottery_count: Dict[str, int] = {}  # key -> 今日抽奖次数
        self.user_inventory: Dict[str, Dict[str, int]] = {}  # key -> {item_name: count}
        self.last_reset_date = datetime.now().date()

    def reset_daily(self):
        """重置每日数据"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            self.daily_lottery_count.clear()
            self.last_reset_date = today
            logger.info("已重置每日抽奖数据")

    # ========== 公共API（全部带 group_id） ==========

    def get_shop_list(self) -> str:
        """获取商店商品列表"""
        shop_text = "🏪 爱莉喵商店\n━━━━━━━━━━━━\n📦 商品列表：\n\n"
        for i, (name, (price, desc, aliases)) in enumerate(ITEMS_DB.items(), 1):
            shop_text += f"{i}. {name}\n   💰 价格: {price} 花花\n   📝 {desc}\n"
            if len(aliases) > 1 or aliases[0] != name:
                shop_text += f"   🔍 简称: {'、'.join(aliases)}\n"
            shop_text += "\n"
        shop_text += "━━━━━━━━━━━━\n💡 指令说明：\n"
        shop_text += "   /购买 <物品> - 购买1件\n   /购买 <物品> n - 购买n件\n"
        shop_text += "   /抽奖 - 抽奖试试手气\n   /背包 - 查看背包\n"
        shop_text += "   <物品> 可使用全称或简称"
        return shop_text

    def find_item(self, query: str) -> Optional[Tuple[str, int]]:
        """查找物品"""
        if query in ITEM_ALIASES:
            return ITEM_ALIASES[query]
        query_lower = query.lower()
        for key, value in ITEM_ALIASES.items():
            if query_lower in key.lower() or key.lower() in query_lower:
                return value
        return None

    def purchase_item(self, item_name: str, quantity: int, user_id: str,
                      user_currency: int, group_id: str = "") -> Tuple[bool, str, int]:
        """购买物品"""
        result = self.find_item(item_name)
        if not result:
            suggestions = [key for key in ITEM_ALIASES if item_name.lower() in key.lower()]
            error_msg = f"❌ 未找到物品「{item_name}」"
            if suggestions:
                error_msg += f"\n💡 你可能想找: {'、'.join(suggestions[:3])}"
            error_msg += "\n请使用 /商店 查看商品列表"
            return False, error_msg, 0

        full_name, unit_price = result
        total_cost = unit_price * quantity

        if user_currency < total_cost:
            return False, (
                f"❌ 花花不足！\n━━━━━━━━━━━━\n"
                f"🛒 购买物品: {full_name} x{quantity}\n"
                f"💰 需要: {total_cost} 花花\n💳 余额: {user_currency} 花花\n"
                f"❌ 差额: {total_cost - user_currency} 花花\n\n"
                f"💡 发送 /签到 获取更多花花"
            ), total_cost

        key = _make_key(user_id, group_id)
        if key not in self.user_inventory:
            self.user_inventory[key] = {}
        self.user_inventory[key][full_name] = self.user_inventory[key].get(full_name, 0) + quantity

        return True, (
            f"✅ 购买成功！\n━━━━━━━━━━━━\n"
            f"🛒 物品: {full_name} x{quantity}\n💰 花费: {total_cost} 花花\n"
            f"💳 剩余花花: {user_currency - total_cost}\n\n"
            f"📦 背包中该物品: {self.user_inventory[key][full_name]}个"
        ), total_cost

    def get_lottery_cost(self, user_id: str, group_id: str = "") -> Tuple[int, str]:
        """获取抽奖费用"""
        self.reset_daily()
        key = _make_key(user_id, group_id)
        count = self.daily_lottery_count.get(key, 0)
        if count == 0:
            return LOTTERY_FREE, "🎉 今日首次抽奖免费！"
        elif count == 1:
            return LOTTERY_HALF, "💎 第二次抽奖半价 (8花花)"
        else:
            return LOTTERY_FULL, f"🎰 第{count+1}次抽奖，费用: {LOTTERY_FULL}花花"

    def do_lottery(self, user_id: str, user_currency: int,
                   group_id: str = "") -> Tuple[bool, str, int, Optional[str], int]:
        """执行抽奖"""
        self.reset_daily()
        key = _make_key(user_id, group_id)
        cost, cost_msg = self.get_lottery_cost(user_id, group_id)

        if user_currency < cost:
            return False, (
                f"❌ 花花不足，无法抽奖\n━━━━━━━━━━━━\n"
                f"💰 需要: {cost} 花花\n💳 余额: {user_currency} 花花\n\n"
                f"💡 发送 /签到 获取更多花花"
            ), 0, None, 0

        total_weight = sum(w for w, _, _, _ in LOTTERY_POOL)
        rand = random.uniform(0, total_weight)
        cumulative = 0
        selected = None
        for weight, prize_type, prize_value, prize_desc in LOTTERY_POOL:
            cumulative += weight
            if rand <= cumulative:
                selected = (prize_type, prize_value, prize_desc)
                break

        if not selected:
            return False, "🎰 抽奖系统故障，请稍后再试", 0, None, 0

        prize_type, prize_value, prize_desc = selected
        item_award = None
        currency_award = 0

        if prize_type == "currency":
            min_val, max_val = prize_value
            currency_award = random.randint(min_val, max_val)
            result_text = f"🌟 恭喜获得 {currency_award} 花花！"
        else:
            item_award = prize_value
            if key not in self.user_inventory:
                self.user_inventory[key] = {}
            self.user_inventory[key][item_award] = self.user_inventory[key].get(item_award, 0) + 1
            result_text = f"🎁 恭喜获得物品: {item_award}！"

        self.daily_lottery_count[key] = self.daily_lottery_count.get(key, 0) + 1
        new_balance = user_currency - cost + currency_award

        full_msg = (
            f"🎰 抽奖结果\n━━━━━━━━━━━━\n{cost_msg}\n{result_text}\n"
            f"━━━━━━━━━━━━\n💰 抽奖花费: {cost} 花花\n💳 当前余额: {new_balance} 花花"
        )
        if item_award:
            full_msg += f"\n📦 背包中该物品: {self.user_inventory[key][item_award]}个"

        return True, full_msg, cost, item_award, currency_award

    def get_inventory(self, user_id: str, group_id: str = "") -> str:
        """查看背包"""
        key = _make_key(user_id, group_id)
        if key not in self.user_inventory or not self.user_inventory[key]:
            return (
                "📦 你的背包空空如也\n━━━━━━━━━━━━\n"
                "💡 使用 /商店 查看商品\n💡 使用 /抽奖 试试手气"
            )
        inventory_text = "📦 背包物品\n━━━━━━━━━━━━\n"
        total_items = 0
        for item_name, count in self.user_inventory[key].items():
            if count > 0:
                price = ITEMS_DB[item_name][0]
                total_value = price * count
                inventory_text += f"🔸 {item_name} x{count} (价值{total_value}花花)\n"
                total_items += count
        if total_items == 0:
            inventory_text += "空空如也...\n"
        else:
            inventory_text += f"━━━━━━━━━━━━\n📊 共 {len(self.user_inventory[key])} 种物品，总计 {total_items} 个"
        return inventory_text

    def add_item_to_inventory(self, user_id: str, item_name: str,
                              quantity: int = 1, group_id: str = "") -> bool:
        """直接添加物品到背包（开发者功能）"""
        result = self.find_item(item_name)
        if not result:
            return False
        full_name, _ = result
        key = _make_key(user_id, group_id)
        if key not in self.user_inventory:
            self.user_inventory[key] = {}
        self.user_inventory[key][full_name] = self.user_inventory[key].get(full_name, 0) + quantity
        return True

    def remove_item_from_inventory(self, user_id: str, item_name: str,
                                   quantity: int = 1, group_id: str = "") -> bool:
        """从背包移除物品"""
        result = self.find_item(item_name)
        if not result:
            return False
        full_name, _ = result
        key = _make_key(user_id, group_id)
        if key not in self.user_inventory:
            return False
        current = self.user_inventory[key].get(full_name, 0)
        if current < quantity:
            return False
        self.user_inventory[key][full_name] = current - quantity
        if self.user_inventory[key][full_name] <= 0:
            del self.user_inventory[key][full_name]
        return True

    def get_inventory_item_count(self, user_id: str, item_name: str,
                                 group_id: str = "") -> int:
        """获取背包中某物品数量"""
        result = self.find_item(item_name)
        if not result:
            return 0
        full_name, _ = result
        key = _make_key(user_id, group_id)
        return self.user_inventory.get(key, {}).get(full_name, 0)

    # ========== 管理员reset ==========

    def reset_user_lottery(self, user_id: str, group_id: str = "") -> bool:
        """重置指定用户的今日抽奖次数"""
        key = _make_key(user_id, group_id)
        if key in self.daily_lottery_count:
            del self.daily_lottery_count[key]
        logger.info(f"已重置用户 {user_id} 的抽奖状态")
        return True

    def reset_all_lottery(self, group_id: str = "") -> int:
        """重置所有用户的今日抽奖次数"""
        count = 0
        if SEPARATE_BY_GROUP and group_id:
            prefix = f"{group_id}:"
            keys_to_del = [k for k in self.daily_lottery_count if k.startswith(prefix)]
            count = len(keys_to_del)
            for k in keys_to_del:
                del self.daily_lottery_count[k]
        else:
            count = len(self.daily_lottery_count)
            self.daily_lottery_count.clear()
        logger.info(f"已重置 {count} 个用户的抽奖状态")
        return count


# 全局商店管理器实例
shop_manager = ShopManager()
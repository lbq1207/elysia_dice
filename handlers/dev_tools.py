"""
开发者工具处理逻辑
"""
from typing import Optional
from pathlib import Path
import json

from src.app.plugin_system.api.log_api import get_logger

logger = get_logger("elysia_dice.dev_tools")

# 全局分群开关：True=按群隔离数据, False=全局共享数据
SEPARATE_BY_GROUP = True

# 开发者QQ号列表 （拿到插件以后改成你的QQ号）
DEVELOPER_IDS = ["123456789"]


def _make_key(user_id: str, group_id: str = "") -> str:
    """生成存储key
    如果 SEPARATE_BY_GROUP=True 且有 group_id，返回 "group_id:user_id"
    否则返回 user_id
    """
    if SEPARATE_BY_GROUP and group_id:
        return f"{group_id}:{user_id}"
    return user_id


class CurrencyManager:
    """花花货币管理器"""

    def __init__(self):
        self.data_dir = Path("data/elysia_dice")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.currency_file = self.data_dir / "currency.json"
        self.currency_data = self._load_data()

    def _load_data(self) -> dict:
        try:
            if self.currency_file.exists():
                with open(self.currency_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载货币数据失败: {e}")
        return {}

    def _save_data(self) -> bool:
        try:
            with open(self.currency_file, 'w', encoding='utf-8') as f:
                json.dump(self.currency_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存货币数据失败: {e}")
            return False

    def get_currency(self, user_id: str, group_id: str = "") -> int:
        key = _make_key(user_id, group_id)
        if key not in self.currency_data:
            return 0
        return self.currency_data[key].get("flowers", 0)

    def set_currency(self, user_id: str, amount: int, group_id: str = "") -> bool:
        key = _make_key(user_id, group_id)
        if key not in self.currency_data:
            self.currency_data[key] = {}

        old_amount = self.currency_data[key].get("flowers", 0)
        self.currency_data[key]["flowers"] = max(0, amount)

        if self._save_data():
            scope = f"群{group_id}" if (SEPARATE_BY_GROUP and group_id) else "全局"
            logger.info(f"设置用户 {user_id}({scope}) 花花: {old_amount} -> {amount}")
            return True
        return False

    def add_currency(self, user_id: str, amount: int, group_id: str = "") -> int:
        current = self.get_currency(user_id, group_id)
        new_amount = current + amount
        self.set_currency(user_id, new_amount, group_id)
        return new_amount

    def reset_user_currency(self, user_id: str, group_id: str = "") -> bool:
        return self.set_currency(user_id, 0, group_id)

    def reset_all_currency(self, group_id: str = "") -> int:
        count = 0
        if SEPARATE_BY_GROUP and group_id:
            prefix = f"{group_id}:"
            for uid in list(self.currency_data.keys()):
                if uid.startswith(prefix):
                    self.currency_data[uid]["flowers"] = 0
                    count += 1
        else:
            for uid in list(self.currency_data.keys()):
                self.currency_data[uid]["flowers"] = 0
                count += 1
        self._save_data()
        scope = f"群{group_id}" if (SEPARATE_BY_GROUP and group_id) else "全局"
        logger.info(f"已重置 {scope} {count} 个用户的花花")
        return count


currency_manager = CurrencyManager()


def is_developer(user_id: str) -> bool:
    return str(user_id) in DEVELOPER_IDS


async def handle_set_command(user_id: str, command_parts: list) -> str:
    if not is_developer(user_id):
        return "⚠️ 此命令仅限插件开发者使用\n如需帮助，请联系开发者"

    if len(command_parts) < 4:
        return (
            "❀ 开发者工具 - /set 命令格式：\n"
            "━━━━━━━━━━━━\n"
            "📝 /set currency <用户ID> <数量>\n"
            "   设置指定用户的花花数量\n\n"
            "💡 示例：\n"
            "   /set currency 123456789 100\n"
            "   将用户123456789的花花设为100\n"
            "━━━━━━━━━━━━\n"
            "⚠️ 仅限插件开发者使用"
        )

    command_type = command_parts[1].lower()

    if command_type == "currency":
        if len(command_parts) != 4:
            return "❌ 格式错误\n正确格式：/set currency <用户ID> <数量>"

        target_id = command_parts[2]
        try:
            amount = int(command_parts[3])
        except ValueError:
            return "❌ 数量必须为整数"
        if amount < 0:
            return "❌ 花花数量不能为负数"

        if currency_manager.set_currency(target_id, amount):
            return (
                f"✅ 开发者操作成功\n"
                f"━━━━━━━━━━━━\n"
                f"👤 目标用户：{target_id}\n"
                f"🌸 花花数量：{amount} 花花\n"
                f"━━━━━━━━━━━━\n"
                f"💡 已成功设置用户花花"
            )
        else:
            return "❌ 设置失败，请检查数据存储"
    else:
        return f"❌ 未知的 /set 子命令: {command_type}\n可用子命令: currency"


async def handle_get_command(user_id: str, command_parts: list) -> str:
    if not is_developer(user_id):
        return "⚠️ 此命令仅限插件开发者使用\n如需帮助，请联系开发者"

    if len(command_parts) < 3:
        return (
            "❀ 开发者工具 - /get 命令格式：\n"
            "━━━━━━━━━━━━\n"
            "📝 /get currency <用户ID>\n"
            "   查询指定用户的花花数量\n\n"
            "💡 示例：\n"
            "   /get currency 123456789\n"
            "   查询用户123456789的花花\n"
            "━━━━━━━━━━━━\n"
            "⚠️ 仅限插件开发者使用"
        )

    command_type = command_parts[1].lower()

    if command_type == "currency":
        if len(command_parts) != 3:
            return "❌ 格式错误\n正确格式：/get currency <用户ID>"
        target_id = command_parts[2]
        amount = currency_manager.get_currency(target_id)
        return (
            f"📊 用户花花查询结果\n"
            f"━━━━━━━━━━━━\n"
            f"👤 用户ID：{target_id}\n"
            f"🌸 花花数量：{amount} 花花\n"
            f"━━━━━━━━━━━━\n"
        )
    else:
        return f"❌ 未知的 /get 子命令: {command_type}\n可用子命令: currency"
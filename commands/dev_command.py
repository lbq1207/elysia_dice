"""
开发者工具命令组件
支持 /set, /get, /elyset, /elyget 命令
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.app.plugin_system.api.log_api import get_logger
from src.app.plugin_system.api.send_api import send_text
from src.app.plugin_system.base import BaseCommand, cmd_route
from src.app.plugin_system.types import PermissionLevel, ChatType
from src.app.plugin_system.api.stream_api import get_stream_info

from ..handlers.dev_tools import (
    handle_set_command,
    handle_get_command,
    currency_manager,
)
from ..handlers.shop import shop_manager, ITEM_ALIASES
from ..handlers.favor import favor_manager
from ..handlers.crystal import crystal_manager

if TYPE_CHECKING:
    from ..plugin import ElysiaDicePlugin

logger = get_logger("elysia_dice.dev_command")


# ==================== 基础处理逻辑（共享） ====================

class DevToolsMixin:
    """开发者工具公共逻辑"""

    @staticmethod
    def _parse_target_id(raw_id: str) -> str:
        """解析目标用户ID，支持多种格式"""
        import re

        # <@数字> 或 <@!数字>
        if raw_id.startswith("<@") and raw_id.endswith(">"):
            return raw_id[2:-1].lstrip("!")

        # @<昵称:数字>
        if raw_id.startswith("@<") and raw_id.endswith(">"):
            match = re.search(r'[:：](\d+)>', raw_id)
            if match:
                return match.group(1)

        # 纯数字
        if raw_id.isdigit():
            return raw_id

        return raw_id

    @staticmethod
    def _find_item(query: str):
        """查找物品，支持模糊匹配"""
        if query in ITEM_ALIASES:
            return ITEM_ALIASES[query]
        for key in ITEM_ALIASES:
            if query in key or key in query:
                return ITEM_ALIASES[key]
        return None

    @staticmethod
    def _search_items(query: str) -> list:
        """模糊搜索物品"""
        results = []
        for key in ITEM_ALIASES:
            if query.lower() in key.lower():
                results.append(key)
        return results[:5]

    @staticmethod
    def _get_help() -> str:
        """获取帮助信息"""
        return (
            "🔧 开发者工具 - 设置命令\n"
            "━━━━━━━━━━━━\n"
            "📝 可用子命令：\n\n"
            "1. currency <用户ID> <数量>\n"
            "   设置用户花花数量\n\n"
            "2. crystal <用户ID> <数量>\n"
            "   设置用户水晶数量\n\n"
            "3. favor <用户ID> <数量>\n"
            "   设置用户好感度\n\n"
            "4. item <用户ID> <物品> [数量]\n"
            "   添加物品到用户背包\n\n"
            "5. reset <类型> [用户ID]\n"
            "   重置数据\n"
            "   类型: all/sign/lottery/crystal/补给/女武神/群友\n\n"
            "6. <物品> <用户ID> [数量]\n"
            "   快捷添加物品\n\n"
            "💡 示例：\n"
            "   /set currency 123456789 100\n"
            "   /set crystal 123456789 28000\n"
            "   /set 蒸蛋 123456789 10\n"
            "   /set reset all\n"
            "   /set reset 女武神 123456789"
        )

    @staticmethod
    def _get_reset_help() -> str:
        return (
            "🔧 开发者工具 - reset 命令\n"
            "━━━━━━━━━━━━\n"
            "📝 可用格式：\n\n"
            "重置所有人：\n"
            "  /set reset all        - 重置全部数据\n"
            "  /set reset sign       - 重置签到状态\n"
            "  /set reset lottery    - 重置抽奖次数\n"
            "  /set reset crystal    - 重置所有水晶\n"
            "  /set reset 补给        - 重置所有补给保底\n"
            "  /set reset 补给 角色   - 重置角色补给保底\n"
            "  /set reset 女武神 all  - 重置所有女武神数据\n"
            "  /set reset 女武神图鉴 all - 重置所有图鉴\n"
            "  /set reset 女武神抽取 all - 重置所有抽取次数\n\n"
            "重置指定用户：\n"
            "  /set reset all <用户ID>        - 重置全部\n"
            "  /set reset sign <用户ID>       - 重置签到\n"
            "  /set reset lottery <用户ID>    - 重置抽奖\n"
            "  /set reset crystal <用户ID>    - 重置水晶\n"
            "  /set reset 女武神 <用户ID>     - 重置女武神全部数据\n"
            "  /set reset 女武神图鉴 <用户ID> - 仅重置图鉴\n"
            "  /set reset 女武神抽取 <用户ID> - 仅重置抽取次数\n"
            "  /set reset 图鉴 <用户ID>       - 同上（图鉴）\n"
            "  /set reset 女武神次数 <用户ID>  - 同上（抽取次数）\n"
            "  /set reset 群友 <用户ID>       - 重置今日群友\n"
            "  /set reset 补给 <用户ID>        - 重置补给保底\n"
            "  /set reset 补给 角色 <用户ID>   - 重置角色保底\n\n"
            "⚠️ 重置所有人的操作不可撤销！"
        )


# ==================== SetCommand 基类 ====================

class BaseSetCommand(BaseCommand):
    """设置命令基类"""
    permission_level: PermissionLevel = PermissionLevel.OPERATOR
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"

    _command_prefix: str = "set"

    @cmd_route()
    async def handle_root(self, target: str = "") -> tuple[bool, str]:
        """处理设置命令"""
        try:
            user_id = str(self._message.sender_id) if self._message else ""
            if not user_id:
                await send_text("无法识别用户身份", stream_id=self.stream_id)
                return False, "no user"

            raw_content = self._message.content if self._message else ""
            import re
            pattern = rf'^[/!！]?{self._command_prefix}\s*'
            args_str = re.sub(pattern, '', raw_content, flags=re.IGNORECASE).strip()
            command_parts = [self._command_prefix] + (args_str.split() if args_str else [])

            logger.info(f"📝 完整命令 ({self._command_prefix}): {command_parts}")

            if len(command_parts) < 2:
                await send_text(DevToolsMixin._get_help(), stream_id=self.stream_id)
                return False, "missing args"

            sub_command = command_parts[1]

            # 路由到对应处理方法
            if sub_command == "reset":
                return await self._handle_reset(command_parts)
            elif sub_command == "currency":
                return await self._handle_currency(command_parts)
            elif sub_command == "crystal":
                return await self._handle_crystal(command_parts)
            elif sub_command == "favor":
                return await self._handle_favor(command_parts)
            elif sub_command == "item":
                return await self._handle_item(command_parts)
            elif sub_command == "水晶":
                return await self._handle_crystal_shortcut(command_parts)
            else:
                return await self._handle_shortcut(command_parts)

        except Exception as e:
            logger.error(f"设置失败: {e}", exc_info=True)
            await send_text(f"设置失败: {str(e)}", stream_id=self.stream_id)
            return False, str(e)

    # ========== 处理方法 ==========

    async def _handle_currency(self, command_parts: list) -> tuple[bool, str]:
        """处理 currency 子命令"""
        if len(command_parts) < 4:
            await send_text(
                "❌ 参数不足\n格式: currency <用户ID> <数量>",
                stream_id=self.stream_id
            )
            return False, "missing args"

        target_id = DevToolsMixin._parse_target_id(command_parts[2])
        try:
            amount = int(command_parts[3])
        except ValueError:
            await send_text("❌ 数量必须是数字", stream_id=self.stream_id)
            return False, "invalid amount"

        info = await get_stream_info(self.stream_id)
        group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""

        currency_manager.set_currency(target_id, amount, group_id)
        await send_text(
            f"✅ 已设置用户 {target_id} 的花花数量为 {amount}",
            stream_id=self.stream_id
        )
        return True, "ok"

    async def _handle_crystal(self, command_parts: list) -> tuple[bool, str]:
        """处理 crystal 子命令"""
        if len(command_parts) < 4:
            await send_text(
                "❌ 参数不足\n格式: crystal <用户ID> <数量>",
                stream_id=self.stream_id
            )
            return False, "missing args"

        target_id = DevToolsMixin._parse_target_id(command_parts[2])
        try:
            amount = int(command_parts[3])
        except ValueError:
            await send_text("❌ 数量必须是数字", stream_id=self.stream_id)
            return False, "invalid amount"

        info = await get_stream_info(self.stream_id)
        group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""

        crystal_manager.set_crystal(target_id, amount, group_id)
        await send_text(
            f"✅ 已设置用户 {target_id} 的水晶数量为 {amount}",
            stream_id=self.stream_id
        )
        return True, "ok"

    async def _handle_crystal_shortcut(self, command_parts: list) -> tuple[bool, str]:
        """处理 水晶 快捷命令: /set 水晶 <用户ID> <数量>"""
        if len(command_parts) < 4:
            await send_text(
                "❌ 参数不足\n格式: 水晶 <用户ID> <数量>",
                stream_id=self.stream_id
            )
            return False, "missing args"

        target_id = DevToolsMixin._parse_target_id(command_parts[2])
        try:
            amount = int(command_parts[3])
        except ValueError:
            await send_text("❌ 数量必须是数字", stream_id=self.stream_id)
            return False, "invalid amount"

        info = await get_stream_info(self.stream_id)
        group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""

        crystal_manager.set_crystal(target_id, amount, group_id)
        await send_text(
            f"✅ 已设置用户 {target_id} 的水晶为 {amount}",
            stream_id=self.stream_id
        )
        return True, "ok"

    async def _handle_favor(self, command_parts: list) -> tuple[bool, str]:
        """处理 favor 子命令"""
        if len(command_parts) < 4:
            await send_text(
                "❌ 参数不足\n格式: favor <用户ID> <数量>",
                stream_id=self.stream_id
            )
            return False, "missing args"

        target_id = DevToolsMixin._parse_target_id(command_parts[2])
        try:
            amount = int(command_parts[3])
        except ValueError:
            await send_text("❌ 好感度必须是数字", stream_id=self.stream_id)
            return False, "invalid amount"

        info = await get_stream_info(self.stream_id)
        group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""

        favor_manager.set_favor(target_id, amount, group_id)
        await send_text(
            f"✅ 已设置 {target_id} 的好感度为 {amount}♡",
            stream_id=self.stream_id
        )
        return True, "ok"

    async def _handle_item(self, command_parts: list) -> tuple[bool, str]:
        """处理 item 子命令: /set item <用户ID> <物品名/字段名> [数量]"""
        if len(command_parts) < 4:
            await send_text(
                "❌ 参数不足\n格式: item <用户ID> <物品名/字段名> [数量]\n"
                "💡 特殊字段: 水晶",
                stream_id=self.stream_id
            )
            return False, "missing args"

        target_id = DevToolsMixin._parse_target_id(command_parts[2])
        item_name = command_parts[3]

        try:
            quantity = int(command_parts[4]) if len(command_parts) >= 5 else 1
        except ValueError:
            await send_text("❌ 数量必须是数字", stream_id=self.stream_id)
            return False, "invalid amount"

        info = await get_stream_info(self.stream_id)
        group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""

        # 特殊字段处理
        if item_name == "水晶":
            crystal_manager.set_crystal(target_id, quantity, group_id)
            await send_text(
                f"✅ 已设置用户 {target_id} 水晶为 {quantity}",
                stream_id=self.stream_id
            )
            logger.info(f"管理员 {self._message.sender_id} 设置用户 {target_id} 水晶={quantity}")
            return True, "ok"

        # 物品查找
        item_result = DevToolsMixin._find_item(item_name)

        if not item_result:
            similar_items = DevToolsMixin._search_items(item_name)
            if similar_items:
                tips = "、".join(similar_items[:5])
                await send_text(
                    f"❌ 未找到物品「{item_name}」\n"
                    f"💡 你可能想找: {tips}",
                    stream_id=self.stream_id
                )
            else:
                await send_text(
                    f"❌ 未找到物品「{item_name}」\n"
                    f"💡 发送 /商店 查看所有物品",
                    stream_id=self.stream_id
                )
            return False, "item not found"

        full_name, _ = item_result
        success = shop_manager.add_item_to_inventory(target_id, full_name, quantity, group_id)

        if success:
            await send_text(
                f"✅ 已给 {target_id} 添加 {full_name} x{quantity}",
                stream_id=self.stream_id
            )
        else:
            await send_text(f"❌ 操作失败", stream_id=self.stream_id)

        return True, "ok"

    async def _handle_shortcut(self, command_parts: list) -> tuple[bool, str]:
        """处理快捷命令: /set <物品> <用户ID> [数量]"""
        item_name = command_parts[1]

        info = await get_stream_info(self.stream_id)
        group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""

        # 特殊字段快捷设置
        SPECIAL_FIELDS = {
            "水晶": lambda tid, qty: crystal_manager.set_crystal(tid, qty, group_id),
            "金币": lambda tid, qty: currency_manager.set_currency(tid, qty, group_id),
        }

        if item_name in SPECIAL_FIELDS and len(command_parts) >= 3:
            target_id = DevToolsMixin._parse_target_id(command_parts[2])
            quantity = int(command_parts[3]) if len(command_parts) >= 4 else 1

            SPECIAL_FIELDS[item_name](target_id, quantity)

            await send_text(
                f"✅ 已设置用户 {target_id} {item_name}为 {quantity}",
                stream_id=self.stream_id
            )
            return True, "ok"

        # 物品查找
        item_result = DevToolsMixin._find_item(item_name)

        if item_result and len(command_parts) >= 3:
            target_id = DevToolsMixin._parse_target_id(command_parts[2])
            quantity = int(command_parts[3]) if len(command_parts) >= 4 else 1
            full_name, _ = item_result

            success = shop_manager.add_item_to_inventory(target_id, full_name, quantity, group_id)
            if success:
                await send_text(
                    f"✅ 已给 {target_id} 添加 {full_name} x{quantity}",
                    stream_id=self.stream_id
                )
            else:
                await send_text(f"❌ 操作失败", stream_id=self.stream_id)
            return True, "ok"

        # 未找到
        await send_text(DevToolsMixin._get_help(), stream_id=self.stream_id)
        return False, "unknown command"

    async def _handle_reset(self, command_parts: list) -> tuple[bool, str]:
        """处理 reset 子命令"""
        from ..handlers.sign import sign_manager
        from ..handlers.gacha_handler import gacha_handler
        from ..handlers.valkyrie_handler import valkyrie_handler

        if len(command_parts) < 3:
            await send_text(DevToolsMixin._get_reset_help(), stream_id=self.stream_id)
            return False, "missing args"

        reset_type = command_parts[2].lower()

        info = await get_stream_info(self.stream_id)
        group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""

        # 判断是否有指定用户
        has_target = len(command_parts) >= 4 and command_parts[3] not in ("角色", "装备", "协同", "补给")

        # ==================== 重置补给保底 ====================
        if reset_type == "补给" or reset_type == "supply":
            import json
            from pathlib import Path

            # 获取补给类型
            supply_type = None
            type_index = 3

            if len(command_parts) > 3:
                type_map = {
                    "角色": "角色补给",
                    "装备": "装备补给",
                    "协同": "协同补给",
                    "跃升": "跃升补给",
                    "跃升武装": "跃升武装",
                    "服装": "服装补给",
                }
                type_str = command_parts[3]
                if type_str in type_map:
                    supply_type = type_map[type_str]
                    type_index = 4

            # 获取目标用户
            target_id = None
            if len(command_parts) > type_index:
                target_id = DevToolsMixin._parse_target_id(command_parts[type_index])

            # 清除补给保底数据
            pity_file = Path("data/elysia_dice/gacha_pity.json")
            if target_id:
                # 清除指定用户
                if pity_file.exists():
                    with open(pity_file, 'r', encoding='utf-8') as f:
                        pity_data = json.load(f)
                    
                    base_key = f"{group_id}:{target_id}" if group_id else target_id
                    keys_to_delete = []
                    
                    for key in pity_data:
                        if key.startswith(base_key):
                            if supply_type:
                                # 清除指定类型
                                if f":{supply_type}" in key or key.endswith(f":shared:{supply_type}"):
                                    keys_to_delete.append(key)
                            else:
                                keys_to_delete.append(key)
                    
                    for key in keys_to_delete:
                        del pity_data[key]
                    
                    with open(pity_file, 'w', encoding='utf-8') as f:
                        json.dump(pity_data, f, ensure_ascii=False, indent=2)
                
                msg = f"✅ 已重置用户 {target_id} "
                msg += f"的{supply_type}补给保底" if supply_type else "的所有补给保底"
            else:
                # 清除所有人
                if pity_file.exists():
                    if supply_type:
                        # 只清除指定类型
                        with open(pity_file, 'r', encoding='utf-8') as f:
                            pity_data = json.load(f)
                        
                        keys_to_delete = []
                        for key in pity_data:
                            if f":{supply_type}" in key or key.endswith(f":shared:{supply_type}"):
                                keys_to_delete.append(key)
                        
                        for key in keys_to_delete:
                            del pity_data[key]
                        
                        with open(pity_file, 'w', encoding='utf-8') as f:
                            json.dump(pity_data, f, ensure_ascii=False, indent=2)
                        
                        msg = f"✅ 已重置所有人的{supply_type}补给保底"
                    else:
                        pity_file.unlink()
                        msg = "✅ 已重置所有人的补给保底"

            # 清除服装补给数据
            costume_file = Path("data/elysia_dice/costume_supply.json")
            if target_id:
                if costume_file.exists():
                    with open(costume_file, 'r', encoding='utf-8') as f:
                        costume_data = json.load(f)
                    
                    base_key = f"{group_id}:{target_id}" if group_id else target_id
                    keys_to_delete = [k for k in costume_data if k.startswith(f"{base_key}:costume")]
                    
                    for key in keys_to_delete:
                        del costume_data[key]
                    
                    with open(costume_file, 'w', encoding='utf-8') as f:
                        json.dump(costume_data, f, ensure_ascii=False, indent=2)

            await send_text(msg, stream_id=self.stream_id)
            return True, "ok"

        # ==================== 重置女武神 ====================
        if reset_type == "女武神":
            return await self._handle_reset_valkyrie(command_parts, group_id)

        # ==================== 重置女武神图鉴 ====================
        if reset_type in ("女武神图鉴", "图鉴"):
            return await self._handle_reset_valkyrie_collection(command_parts, group_id)

        # ==================== 重置女武神抽取次数 ====================
        if reset_type in ("女武神抽取", "女武神次数"):
            return await self._handle_reset_valkyrie_pulls(command_parts, group_id)

        # ==================== 重置群友 ====================
        if reset_type in ("群友", "群老婆", "群友老婆"):
            return await self._handle_reset_groupmate(command_parts, group_id)

        # ==================== 重置其他类型 ====================
        valid_types = ("all", "sign", "lottery", "crystal")
        if reset_type not in valid_types:
            await send_text(
                f"❌ 未知的 reset 类型: {reset_type}\n"
                f"可用类型: all, sign, lottery, crystal, 补给, 女武神, 群友\n"
                f"💡 发送 /set reset 查看帮助",
                stream_id=self.stream_id
            )
            return False, "invalid reset type"

        # 如果有指定用户ID
        if has_target:
            target_id = DevToolsMixin._parse_target_id(command_parts[3])

            if reset_type == "all":
                currency_manager.reset_user_currency(target_id, group_id)
                sign_manager.reset_user(target_id, group_id)
                shop_manager.reset_user_lottery(target_id, group_id)
                favor_manager.reset_user_favor(target_id, group_id)
                crystal_manager.reset_crystal(target_id, group_id)
                msg = (
                    f"✅ 已重置用户 {target_id} 的全部数据\n"
                    f"━━━━━━━━━━━━\n"
                    f"• 花花数量 → 0\n"
                    f"• 签到状态 → 已重置\n"
                    f"• 抽奖次数 → 已重置\n"
                    f"• 好感度 → 0\n"
                    f"• 水品 → 0"
                )
            elif reset_type == "sign":
                sign_manager.reset_user(target_id, group_id)
                msg = f"✅ 已重置用户 {target_id} 的今日签到状态"
            elif reset_type == "lottery":
                shop_manager.reset_user_lottery(target_id, group_id)
                msg = f"✅ 已重置用户 {target_id} 的今日抽奖次数"
            elif reset_type == "crystal":
                crystal_manager.reset_crystal(target_id, group_id)
                msg = f"✅ 已重置用户 {target_id} 的水晶"

            await send_text(msg, stream_id=self.stream_id)
            return True, "ok"

        # 重置所有人
        else:
            if reset_type == "all":
                c_count = currency_manager.reset_all_currency(group_id)
                s_count = sign_manager.reset_all_sign(group_id)
                l_count = shop_manager.reset_all_lottery(group_id)
                f_count = favor_manager.reset_all_favor(group_id)
                cr_count = crystal_manager.reset_all_crystal(group_id)
                msg = (
                    f"⚠️ 已重置所有人全部数据\n"
                    f"━━━━━━━━━━━━\n"
                    f"• 花花: {c_count} 个用户 → 0\n"
                    f"• 签到: {s_count} 个用户 → 已重置\n"
                    f"• 抽奖: {l_count} 个用户 → 已重置\n"
                    f"• 好感度: {f_count} 个用户 → 0\n"
                    f"• 水晶: {cr_count} 个用户 → 0\n"
                    f"━━━━━━━━━━━━\n"
                    f"⚠️ 此操作不可撤销！"
                )
            elif reset_type == "sign":
                count = sign_manager.reset_all_sign(group_id)
                msg = f"✅ 已重置 {count} 个用户的今日签到状态"
            elif reset_type == "lottery":
                count = shop_manager.reset_all_lottery(group_id)
                msg = f"✅ 已重置 {count} 个用户的今日抽奖次数"
            elif reset_type == "crystal":
                count = crystal_manager.reset_all_crystal(group_id)
                msg = f"✅ 已重置 {count} 个用户的水晶"

            await send_text(msg, stream_id=self.stream_id)
            return True, "ok"
        
    async def _handle_reset_valkyrie(self, command_parts: list, group_id: str) -> tuple[bool, str]:
        """处理重置女武神数据"""
        from ..handlers.valkyrie_handler import valkyrie_handler

        if len(command_parts) < 4:
            await send_text(
                "❌ 请指定用户ID 或 all\n"
                "格式:\n"
                "  reset 女武神 <用户ID>  - 重置指定用户\n"
                "  reset 女武神 all       - 重置所有人",
                stream_id=self.stream_id
            )
            return False, "missing target"

        target = command_parts[3]

        if target.lower() == "all":
            count = valkyrie_handler.reset_all_valkyrie(group_id)
            await send_text(
                f"⚠️ 已重置 {count} 个用户的所有女武神数据\n"
                f"━━━━━━━━━━━━\n"
                f"• 抽取次数 → 已清除\n"
                f"• 女武神图鉴 → 已清除\n"
                f"• 今日女武神 → 已清除\n"
                f"━━━━━━━━━━━━\n"
                f"⚠️ 此操作不可撤销！",
                stream_id=self.stream_id
            )
        else:
            target_id = DevToolsMixin._parse_target_id(target)
            valkyrie_handler.reset_valkyrie(target_id, group_id)
            valkyrie_handler.reset_collection(target_id, group_id)
            valkyrie_handler.reset_pull_records(target_id, group_id)

            await send_text(
                f"✅ 已重置用户 {target_id} 的女武神数据\n"
                f"━━━━━━━━━━━━\n"
                f"• 抽取次数 → 已清除\n"
                f"• 女武神图鉴 → 已清除\n"
                f"• 今日女武神 → 已清除",
                stream_id=self.stream_id
            )

        return True, "ok"

    async def _handle_reset_valkyrie_collection(self, command_parts: list, group_id: str) -> tuple[bool, str]:
        """处理重置女武神图鉴"""
        from ..handlers.valkyrie_handler import valkyrie_handler

        if len(command_parts) < 4:
            await send_text(
                "❌ 请指定用户ID 或 all\n"
                "格式:\n"
                "  reset 女武神图鉴 <用户ID>  - 重置指定用户图鉴\n"
                "  reset 女武神图鉴 all       - 重置所有人图鉴",
                stream_id=self.stream_id
            )
            return False, "missing target"

        target = command_parts[3]

        if target.lower() == "all":
            count = valkyrie_handler.reset_all_collection(group_id)
            await send_text(
                f"⚠️ 已重置 {count} 个用户的女武神图鉴\n"
                f"⚠️ 此操作不可撤销！",
                stream_id=self.stream_id
            )
        else:
            target_id = DevToolsMixin._parse_target_id(target)
            valkyrie_handler.reset_collection(target_id, group_id)
            await send_text(
                f"✅ 已重置用户 {target_id} 的女武神图鉴",
                stream_id=self.stream_id
            )

        return True, "ok"

    async def _handle_reset_valkyrie_pulls(self, command_parts: list, group_id: str) -> tuple[bool, str]:
        """处理重置女武神抽取次数"""
        from ..handlers.valkyrie_handler import valkyrie_handler

        if len(command_parts) < 4:
            await send_text(
                "❌ 请指定用户ID 或 all\n"
                "格式:\n"
                "  reset 女武神抽取 <用户ID>  - 重置指定用户抽取次数\n"
                "  reset 女武神抽取 all       - 重置所有人抽取次数",
                stream_id=self.stream_id
            )
            return False, "missing target"

        target = command_parts[3]

        if target.lower() == "all":
            count = valkyrie_handler.reset_all_pull_records(group_id)
            await send_text(
                f"⚠️ 已重置 {count} 个用户的女武神抽取次数\n"
                f"⚠️ 此操作不可撤销！",
                stream_id=self.stream_id
            )
        else:
            target_id = DevToolsMixin._parse_target_id(target)
            valkyrie_handler.reset_pull_records(target_id, group_id)
            valkyrie_handler.reset_valkyrie(target_id, group_id)
            await send_text(
                f"✅ 已重置用户 {target_id} 的女武神抽取次数\n"
                f"━━━━━━━━━━━━\n"
                f"• 累计抽取次数 → 已清除\n"
                f"• 今日抽取次数 → 已清除",
                stream_id=self.stream_id
            )

        return True, "ok"
    
    async def _handle_reset_groupmate(self, command_parts: list, group_id: str) -> tuple[bool, str]:
        """处理重置群友关系
        支持：
        - reset 群友 <用户ID>          清除指定用户的群友关系（若已婚则解除双方锁定）
        - reset 群友 all               清除所有群友关系
        - reset 群友 <用户ID> 抽取     仅重置抽取次数，保留关系
        - reset 群友 <用户ID> 关系     仅清除关系，保留抽取次数
        """
        from ..handlers.groupmate_handler import groupmate_handler
    
        if len(command_parts) < 4:
            await send_text(
                "❌ 请指定用户ID 或 all\n"
                "格式:\n"
                "  reset 群友 <用户ID>         - 清除关系+重置抽取次数\n"
                "  reset 群友 all              - 清除所有群友关系\n"
                "  reset 群友 <用户ID> 抽取    - 仅重置抽取次数\n"
                "  reset 群友 <用户ID> 关系    - 仅清除关系",
                stream_id=self.stream_id
            )
            return False, "missing target"
    
        target = command_parts[3]
        sub_action = command_parts[4] if len(command_parts) >= 5 else ""
    
        if target.lower() == "all":
            # 清除所有群友关系
            count = groupmate_handler.reset_all_groupmate(group_id)
            await send_text(
                f"⚠️ 已清除 {count} 个用户的全部群友关系\n"
                f"━━━━━━━━━━━━\n"
                f"• 群友关系 → 已清除\n"
                f"• 抽取次数 → 已重置\n"
                f"• 锁定状态 → 已解除\n"
                f"━━━━━━━━━━━━\n"
                f"⚠️ 此操作不可撤销！",
                stream_id=self.stream_id
            )
            return True, "ok"
    
        target_id = DevToolsMixin._parse_target_id(target)
    
        if sub_action == "抽取":
            # 仅重置抽取次数
            groupmate_handler.reset_swap_count(target_id, group_id)
            await send_text(
                f"✅ 已重置用户 {target_id} 的群友抽取次数\n"
                f"• 抽取次数 → 已重置为0\n"
                f"• 群友关系 → 保留",
                stream_id=self.stream_id
            )
            return True, "ok"
    
        if sub_action == "关系":
            # 仅清除关系
            cleared = groupmate_handler.clear_relationship(target_id, group_id)
            if cleared.get("mutual_cleared"):
                await send_text(
                    f"✅ 已清除用户 {target_id} 的群友关系\n"
                    f"━━━━━━━━━━━━\n"
                    f"• 被解除方：{cleared.get('target', '')} 的锁定已解除\n"
                    f"• 双方锁定 → 已清除\n"
                    f"• 抽取次数 → 保留",
                    stream_id=self.stream_id
                )
            else:
                await send_text(
                    f"✅ 已清除用户 {target_id} 的群友关系\n"
                    f"• 抽取次数 → 保留",
                    stream_id=self.stream_id
                )
            return True, "ok"
    
        # 默认：清除关系 + 重置抽取次数
        cleared = groupmate_handler.reset_groupmate_full(target_id, group_id)
        
        msg = f"✅ 已清除用户 {target_id} 的全部群友数据\n"
        msg += f"━━━━━━━━━━━━\n"
        msg += f"• 群友关系 → 已清除\n"
        msg += f"• 抽取次数 → 已重置\n"
        
        if cleared.get("target"):
            msg += f"• {cleared.get('target')} → 已解除锁定\n"
        
        if cleared.get("claimed_by"):
            msg += f"• {cleared.get('claimed_by')} → 已解除锁定\n"
        
        await send_text(msg, stream_id=self.stream_id)
        return True, "ok"


# ==================== GetCommand 基类 ====================

class BaseGetCommand(BaseCommand):
    """查询命令基类"""
    permission_level: PermissionLevel = PermissionLevel.OPERATOR
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"

    _command_prefix: str = "get"

    @cmd_route()
    async def handle_root(self, target: str = "") -> tuple[bool, str]:
        """处理查询命令"""
        try:
            user_id = str(self._message.sender_id) if self._message else ""

            if not user_id:
                await send_text("无法识别用户身份", stream_id=self.stream_id)
                return False, "no user"

            raw_content = self._message.content if self._message else ""
            import re
            pattern = rf'^[/!！]?{self._command_prefix}\s*'
            args_str = re.sub(pattern, '', raw_content, flags=re.IGNORECASE).strip()
            command_parts = ["get"] + (args_str.split() if args_str else [])

            logger.info(f"📝 完整命令 ({self._command_prefix}): {command_parts}")

            result = await handle_get_command(user_id, command_parts)
            await send_text(result, stream_id=self.stream_id)
            return True, "ok"

        except Exception as e:
            logger.error(f"查询失败: {e}", exc_info=True)
            await send_text(f"查询失败: {str(e)}", stream_id=self.stream_id)
            return False, str(e)


# ==================== 具体命令类 ====================

class SetCommand(BaseSetCommand):
    """设置命令 - /set"""
    command_name: str = "set"
    command_description: str = "开发者设置工具"
    _command_prefix: str = "set"


class ElySetCommand(BaseSetCommand):
    """设置命令 - /elyset"""
    command_name: str = "elyset"
    command_description: str = "开发者设置工具（Elysia前缀）"
    _command_prefix: str = "elyset"


class GetCommand(BaseGetCommand):
    """查询命令 - /get"""
    command_name: str = "get"
    command_description: str = "开发者查询工具"
    _command_prefix: str = "get"


class ElyGetCommand(BaseGetCommand):
    """查询命令 - /elyget"""
    command_name: str = "elyget"
    command_description: str = "开发者查询工具（Elysia前缀）"
    _command_prefix: str = "elyget"
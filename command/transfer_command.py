"""
转让命令组件 - /转让
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from src.app.plugin_system.api.log_api import get_logger
from src.app.plugin_system.api.send_api import send_text
from src.app.plugin_system.base import BaseCommand, cmd_route
from src.app.plugin_system.types import PermissionLevel, ChatType
from src.app.plugin_system.api.stream_api import get_stream_info

from ..handlers.shop import shop_manager, ITEM_ALIASES, _make_key
from ..handlers.dev_tools import currency_manager

if TYPE_CHECKING:
    from ..plugin import ElysiaDicePlugin

logger = get_logger("elysia_dice.transfer_command")


class TransferCommand(BaseCommand):
    """转让命令 - /转让"""
    command_name: str = "转让"
    command_description: str = "转让花花或物品给群内其他用户"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.GROUP  # 仅群聊
    plugin: "ElysiaDicePlugin"

    @classmethod
    def match(cls, parts: list[str]) -> int:
        if not parts:
            return 0
        if parts[0] in ("转让", "transfer"):
            return 1
        return 0

    @cmd_route()
    async def handle_root(self, target: str = "") -> tuple[bool, str]:
        try:
            user_id = str(self._message.sender_id) if self._message else ""
            if not user_id:
                await send_text("无法识别用户身份", stream_id=self.stream_id)
                return False, "no user"

            # 获取群ID
            info = await get_stream_info(self.stream_id)
            group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""

            if not group_id:
                await send_text("❌ 转让功能仅在群聊可用", stream_id=self.stream_id)
                return False, "not group"

            # 获取原始消息内容
            raw_content = self._message.content if self._message else ""
            logger.info(f"📝 转让原始消息: {raw_content}")

            # 移除命令前缀
            import re
            args_str = re.sub(
                r'^[/!！]?(转让|transfer)\s*', '', raw_content, flags=re.IGNORECASE
            ).strip()

            logger.info(f"📝 转让参数: {args_str}")

            if not args_str:
                await send_text(self._get_help_text(), stream_id=self.stream_id)
                return False, "no args"

            # 提取 @用户 或直接用户ID
            target_user_id = None
            target_display = ""

            # 优先从 mentions 中获取
            if self._message and hasattr(self._message, 'mentions') and self._message.mentions:
                target_user_id = str(self._message.mentions[0])
                target_display = f"<@{target_user_id}>"
                args_str = self._remove_mention(raw_content)

            if not target_user_id:
                # 尝试从参数中解析用户ID（纯数字或 @ 格式）
                parts = args_str.split()
                if parts:
                    first_part = parts[0]
                    # 检查是否是纯数字用户ID
                    if first_part.isdigit() and len(first_part) >= 5:
                        target_user_id = first_part
                        target_display = target_user_id
                        args_str = " ".join(parts[1:])
                    # 检查是否是 <@数字> 格式
                    elif first_part.startswith("<@") and first_part.endswith(">"):
                        target_user_id = first_part[2:-1].strip("!")
                        target_display = first_part
                        args_str = " ".join(parts[1:])
                    # 检查是否是 @<昵称:数字> 格式 (NapCat)
                    elif first_part.startswith("@<") and first_part.endswith(">"):
                        import re as re2
                        match = re2.search(r'[:：](\d+)>', first_part)
                        if match:
                            target_user_id = match.group(1)
                            target_display = first_part
                            args_str = " ".join(parts[1:])

            if not target_user_id:
                await send_text(
                    "❌ 请指定转让目标\n"
                    "格式: /转让 @用户 <花花/物品> [数量]\n"
                    "示例: /转让 @莎琳娜 花花 100\n"
                    "      /转让 123456789 蒸蛋 3",
                    stream_id=self.stream_id
                )
                return False, "no target"

            # 不能转让给自己
            if target_user_id == user_id:
                await send_text("❌ 不能转让给自己哦~", stream_id=self.stream_id)
                return False, "self transfer"

            args_str = args_str.strip()
            if not args_str:
                await send_text(self._get_help_text(), stream_id=self.stream_id)
                return False, "no item"

            parts = args_str.split()

            # 判断是转让花花还是物品
            if parts[0] in ("花花", "花", "flower", "flowers"):
                quantity = 1
                if len(parts) >= 2:
                    try:
                        quantity = int(parts[1])
                    except ValueError:
                        await send_text(
                            f"❌ 数量格式错误: {parts[1]}\n"
                            f"格式: /转让 @用户 花花 <数量>",
                            stream_id=self.stream_id
                        )
                        return False, "invalid quantity"

                if quantity <= 0:
                    await send_text("❌ 转让数量必须大于0", stream_id=self.stream_id)
                    return False, "invalid quantity"

                return await self._transfer_flowers(
                    user_id, target_user_id, target_display, quantity, group_id
                )
            else:
                # 转让物品
                item_name = args_str
                quantity = 1

                if parts[-1].isdigit():
                    quantity = int(parts[-1])
                    item_name = " ".join(parts[:-1])

                if quantity <= 0:
                    await send_text("❌ 转让数量必须大于0", stream_id=self.stream_id)
                    return False, "invalid quantity"

                return await self._transfer_item(
                    user_id, target_user_id, target_display, item_name, quantity, group_id
                )

        except Exception as e:
            logger.error(f"转让失败: {e}", exc_info=True)
            await send_text(f"转让失败: {str(e)}", stream_id=self.stream_id)
            return False, str(e)

    def _remove_mention(self, raw_content: str) -> str:
        """移除消息中的 @用户 部分"""
        import re
        args_str = re.sub(
            r'^[/!！]?(转让|transfer)\s*', '', raw_content, flags=re.IGNORECASE
        )
        # 匹配 <@数字> 或 <@!数字>
        args_str = re.sub(r'<@!?\d+>', '', args_str).strip()
        # 匹配 @<昵称:数字> (NapCat格式)
        args_str = re.sub(r'@<[^>]*[:：]\d+>', '', args_str).strip()
        # 也尝试移除 @用户名 格式（用户名不含空格）
        args_str = re.sub(r'@\S+', '', args_str).strip()
        return args_str

    async def _transfer_flowers(
        self, from_user: str, to_user: str, to_display: str, quantity: int, group_id: str
    ) -> tuple[bool, str]:
        """转让花花"""
        from_balance = currency_manager.get_currency(from_user, group_id)

        logger.info(
            f"💐 转让花花: from={from_user}, to={to_user}, "
            f"amount={quantity}, balance={from_balance}"
        )

        if from_balance < quantity:
            await send_text(
                f"❌ 花花不足！\n"
                f"━━━━━━━━━━━━\n"
                f"💐 想要转让: {quantity} 花花\n"
                f"💳 当前余额: {from_balance} 花花\n"
                f"❌ 缺少: {quantity - from_balance} 花花\n\n"
                f"💡 发送 /签到 获取更多花花",
                stream_id=self.stream_id
            )
            return False, "not enough flowers"

        # 扣除转让方花花
        currency_manager.add_currency(from_user, -quantity, group_id)
        # 增加接收方花花
        currency_manager.add_currency(to_user, quantity, group_id)

        from_new = currency_manager.get_currency(from_user, group_id)
        to_new = currency_manager.get_currency(to_user, group_id)

        transfer_msg = (
            f"💐 转让成功！\n"
            f"━━━━━━━━━━━━\n"
            f"💛 转让花花: {quantity} 朵\n"
            f"📤 转出方余额: {from_new} 花花\n"
            f"📥 接收方余额: {to_new} 花花\n"
        )

        await send_text(transfer_msg, stream_id=self.stream_id)
        return True, "ok"

    async def _transfer_item(
        self, from_user: str, to_user: str, to_display: str,
        item_name: str, quantity: int, group_id: str
    ) -> tuple[bool, str]:
        """转让物品"""
        logger.info(
            f"🎁 转让物品: from={from_user}, to={to_user}, "
            f"item={item_name}, qty={quantity}"
        )

        # 查找物品
        item_result = ITEM_ALIASES.get(item_name)
        if not item_result:
            for key in ITEM_ALIASES:
                if item_name in key or key in item_name:
                    item_result = ITEM_ALIASES[key]
                    break

        if not item_result:
            await send_text(
                f"❌ 未找到物品「{item_name}」\n"
                f"💡 使用 /背包 查看你的物品",
                stream_id=self.stream_id
            )
            return False, "item not found"

        full_name, _ = item_result

        # 检查转让方是否有足够物品（用分群key）
        from_key = _make_key(from_user, group_id)
        from_inventory = shop_manager.user_inventory.get(from_key, {})
        owned_count = from_inventory.get(full_name, 0)

        if owned_count < quantity:
            await send_text(
                f"❌ 背包物品不足\n"
                f"━━━━━━━━━━━━\n"
                f"🎁 想要转让: {full_name} x{quantity}\n"
                f"📦 当前拥有: {full_name} x{owned_count}\n"
                f"❌ 缺少: {quantity - owned_count}个",
                stream_id=self.stream_id
            )
            return False, "not enough items"

        # 扣除转让方物品
        shop_manager.user_inventory[from_key][full_name] = owned_count - quantity
        if shop_manager.user_inventory[from_key][full_name] <= 0:
            del shop_manager.user_inventory[from_key][full_name]

        # 增加接收方物品
        to_key = _make_key(to_user, group_id)
        if to_key not in shop_manager.user_inventory:
            shop_manager.user_inventory[to_key] = {}
        shop_manager.user_inventory[to_key][full_name] = (
            shop_manager.user_inventory[to_key].get(full_name, 0) + quantity
        )

        from_remaining = shop_manager.user_inventory[from_key].get(full_name, 0)
        to_total = shop_manager.user_inventory[to_key].get(full_name, 0)

        transfer_msg = (
            f"🎁 转让成功！\n"
            f"━━━━━━━━━━━━\n"
            f"💝 转让物品: {full_name} x{quantity}\n"
            f"📤 转出方剩余: {full_name} x{from_remaining}\n"
            f"📥 接收方拥有: {full_name} x{to_total}\n"
        )

        await send_text(transfer_msg, stream_id=self.stream_id)
        return True, "ok"

    def _get_help_text(self) -> str:
        return (
            "💝 转让帮助\n"
            "━━━━━━━━━━━━\n"
            "📝 使用方法：\n\n"
            "1️⃣ 转让花花：\n"
            "   /转让 @用户 花花 <数量>\n\n"
            "2️⃣ 转让物品：\n"
            "   /转让 @用户 <物品> [数量]\n\n"
            "💡 示例：\n"
            "   /转让 @莎琳娜 花花 100\n"
            "   /转让 @小红 蒸蛋 3\n"
            "   /转让 @小明 蛋糕\n\n"
            "⚠️ 注意：\n"
            "   - 仅群聊可用\n"
            "   - 不能转让给自己"
        )

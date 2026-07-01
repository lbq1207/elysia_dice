"""
水晶相关命令：/补给、/抽卡、/获取水晶
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.app.plugin_system.api.log_api import get_logger
from src.app.plugin_system.api.send_api import send_text
from src.app.plugin_system.base import BaseCommand, cmd_route
from src.app.plugin_system.types import PermissionLevel, ChatType
from src.app.plugin_system.api.stream_api import get_stream_info

from ..handlers.crystal import crystal_manager, DAILY_CRYSTAL_AMOUNT

if TYPE_CHECKING:
    from ..plugin import ElysiaDicePlugin

logger = get_logger("elysia_dice.crystal_command")


class SupplyCommand(BaseCommand):
    """补给/抽卡菜单 - /补给 或 /抽卡"""
    command_name: str = "补给"
    command_description: str = "打开崩坏3补给菜单"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"

    @classmethod
    def match(cls, parts: list[str]) -> int:
        if not parts:
            return 0
        if parts[0] in ("补给", "抽卡"):
            return 1
        return 0

    @cmd_route()
    async def handle_root(self) -> tuple[bool, str]:
        try:
            user_id = str(self._message.sender_id) if self._message else ""
            if not user_id:
                await send_text("无法识别用户身份", stream_id=self.stream_id)
                return False, "no user"

            info = await get_stream_info(self.stream_id)
            group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""

            current_crystal = crystal_manager.get_crystal(user_id, group_id)

            menu = (
                f"💎 崩坏3补给菜单\n"
                f"━━━━━━━━━━━━\n"
                f"💎 当前水晶：{current_crystal}\n"
                f"━━━━━━━━━━━━\n"
                f"📋 可用补给类型：\n\n"
                f"🔹 /角色补给A（或B）（或跃升补给）  - 抽取女武神角色\n"
                f"🔹 /装备补给A（或B）（或跃升武装）  - 抽取武器和圣痕\n"
                f"🔹 /协同补给  - 抽取武装人偶\n"
                f"🔹 /服装补给  - 抽取限定服装\n"
                f"━━━━━━━━━━━━\n"
                f"📝 使用方法：\n"
                f"   /角色补给A（或B）（或跃升补给） [次数]\n"
                f"   /装备补给A（或B）（或跃升武装） [次数]\n"
                f"   /协同补给 [次数]\n"
                f"   /服装补给 [次数]\n"
                f"💡 示例：\n"
                f"   /角色补给A\n"
                f"   /装备补给B 10\n"
                f"   /协同补给 5\n"
                f"   /服装补给\n"
                f"━━━━━━━━━━━━\n"
                f"💡 发送 /获取水晶 每日领取 {DAILY_CRYSTAL_AMOUNT} 水晶"
            )

            await send_text(menu, stream_id=self.stream_id)
            return True, "ok"

        except Exception as e:
            logger.error(f"补给菜单失败: {e}", exc_info=True)
            await send_text(f"补给菜单加载失败: {str(e)}", stream_id=self.stream_id)
            return False, str(e)


class GetCrystalCommand(BaseCommand):
    """获取水晶 - /获取水晶"""
    command_name: str = "获取水晶"
    command_description: str = f"每日获取 {DAILY_CRYSTAL_AMOUNT} 水晶（每人每日限一次）"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"

    @classmethod
    def match(cls, parts: list[str]) -> int:
        if not parts:
            return 0
        if parts[0] == "获取水晶":
            return 1
        return 0

    @cmd_route()
    async def handle_root(self) -> tuple[bool, str]:
        try:
            user_id = str(self._message.sender_id) if self._message else ""
            if not user_id:
                await send_text("无法识别用户身份", stream_id=self.stream_id)
                return False, "no user"

            info = await get_stream_info(self.stream_id)
            group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""

            if not crystal_manager.can_get_daily_crystal(user_id, group_id):
                current = crystal_manager.get_crystal(user_id, group_id)
                await send_text(
                    f"⏰ 今日水晶已领取\n"
                    f"━━━━━━━━━━━━\n"
                    f"💎 当前水晶：{current}\n"
                    f"━━━━━━━━━━━━\n"
                    f"💡 每日北京时间0点刷新领取机会",
                    stream_id=self.stream_id
                )
                return True, "already claimed"

            amount = crystal_manager.claim_daily_crystal(user_id, group_id)
            current = crystal_manager.get_crystal(user_id, group_id)

            msg = (
                f"💎 水晶领取成功！\n"
                f"━━━━━━━━━━━━\n"
                f"💎 获得水晶：+{amount}\n"
                f"💎 当前水晶：{current}\n"
                f"━━━━━━━━━━━━\n"
                f"💡 发送 /补给 或 /抽卡 使用水晶\n"
                f"💡 每日可领取一次"
            )

            await send_text(msg, stream_id=self.stream_id)
            return True, "ok"

        except Exception as e:
            logger.error(f"获取水晶失败: {e}", exc_info=True)
            await send_text(f"获取水晶失败: {str(e)}", stream_id=self.stream_id)
            return False, str(e)


class CrystalQueryCommand(BaseCommand):
    """水晶查询 - /水晶"""
    command_name: str = "水晶"
    command_description: str = "查询当前水晶数量"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"

    @classmethod
    def match(cls, parts: list[str]) -> int:
        if not parts:
            return 0
        if parts[0] == "水晶":
            return 1
        return 0

    @cmd_route()
    async def handle_root(self) -> tuple[bool, str]:
        try:
            user_id = str(self._message.sender_id) if self._message else ""
            if not user_id:
                await send_text("无法识别用户身份", stream_id=self.stream_id)
                return False, "no user"

            info = await get_stream_info(self.stream_id)
            group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""

            current = crystal_manager.get_crystal(user_id, group_id)
            can_claim = crystal_manager.can_get_daily_crystal(user_id, group_id)

            msg = (
                f"💎 水晶查询\n"
                f"━━━━━━━━━━━━\n"
                f"💎 当前水晶：{current}\n"
                f"📅 今日领取：{'未领取' if can_claim else '已领取'}\n"
                f"━━━━━━━━━━━━\n"
                f"💡 未领取？发送 /获取水晶\n"
                f"💡 使用水晶？发送 /补给 或 /抽卡"
            )

            await send_text(msg, stream_id=self.stream_id)
            return True, "ok"

        except Exception as e:
            logger.error(f"水晶查询失败: {e}", exc_info=True)
            return False, str(e)
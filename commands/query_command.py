"""
查询花花命令组件
支持 /花花, /balance, /余额
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.app.plugin_system.api.log_api import get_logger
from src.app.plugin_system.api.send_api import send_text
from src.app.plugin_system.base import BaseCommand, cmd_route
from src.app.plugin_system.types import PermissionLevel, ChatType
from src.app.plugin_system.api.stream_api import get_stream_info

from ..handlers.dev_tools import currency_manager

if TYPE_CHECKING:
    from ..plugin import ElysiaDicePlugin

logger = get_logger("elysia_dice.query_command")


class QueryCommand(BaseCommand):
    """查询花花命令组件"""
    
    command_name: str = "花花"
    command_description: str = "查询花花余额"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    
    plugin: "ElysiaDicePlugin"
    
    @classmethod
    def match(cls, parts: list[str]) -> int:
        """匹配命令名，支持多个别名"""
        if not parts:
            return 0
        if parts[0] in ("花花", "balance", "余额"):
            return 1
        return 0
    
    @cmd_route()
    async def handle_root(self) -> tuple[bool, str]:
        """查询花花余额"""
        try:
            user_id = str(self._message.sender_id) if self._message else ""
            
            if not user_id:
                await self._reply("无法识别用户身份")
                return False, "no user"
            
            info = await get_stream_info(self.stream_id)
            group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""
            
            amount = currency_manager.get_currency(user_id, group_id)
            result = (
                f"❀ 花花余额查询\n"
                f"━━━━━━━━━━━━\n"
                f"👤 你的花花：{amount} 花花\n"
                f"━━━━━━━━━━━━\n"
                f"💡 发送 /签到 获取更多花花"
            )
            await self._reply(result)
            return True, "ok"
            
        except Exception as e:
            logger.error(f"查询失败: {e}")
            await self._reply("查询系统维护中，请稍后再试")
            return False, str(e)
    
    async def _reply(self, text: str) -> None:
        """向当前流发送消息"""
        await send_text(text, stream_id=self.stream_id)
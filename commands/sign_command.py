"""
签到命令组件
支持 /签到 和 /sign 命令
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.app.plugin_system.api.log_api import get_logger
from src.app.plugin_system.api.send_api import send_text
from src.app.plugin_system.base import BaseCommand, cmd_route
from src.app.plugin_system.types import PermissionLevel, ChatType

from ..handlers.sign import handle_sign

if TYPE_CHECKING:
    from ..plugin import ElysiaDicePlugin

logger = get_logger("elysia_dice.sign_command")


class SignCommand(BaseCommand):
    """签到命令组件"""
    
    command_name: str = "签到"
    command_description: str = "每日签到获取花花"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    
    plugin: "ElysiaDicePlugin"
    
    @classmethod
    def match(cls, parts: list[str]) -> int:
        """匹配命令名，支持 '签到' 和 'sign'"""
        if not parts:
            return 0
        if parts[0] in ("签到", "sign"):
            return 1
        return 0
    
    @cmd_route()
    async def handle_root(self) -> tuple[bool, str]:
        """签到主入口"""
        try:
            user_id = str(self._message.sender_id) if self._message else ""
            group_id = await self._get_group_id()
            
            if not user_id:
                await self._reply("无法识别用户身份")
                return False, "no user"
            
            result = await handle_sign(user_id, group_id)
            await self._reply(result)
            return True, "ok"
            
        except Exception as e:
            logger.error(f"签到失败: {e}")
            await self._reply(f"签到系统维护中，请稍后再试")
            return False, str(e)
    
    async def _reply(self, text: str) -> None:
        """向当前流发送消息"""
        await send_text(text, stream_id=self.stream_id)
    
    async def _get_group_id(self) -> str:
        """获取当前群组ID，私聊返回空"""
        from src.app.plugin_system.api.stream_api import get_stream_info
        info = await get_stream_info(self.stream_id)
        if isinstance(info, dict) and info.get("chat_type") == "group":
            return str(info.get("group_id", ""))
        return ""
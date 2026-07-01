"""
好感度命令
"""
from src.app.plugin_system.api.log_api import get_logger
from src.app.plugin_system.api.send_api import send_text
from src.app.plugin_system.base import BaseCommand, cmd_route
from src.app.plugin_system.types import PermissionLevel, ChatType
from src.app.plugin_system.api.stream_api import get_stream_info
from ..handlers.favor import favor_manager

logger = get_logger("elysia_dice.favor_command")


class FavorCommand(BaseCommand):
    command_name = "好感度"
    command_description = "查询爱莉对你的好感度"
    permission_level = PermissionLevel.USER
    chat_type = ChatType.ALL

    @classmethod
    def match(cls, parts: list[str]) -> int:
        return 1 if parts and parts[0] in ("好感度", "favor", "查询好感度") else 0

    @cmd_route()
    async def handle_root(self) -> tuple[bool, str]:
        uid = str(getattr(self._message, 'sender_id', ''))
        if not uid:
            return False, "no user"
        info = await get_stream_info(self.stream_id)
        gid = str(info.get("group_id", "")) if isinstance(info, dict) else ""
        favor = favor_manager.get_favor(uid, gid)
        msg = self._favor_msg(favor)
        await send_text(f"💖 好感度: {favor}♡\n{msg}\n💡 /赠送 <物品> 提升好感", stream_id=self.stream_id)
        return True, "ok"

    def _favor_msg(self, f: int) -> str:
        if f >= 520: return "💖 你永远喜欢爱莉希雅！"
        if f >= 320: return "💕 爱莉永远喜欢你~"
        if f >= 160: return "💗 爱莉很喜欢你！"
        if f >= 80:  return "💓 对你很有好感~"
        if f >= 30:  return "💝 开始注意到你了~"
        if f > 0:    return "💌 初次见面~"
        return "🌱 还没有好感度记录"


class RankCommand(BaseCommand):
    command_name = "排行"
    command_description = "好感度排行（显示昵称）"
    permission_level = PermissionLevel.USER
    chat_type = ChatType.GROUP

    @classmethod
    def match(cls, parts: list[str]) -> int:
        return 1 if parts and parts[0] in ("排行", "rank", "排名") else 0

    @cmd_route()
    async def handle_root(self) -> tuple[bool, str]:
        uid = str(getattr(self._message, 'sender_id', ''))
        if not uid:
            return False, "no user"
        info = await get_stream_info(self.stream_id)
        gid = str(info.get("group_id", "")) if isinstance(info, dict) else ""
        if not gid:
            await send_text("❌ 仅群聊可用", stream_id=self.stream_id)
            return False, "not group"

        from ..handlers.member_collector import get_nickname

        rankings = favor_manager.get_rankings(gid, 10)
        if not rankings:
            await send_text("📊 暂无好感度记录", stream_id=self.stream_id)
            return True, "ok"

        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        lines = ["💖 好感度排行", "━" * 16]
        for rank, rid, fav in rankings:
            medal = medals.get(rank, f"{rank}.")
            nick = get_nickname(gid, rid) or rid
            lines.append(f"{medal} {nick}: {fav}♡")
        lines.append("━" * 12)

        my_fav = favor_manager.get_favor(uid, gid)
        my_rank = favor_manager.get_user_rank(uid, gid)
        if my_rank:
            lines.append(f"💁 你: {my_fav}♡ 第{my_rank[0]}/{my_rank[1]}名")
        else:
            lines.append(f"💁 你: {my_fav}♡ (未上榜)")

        await send_text("\n".join(lines), stream_id=self.stream_id)
        return True, "ok"
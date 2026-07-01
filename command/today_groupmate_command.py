"""
今日群友 + 婚姻命令
"""

import random

from src.app.plugin_system.api.log_api import get_logger
from src.app.plugin_system.api.send_api import send_text
from src.app.plugin_system.base import BaseCommand, cmd_route
from src.app.plugin_system.types import PermissionLevel, ChatType
from src.app.plugin_system.api.stream_api import get_stream_info

from ..handlers.currency import currency_manager
from ..handlers.marriage_manager import marriage_manager
from ..handlers.member_collector import get_members, get_nickname

logger = get_logger("elysia_dice.groupmate")

MAX_SWAPS = 3
COSTS = [0, 10, 20]


def _get_ids(cmd) -> tuple[str, str]:
    """获取uid和gid"""
    uid = str(getattr(cmd._message, 'sender_id', ''))
    return uid, None if not uid else None


async def _get_gid(cmd) -> str:
    """异步获取gid"""
    info = await get_stream_info(cmd.stream_id)
    return str(info.get("group_id", "")) if isinstance(info, dict) else ""


def _build_pool(uid: str, gid: str) -> list[str]:
    """构建可选老婆池"""
    members = get_members(gid)
    return [
        m for m in members
        if m != uid
        and not marriage_manager.is_married(m, gid)
        and not marriage_manager.is_locked(m, gid)
    ]


# ═══════════════════════════════════════════════════
# 今日群友
# ═══════════════════════════════════════════════════

class TodayGroupmateCommand(BaseCommand):
    command_name = "今日群友"
    command_description = "随机抽取今日群友老婆"
    permission_level = PermissionLevel.USER
    chat_type = ChatType.GROUP

    @classmethod
    def match(cls, parts: list[str]) -> int:
        return 1 if parts and parts[0] in ("今日群友", "群友老婆", "群老婆") else 0

    @cmd_route()
    async def handle_root(self, action: str = "") -> tuple[bool, str]:
        uid = str(getattr(self._message, 'sender_id', ''))
        if not uid:
            return False, "no user"

        gid = await _get_gid(self)
        if not gid:
            await send_text("请在群聊中使用", stream_id=self.stream_id)
            return True, "no group"

        if action.strip() == "换":
            return await self._swap(uid, gid)
        return await self._pull(uid, gid)

    async def _pull(self, uid: str, gid: str) -> tuple[bool, str]:
        # 已结婚
        if marriage_manager.is_married(uid, gid):
            spouse = marriage_manager.get_spouse(uid, gid)
            name = get_nickname(gid, spouse) or f"<@{spouse}>"
            await send_text(f"你已经和 {name} 结婚啦~", stream_id=self.stream_id)
            return True, "married"

        # 已被锁定
        if marriage_manager.is_locked(uid, gid):
            partner = marriage_manager.get_locked(uid, gid)
            name = get_nickname(gid, partner) or f"<@{partner}>"
            await send_text(
                f"你今天已被 {name} 选为老婆了~\n"
                f"等待对方发送 /结婚 后，你再回复 /同意 或 /拒绝\n"
                f"你也可以 /今日群友 主动选择别人（会自动拒绝对方）",
                stream_id=self.stream_id
            )
            return True, "locked"

        # 已有锁定对象
        current = marriage_manager.get_locked(uid, gid)
        if current:
            name = get_nickname(gid, current) or f"<@{current}>"
            await send_text(
                f"今天的老婆: {name}\n"
                f"/今日群友 换 更换（{MAX_SWAPS}次）\n"
                f"/结婚 申请结婚",
                stream_id=self.stream_id
            )
            return True, "already"

        # 从成员池中选择
        pool = _build_pool(uid, gid)
        if not pool:
            members = get_members(gid)
            await send_text(
                f"可选老婆太少啦！\n"
                f"群成员: {len(members)} 人\n"
                f"多使用骰娘指令扩充候选池~",
                stream_id=self.stream_id
            )
            return True, "no pool"

        target = random.choice(pool)
        marriage_manager.lock(uid, target, gid)
        name = get_nickname(gid, target) or f"<@{target}>"

        await send_text(
            f"今日群友: {name}\n"
            f"候选池: {len(pool)} 人\n"
            f"/今日群友 换（{MAX_SWAPS}次）\n"
            f"/结婚 申请结婚",
            stream_id=self.stream_id
        )
        return True, "ok"

    async def _swap(self, uid: str, gid: str) -> tuple[bool, str]:
        if marriage_manager.is_married(uid, gid):
            await send_text("已婚不能更换~", stream_id=self.stream_id)
            return True, "married"

        current = marriage_manager.get_locked(uid, gid)
        if not current:
            return await self._pull(uid, gid)

        cnt = marriage_manager.get_swap_count(uid, gid)
        if cnt >= MAX_SWAPS:
            await send_text("今日更换次数已用完", stream_id=self.stream_id)
            return True, "max"

        cost = COSTS[cnt] if cnt < len(COSTS) else COSTS[-1]
        if cost > 0:
            bal = currency_manager.get_currency(uid, gid)
            if bal < cost:
                await send_text(f"花花不足 ({bal}/{cost})", stream_id=self.stream_id)
                return True, "no money"
            currency_manager.add_currency(uid, -cost, gid)

        # 解除旧锁定（也会清除对方的申请）
        marriage_manager.unlock(uid, gid)

        # 重新选择
        pool = _build_pool(uid, gid)
        if not pool:
            await send_text("没有其他可选的人了~", stream_id=self.stream_id)
            return True, "no pool"

        target = random.choice(pool)
        marriage_manager.lock(uid, target, gid)
        marriage_manager.increment_swap(uid, gid)
        name = get_nickname(gid, target) or f"<@{target}>"

        await send_text(
            f"已更换: {name}\n"
            f"花费 {cost}🌸\n"
            f"今日 {cnt + 1}/{MAX_SWAPS} 次",
            stream_id=self.stream_id
        )
        return True, "ok"


# ═══════════════════════════════════════════════════
# 结婚
# ═══════════════════════════════════════════════════

class ProposeCommand(BaseCommand):
    command_name = "结婚"
    command_description = "向今日群友老婆申请结婚"
    permission_level = PermissionLevel.USER
    chat_type = ChatType.GROUP

    @classmethod
    def match(cls, parts: list[str]) -> int:
        return 1 if parts and parts[0] in ("结婚", "申请结婚", "申请") else 0

    @cmd_route()
    async def handle_root(self) -> tuple[bool, str]:
        uid = str(getattr(self._message, 'sender_id', ''))
        if not uid:
            return False, "no user"

        gid = await _get_gid(self)
        if not gid:
            await send_text("请在群聊中使用", stream_id=self.stream_id)
            return True, "no group"

        # 已结婚
        if marriage_manager.is_married(uid, gid):
            spouse = marriage_manager.get_spouse(uid, gid)
            name = get_nickname(gid, spouse) or f"<@{spouse}>"
            await send_text(
                f"你已经结婚了~\n"
                f"你的老婆: {name}",
                stream_id=self.stream_id
            )
            return True, "married"

        # 已被别人锁定
        if marriage_manager.is_locked(uid, gid):
            locker = marriage_manager.get_locked(uid, gid)
            # 检查是不是双向锁定
            if marriage_manager.get_locked(locker, gid) == uid:
                # 双向锁，但uid是被动方，可以发起
                pass
            else:
                await send_text(
                    "你今天已经被别人选为老婆了~\n"
                    "等待对方的 /结婚 后回复 /同意 或 /拒绝",
                    stream_id=self.stream_id
                )
                return True, "locked"

        # 获取自己的锁定对象
        partner_id = marriage_manager.get_locked(uid, gid)
        if not partner_id:
            await send_text(
                "你还没有今日群友老婆~\n先使用 /今日群友",
                stream_id=self.stream_id
            )
            return True, "no_partner"

        # 对方已结婚
        if marriage_manager.is_married(partner_id, gid):
            await send_text("对方已经结婚了~", stream_id=self.stream_id)
            return True, "target_married"

        # 发起结婚申请
        result = marriage_manager.propose(uid, partner_id, gid)
        if result == "already_married":
            await send_text("你已经结婚了~", stream_id=self.stream_id)
        elif result == "not_locked":
            await send_text("只能和今日群友老婆结婚~", stream_id=self.stream_id)
        else:
            name = get_nickname(gid, partner_id) or f"<@{partner_id}>"
            await send_text(
                f"{name}，有人向你求婚啦！\n"
                f"回复 /同意 或 /拒绝",
                stream_id=self.stream_id
            )
        return True, "ok"


# ═══════════════════════════════════════════════════
# 同意
# ═══════════════════════════════════════════════════

class AcceptCommand(BaseCommand):
    command_name = "同意"
    command_description = "同意结婚申请"
    permission_level = PermissionLevel.USER
    chat_type = ChatType.GROUP

    @classmethod
    def match(cls, parts: list[str]) -> int:
        return 1 if parts and parts[0] in ("同意",) else 0

    @cmd_route()
    async def handle_root(self) -> tuple[bool, str]:
        uid = str(getattr(self._message, 'sender_id', ''))
        if not uid:
            return False, "no user"

        gid = await _get_gid(self)
        if not gid:
            await send_text("请在群聊中使用", stream_id=self.stream_id)
            return True, "no group"

        result = marriage_manager.accept(uid, gid)

        if result == "already_married":
            await send_text("你已经结婚了~", stream_id=self.stream_id)
        elif result == "no_proposal":
            await send_text("没有人向你求婚~", stream_id=self.stream_id)
        elif result == "not_locked":
            await send_text("对方已解除锁定，无法结婚", stream_id=self.stream_id)
        else:
            spouse = marriage_manager.get_spouse(uid, gid)
            name = get_nickname(gid, spouse) or f"<@{spouse}>"
            await send_text(
                f"恭喜！{name} 和你结婚啦！\n"
                f"婚姻关系持续到今天结束~",
                stream_id=self.stream_id
            )
        return True, result


# ═══════════════════════════════════════════════════
# 拒绝
# ═══════════════════════════════════════════════════

class RejectCommand(BaseCommand):
    command_name = "拒绝"
    command_description = "拒绝结婚申请"
    permission_level = PermissionLevel.USER
    chat_type = ChatType.GROUP

    @classmethod
    def match(cls, parts: list[str]) -> int:
        return 1 if parts and parts[0] in ("拒绝",) else 0

    @cmd_route()
    async def handle_root(self) -> tuple[bool, str]:
        uid = str(getattr(self._message, 'sender_id', ''))
        if not uid:
            return False, "no user"

        gid = await _get_gid(self)
        if not gid:
            await send_text("请在群聊中使用", stream_id=self.stream_id)
            return True, "no group"

        result = marriage_manager.reject(uid, gid)

        if result == "no_proposal":
            await send_text("没有人向你求婚~", stream_id=self.stream_id)
        else:
            await send_text(
                "你拒绝了求婚\n"
                "今天恢复自由身，可以等待新的 /今日群友",
                stream_id=self.stream_id
            )
        return True, "ok"
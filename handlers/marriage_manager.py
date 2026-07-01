"""
婚姻管理器 - 今日群友老婆 + 结婚系统
"""

import json
import time
from pathlib import Path

from src.app.plugin_system.api.log_api import get_logger

logger = get_logger("elysia_dice.marriage")

DATA_FILE = Path("data/elysia_dice/marriage.json")


def _load() -> dict:
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        if DATA_FILE.exists():
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save(data: dict):
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存婚姻数据失败: {e}")


def _get_date() -> str:
    return time.strftime("%Y%m%d")


class MarriageManager:
    """婚姻管理器
    数据结构:
    {
      "<gid>": {
        "_date": "20250101",
        "marriages": {"uid_a": "uid_b", "uid_b": "uid_a"},  # 已婚配对
        "locks": {"uid_a": "uid_b", "uid_b": "uid_a"},       # 锁定配对(双向)
        "proposals": {"uid_a": "uid_b"},                      # uid_a向uid_b求婚
        "swaps": {"uid": 3}                                   # 今日更换次数
      }
    }
    """

    def __init__(self):
        self._data = None

    @property
    def data(self) -> dict:
        if self._data is None:
            try:
                self._data = self._cleanup(_load())
            except Exception as e:
                logger.error(f"加载婚姻数据失败: {e}")
                self._data = {}
        if not isinstance(self._data, dict):
            self._data = {}
        return self._data

    def _cleanup(self, data: dict) -> dict:
        """新的一天清除所有婚姻关系"""
        today = _get_date()
        for gid in list(data.keys()):
            if not isinstance(data[gid], dict) or data[gid].get("_date") != today:
                data[gid] = {"_date": today}
        return data

    def _group(self, group_id: str) -> dict:
        """获取群组数据，不存在则创建"""
        g = self.data.setdefault(group_id, {"_date": _get_date()})
        if not isinstance(g, dict):
            self.data[group_id] = g = {"_date": _get_date()}
        return g

    def _save(self):
        _save(self.data)

    # ═══════════════════════════════════════════════════
    # 已婚
    # ═══════════════════════════════════════════════════

    def is_married(self, user_id: str, group_id: str) -> bool:
        return user_id in self._group(group_id).get("marriages", {})

    def get_spouse(self, user_id: str, group_id: str) -> str | None:
        return self._group(group_id).get("marriages", {}).get(user_id)

    def marry(self, uid_a: str, uid_b: str, group_id: str):
        """建立婚姻"""
        g = self._group(group_id)
        m = g.setdefault("marriages", {})
        m[uid_a] = uid_b
        m[uid_b] = uid_a
        # 清除锁定和申请
        g.pop("locks", None)
        g.pop("proposals", None)
        self._save()

    # ═══════════════════════════════════════════════════
    # 锁定
    # ═══════════════════════════════════════════════════

    def is_locked(self, user_id: str, group_id: str) -> bool:
        return user_id in self._group(group_id).get("locks", {})

    def get_locked(self, user_id: str, group_id: str) -> str | None:
        """获取user_id被谁锁定"""
        return self._group(group_id).get("locks", {}).get(user_id)

    def lock(self, uid_a: str, uid_b: str, group_id: str):
        """A锁定B（双向），如果B之前锁定了别人，则先解除"""
        g = self._group(group_id)
        locks = g.setdefault("locks", {})

        # 如果B已有锁定且是被别人锁定的（不等同于双向），清除旧的
        # 实际上是双向锁，直接覆盖即可
        old_a = locks.pop(uid_b, None)  # B之前锁定的对象
        if old_a and old_a != uid_a:
            locks.pop(old_a, None)  # 清除旧对象对B的锁定

        # 如果B是主动锁定别人的（B→X），清除B→X
        for k, v in list(locks.items()):
            if k == uid_b and v != uid_a:
                locks.pop(v, None)

        locks[uid_a] = uid_b
        locks[uid_b] = uid_a
        self._save()

    def unlock(self, uid: str, group_id: str):
        """解除锁定"""
        g = self._group(group_id)
        locks = g.get("locks", {})
        partner = locks.pop(uid, None)
        if partner:
            locks.pop(partner, None)
        # 同时清除申请
        g.pop("proposals", None)
        self._save()

    # ═══════════════════════════════════════════════════
    # 申请
    # ═══════════════════════════════════════════════════

    def propose(self, uid_a: str, uid_b: str, group_id: str) -> str:
        """发起结婚申请
        Returns: "ok" | "not_locked" | "already_married"
        """
        g = self._group(group_id)

        if self.is_married(uid_a, group_id):
            return "already_married"
        if self.is_married(uid_b, group_id):
            return "target_married"

        # 必须是锁定关系
        if self.get_locked(uid_a, group_id) != uid_b:
            return "not_locked"

        g.setdefault("proposals", {})[uid_a] = uid_b
        self._save()
        return "ok"

    def has_proposal(self, user_id: str, group_id: str) -> str | None:
        """查看谁向user_id求婚了，返回求婚者ID"""
        proposals = self._group(group_id).get("proposals", {})
        for a, b in proposals.items():
            if b == user_id:
                return a
        return None

    def accept(self, user_id: str, group_id: str) -> str:
        """同意结婚请求
        Returns: "ok" | "no_proposal" | "already_married"
        """
        g = self._group(group_id)

        if self.is_married(user_id, group_id):
            return "already_married"

        proposer = self.has_proposal(user_id, group_id)
        if not proposer:
            return "no_proposal"

        # 必须是锁定关系
        if g.get("locks", {}).get(proposer) != user_id:
            return "not_locked"

        self.marry(proposer, user_id, group_id)
        return "ok"

    def reject(self, user_id: str, group_id: str) -> str:
        """拒绝结婚请求
        Returns: "ok" | "no_proposal"
        """
        g = self._group(group_id)
        proposals = g.get("proposals", {})

        proposer = None
        for a, b in proposals.items():
            if b == user_id:
                proposer = a
                break

        if not proposer:
            return "no_proposal"

        self.unlock(proposer, group_id)
        return "ok"

    # ═══════════════════════════════════════════════════
    # 更换次数
    # ═══════════════════════════════════════════════════

    def get_swap_count(self, user_id: str, group_id: str) -> int:
        return self._group(group_id).get("swaps", {}).get(user_id, 0)

    def increment_swap(self, user_id: str, group_id: str):
        g = self._group(group_id)
        s = g.setdefault("swaps", {})
        s[user_id] = s.get(user_id, 0) + 1
        self._save()

    # ═══════════════════════════════════════════════════
    # 开发者重置
    # ═══════════════════════════════════════════════════

    def reset_user(self, user_id: str, group_id: str):
        """重置用户在本群的所有婚姻相关数据"""
        g = self._group(group_id)
        for key in ("marriages", "locks", "proposals", "swaps"):
            d = g.get(key, {})
            if user_id in d:
                partner = d.pop(user_id)
                if key in ("marriages", "locks") and partner in d:
                    d.pop(partner)
        self._save()


marriage_manager = MarriageManager()
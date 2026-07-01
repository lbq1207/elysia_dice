"""
好感度管理器
"""
import json
import random
import time
from pathlib import Path
from src.app.plugin_system.api.log_api import get_logger

logger = get_logger("elysia_dice.favor")
DATA_FILE = Path("data/elysia_dice/favor.json")

ITEM_FAVOR_MAP = {
    "蒸蛋": (6, (1, 3)),
    "薯条": (13, (1, 3)),
    "培根": (16, (1, 6)),
    "早餐面包": (22, (1, 8)),
    "冰镇西瓜": (27, (1, 8)),
    "草莓蛋糕": (31, (1, 10)),
    "速冻饺子": (40, (1, 15)),
    "芋泥奶茶": (43, (1, 16)),
}
FLOWER_FAVOR_RATE = 1


def _load() -> dict:
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        if DATA_FILE.exists():
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        return {}


def _save(data: dict):
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存失败: {e}")


def should_reset(group_data: dict) -> bool:
    today = int(time.strftime("%d"))
    last_reset = group_data.get("_reset_day", 0)
    return today in (1, 16) and last_reset != today


class FavorManager:
    def __init__(self):
        self._data = None

    @property
    def data(self) -> dict:
        if self._data is None:
            self._data = _load()
        return self._data

    def _save(self):
        _save(self.data)

    def _cleanup(self, group_id: str):
        g = self.data.setdefault(group_id, {})
        if should_reset(g):
            logger.info(f"📅 好感度重置: 群 {group_id}")
            self.data[group_id] = {"_reset_day": int(time.strftime("%d"))}
            self._save()

    def get_favor(self, user_id: str, group_id: str) -> int:
        self._cleanup(group_id)
        return self.data.get(group_id, {}).get(str(user_id), 0)

    def add_favor(self, user_id: str, amount: int, group_id: str) -> int:
        self._cleanup(group_id)
        g = self.data.setdefault(group_id, {"_reset_day": int(time.strftime("%d"))})
        uid = str(user_id)
        g[uid] = g.get(uid, 0) + amount
        self._save()
        return g[uid]

    def get_rankings(self, group_id: str, top_n: int = 10) -> list[tuple[int, str, int]]:
        self._cleanup(group_id)
        g = self.data.get(group_id, {})
        users = [(uid, fav) for uid, fav in g.items() if not uid.startswith("_") and fav > 0]
        users.sort(key=lambda x: x[1], reverse=True)
        if not users:
            return []
        rankings = []
        rank = 1
        prev_fav = None
        for i, (uid, fav) in enumerate(users):
            if fav != prev_fav:
                rank = i + 1
                prev_fav = fav
            if rank <= top_n:
                rankings.append((rank, uid, fav))
        return rankings

    def get_user_rank(self, user_id: str, group_id: str) -> tuple[int, int] | None:
        self._cleanup(group_id)
        g = self.data.get(group_id, {})
        users = [(uid, fav) for uid, fav in g.items() if not uid.startswith("_") and fav > 0]
        users.sort(key=lambda x: x[1], reverse=True)
        uid = str(user_id)
        total = len(users)
        prev_fav = None
        rank = 0
        for i, (u, fav) in enumerate(users):
            if fav != prev_fav:
                rank = i + 1
                prev_fav = fav
            if u == uid:
                return (rank, total)
        return None

    def calc_gift_favor(self, item_name: str, quantity: int = 1) -> tuple[bool, str, int, list[str]]:
        from .shop import ITEM_ALIASES
        result = ITEM_ALIASES.get(item_name)
        if not result:
            for key in ITEM_ALIASES:
                if item_name in key or key in item_name:
                    result = ITEM_ALIASES[key]
                    break
        if not result:
            return False, item_name, 0, []
        full_name, _ = result
        favor_info = ITEM_FAVOR_MAP.get(full_name)
        if not favor_info:
            return False, full_name, 0, []
        base, (rmin, rmax) = favor_info
        total = 0
        details = []
        for i in range(quantity):
            bonus = random.randint(rmin, rmax) if rmax > rmin else 0
            item_favor = base + bonus
            total += item_favor
            if quantity > 1:
                details.append(f"  第{i+1}件: {base}+{bonus}={item_favor}♡")
        return True, full_name, total, details

    def calc_flower_favor(self, amount: int) -> int:
        return amount * FLOWER_FAVOR_RATE


favor_manager = FavorManager()
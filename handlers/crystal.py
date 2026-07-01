"""
水晶货币管理器
水晶：特殊货币，不可赠送，可转让，不在个人界面显示，可通过开发者工具修改，永不过期
"""

import json
from pathlib import Path
from typing import Optional

from src.app.plugin_system.api.log_api import get_logger

logger = get_logger("elysia_dice.crystal")

# 与 dev_tools.py 一致的分群开关
SEPARATE_BY_GROUP = True

# 每日获取水晶数量
DAILY_CRYSTAL_AMOUNT = 42000


def _make_key(user_id: str, group_id: str = "") -> str:
    """生成存储key"""
    if SEPARATE_BY_GROUP and group_id:
        return f"{group_id}:{user_id}"
    return user_id


class CrystalManager:
    """水晶管理器"""

    def __init__(self):
        self.data_dir = Path("data/elysia_dice")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.crystal_file = self.data_dir / "crystal.json"
        self.daily_crystal_file = self.data_dir / "daily_crystal.json"
        self.crystal_data = self._load_json(self.crystal_file)
        self.daily_crystal_data = self._load_json(self.daily_crystal_file)

    def _load_json(self, file_path: Path) -> dict:
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载数据失败 {file_path}: {e}")
        return {}

    def _save_json(self, file_path: Path, data: dict) -> bool:
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存数据失败 {file_path}: {e}")
            return False

    # ========== 水晶数量操作 ==========

    def get_crystal(self, user_id: str, group_id: str = "") -> int:
        """获取水晶数量"""
        key = _make_key(user_id, group_id)
        return self.crystal_data.get(key, {}).get("crystal", 0)

    def set_crystal(self, user_id: str, amount: int, group_id: str = "") -> bool:
        """设置水晶数量"""
        key = _make_key(user_id, group_id)
        if key not in self.crystal_data:
            self.crystal_data[key] = {}
        old = self.crystal_data[key].get("crystal", 0)
        self.crystal_data[key]["crystal"] = max(0, amount)
        self._save_json(self.crystal_file, self.crystal_data)
        scope = f"群{group_id}" if (SEPARATE_BY_GROUP and group_id) else "全局"
        logger.info(f"设置用户 {user_id}({scope}) 水晶: {old} -> {amount}")
        return True

    def add_crystal(self, user_id: str, amount: int, group_id: str = "") -> int:
        """增减水晶，返回新数量"""
        current = self.get_crystal(user_id, group_id)
        new_amount = max(0, current + amount)
        self.set_crystal(user_id, new_amount, group_id)
        return new_amount

    def has_enough_crystal(self, user_id: str, amount: int, group_id: str = "") -> bool:
        """检查水晶是否足够"""
        return self.get_crystal(user_id, group_id) >= amount

    def reset_crystal(self, user_id: str, group_id: str = "") -> bool:
        """重置指定用户水晶"""
        return self.set_crystal(user_id, 0, group_id)

    def reset_all_crystal(self, group_id: str = "") -> int:
        """重置所有用户水晶"""
        count = 0
        if SEPARATE_BY_GROUP and group_id:
            prefix = f"{group_id}:"
            for key in list(self.crystal_data.keys()):
                if key.startswith(prefix):
                    self.crystal_data[key]["crystal"] = 0
                    count += 1
        else:
            for key in list(self.crystal_data.keys()):
                self.crystal_data[key]["crystal"] = 0
                count += 1
        self._save_json(self.crystal_file, self.crystal_data)
        scope = f"群{group_id}" if (SEPARATE_BY_GROUP and group_id) else "全局"
        logger.info(f"已重置 {scope} {count} 个用户的水晶")
        return count

    # ========== 每日获取水晶 ==========

    def can_get_daily_crystal(self, user_id: str, group_id: str = "") -> bool:
        """检查今日是否已领取"""
        import datetime
        key = _make_key(user_id, group_id)
        today = datetime.date.today().isoformat()
        last_date = self.daily_crystal_data.get(key, {}).get("date", "")
        return last_date != today

    def claim_daily_crystal(self, user_id: str, group_id: str = "") -> int:
        """领取每日水晶，返回本次领取数量（0代表已领取）"""
        import datetime
        key = _make_key(user_id, group_id)
        today = datetime.date.today().isoformat()  # ← 加 .isoformat()

        if not self.can_get_daily_crystal(user_id, group_id):
            return 0  # 已领取

        # 记录领取日期
        self.daily_crystal_data[key] = {"date": today}  # ← 直接用字符串，不要再 .isoformat()
        self._save_json(self.daily_crystal_file, self.daily_crystal_data)

        # 增加水晶
        new_balance = self.add_crystal(user_id, DAILY_CRYSTAL_AMOUNT, group_id)
        logger.info(f"用户 {user_id}({group_id}) 领取每日水晶 {DAILY_CRYSTAL_AMOUNT}，余额 {new_balance}")
        return DAILY_CRYSTAL_AMOUNT

    def reset_daily_claim(self, user_id: str, group_id: str = "") -> bool:
        """重置指定用户的每日领取状态（开发者用）"""
        key = _make_key(user_id, group_id)
        if key in self.daily_crystal_data:
            del self.daily_crystal_data[key]
            self._save_json(self.daily_crystal_file, self.daily_crystal_data)
            return True
        return False

    def reset_all_daily(self, group_id: str = "") -> int:
        """重置所有用户的每日领取状态"""
        count = 0
        if SEPARATE_BY_GROUP and group_id:
            prefix = f"{group_id}:"
            for key in list(self.daily_crystal_data.keys()):
                if key.startswith(prefix):
                    del self.daily_crystal_data[key]
                    count += 1
        else:
            count = len(self.daily_crystal_data)
            self.daily_crystal_data.clear()
        self._save_json(self.daily_crystal_file, self.daily_crystal_data)
        scope = f"群{group_id}" if (SEPARATE_BY_GROUP and group_id) else "全局"
        logger.info(f"已重置 {scope} {count} 个用户的每日水晶领取状态")
        return count


crystal_manager = CrystalManager()
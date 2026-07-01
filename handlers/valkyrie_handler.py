"""
女武神系统处理器 - 抽取女武神、今日女武神、图鉴、结婚、今日群友
"""

import random
import json
from pathlib import Path
from datetime import date
from typing import Optional

from src.app.plugin_system.api.log_api import get_logger

from ..data.valkyrie_data import (
    ALL_VALKYRIE_POOL, VALKYRIES, DOLLS, SYNERGISTS,
    VALKYRIE_BY_ID, VALKYRIE_BY_NAME,
)

logger = get_logger("elysia_dice.valkyrie_handler")


def _make_key(user_id: str, group_id: str = "") -> str:
    if group_id:
        return f"{group_id}:{user_id}"
    return user_id


class ValkyrieHandler:
    """女武神系统处理器"""

    def __init__(self):
        self.data_dir = Path("data/elysia_dice")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 女武神收集数据
        self.collection_file = self.data_dir / "valkyrie_collection.json"
        self.collection_data = self._load_json(self.collection_file)
        
        # 今日女武神数据
        self.today_valkyrie_file = self.data_dir / "today_valkyrie.json"
        self.today_valkyrie_data = self._load_json(self.today_valkyrie_file)
        
        # 抽取次数数据
        self.pull_record_file = self.data_dir / "valkyrie_pull_record.json"
        self.pull_record_data = self._load_json(self.pull_record_file)
        
        # 结婚数据
        self.marriage_file = self.data_dir / "marriage.json"
        self.marriage_data = self._load_json(self.marriage_file)
        
        # 今日群友数据
        self.today_groupmate_file = self.data_dir / "today_groupmate.json"
        self.today_groupmate_data = self._load_json(self.today_groupmate_file)

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

    def _get_today(self) -> str:
        return date.today().isoformat()

    def _get_daily_key(self, user_id: str, group_id: str, prefix: str) -> str:
        base = _make_key(user_id, group_id)
        return f"{base}:{prefix}:{self._get_today()}"

    # ========== 抽取女武神 ==========
    def random_valkyrie(self) -> tuple:
        """随机抽取一个女武神/人偶/协同者"""
        return random.choice(ALL_VALKYRIE_POOL)

    def can_pull_valkyrie(self, user_id: str, group_id: str) -> tuple[bool, int, int]:
        """检查是否可以抽取女武神，返回(可抽, 今日已抽次数, 剩余免费次数)"""
        key = self._get_daily_key(user_id, group_id, "pull_count")
        pull_data = self.today_valkyrie_data.get(key, {"count": 0, "free_used": False})
        count = pull_data.get("count", 0)
        free_used = pull_data.get("free_used", False)
        
        max_pulls = 10
        remaining = max_pulls - count
        
        return (remaining > 0, count, 0 if free_used else 1)

    def get_pull_cost(self, pull_count: int) -> int:
        """获取抽取花费（花花）"""
        if pull_count == 0:
            return 0  # 首次免费
        elif pull_count == 1:
            return 5  # 第2次
        else:
            return 10  # 第3-10次

    def do_pull_valkyrie(self, user_id: str, group_id: str) -> dict:
        """执行抽取女武神"""
        can_pull, count, free_remaining = self.can_pull_valkyrie(user_id, group_id)
        
        if not can_pull:
            return {"error": "今日抽取次数已用完（最多10次）"}
        
        cost = self.get_pull_cost(count)
        
        # 随机抽取
        result = self.random_valkyrie()
        
        # 更新抽取记录
        key = self._get_daily_key(user_id, group_id, "pull_count")
        new_count = count + 1
        free_used = cost == 0 or (count == 0)
        
        self.today_valkyrie_data[key] = {
            "count": new_count,
            "free_used": free_used or (self.today_valkyrie_data.get(key, {}).get("free_used", False))
        }
        self._save_json(self.today_valkyrie_file, self.today_valkyrie_data)
        
        # 更新抽到次数
        self._add_pull_record(user_id, group_id, result)
        
        return {
            "valkyrie": result,
            "cost": cost,
            "pull_number": new_count,
            "is_free": cost == 0,
        }
    
    def _add_pull_record(self, user_id: str, group_id: str, valkyrie: tuple):
        """记录抽到次数"""
        base = _make_key(user_id, group_id)
        v_id = str(valkyrie[0])
        
        if base not in self.pull_record_data:
            self.pull_record_data[base] = {}
        if v_id not in self.pull_record_data[base]:
            self.pull_record_data[base][v_id] = 0
        
        self.pull_record_data[base][v_id] += 1
        self._save_json(self.pull_record_file, self.pull_record_data)

    def get_pull_count(self, user_id: str, group_id: str, valkyrie_id: int) -> int:
        """获取被抽到次数"""
        base = _make_key(user_id, group_id)
        return self.pull_record_data.get(base, {}).get(str(valkyrie_id), 0)

    # ========== 今日女武神 ==========
    def get_today_valkyries(self, user_id: str, group_id: str) -> list:
        """获取今日设置的女武神"""
        key = self._get_daily_key(user_id, group_id, "today")
        return self.today_valkyrie_data.get(key, {}).get("valkyries", [])

    def set_today_valkyrie(self, user_id: str, group_id: str, valkyrie_query: str) -> dict:
        """设置今日女武神"""
        # 查找女武神
        valkyrie = self._find_valkyrie(valkyrie_query)
        if not valkyrie:
            return {"error": f"未找到女武神「{valkyrie_query}」"}
        
        key = self._get_daily_key(user_id, group_id, "today")
        today_data = self.today_valkyrie_data.get(key, {"valkyries": [], "count": 0})
        valkyries = today_data.get("valkyries", [])
        count = today_data.get("count", 0)
        
        # 检查数量
        if count >= 3:
            return {"error": "今日已设置3个女武神（已达上限）"}
        
        # 检查是否已设置
        for v in valkyries:
            if v["id"] == valkyrie[0]:
                return {"error": f"「{valkyrie[1]}」已经是今日女武神"}
        
        valkyries.append({
            "id": valkyrie[0],
            "name": valkyrie[1],
        })
        
        self.today_valkyrie_data[key] = {
            "valkyries": valkyries,
            "count": count + 1,
        }
        self._save_json(self.today_valkyrie_file, self.today_valkyrie_data)
        
        # 更新被设置次数
        self._add_set_record(user_id, group_id, valkyrie)
        
        return {"success": True, "valkyrie": valkyrie, "current_count": count + 1}
    
    def _add_set_record(self, user_id: str, group_id: str, valkyrie: tuple):
        """记录被设置为今日女武神次数"""
        base = _make_key(user_id, group_id)
        v_id = str(valkyrie[0])
        
        if base not in self.pull_record_data:
            self.pull_record_data[base] = {}
        set_key = f"{v_id}_set"
        if set_key not in self.pull_record_data[base]:
            self.pull_record_data[base][set_key] = 0
        
        self.pull_record_data[base][set_key] += 1
        self._save_json(self.pull_record_file, self.pull_record_data)

    def get_set_count(self, user_id: str, group_id: str, valkyrie_id: int) -> int:
        """获取被设置次数"""
        base = _make_key(user_id, group_id)
        return self.pull_record_data.get(base, {}).get(f"{valkyrie_id}_set", 0)

    # ========== 图鉴 ==========
    def get_full_collection(self) -> list:
        """获取全图鉴"""
        return {
            "valkyries": VALKYRIES,
            "dolls": DOLLS,
            "synergists": SYNERGISTS,
            "total": len(VALKYRIES) + len(DOLLS) + len(SYNERGISTS),
        }

    def get_user_collection(self, user_id: str, group_id: str) -> dict:
        """获取用户收集程度"""
        base = _make_key(user_id, group_id)
        collection = self.collection_data.get(base, {})
        
        owned_valkyries = collection.get("valkyries", [])
        owned_dolls = collection.get("dolls", [])
        owned_synergists = collection.get("synergists", [])
        
        total_owned = len(owned_valkyries) + len(owned_dolls) + len(owned_synergists)
        total_all = len(VALKYRIES) + len(DOLLS) + len(SYNERGISTS)
        
        return {
            "owned_valkyries": owned_valkyries,
            "owned_dolls": owned_dolls,
            "owned_synergists": owned_synergists,
            "total_owned": total_owned,
            "total_all": total_all,
            "percentage": round(total_owned / total_all * 100, 1) if total_all > 0 else 0,
        }

    def has_valkyrie_before(self, user_id: str, group_id: str, valkyrie_id: int) -> bool:
        """检查用户是否已拥有该女武神/人偶/协同者"""
        base = _make_key(user_id, group_id)
        collection = self.collection_data.get(base, {"valkyries": [], "dolls": [], "synergists": []})
        
        if valkyrie_id < 200:
            return valkyrie_id in collection.get("valkyries", [])
        elif valkyrie_id < 900:
            return valkyrie_id in collection.get("dolls", [])
        else:
            return valkyrie_id in collection.get("synergists", [])

    def add_to_collection(self, user_id: str, group_id: str, valkyrie: tuple, valkyrie_type: str):
        """添加到图鉴"""
        base = _make_key(user_id, group_id)
        if base not in self.collection_data:
            self.collection_data[base] = {"valkyries": [], "dolls": [], "synergists": []}
        
        v_id = valkyrie[0]  # 直接用 int，不转字符串
        
        if valkyrie_type == "valkyrie":
            if v_id not in self.collection_data[base]["valkyries"]:
                self.collection_data[base]["valkyries"].append(v_id)
        elif valkyrie_type == "doll":
            if v_id not in self.collection_data[base]["dolls"]:
                self.collection_data[base]["dolls"].append(v_id)
        elif valkyrie_type == "synergist":
            if v_id not in self.collection_data[base]["synergists"]:
                self.collection_data[base]["synergists"].append(v_id)
        
        self._save_json(self.collection_file, self.collection_data)

    # ========== 查询女武神 ==========
    def _find_valkyrie(self, query: str) -> Optional[tuple]:
        """根据ID或名称查找女武神"""
        # 尝试ID查找
        try:
            v_id = int(query)
            if v_id in VALKYRIE_BY_ID:
                return VALKYRIE_BY_ID[v_id]
        except ValueError:
            pass
        
        # 名称查找
        if query in VALKYRIE_BY_NAME:
            return VALKYRIE_BY_NAME[query]
        
        # 模糊查找
        query_lower = query.lower()
        for v in ALL_VALKYRIE_POOL:
            if query_lower in v[1].lower():
                return v
        
        return None

    def query_valkyrie(self, user_id: str, group_id: str, query: str) -> dict:
        """查询女武神信息"""
        valkyrie = self._find_valkyrie(query)
        if not valkyrie:
            return {"error": f"未找到女武神「{query}」"}
        
        pull_count = self.get_pull_count(user_id, group_id, valkyrie[0])
        set_count = self.get_set_count(user_id, group_id, valkyrie[0])
        
        result = {
            "found": True,
            "valkyrie": valkyrie,
            "pull_count": pull_count,
            "set_count": set_count,
        }
        
        return result

    # ========== 重置 ==========
    def reset_valkyrie(self, user_id: str, group_id: str) -> bool:
        """重置女武神数据"""
        base = _make_key(user_id, group_id)
        # 清除今日数据
        for key in list(self.today_valkyrie_data.keys()):
            if key.startswith(f"{base}:pull_count:") or key.startswith(f"{base}:today:"):
                del self.today_valkyrie_data[key]
        self._save_json(self.today_valkyrie_file, self.today_valkyrie_data)
        return True
    
    def reset_collection(self, user_id: str, group_id: str) -> bool:
        """重置指定用户的女武神图鉴"""
        base = _make_key(user_id, group_id)
        if base in self.collection_data:
            del self.collection_data[base]
            self._save_json(self.collection_file, self.collection_data)
        return True

    def reset_all_collection(self, group_id: str = "") -> int:
        """重置所有用户的女武神图鉴"""
        count = 0
        if group_id:
            prefix = f"{group_id}:"
            keys_to_delete = [k for k in self.collection_data if k.startswith(prefix)]
        else:
            keys_to_delete = list(self.collection_data.keys())

        for key in keys_to_delete:
            del self.collection_data[key]
            count += 1

        if count > 0:
            self._save_json(self.collection_file, self.collection_data)
        return count

    def reset_pull_records(self, user_id: str, group_id: str) -> bool:
        """重置指定用户的女武神抽取记录（累计次数+今日次数）"""
        base = _make_key(user_id, group_id)

        # 清除累计抽取记录
        if base in self.pull_record_data:
            del self.pull_record_data[base]
            self._save_json(self.pull_record_file, self.pull_record_data)

        return True

    def reset_all_pull_records(self, group_id: str = "") -> int:
        """重置所有用户的女武神抽取记录"""
        count = 0
        if group_id:
            prefix = f"{group_id}:"
            keys_to_delete = [k for k in self.pull_record_data if k.startswith(prefix)]
        else:
            keys_to_delete = list(self.pull_record_data.keys())

        for key in keys_to_delete:
            del self.pull_record_data[key]
            count += 1

        if count > 0:
            self._save_json(self.pull_record_file, self.pull_record_data)
        return count

    def reset_all_valkyrie(self, group_id: str = "") -> int:
        """重置所有用户的所有女武神数据（图鉴+抽取记录+今日女武神）"""
        # 重置图鉴
        collection_count = self.reset_all_collection(group_id)

        # 重置抽取记录
        pull_count = self.reset_all_pull_records(group_id)

        # 重置今日女武神
        today_count = 0
        today_keys = list(self.today_valkyrie_data.keys())
        for key in today_keys:
            if not group_id or key.startswith(f"{group_id}:"):
                del self.today_valkyrie_data[key]
                today_count += 1
        if today_count > 0:
            self._save_json(self.today_valkyrie_file, self.today_valkyrie_data)

        return max(collection_count, pull_count, today_count)


valkyrie_handler = ValkyrieHandler()
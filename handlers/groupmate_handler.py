"""
群友老婆管理器
"""

import json
import time
from pathlib import Path
from src.app.plugin_system.api.log_api import get_logger

logger = get_logger("elysia_dice.groupmate_handler")


def _make_key(user_id: str, group_id: str) -> str:
    if group_id:
        return f"{group_id}:{user_id}"
    return user_id


def _get_date() -> str:
    """获取当前日期字符串"""
    return time.strftime("%Y%m%d")


class GroupmateHandler:
    """群友老婆管理器"""
    
    def __init__(self):
        self.data_dir = Path("data/elysia_dice")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 今日群友记录 {group_id:user_id: {target, date, swap_count}}
        self.groupmate_file = self.data_dir / "groupmate.json"
        self._groupmate_data = self._load(self.groupmate_file)
        
        # 群成员缓存 {group_id: [user_ids]}
        self.member_cache_file = self.data_dir / "member_cache.json"
        self._member_cache = self._load(self.member_cache_file)
        
        # 每日清理
        self._cleanup_daily()
    
    def _load(self, file_path: Path) -> dict:
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载数据失败 {file_path}: {e}")
        return {}
    
    def _save(self, file_path: Path, data: dict):
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存数据失败 {file_path}: {e}")
    
    def _cleanup_daily(self):
        """清理过期的每日数据"""
        today = _get_date()
        cleaned = False
        
        keys_to_delete = []
        for key, value in self._groupmate_data.items():
            if isinstance(value, dict) and value.get("date") != today:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self._groupmate_data[key]
            cleaned = True
        
        if cleaned:
            self._save(self.groupmate_file, self._groupmate_data)
    
    # ==================== 群成员缓存 ====================
    
    def cache_members(self, group_id: str, member_ids: list[str]):
        """缓存群成员列表"""
        self._member_cache[group_id] = {
            "members": member_ids,
            "timestamp": time.time()
        }
        self._save(self.member_cache_file, self._member_cache)
    
    def get_cached_members(self, user_id: str, group_id: str) -> list[str]:
        """获取缓存的群成员列表"""
        cache = self._member_cache.get(group_id, {})
        members = cache.get("members", [])
        if not members:
            # 如果没有缓存，用假数据
            members = [user_id, f"fake_{user_id}_1", f"fake_{user_id}_2"]
        return members
    
    def get_member_name(self, user_id: str, group_id: str) -> str:
        """获取成员名称"""
        cache = self._member_cache.get(group_id, {})
        members = cache.get("members", [])
        # 尝试从缓存中找到该用户的信息
        for m in members:
            if str(m) == str(user_id):
                return str(m)
        return str(user_id)
    
    # ==================== 今日群友 ====================
    
    def get_today_groupmate(self, user_id: str, group_id: str) -> str:
        """获取今日群友"""
        key = _make_key(user_id, group_id)
        record = self._groupmate_data.get(key, {})
        if record.get("date") == _get_date():
            return record.get("target", "")
        return ""
    
    def set_today_groupmate(self, user_id: str, group_id: str, target_id: str):
        """设置今日群友"""
        key = _make_key(user_id, group_id)
        old_record = self._groupmate_data.get(key, {})
        
        self._groupmate_data[key] = {
            "target": target_id,
            "date": _get_date(),
            "swap_count": old_record.get("swap_count", 0),
        }
        self._save(self.groupmate_file, self._groupmate_data)
    
    def get_swap_count(self, user_id: str, group_id: str) -> int:
        """获取今日更换次数"""
        key = _make_key(user_id, group_id)
        record = self._groupmate_data.get(key, {})
        if record.get("date") == _get_date():
            return record.get("swap_count", 0)
        return 0
    
    def increment_swap_count(self, user_id: str, group_id: str):
        """增加更换次数"""
        key = _make_key(user_id, group_id)
        record = self._groupmate_data.get(key, {})
        if record.get("date") == _get_date():
            record["swap_count"] = record.get("swap_count", 0) + 1
            self._groupmate_data[key] = record
            self._save(self.groupmate_file, self._groupmate_data)
    
    # ==================== 婚姻/被选状态 ====================
    
    def get_married_target(self, user_id: str, group_id: str) -> str:
        """获取用户选中的群友（已婚对象）"""
        return self.get_today_groupmate(user_id, group_id)
    
    def is_claimed_by_others(self, user_id: str, group_id: str) -> bool:
        """检查用户是否已被其他人选为群友"""
        today = _get_date()
        for key, record in self._groupmate_data.items():
            if not isinstance(record, dict):
                continue
            if record.get("date") != today:
                continue
            if record.get("target") == user_id:
                return True
        return False
    
    def get_claimer(self, user_id: str, group_id: str) -> str:
        """获取选中了该用户的人"""
        today = _get_date()
        for key, record in self._groupmate_data.items():
            if not isinstance(record, dict):
                continue
            if record.get("date") != today:
                continue
            if record.get("target") == user_id:
                # 从 key 中提取用户ID
                # key 格式: group_id:user_id
                parts = key.rsplit(":", 1)
                return parts[-1] if len(parts) > 1 else ""
        return ""
    
    # ==================== 重置 ====================
    
    def reset_groupmate(self, user_id: str, group_id: str):
        """重置指定用户的今日群友"""
        key = _make_key(user_id, group_id)
        if key in self._groupmate_data:
            del self._groupmate_data[key]
            self._save(self.groupmate_file, self._groupmate_data)
    
    def reset_all_groupmate(self, group_id: str = "") -> int:
        """重置所有用户的今日群友"""
        count = 0
        prefix = f"{group_id}:" if group_id else ""
        keys_to_delete = [k for k in self._groupmate_data if k.startswith(prefix)]
        
        for key in keys_to_delete:
            del self._groupmate_data[key]
            count += 1
        
        if count > 0:
            self._save(self.groupmate_file, self._groupmate_data)
        return count
    
    def reset_swap_count(self, user_id: str, group_id: str):
        """仅重置抽取次数"""
        key = _make_key(user_id, group_id)
        if key in self._groupmate_data:
            self._groupmate_data[key]["swap_count"] = 0
            self._save(self.groupmate_file, self._groupmate_data)
    
    def clear_relationship(self, user_id: str, group_id: str) -> dict:
        """清除指定用户的群友关系（保留抽取次数）
        
        Returns:
            dict: {
                "target": str,        # 被选中的群友
                "mutual_cleared": bool,  # 是否解除了相互锁定
            }
        """
        key = _make_key(user_id, group_id)
        result = {}
        
        if key in self._groupmate_data:
            record = self._groupmate_data[key]
            target = record.get("target", "")
            
            if target:
                result["target"] = target
                # 检查对方是否也选了自己
                target_key = _make_key(target, group_id)
                if target_key in self._groupmate_data:
                    target_record = self._groupmate_data[target_key]
                    if target_record.get("target") == user_id:
                        # 相互锁定，清除双方
                        del self._groupmate_data[target_key]
                        result["mutual_cleared"] = True
            
            # 清除自己的关系但保留 swap_count
            swap_count = record.get("swap_count", 0)
            self._groupmate_data[key] = {
                "target": "",
                "date": _get_date(),
                "swap_count": swap_count,
            }
            
            self._save(self.groupmate_file, self._groupmate_data)
        
        return result
    
    def reset_groupmate_full(self, user_id: str, group_id: str) -> dict:
        """完全清除群友数据（关系+抽取次数+双方锁定）"""
        key = _make_key(user_id, group_id)
        result = {}
        
        if key in self._groupmate_data:
            record = self._groupmate_data[key]
            target = record.get("target", "")
            
            if target:
                result["target"] = target
                # 检查对方是否也选了自己
                target_key = _make_key(target, group_id)
                if target_key in self._groupmate_data:
                    target_record = self._groupmate_data[target_key]
                    if target_record.get("target") == user_id:
                        del self._groupmate_data[target_key]
                        result["mutual_cleared"] = True
            
            del self._groupmate_data[key]
            self._save(self.groupmate_file, self._groupmate_data)
        
        # 检查是否被别人选为群友
        claimed_by = self.get_claimer(user_id, group_id)
        if claimed_by:
            claimed_key = _make_key(claimed_by, group_id)
            if claimed_key in self._groupmate_data:
                del self._groupmate_data[claimed_key]
                result["claimed_by"] = claimed_by
                self._save(self.groupmate_file, self._groupmate_data)
        
        return result
    
    def get_member_name(self, user_id: str, group_id: str) -> str:
        """获取成员名称"""
        from .member_collector import get_nickname
        
        # 优先从收集器获取昵称
        nickname = get_nickname(group_id, user_id)
        if nickname:
            return nickname
        
        # 降级：显示用户ID
        return f"<@{user_id}>"


groupmate_handler = GroupmateHandler()
"""
抽卡处理器 - 保底、抽卡逻辑
"""

import random
import json
from pathlib import Path
from typing import Optional

from src.app.plugin_system.api.log_api import get_logger

from ..data.gacha_pools import (
    ROLE_SUPPLY_A, ROLE_SUPPLY_B,
    EQUIP_SUPPLY_A, EQUIP_SUPPLY_B,
    SYNERGY_SUPPLY,
    ADVANCED_SUPPLY, ADVANCED_ARMAMENT,
    COSTUME_SUPPLY,
)


logger = get_logger("elysia_dice.gacha_handler")

SUPPLY_COST = 280
TEN_PULL_COST = 2800


def _make_key(user_id: str, group_id: str = "") -> str:
    if group_id:
        return f"{group_id}:{user_id}"
    return user_id


class GachaHandler:
    """抽卡处理器"""

    def __init__(self):
        self.data_dir = Path("data/elysia_dice")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.pity_file = self.data_dir / "gacha_pity.json"
        self.pity_data = self._load_json(self.pity_file)
        self.costume_file = self.data_dir / "costume_supply.json"
        self.costume_data = self._load_json(self.costume_file)

        # 补给池配置
        self.pools = {
            "角色补给A": ROLE_SUPPLY_A,
            "角色补给B": ROLE_SUPPLY_B,
            "装备补给A": EQUIP_SUPPLY_A,
            "装备补给B": EQUIP_SUPPLY_B,
            "协同补给": SYNERGY_SUPPLY,
            "跃升补给": ADVANCED_SUPPLY,
            "跃升武装": ADVANCED_ARMAMENT,
            "服装补给": COSTUME_SUPPLY,
        }

    def _load_json(self, file_path: Path) -> dict:
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载保底数据失败 {file_path}: {e}")
        return {}

    def _save_json(self, file_path: Path, data: dict) -> bool:
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存保底数据失败 {file_path}: {e}")
            return False

    def _get_shared_pity_key(self, user_id: str, group_id: str, pool_type: str) -> str:
        """获取共享保底key（角色AB共享，装备AB共享）"""
        base = _make_key(user_id, group_id)
        return f"{base}:shared:{pool_type}"

    def _get_shared_pity(self, user_id: str, group_id: str, pool_type: str) -> int:
        """获取共享保底计数"""
        key = self._get_shared_pity_key(user_id, group_id, pool_type)
        return self.pity_data.get(key, 0)

    def _set_shared_pity(self, user_id: str, group_id: str, pool_type: str, count: int):
        """设置共享保底计数"""
        key = self._get_shared_pity_key(user_id, group_id, pool_type)
        self.pity_data[key] = count
        self._save_json(self.pity_file, self.pity_data)

    def _weighted_choice(self, items: list) -> tuple:
        """加权随机选择"""
        total = sum(item[4] for item in items)
        r = random.uniform(0, total)
        cumulative = 0
        for item in items:
            cumulative += item[4]
            if r <= cumulative:
                return item
        return items[-1]

    def _do_single_pull(self, pool: dict, pity_before_pull: int, pool_type: str, total_pulled: int) -> tuple:
        """
        执行单抽
        参数:
            pool: 卡池配置
            pity_before_pull: 本次抽卡前的保底计数
            pool_type: 卡池类型
            total_pulled: 已经抽了多少次（含本次）
        返回: (抽到的物品, 新保底计数, 是否触发保底, 稀有物品在第几次抽到)
        """
        guarantee = pool["guarantee"]

        if pool_type == "role":
            s_pity = guarantee["s_rank_pity"]
            a_pity = guarantee["a_rank_pity"]

            # 检查S级保底（第90次必定S）
            if pity_before_pull >= s_pity - 1:
                for item in pool["items"]:
                    if item[2] == "S级" and item[3] == "角色卡":
                        return (item, 0, True, total_pulled)
            
            # 检查A级保底（每10次必定A或以上）
            if pity_before_pull > 0 and (pity_before_pull % a_pity) == a_pity - 1:
                s_items = [i for i in pool["items"] if i[2] == "S级" and i[3] == "角色卡"]
                a_items = [i for i in pool["items"] if i[2] == "A级" and i[3] == "角色卡"]
                choice_pool = s_items + a_items
                total_weight = sum(i[4] for i in choice_pool)
                r = random.uniform(0, total_weight)
                cumulative = 0
                for item in choice_pool:
                    cumulative += item[4]
                    if r <= cumulative:
                        if item[2] == "S级":
                            return (item, 0, True, total_pulled)
                        else:
                            return (item, pity_before_pull + 1, True, total_pulled)

            # 普通抽取
            result = self._weighted_choice(pool["items"])
            if result[2] == "S级" and result[3] == "角色卡":
                return (result, 0, True, total_pulled)
            else:
                return (result, pity_before_pull + 1, False, total_pulled)

        elif pool_type == "equip":
            weapon_pity = guarantee["weapon_pity"]
            star4_pity = guarantee["4star_pity"]

            # 检查武器保底（第60次必定UP武器）
            if pity_before_pull >= weapon_pity - 1:
                up_weapon = pool["up_weapon"]
                for item in pool["items"]:
                    if item[1] == up_weapon and item[3] == "武器":
                        return (item, 0, True, total_pulled)

            # 检查4星保底（每10次必定4星）
            if pity_before_pull > 0 and (pity_before_pull % star4_pity) == star4_pity - 1:
                star4_items = [i for i in pool["items"] if i[2] == "4星"]
                result = self._weighted_choice(star4_items)
                is_up_weapon = (result[1] == pool.get("up_weapon") and result[3] == "武器")
                if is_up_weapon:
                    return (result, 0, True, total_pulled)
                else:
                    return (result, pity_before_pull + 1, True, total_pulled)

            # 普通抽取
            result = self._weighted_choice(pool["items"])
            is_up_weapon = (result[1] == pool.get("up_weapon") and result[3] == "武器")
            if is_up_weapon:
                return (result, 0, True, total_pulled)
            else:
                return (result, pity_before_pull + 1, False, total_pulled)

        elif pool_type == "synergy":
            synergist_pity = guarantee["synergist_pity"]
            star4_pity = guarantee["4star_pity"]

            # 检查协同者保底（第60次必定S协同者）
            if pity_before_pull >= synergist_pity - 1:
                up_syn = pool["up_synergist"]
                for item in pool["items"]:
                    if item[1] == up_syn and item[3] == "协同者":
                        return (item, 0, True, total_pulled)

            # 检查4星保底
            if pity_before_pull > 0 and (pity_before_pull % star4_pity) == star4_pity - 1:
                star4_items = [i for i in pool["items"] if i[2] == "4星"]
                result = self._weighted_choice(star4_items)
                is_synergist = (result[3] == "协同者")
                if is_synergist:
                    return (result, 0, True, total_pulled)
                else:
                    return (result, pity_before_pull + 1, True, total_pulled)

            # 普通抽取
            result = self._weighted_choice(pool["items"])
            is_synergist = (result[3] == "协同者")
            if is_synergist:
                return (result, 0, True, total_pulled)
            else:
                return (result, pity_before_pull + 1, False, total_pulled)

        # 兜底
        result = self._weighted_choice(pool["items"])
        return (result, pity_before_pull + 1, False, total_pulled)
    
    def _get_costume_key(self, user_id: str, group_id: str) -> str:
        """获取服装补给状态key"""
        base = _make_key(user_id, group_id)
        return f"{base}:costume"
    
    def get_costume_state(self, user_id: str, group_id: str) -> dict:
        """获取服装补给状态"""
        key = self._get_costume_key(user_id, group_id)
        return self.costume_data.get(key, {
            "pull_count": 0,           # 当前已抽次数 (0-9)
            "obtained_items": [],       # 本轮已获得的物品
            "remaining_items": [],      # 本轮剩余物品
        })
    
    def save_costume_state(self, user_id: str, group_id: str, state: dict):
        """保存服装补给状态"""
        key = self._get_costume_key(user_id, group_id)
        self.costume_data[key] = state
        self._save_json(self.costume_file, self.costume_data)
    
    def reset_costume_state(self, user_id: str, group_id: str):
        """重置服装补给状态"""
        key = self._get_costume_key(user_id, group_id)
        if key in self.costume_data:
            del self.costume_data[key]
            self._save_json(self.costume_file, self.costume_data)
    
    def _do_costume_pull(self, user_id: str, group_id: str) -> dict:
        """执行服装补给单抽"""
        pool = self.pools["服装补给"]
        state = self.get_costume_state(user_id, group_id)
        
        pull_count = state["pull_count"]  # 0-9
        
        # 如果是第0次（新的一轮），初始化剩余物品
        if pull_count == 0:
            state["obtained_items"] = []
            state["remaining_items"] = list(pool["pool_items"])
        
        remaining = state["remaining_items"]
        prob_row = pool["probability_matrix"][pull_count]
        
        # 根据剩余物品和概率权重计算实际概率
        # 只计算剩余物品的权重
        item_probabilities = []
        total_weight = 0.0
        for i, item_name in enumerate(pool["pool_items"]):
            if item_name in remaining:
                weight = prob_row[i]
                total_weight += weight
                item_probabilities.append((item_name, weight))
        
        # 归一化概率
        normalized_probs = [(name, w / total_weight * 100) for name, w in item_probabilities]
        
        # 加权随机选择
        r = random.uniform(0, total_weight)
        cumulative = 0.0
        chosen_item = None
        for name, weight in item_probabilities:
            cumulative += weight
            if r <= cumulative:
                chosen_item = name
                break
            
        if chosen_item is None:
            chosen_item = item_probabilities[-1][0]
        
        # 从剩余列表中移除
        remaining.remove(chosen_item)
        state["obtained_items"].append(chosen_item)
        state["remaining_items"] = remaining
        
        # 计算消耗
        cost_index = pull_count  # 0-based
        cost = pool["cost"][cost_index] if cost_index < len(pool["cost"]) else 0
        
        # 增加计数
        new_pull_count = pull_count + 1
        
        # 检查是否完成一轮（10次）
        is_complete = (new_pull_count >= 10)
        
        if is_complete:
            state["pull_count"] = 0
            state["obtained_items"] = []
            state["remaining_items"] = list(pool["pool_items"])
        else:
            state["pull_count"] = new_pull_count
        
        self.save_costume_state(user_id, group_id, state)
        
        return {
            "item": chosen_item,
            "cost": cost,
            "pull_number": pull_count + 1,  # 第几次（1-based）
            "is_free": (pull_count == 0),   # 首次免费
            "remaining_items": remaining,
            "obtained_items": state["obtained_items"],
            "is_complete": is_complete,
            "next_cost": pool["cost"][new_pull_count] if new_pull_count < 10 else pool["cost"][0],
        }
    
    def costume_pull(self, user_id: str, group_id: str, times: int = 1) -> dict:
        """服装补给抽卡（支持多次）"""
        pool = self.pools["服装补给"]
        state = self.get_costume_state(user_id, group_id)
        
        results = []
        total_cost = 0
        free_used = False
        
        current_pull = state["pull_count"]
        
        for i in range(times):
            result = self._do_costume_pull(user_id, group_id)
            results.append(result)
            total_cost += result["cost"]
            if result["is_free"]:
                free_used = True
            
            # 更新状态（_do_costume_pull已经保存）
            state = self.get_costume_state(user_id, group_id)
            current_pull = state["pull_count"]
        
        return {
            "results": results,
            "total_cost": total_cost,
            "free_used": free_used,
            "current_pull": current_pull,
            "next_cost": pool["cost"][current_pull] if current_pull < 10 else pool["cost"][0],
        }
    
    def get_milestone_rewards(self, pity_before: int, pity_after: int, pool_name: str) -> list:
        """获取里程碑奖励"""
        pool = self.pools.get(pool_name)
        if not pool:
            return []
        
        milestone_rewards = pool.get("milestone_rewards", {})
        rewards = []
        
        # 找到从pity_before到pity_after之间触发的里程碑
        for milestone, items in sorted(milestone_rewards.items()):
            if pity_before < milestone <= pity_after:
                rewards.extend(items)
        
        return rewards

    def get_pool_type(self, pool_name: str) -> str:
        """获取补给池类型"""
        if pool_name.startswith("角色补给") or pool_name == "跃升补给":
            return "role"
        elif pool_name.startswith("装备补给") or pool_name == "跃升武装":
            return "equip"
        elif pool_name == "协同补给":
            return "synergy"
        elif pool_name == "服装补给":
            return "costume"
        return "role"
    
    def get_shared_pool_key(self, pool_name: str) -> str:
        """获取共享保底key"""
        # 跃升补给和跃升武装不与AB共享
        if pool_name == "跃升补给":
            return "跃升补给"
        elif pool_name == "跃升武装":
            return "跃升武装"
        elif pool_name == "服装补给":
            return "服装补给"
        elif pool_name.startswith("角色补给"):
            return "角色补给"
        elif pool_name.startswith("装备补给"):
            return "装备补给"
        return pool_name

    def pull(self, user_id: str, group_id: str, pool_name: str, times: int) -> dict:
        """
        执行抽卡
        返回: {
            "results": [(item_tuple, ...)],
            "total_cost": int,
            "pity_before": int,
            "pity_after": int,
            "triggered_guarantee": bool,
            "rare_results": [{"item_name": str, "pull_number": int, "type": str}, ...]
        }
        """
        pool = self.pools.get(pool_name)
        if not pool:
            return {"error": f"未知补给池: {pool_name}"}

        pool_type = self.get_pool_type(pool_name)
        shared_key = self.get_shared_pool_key(pool_name)

        # 获取共享保底计数
        pity = self._get_shared_pity(user_id, group_id, shared_key)
        pity_before = pity

        results = []
        rare_results = []
        triggered = False

        for i in range(times):
            current_pull_number = pity_before + i + 1  # 本次是累计第几次
            item, pity, is_triggered, pull_num = self._do_single_pull(pool, pity, pool_type, current_pull_number)
            results.append(item)
            
            if is_triggered:
                triggered = True
                # 记录稀有掉落及次数
                if pool_type == "role" and item[2] == "S级":
                    rare_results.append({
                        "item_name": item[1],
                        "pull_number": current_pull_number,
                        "type": "s_rank",
                        "icon": "🌟"
                    })
                elif pool_type == "equip" and item[1] == pool.get("up_weapon"):
                    rare_results.append({
                        "item_name": item[1],
                        "pull_number": current_pull_number,
                        "type": "up_weapon",
                        "icon": "💫"
                    })
                elif pool_type == "synergy" and item[3] == "协同者":
                    rare_results.append({
                        "item_name": item[1],
                        "pull_number": current_pull_number,
                        "type": "synergist",
                        "icon": "✨"
                    })

        # 保存保底计数
        self._set_shared_pity(user_id, group_id, shared_key, pity)

        total_cost = TEN_PULL_COST if times == 10 else SUPPLY_COST * times

        return {
            "results": results,
            "total_cost": total_cost,
            "pity_before": pity_before,
            "pity_after": pity,
            "triggered_guarantee": triggered,
            "rare_results": rare_results,
        }

    def get_pity_info(self, user_id: str, group_id: str, pool_name: str) -> dict:
        """获取保底信息"""
        pool = self.pools.get(pool_name)
        if not pool:
            return {}

        shared_key = self.get_shared_pool_key(pool_name)
        pity = self._get_shared_pity(user_id, group_id, shared_key)

        pool_type = self.get_pool_type(pool_name)
        guarantee = pool["guarantee"]

        info = {
            "current_pity": pity,
        }

        if pool_type == "role":
            info["s_rank_pity"] = guarantee["s_rank_pity"]
            info["a_rank_pity"] = guarantee["a_rank_pity"]
            info["until_s_rank"] = guarantee["s_rank_pity"] - pity if pity > 0 else guarantee["s_rank_pity"]
            info["until_a_rank"] = guarantee["a_rank_pity"] - (pity % guarantee["a_rank_pity"]) if pity % guarantee["a_rank_pity"] > 0 else 0
        elif pool_type == "equip":
            info["weapon_pity"] = guarantee["weapon_pity"]
            info["4star_pity"] = guarantee["4star_pity"]
            info["until_weapon"] = guarantee["weapon_pity"] - pity if pity > 0 else guarantee["weapon_pity"]
            info["until_4star"] = guarantee["4star_pity"] - (pity % guarantee["4star_pity"]) if pity % guarantee["4star_pity"] > 0 else 0
        elif pool_type == "synergy":
            info["synergist_pity"] = guarantee["synergist_pity"]
            info["4star_pity"] = guarantee["4star_pity"]
            info["until_synergist"] = guarantee["synergist_pity"] - pity if pity > 0 else guarantee["synergist_pity"]
            info["until_4star"] = guarantee["4star_pity"] - (pity % guarantee["4star_pity"]) if pity % guarantee["4star_pity"] > 0 else 0

        return info


gacha_handler = GachaHandler()
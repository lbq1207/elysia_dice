"""
签到相关逻辑
"""
import random
from datetime import datetime, timedelta
from typing import Optional, Tuple
from pathlib import Path
import json

from src.app.plugin_system.api.log_api import get_logger

logger = get_logger("elysia_dice.sign")

# 全局分群开关（与 dev_tools.py 保持一致）
SEPARATE_BY_GROUP = True


def _make_key(user_id: str, group_id: str = "") -> str:
    """生成存储key"""
    if SEPARATE_BY_GROUP and group_id:
        return f"{group_id}:{user_id}"
    return user_id


class SignManager:
    """签到管理器"""

    def __init__(self):
        self.data_dir = Path("data/elysia_dice")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sign_data_file = self.data_dir / "sign_data.json"
        self.sign_data = self._load_data()
        self.reward_config = {
            1: (1, 5, 10),
            2: (3, 5, 11),
            3: (6, 5, 13),
            4: (10, 5, 16),
            5: (15, 5, 20),
        }

    def _load_data(self) -> dict:
        try:
            if self.sign_data_file.exists():
                with open(self.sign_data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载签到数据失败: {e}")
        return {}

    def _save_data(self) -> bool:
        try:
            with open(self.sign_data_file, 'w', encoding='utf-8') as f:
                json.dump(self.sign_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存签到数据失败: {e}")
            return False

    def _get_reward_config(self, continuous_days: int) -> tuple:
        if continuous_days >= 5:
            return self.reward_config[5]
        return self.reward_config.get(continuous_days, self.reward_config[1])

    def sign(self, user_id: str, group_id: str = "") -> str:
        """执行签到"""
        key = _make_key(user_id, group_id)
        today = datetime.now().strftime("%Y-%m-%d")

        if key not in self.sign_data:
            self.sign_data[key] = {
                "last_sign": None,
                "sign_count": 0,
                "current_streak": 0,
                "max_streak": 0,
                "total_reward": 0
            }

        user = self.sign_data[key]

        if user["last_sign"] == today:
            return "❀ 你今天已经签到过了，明天再来吧~\n⚠️ 每天只能签到一次哦"

        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if user["last_sign"] == yesterday:
            streak = user["current_streak"] + 1
        else:
            streak = 1

        base_reward, random_min, random_max = self._get_reward_config(streak)
        random_reward = random.randint(random_min, random_max)
        total_reward = base_reward + random_reward

        user["last_sign"] = today
        user["sign_count"] += 1
        user["current_streak"] = streak
        user["max_streak"] = max(user["max_streak"], streak)
        user["total_reward"] += total_reward

        self._save_data()

        # 写入花花到 currency_manager
        from .dev_tools import currency_manager
        new_balance = currency_manager.add_currency(user_id, total_reward, group_id)

        continuous_text = "首次" if streak == 1 else f"连续{streak}天"

        msg = "❀ 签到成功！\n━━━━━━━━━━━━\n"
        msg += f"📅 签到状态：{continuous_text}\n"
        msg += f"💮 基础奖励：{base_reward} 花花\n"
        msg += f"🎲 随机奖励：+{random_reward} 花花\n"
        msg += "━━━━━━━━━━━━\n"
        msg += f"💐 本次获得：{total_reward} 花花\n"
        msg += f"💳 当前余额：{new_balance} 花花\n"
        msg += f"🌺 累计获得：{user['total_reward']} 花花\n"

        if streak == 3:
            msg += "\n🌟 连续签到3天！继续保持！"
        elif streak == 5:
            msg += "\n🎉 连续签到5天！基础奖励已达上限！"
        elif streak == 7:
            msg += "\n👑 连续签到一周！你太棒了！"

        if user["sign_count"] == 1:
            msg += "\n\n💡 签到规则：\n• 每天只能签到1次\n• 签到奖励=基础奖励+随机奖励\n"
            msg += "• 连续签到可获得更多花花\n• 连续签到第5天起,基础奖励与随机奖励上限达到最高\n"
            msg += "• 花花可用于赠送、商店购买以及抽奖，发送 /赠送、/商店、/抽奖 以查看详情 "

        logger.info(f"用户 {key} 签到成功 - {continuous_text}签到，获得 {total_reward} 花花，余额 {new_balance}")
        return msg

    def reset_user(self, user_id: str, group_id: str = "") -> bool:
        """重置指定用户的签到状态（保留累计数据）"""
        key = _make_key(user_id, group_id)
        if key in self.sign_data:
            old = self.sign_data[key]
            max_streak = old.get("max_streak", 0)
            total_reward = old.get("total_reward", 0)
            self.sign_data[key] = {
                "last_sign": None,
                "sign_count": 0,
                "current_streak": 0,
                "max_streak": max_streak,
                "total_reward": total_reward
            }
        else:
            self.sign_data[key] = {
                "last_sign": None,
                "sign_count": 0,
                "current_streak": 0,
                "max_streak": 0,
                "total_reward": 0
            }
        self._save_data()
        logger.info(f"已重置用户 {key} 的签到状态")
        return True

    def reset_all_sign(self, group_id: str = "") -> int:
        """重置所有用户的今日签到状态"""
        count = 0
        if SEPARATE_BY_GROUP and group_id:
            prefix = f"{group_id}:"
            for uid in self.sign_data:
                if uid.startswith(prefix):
                    self.sign_data[uid]["last_sign"] = None
                    self.sign_data[uid]["current_streak"] = 0
                    count += 1
        else:
            for uid in self.sign_data:
                if not SEPARATE_BY_GROUP or ":" not in uid:
                    self.sign_data[uid]["last_sign"] = None
                    self.sign_data[uid]["current_streak"] = 0
                    count += 1
        self._save_data()
        logger.info(f"已重置 {count} 个用户的签到状态")
        return count


async def handle_sign(user_id: str, group_id: str = "") -> str:
    """处理签到请求"""
    try:
        return sign_manager.sign(user_id, group_id)
    except Exception as e:
        logger.error(f"签到处理失败: {e}")
        return f"❌ 签到失败: {str(e)}\n请联系管理员处理"


sign_manager = SignManager()
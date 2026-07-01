"""
补给抽卡命令
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.app.plugin_system.api.log_api import get_logger
from src.app.plugin_system.api.send_api import send_text
from src.app.plugin_system.base import BaseCommand, cmd_route
from src.app.plugin_system.types import PermissionLevel, ChatType
from src.app.plugin_system.api.stream_api import get_stream_info

from ..handlers.crystal import crystal_manager
from ..handlers.gacha_handler import gacha_handler, SUPPLY_COST, TEN_PULL_COST

if TYPE_CHECKING:
    from ..plugin import ElysiaDicePlugin

logger = get_logger("elysia_dice.supply_command")


async def _do_supply(command_instance, pool_name: str, times_str: str) -> tuple[bool, str]:
    """执行补给抽卡"""
    try:
        user_id = str(command_instance._message.sender_id) if command_instance._message else ""
        if not user_id:
            await send_text("无法识别用户身份", stream_id=command_instance.stream_id)
            return False, "no user"

        info = await get_stream_info(command_instance.stream_id)
        group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""

        # 解析次数
        times_str = times_str.strip()
        if not times_str:
            times = 1
        else:
            try:
                times = int(times_str)
                if times < 1:
                    times = 1
                elif times > 100:
                    await send_text("⚠️ 单次最多抽取100次", stream_id=command_instance.stream_id)
                    return True, "too many"
            except ValueError:
                await send_text("⚠️ 次数格式错误，请输入数字", stream_id=command_instance.stream_id)
                return True, "bad format"

        # 计算消耗
        cost = TEN_PULL_COST if times == 10 else SUPPLY_COST * times

        # 检查水晶
        current = crystal_manager.get_crystal(user_id, group_id)
        if current < cost:
            await send_text(
                f"💎 水晶不足！\n"
                f"━━━━━━━━━━━━\n"
                f"💎 当前水晶：{current}\n"
                f"💎 需要水晶：{cost}\n"
                f"━━━━━━━━━━━━\n"
                f"💡 发送 /获取水晶 领取每日水晶",
                stream_id=command_instance.stream_id
            )
            return True, "no enough crystal"

        # 执行抽卡
        result = gacha_handler.pull(user_id, group_id, pool_name, times)

        if "error" in result:
            await send_text(result["error"], stream_id=command_instance.stream_id)
            return True, "pool error"

        # 扣除水晶
        new_balance = crystal_manager.add_crystal(user_id, -result["total_cost"], group_id)

        # 获取保底信息（抽卡后）
        pity_after = gacha_handler.get_pity_info(user_id, group_id, pool_name)

        # 格式化消息
        pool = gacha_handler.pools[pool_name]
        msg = f"💎 {pool['name']} - {pool['title']}\n"
        msg += f"━━━━━━━━━━━━\n"
        msg += f"📊 抽取次数：{times}\n"
        msg += f"💎 消耗水晶：{result['total_cost']}\n"
        msg += f"💎 剩余水晶：{new_balance}\n"
        msg += f"━━━━━━━━━━━━\n"

        # 稀有掉落（显示第几次抽到）
        if result["rare_results"]:
            msg += f"🎯 稀有掉落：\n"
            for rare in result["rare_results"]:
                msg += f"  {rare['icon']} {rare['item_name']}（第{rare['pull_number']}次）\n"
            msg += f"━━━━━━━━━━━━\n"

        # 所有结果
        msg += f"📦 获得物品：\n"
        display_count = min(times, 10)
        for i in range(display_count):
            item = result["results"][i]
            rarity_icon = {"S级": "🌟", "A级": "⭐", "4星": "💜", "3星": "🔷", "2星": "🔹"}.get(item[2], "📦")
            msg += f"  {rarity_icon} {item[1]}\n"

        if times > 10:
            msg += f"  ... 还有 {times - 10} 个结果\n"

        msg += f"━━━━━━━━━━━━\n"

        # 保底提示
        pool_type = gacha_handler.get_pool_type(pool_name)
        if pool_type == "role":
            msg += f"📅 S级保底：{pity_after['current_pity']}/{pity_after['s_rank_pity']}（还需 {pity_after['until_s_rank']} 次）\n"
        elif pool_type == "equip":
            msg += f"📅 UP武器保底：{pity_after['current_pity']}/{pity_after['weapon_pity']}（还需 {pity_after['until_weapon']} 次）\n"
        elif pool_type == "synergy":
            msg += f"📅 协同者保底：{pity_after['current_pity']}/{pity_after['synergist_pity']}（还需 {pity_after['until_synergist']} 次）\n"

        msg += f"💡 继续发送 /{pool_name} 抽取"

        await send_text(msg, stream_id=command_instance.stream_id)
        return True, "ok"

    except Exception as e:
        logger.error(f"补给失败: {e}", exc_info=True)
        await send_text(f"补给失败: {str(e)}", stream_id=command_instance.stream_id)
        return False, str(e)


class RoleSupplyACommand(BaseCommand):
    """角色补给A"""
    command_name: str = "角色补给A"
    command_description: str = "「愈生佑翎」角色补给（280水晶/次）"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"

    @classmethod
    def match(cls, parts: list[str]) -> int:
        if not parts:
            return 0
        if parts[0] == "角色补给A":
            return 1
        return 0

    @cmd_route()
    async def handle_root(self, times: str = "") -> tuple[bool, str]:
        return await _do_supply(self, "角色补给A", times)


class RoleSupplyBCommand(BaseCommand):
    """角色补给B"""
    command_name: str = "角色补给B"
    command_description: str = "「嗨♪爱愿妖精♥」角色补给（280水晶/次）"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"

    @classmethod
    def match(cls, parts: list[str]) -> int:
        if not parts:
            return 0
        if parts[0] == "角色补给B":
            return 1
        return 0

    @cmd_route()
    async def handle_root(self, times: str = "") -> tuple[bool, str]:
        return await _do_supply(self, "角色补给B", times)


class EquipSupplyACommand(BaseCommand):
    """装备补给A"""
    command_name: str = "装备补给A"
    command_description: str = "「愈生佑翎」装备补给（280水晶/次）"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"

    @classmethod
    def match(cls, parts: list[str]) -> int:
        if not parts:
            return 0
        if parts[0] == "装备补给A":
            return 1
        return 0

    @cmd_route()
    async def handle_root(self, times: str = "") -> tuple[bool, str]:
        return await _do_supply(self, "装备补给A", times)


class EquipSupplyBCommand(BaseCommand):
    """装备补给B"""
    command_name: str = "装备补给B"
    command_description: str = "「嗨♪爱愿妖精♥」装备补给（280水晶/次）"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"

    @classmethod
    def match(cls, parts: list[str]) -> int:
        if not parts:
            return 0
        if parts[0] == "装备补给B":
            return 1
        return 0

    @cmd_route()
    async def handle_root(self, times: str = "") -> tuple[bool, str]:
        return await _do_supply(self, "装备补给B", times)


class SynergySupplyCommand(BaseCommand):
    """协同补给"""
    command_name: str = "协同补给"
    command_description: str = "S级协同者「希娜狄雅」（280水晶/次）"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"

    @classmethod
    def match(cls, parts: list[str]) -> int:
        if not parts:
            return 0
        if parts[0] == "协同补给":
            return 1
        return 0

    @cmd_route()
    async def handle_root(self, times: str = "") -> tuple[bool, str]:
        return await _do_supply(self, "协同补给", times)
    
async def _do_costume_supply(command_instance, times_str: str) -> tuple[bool, str]:
    """执行服装补给"""
    try:
        user_id = str(command_instance._message.sender_id) if command_instance._message else ""
        if not user_id:
            await send_text("无法识别用户身份", stream_id=command_instance.stream_id)
            return False, "no user"

        info = await get_stream_info(command_instance.stream_id)
        group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""

        # 服装补给只支持单抽
        times = 1
        if times_str.strip():
            try:
                times = int(times_str)
                if times > 10:
                    await send_text("⚠️ 服装补给最多连续抽取10次", stream_id=command_instance.stream_id)
                    return True, "too many"
                if times < 1:
                    times = 1
            except ValueError:
                times = 1

        # 获取当前状态
        state = gacha_handler.get_costume_state(user_id, group_id)
        current_count = state["pull_count"]
        
        # 计算消耗
        pool = gacha_handler.pools["服装补给"]
        total_cost = 0
        temp_count = current_count
        for i in range(times):
            cost_index = temp_count
            if cost_index >= 10:
                cost_index = 0
                temp_count = 0
            if cost_index == 0:
                # 首次免费
                total_cost += 0
            else:
                total_cost += pool["cost"][cost_index]
            temp_count += 1
        
        # 检查水晶
        current_crystal = crystal_manager.get_crystal(user_id, group_id)
        if current_crystal < total_cost:
            await send_text(
                f"💎 水晶不足！\n"
                f"━━━━━━━━━━━━\n"
                f"💎 当前水晶：{current_crystal}\n"
                f"💎 需要水晶：{total_cost}\n",
                stream_id=command_instance.stream_id
            )
            return True, "no enough crystal"

        # 执行抽卡
        result = gacha_handler.costume_pull(user_id, group_id, times)
        
        # 扣除水晶
        new_balance = crystal_manager.add_crystal(user_id, -result["total_cost"], group_id)
        
        # 格式化消息
        msg = f"👗 服装补给 - 「霁月婵娟」\n"
        msg += f"━━━━━━━━━━━━\n"
        msg += f"📊 抽取次数：{times}\n"
        msg += f"💎 消耗水晶：{result['total_cost']}"
        if result["free_used"]:
            msg += f"（含首次免费）"
        msg += f"\n💎 剩余水晶：{new_balance}\n"
        msg += f"━━━━━━━━━━━━\n"
        msg += f"🎯 获得物品：\n"
        
        for i, r in enumerate(result["results"]):
            item_label = "免费" if r["is_free"] else f"第{r['pull_number']}次"
            msg += f"  📦 {r['item']} ({item_label})\n"
        msg += f"━━━━━━━━━━━━\n"
        
        # 剩余物品
        final_state = gacha_handler.get_costume_state(user_id, group_id)
        remaining = final_state["remaining_items"]
        if remaining:
            msg += f"📋 奖池剩余 {len(remaining)} 件：\n"
            for item in remaining:
                msg += f"  · {item}\n"
            msg += f"━━━━━━━━━━━━\n"
        
        # 下一抽消耗
        if final_state["pull_count"] < 10:
            next_cost = pool["cost"][final_state["pull_count"]]
            msg += f"💎 下次消耗：{next_cost}水晶\n"
        else:
            msg += f"💎 奖池已重置，下次消耗：0水晶（免费）\n"
        
        msg += f"💡 发送 /服装补给 继续抽取"
        
        await send_text(msg, stream_id=command_instance.stream_id)
        return True, "ok"

    except Exception as e:
        logger.error(f"服装补给失败: {e}", exc_info=True)
        await send_text(f"服装补给失败: {str(e)}", stream_id=command_instance.stream_id)
        return False, str(e)


# 更新 _do_supply 函数以处理里程碑奖励
async def _do_supply(command_instance, pool_name: str, times_str: str) -> tuple[bool, str]:
    """执行补给抽卡"""
    try:
        user_id = str(command_instance._message.sender_id) if command_instance._message else ""
        if not user_id:
            await send_text("无法识别用户身份", stream_id=command_instance.stream_id)
            return False, "no user"

        info = await get_stream_info(command_instance.stream_id)
        group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""

        # 服装补给走单独逻辑
        if pool_name == "服装补给":
            return await _do_costume_supply(command_instance, times_str)

        # 解析次数
        times_str = times_str.strip()
        if not times_str:
            times = 1
        else:
            try:
                times = int(times_str)
                if times < 1:
                    times = 1
                elif times > 100:
                    await send_text("⚠️ 单次最多抽取100次", stream_id=command_instance.stream_id)
                    return True, "too many"
            except ValueError:
                await send_text("⚠️ 次数格式错误，请输入数字", stream_id=command_instance.stream_id)
                return True, "bad format"

        # 计算消耗
        cost = TEN_PULL_COST if times == 10 else SUPPLY_COST * times

        # 检查水晶
        current = crystal_manager.get_crystal(user_id, group_id)
        if current < cost:
            await send_text(
                f"💎 水晶不足！\n"
                f"━━━━━━━━━━━━\n"
                f"💎 当前水晶：{current}\n"
                f"💎 需要水晶：{cost}\n"
                f"━━━━━━━━━━━━\n"
                f"💡 发送 /获取水晶 领取每日水晶",
                stream_id=command_instance.stream_id
            )
            return True, "no enough crystal"

        # 执行抽卡
        result = gacha_handler.pull(user_id, group_id, pool_name, times)

        if "error" in result:
            await send_text(result["error"], stream_id=command_instance.stream_id)
            return True, "pool error"

        # 检查里程碑奖励
        milestone_rewards = gacha_handler.get_milestone_rewards(
            result["pity_before"], result["pity_after"], pool_name
        )
        
        # 扣除水晶
        new_balance = crystal_manager.add_crystal(user_id, -result["total_cost"], group_id)
        
        # 发放里程碑奖励
        milestone_msg = ""
        if milestone_rewards:
            for reward_name, reward_qty in milestone_rewards:
                if reward_name == "水晶":
                    new_balance = crystal_manager.add_crystal(user_id, reward_qty, group_id)
                    milestone_msg += f"  💎 {reward_name}+{reward_qty}\n"
                else:
                    milestone_msg += f"  🏅 {reward_name}×{reward_qty}\n"

        # 获取保底信息（抽卡后）
        pity_after = gacha_handler.get_pity_info(user_id, group_id, pool_name)

        # 格式化消息
        pool = gacha_handler.pools[pool_name]
        msg = f"💎 {pool['name']} - {pool['title']}\n"
        msg += f"━━━━━━━━━━━━\n"
        msg += f"📊 抽取次数：{times}\n"
        msg += f"💎 消耗水晶：{result['total_cost']}\n"
        msg += f"💎 剩余水晶：{new_balance}\n"
        msg += f"━━━━━━━━━━━━\n"

        # 稀有掉落（显示第几次抽到）
        if result["rare_results"]:
            msg += f"🎯 稀有掉落：\n"
            for rare in result["rare_results"]:
                msg += f"  {rare['icon']} {rare['item_name']}（第{rare['pull_number']}次）\n"
            msg += f"━━━━━━━━━━━━\n"

        # 里程碑奖励
        if milestone_rewards:
            msg += f"🎁 里程碑奖励：\n"
            msg += milestone_msg
            msg += f"━━━━━━━━━━━━\n"

        # 所有结果
        msg += f"📦 获得物品：\n"
        display_count = min(times, 10)
        for i in range(display_count):
            item = result["results"][i]
            rarity_icon = {"S级": "🌟", "A级": "⭐", "4星": "💜", "3星": "🔷", "2星": "🔹"}.get(item[2], "📦")
            msg += f"  {rarity_icon} {item[1]}\n"

        if times > 10:
            msg += f"  ... 还有 {times - 10} 个结果\n"

        msg += f"━━━━━━━━━━━━\n"

        # 保底提示
        pool_type = gacha_handler.get_pool_type(pool_name)
        if pool_type == "role":
            msg += f"📅 S级保底：{pity_after['current_pity']}/{pity_after['s_rank_pity']}（还需 {pity_after['until_s_rank']} 次）\n"
        elif pool_type == "equip":
            msg += f"📅 UP武器保底：{pity_after['current_pity']}/{pity_after['weapon_pity']}（还需 {pity_after['until_weapon']} 次）\n"
        elif pool_type == "synergy":
            msg += f"📅 协同者保底：{pity_after['current_pity']}/{pity_after['synergist_pity']}（还需 {pity_after['until_synergist']} 次）\n"

        msg += f"💡 继续发送 /{pool_name} 抽取"

        await send_text(msg, stream_id=command_instance.stream_id)
        return True, "ok"

    except Exception as e:
        logger.error(f"补给失败: {e}", exc_info=True)
        await send_text(f"补给失败: {str(e)}", stream_id=command_instance.stream_id)
        return False, str(e)


class AdvancedSupplyCommand(BaseCommand):
    """跃升补给"""
    command_name: str = "跃升补给"
    command_description: str = "「一客逍游」跃升补给（280水晶/次）"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"

    @classmethod
    def match(cls, parts: list[str]) -> int:
        if not parts:
            return 0
        if parts[0] == "跃升补给":
            return 1
        return 0

    @cmd_route()
    async def handle_root(self, times: str = "") -> tuple[bool, str]:
        return await _do_supply(self, "跃升补给", times)


class AdvancedArmamentCommand(BaseCommand):
    """跃升武装"""
    command_name: str = "跃升武装"
    command_description: str = "「一客逍游」跃升武装（280水晶/次）"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"

    @classmethod
    def match(cls, parts: list[str]) -> int:
        if not parts:
            return 0
        if parts[0] == "跃升武装":
            return 1
        return 0

    @cmd_route()
    async def handle_root(self, times: str = "") -> tuple[bool, str]:
        return await _do_supply(self, "跃升武装", times)


class CostumeSupplyCommand(BaseCommand):
    """服装补给"""
    command_name: str = "服装补给"
    command_description: str = "「霁月婵娟」服装补给"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"

    @classmethod
    def match(cls, parts: list[str]) -> int:
        if not parts:
            return 0
        if parts[0] == "服装补给":
            return 1
        return 0

    @cmd_route()
    async def handle_root(self, times: str = "") -> tuple[bool, str]:
        return await _do_costume_supply(self, times)
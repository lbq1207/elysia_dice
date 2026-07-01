"""
商店命令组件
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.app.plugin_system.api.log_api import get_logger
from src.app.plugin_system.api.send_api import send_text
from src.app.plugin_system.base import BaseCommand, cmd_route
from src.app.plugin_system.types import PermissionLevel, ChatType
from src.app.plugin_system.api.stream_api import get_stream_info

from ..handlers.shop import shop_manager, ITEM_ALIASES, _make_key
from ..handlers.dev_tools import currency_manager
from ..handlers.favor import favor_manager

if TYPE_CHECKING:
    from ..plugin import ElysiaDicePlugin

logger = get_logger("elysia_dice.shop_command")


class ShopCommand(BaseCommand):
    """商店命令 - /商店"""
    command_name: str = "商店"
    command_description: str = "查看商店商品列表"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"
    
    @cmd_route()
    async def handle_root(self) -> tuple[bool, str]:
        shop_list = shop_manager.get_shop_list()
        await send_text(shop_list, stream_id=self.stream_id)
        return True, "ok"


class BuyCommand(BaseCommand):
    """购买命令 - /购买"""
    command_name: str = "购买"
    command_description: str = "购买商店物品"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"
    
    @classmethod
    def match(cls, parts: list[str]) -> int:
        if not parts:
            return 0
        if parts[0] in ("购买", "buy"):
            return 1
        return 0
    
    @cmd_route()
    async def handle_root(self, target: str = "") -> tuple[bool, str]:
        try:
            user_id = str(self._message.sender_id) if self._message else ""
            if not user_id:
                await send_text("无法识别用户身份", stream_id=self.stream_id)
                return False, "no user"
            
            # 获取群ID
            info = await get_stream_info(self.stream_id)
            group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""
            
            raw_content = self._message.content if self._message else ""
            
            # 移除命令前缀
            import re
            args_str = re.sub(r'^[/!！]?(购买|buy)\s*', '', raw_content, flags=re.IGNORECASE).strip()
            
            if not args_str:
                await send_text(
                    "❌ 请指定物品\n格式: /购买 <物品> [数量]\n示例: /购买 蒸蛋\n      /购买 面包 3",
                    stream_id=self.stream_id
                )
                return False, "no args"
            
            # 解析物品名和数量
            parts = args_str.split()
            if parts[-1].isdigit():
                quantity = int(parts[-1])
                item_name = " ".join(parts[:-1])
            else:
                quantity = 1
                item_name = args_str
            
            if quantity <= 0:
                await send_text("❌ 购买数量必须大于0", stream_id=self.stream_id)
                return False, "invalid quantity"
            
            if quantity > 100:
                await send_text("❌ 单次最多购买100件", stream_id=self.stream_id)
                return False, "too many"
            
            user_currency = currency_manager.get_currency(user_id, group_id)
            success, message, cost = shop_manager.purchase_item(
                item_name, quantity, user_id, user_currency, group_id
            )
            
            if success:
                currency_manager.add_currency(user_id, -cost, group_id)
            
            await send_text(message, stream_id=self.stream_id)
            return True, "ok"
            
        except Exception as e:
            logger.error(f"购买失败: {e}")
            await send_text(f"购买失败: {str(e)}", stream_id=self.stream_id)
            return False, str(e)


class LotteryCommand(BaseCommand):
    """抽奖命令 - /抽奖"""
    command_name: str = "抽奖"
    command_description: str = "试试手气抽奖"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"
    
    @classmethod
    def match(cls, parts: list[str]) -> int:
        if not parts:
            return 0
        if parts[0] in ("抽奖", "lottery"):
            return 1
        return 0
    
    @cmd_route()
    async def handle_root(self) -> tuple[bool, str]:
        try:
            user_id = str(self._message.sender_id) if self._message else ""
            if not user_id:
                await send_text("无法识别用户身份", stream_id=self.stream_id)
                return False, "no user"
            
            # 获取群ID
            info = await get_stream_info(self.stream_id)
            group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""
            
            user_currency = currency_manager.get_currency(user_id, group_id)
            success, message, cost, item_award, currency_award = shop_manager.do_lottery(
                user_id, user_currency, group_id
            )
            
            if success:
                currency_manager.add_currency(user_id, -cost + currency_award, group_id)
            
            await send_text(message, stream_id=self.stream_id)
            return True, "ok"
            
        except Exception as e:
            logger.error(f"抽奖失败: {e}")
            await send_text(f"抽奖失败: {str(e)}", stream_id=self.stream_id)
            return False, str(e)


class InventoryCommand(BaseCommand):
    """背包命令 - /背包"""
    command_name: str = "背包"
    command_description: str = "查看背包物品"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"
    
    @classmethod
    def match(cls, parts: list[str]) -> int:
        if not parts:
            return 0
        if parts[0] in ("背包", "inventory", "物品"):
            return 1
        return 0
    
    @cmd_route()
    async def handle_root(self) -> tuple[bool, str]:
        try:
            user_id = str(self._message.sender_id) if self._message else ""
            if not user_id:
                await send_text("无法识别用户身份", stream_id=self.stream_id)
                return False, "no user"
            
            # 获取群ID
            info = await get_stream_info(self.stream_id)
            group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""
            
            inventory = shop_manager.get_inventory(user_id, group_id)
            await send_text(inventory, stream_id=self.stream_id)
            return True, "ok"
            
        except Exception as e:
            logger.error(f"查看背包失败: {e}")
            return False, str(e)
        

class GiftCommand(BaseCommand):
    """赠送命令 - /赠送"""
    command_name: str = "赠送"
    command_description: str = "赠送物品或花花给爱莉，提升好感度"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.GROUP
    plugin: "ElysiaDicePlugin"
    
    @classmethod
    def match(cls, parts: list[str]) -> int:
        """匹配命令名"""
        if not parts:
            return 0
        if parts[0] in ("赠送", "gift", "give"):
            return 1
        return 0
    
    @cmd_route()
    async def handle_root(self, target: str = "") -> tuple[bool, str]:
        """处理赠送命令"""
        try:
            user_id = str(self._message.sender_id) if self._message else ""
            if not user_id:
                await send_text("无法识别用户身份", stream_id=self.stream_id)
                return False, "no user"
            
            # 获取群ID
            info = await get_stream_info(self.stream_id)
            group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""
            
            if not group_id:
                await send_text("❌ 赠送功能仅在群聊可用", stream_id=self.stream_id)
                return False, "not group"
            
            # 获取原始消息内容
            raw_content = self._message.content if self._message else ""
            logger.info(f"📝 赠送原始消息: {raw_content}")
            
            # 移除命令前缀（兼容 /赠送、赠送、/gift 等）
            import re
            args_str = re.sub(r'^[/!！]?(赠送|gift|give)\s*', '', raw_content, flags=re.IGNORECASE).strip()
            
            logger.info(f"📝 赠送参数: {args_str}")
            
            if not args_str:
                await send_text(self._get_help_text(), stream_id=self.stream_id)
                return False, "no args"
            
            # 解析参数
            parts = args_str.split()
            
            # 检查是否是"花花"赠送
            if parts[0] in ("花花", "花", "flower", "flowers"):
                quantity = 1
                if len(parts) >= 2:
                    try:
                        quantity = int(parts[1])
                    except ValueError:
                        await send_text(
                            f"❌ 数量格式错误: {parts[1]}\n"
                            f"格式: /赠送 花花 <数量>\n"
                            f"示例: /赠送 花花 100",
                            stream_id=self.stream_id
                        )
                        return False, "invalid quantity"
                
                if quantity <= 0:
                    await send_text("❌ 赠送数量必须大于0", stream_id=self.stream_id)
                    return False, "invalid quantity"
                
                if quantity > 1000:
                    await send_text("❌ 单次最多赠送1000花花", stream_id=self.stream_id)
                    return False, "too many"
                
                return await self._gift_flowers(user_id, group_id, quantity)
            
            else:
                # 赠送物品
                item_name = args_str
                quantity = 1
                
                if parts[-1].isdigit():
                    quantity = int(parts[-1])
                    item_name = " ".join(parts[:-1])
                
                if quantity <= 0:
                    await send_text("❌ 赠送数量必须大于0", stream_id=self.stream_id)
                    return False, "invalid quantity"
                
                if quantity > 100:
                    await send_text("❌ 单次最多赠送100件物品", stream_id=self.stream_id)
                    return False, "too many"
                
                return await self._gift_item(user_id, group_id, item_name, quantity)
            
        except Exception as e:
            logger.error(f"赠送失败: {e}", exc_info=True)
            await send_text(f"赠送失败: {str(e)}", stream_id=self.stream_id)
            return False, str(e)
    
    async def _gift_flowers(self, user_id: str, group_id: str, quantity: int) -> tuple[bool, str]:
        """赠送花花提升好感度"""
        user_currency = currency_manager.get_currency(user_id, group_id)
        
        logger.info(f"💐 赠送花花: user={user_id}, amount={quantity}, balance={user_currency}")
        
        if user_currency < quantity:
            await send_text(
                f"❌ 花花不足！\n"
                f"━━━━━━━━━━━━\n"
                f"💐 想要赠送: {quantity} 花花\n"
                f"💳 当前余额: {user_currency} 花花\n"
                f"❌ 缺少: {quantity - user_currency} 花花\n\n"
                f"💡 发送 /签到 获取更多花花",
                stream_id=self.stream_id
            )
            return False, "not enough flowers"
        
        # 扣除花花
        currency_manager.add_currency(user_id, -quantity, group_id)
        
        # 增加好感度（1:1）
        favor_manager.add_favor(user_id, quantity, group_id)
        current_favor = favor_manager.get_favor(user_id, group_id)
        current_currency = currency_manager.get_currency(user_id, group_id)
        
        gift_msg = (
            f"💐 赠送成功！\n"
            f"━━━━━━━━━━━━\n"
            f"💛 赠送花花: {quantity} 朵\n"
            f"💕 获得好感: +{quantity}♡\n"
            f"━━━━━━━━━━━━\n"
            f"💳 剩余花花: {current_currency}\n"
            f"💖 当前好感: {current_favor}♡\n\n"
            f"💡 爱莉很开心！要继续加油哦~"
        )
        
        await send_text(gift_msg, stream_id=self.stream_id)
        return True, "ok"
    
    async def _gift_item(self, user_id: str, group_id: str, item_name: str, quantity: int) -> tuple[bool, str]:
        """赠送物品提升好感度"""
        logger.info(f"🎁 赠送物品: user={user_id}, item={item_name}, quantity={quantity}")
        
        # 查找物品
        item_result = ITEM_ALIASES.get(item_name)
        if not item_result:
            for key in ITEM_ALIASES:
                if item_name in key or key in item_name:
                    item_result = ITEM_ALIASES[key]
                    break
        
        if not item_result:
            await send_text(
                f"❌ 未找到物品「{item_name}」\n"
                f"💡 使用 /背包 查看你的物品\n"
                f"💡 使用 /赠送 花花 <数量> 赠送花花",
                stream_id=self.stream_id
            )
            return False, "item not found"
        
        full_name, price = item_result
        owned_count = shop_manager.get_inventory_item_count(user_id, full_name, group_id)
        
        if owned_count < quantity:
            await send_text(
                f"❌ 背包物品不足\n"
                f"━━━━━━━━━━━━\n"
                f"🎁 想要赠送: {full_name} x{quantity}\n"
                f"📦 当前拥有: {full_name} x{owned_count}\n"
                f"❌ 缺少: {quantity - owned_count}个\n\n"
                f"💡 使用 /商店 购买更多物品",
                stream_id=self.stream_id
            )
            return False, "not enough items"
        
        # 计算好感度
        success, full_name, total_favor, details = favor_manager.calculate_gift_favor(item_name, quantity)
        
        if not success:
            await send_text(f"❌ 该物品无法赠送", stream_id=self.stream_id)
            return False, "cannot gift"
        
        # 扣除物品
        key = _make_key(user_id, group_id)
        current_owned = shop_manager.user_inventory.get(key, {}).get(full_name, 0)
        shop_manager.user_inventory[key][full_name] = current_owned - quantity
        if shop_manager.user_inventory[key][full_name] <= 0:
            del shop_manager.user_inventory[key][full_name]
        
        # 增加好感度
        favor_manager.add_favor(user_id, total_favor, group_id)
        current_favor = favor_manager.get_favor(user_id, group_id)
        
        # 构建回复消息
        gift_msg = (
            f"🎁 赠送成功！\n"
            f"━━━━━━━━━━━━\n"
            f"💝 赠送物品: {full_name} x{quantity}\n"
            f"💕 获得好感: +{total_favor}♡\n"
        )
        
        if quantity > 1 and details:
            gift_msg += f"\n📋 详细加成：\n"
            gift_msg += "\n".join(details[:5])
            if len(details) > 5:
                gift_msg += f"\n  ... 还有{len(details)-5}件"
            gift_msg += f"\n━━━━━━━━━━━━\n"
            gift_msg += f"💕 总好感: +{total_favor}♡\n"
        
        gift_msg += f"━━━━━━━━━━━━\n"
        remaining = shop_manager.user_inventory.get(key, {}).get(full_name, 0)
        if remaining > 0:
            gift_msg += f"📦 剩余: {full_name} x{remaining}\n"
        gift_msg += f"💖 当前好感: {current_favor}♡"
        
        await send_text(gift_msg, stream_id=self.stream_id)
        return True, "ok"
    
    def _get_help_text(self) -> str:
        return (
            "💝 赠送帮助\n"
            "━━━━━━━━━━━━\n"
            "📝 使用方法：\n\n"
            "1️⃣ 赠送花花提升好感度：\n"
            "   /赠送 花花 <数量>\n"
            "   1花花 = 1好感度\n\n"
            "2️⃣ 赠送物品提升好感度：\n"
            "   /赠送 <物品> [数量]\n"
            "   不同物品获得不同好感度\n\n"
            "💡 示例：\n"
            "   /赠送 花花 100\n"
            "   /赠送 蒸蛋\n"
            "   /赠送 蛋糕 3\n\n"
            "💡 使用 /好感度 查看当前好感\n"
            "💡 使用 /背包 查看你的物品\n"
            "💡 使用 /商店 购买物品"
        )
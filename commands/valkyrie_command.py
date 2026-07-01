"""
女武神相关命令
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.app.plugin_system.api.log_api import get_logger
from src.app.plugin_system.api.send_api import send_text
from src.app.plugin_system.base import BaseCommand, cmd_route
from src.app.plugin_system.types import PermissionLevel, ChatType
from src.app.plugin_system.api.stream_api import get_stream_info

from ..handlers.valkyrie_handler import valkyrie_handler
from ..data.valkyrie_data import VALKYRIES, DOLLS, SYNERGISTS
from ..handlers.currency import currency_manager

if TYPE_CHECKING:
    from ..plugin import ElysiaDicePlugin

logger = get_logger("elysia_dice.valkyrie_command")


class PullValkyrieCommand(BaseCommand):
    """抽取女武神"""
    command_name: str = "抽取女武神"
    command_description: str = "随机抽取女武神/人偶/协同者（每日10次）"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"

    @classmethod
    def match(cls, parts: list[str]) -> int:
        if not parts:
            return 0
        if parts[0] == "抽取女武神":
            return 1
        return 0

    @cmd_route()
    async def handle_root(self) -> tuple[bool, str]:
        try:
            user_id = str(self._message.sender_id) if self._message else ""
            if not user_id:
                await send_text("无法识别用户身份", stream_id=self.stream_id)
                return False, "no user"

            info = await get_stream_info(self.stream_id)
            group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""

            can_pull, count, _ = valkyrie_handler.can_pull_valkyrie(user_id, group_id)
            if not can_pull:
                await send_text("⚠️ 今日抽取次数已用完（最多10次）", stream_id=self.stream_id)
                return True, "max pulls"

            cost = valkyrie_handler.get_pull_cost(count)

            # 检查花花（如果不是免费）
            if cost > 0:
                currency = currency_manager.get_currency(user_id, group_id)
                if currency < cost:
                    await send_text(
                        f"💐 花花不足！\n"
                        f"当前花花：{currency}\n"
                        f"需要花花：{cost}\n"
                        f"💡 发送 /签到 获取花花",
                        stream_id=self.stream_id
                    )
                    return True, "no currency"

            # 执行抽取
            result = valkyrie_handler.do_pull_valkyrie(user_id, group_id)

            if "error" in result:
                await send_text(result["error"], stream_id=self.stream_id)
                return True, "error"

            # 扣除花花
            if result["cost"] > 0:
                currency_manager.add_currency(user_id, -result["cost"], group_id)

            valkyrie = result["valkyrie"]
            cost_str = "免费" if result["is_free"] else f"{result['cost']}花花"

            # ========== 新增：自动加入图鉴 ==========
            if valkyrie[0] < 800:
                valkyrie_type = "valkyrie"
            elif valkyrie[0] < 900:
                valkyrie_type = "doll"
            else:
                valkyrie_type = "synergist"

            valkyrie_handler.add_to_collection(user_id, group_id, valkyrie, valkyrie_type)
            # =====================================

            # 判断类型
            if valkyrie[0] < 800:
                valkyrie_type_label = "女武神装甲"
            elif valkyrie[0] < 900:
                valkyrie_type_label = "武装人偶"
            else:
                valkyrie_type_label = "协同者"

            # 新增检查
            is_new = not valkyrie_handler.has_valkyrie_before(user_id, group_id, valkyrie[0])

            # 构建信息
            if valkyrie_type_label == "女武神装甲":
                v_info = valkyrie_handler.query_valkyrie(user_id, group_id, str(valkyrie[0]))
                pull_count = v_info.get("pull_count", 0)
                set_count = v_info.get("set_count", 0)

                star_icon = {"B": "⭐⭐", "A": "⭐⭐⭐", "S": "⭐⭐⭐⭐"}.get(valkyrie[3], "")

                msg = f"🎰 抽取女武神\n"
                msg += f"━━━━━━━━━━━━\n"
                if is_new:
                    msg += f"🆕 新获得！\n"
                msg += f"🏷️ {valkyrie[0]} · {valkyrie[1]}\n"
                msg += f"👤 所属：{valkyrie[2]}\n"
                msg += f"⭐ 等级：{valkyrie[3]} {star_icon}\n"
                msg += f"⚡ 属性：{valkyrie[4]}\n"
                if valkyrie[5]:
                    msg += f"🌠 星环分野：{valkyrie[5]}\n"
                msg += f"📊 被抽到：{pull_count}次\n"
                msg += f"📌 被设为今日：{set_count}次\n"
                msg += f"━━━━━━━━━━━━\n"
                msg += f"💰 花费：{cost_str}\n"
                msg += f"📅 今日第 {result['pull_number']}/10 次"
            else:
                star_icon = {"A": "⭐⭐⭐", "S": "⭐⭐⭐⭐"}.get(valkyrie[2], "")

                msg = f"🎰 抽取女武神\n"
                msg += f"━━━━━━━━━━━━\n"
                if is_new:
                    msg += f"🆕 新获得！\n"
                msg += f"🏷️ {valkyrie[0]} · {valkyrie[1]}\n"
                msg += f"📦 类型：{valkyrie_type_label}\n"
                msg += f"⭐ 等级：{valkyrie[2]} {star_icon}\n"
                msg += f"━━━━━━━━━━━━\n"
                msg += f"💰 花费：{cost_str}\n"
                msg += f"📅 今日第 {result['pull_number']}/10 次"

            await send_text(msg, stream_id=self.stream_id)
            return True, "ok"

        except Exception as e:
            logger.error(f"抽取女武神失败: {e}", exc_info=True)
            await send_text(f"抽取失败: {str(e)}", stream_id=self.stream_id)
            return False, str(e)


class TodayValkyrieCommand(BaseCommand):
    """今日女武神"""
    command_name: str = "今日女武神"
    command_description: str = "设置今日女武神（每天最多3个）"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"

    @classmethod
    def match(cls, parts: list[str]) -> int:
        if not parts:
            return 0
        if parts[0] == "今日女武神":
            return 1
        return 0

    @cmd_route()
    async def handle_root(self, query: str = "") -> tuple[bool, str]:
        try:
            user_id = str(self._message.sender_id) if self._message else ""
            if not user_id:
                await send_text("无法识别用户身份", stream_id=self.stream_id)
                return False, "no user"

            info = await get_stream_info(self.stream_id)
            group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""

            query = query.strip()
            if not query:
                # 查询今日女武神
                today_list = valkyrie_handler.get_today_valkyries(user_id, group_id)
                if not today_list:
                    await send_text("📅 今日尚未设置女武神\n💡 发送 /今日女武神 <ID/名称> 设置", stream_id=self.stream_id)
                    return True, "no today"
                
                msg = "📅 今日女武神：\n"
                msg += f"━━━━━━━━━━━━\n"
                for v in today_list:
                    msg += f"🏷️ {v['id']} · {v['name']}\n"
                msg += f"━━━━━━━━━━━━\n"
                msg += f"📊 已设置 {len(today_list)}/3"
                
                await send_text(msg, stream_id=self.stream_id)
                return True, "ok"

            # 设置今日女武神
            result = valkyrie_handler.set_today_valkyrie(user_id, group_id, query)

            if "error" in result:
                await send_text(f"❌ {result['error']}", stream_id=self.stream_id)
                return True, "error"

            valkyrie = result["valkyrie"]
            msg = f"✅ 已设置今日女武神\n"
            msg += f"━━━━━━━━━━━━\n"
            msg += f"🏷️ {valkyrie[0]} · {valkyrie[1]}\n"
            msg += f"👤 {valkyrie[2]} ｜ ⭐{valkyrie[3]}\n"
            msg += f"━━━━━━━━━━━━\n"
            msg += f"📊 今日进度：{result['current_count']}/3"

            await send_text(msg, stream_id=self.stream_id)
            return True, "ok"

        except Exception as e:
            logger.error(f"今日女武神失败: {e}", exc_info=True)
            await send_text(f"设置失败: {str(e)}", stream_id=self.stream_id)
            return False, str(e)


class FullCollectionCommand(BaseCommand):
    """全图鉴"""
    command_name: str = "全图鉴"
    command_description: str = "查看全部女武神/人偶/协同者图鉴"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"

    @classmethod
    def match(cls, parts: list[str]) -> int:
        if not parts:
            return 0
        if parts[0] == "全图鉴":
            return 1
        return 0

    @cmd_route()
    async def handle_root(self, page: str = "") -> tuple[bool, str]:
        try:
            collection = valkyrie_handler.get_full_collection()
            
            page_num = 1
            if page.strip():
                try:
                    page_num = int(page)
                except ValueError:
                    page_num = 1
            
            items_per_page = 30
            total = collection["total"]
            total_pages = (total + items_per_page - 1) // items_per_page
            
            if page_num > total_pages:
                page_num = total_pages
            
            start = (page_num - 1) * items_per_page
            end = start + items_per_page
            
            # 合并所有
            all_items = []
            all_items.append(("─── 女武神装甲 ───", "", "", "", ""))
            for v in collection["valkyries"]:
                all_items.append(("V", v[0], v[1], v[3], v[4]))
            all_items.append(("─── 武装人偶 ───", "", "", "", ""))
            for d in collection["dolls"]:
                all_items.append(("D", d[0], d[1], d[2], ""))
            all_items.append(("─── 协同者 ───", "", "", "", ""))
            for s in collection["synergists"]:
                all_items.append(("S", s[0], s[1], s[2], ""))
            
            page_items = all_items[start:end]
            
            msg = f"📚 全图鉴 (第{page_num}/{total_pages}页)\n"
            msg += f"━━━━━━━━━━━━\n"
            msg += f"总计：{total} 个\n"
            msg += f"  · 女武神装甲：{len(collection['valkyries'])} 个\n"
            msg += f"  · 武装人偶：{len(collection['dolls'])} 个\n"
            msg += f"  · 协同者：{len(collection['synergists'])} 个\n"
            msg += f"━━━━━━━━━━━━\n"
            
            for item in page_items:
                if item[0] in ("───", ""):
                    msg += f"\n{item[0]} {item[1]}\n"
                else:
                    msg += f"[{item[0]}] {item[2]} · {item[3]} {item[4]}\n"
            
            if total_pages > 1:
                msg += f"━━━━━━━━━━━━\n"
                msg += f"💡 发送 /全图鉴 <页码> 翻页"
            
            await send_text(msg, stream_id=self.stream_id)
            return True, "ok"

        except Exception as e:
            logger.error(f"全图鉴失败: {e}", exc_info=True)
            await send_text(f"查询失败: {str(e)}", stream_id=self.stream_id)
            return False, str(e)


class MyCollectionCommand(BaseCommand):
    """我的图鉴"""
    command_name: str = "我的图鉴"
    command_description: str = "查看我的收集程度"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"

    command_aliases: list[str] = ["图鉴"]

    @classmethod
    def match(cls, parts: list[str]) -> int:
        if not parts:
            return 0
        if parts[0] in ("我的图鉴", "图鉴"):
            return 1
        return 0

    @cmd_route()
    async def handle_root(self) -> tuple[bool, str]:
        try:
            user_id = str(self._message.sender_id) if self._message else ""
            if not user_id:
                await send_text("无法识别用户身份", stream_id=self.stream_id)
                return False, "no user"

            info = await get_stream_info(self.stream_id)
            group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""

            collection = valkyrie_handler.get_user_collection(user_id, group_id)

            msg = f"📚 我的图鉴\n"
            msg += f"━━━━━━━━━━━━\n"
            msg += f"🎯 收集度：{collection['percentage']}%\n"
            msg += f"📊 已收集：{collection['total_owned']}/{collection['total_all']}\n"
            msg += f"━━━━━━━━━━━━\n"
            msg += f"👤 女武神装甲：{len(collection['owned_valkyries'])}/{len(VALKYRIES)}\n"
            msg += f"🎎 武装人偶：{len(collection['owned_dolls'])}/{len(DOLLS)}\n"
            msg += f"🤝 协同者：{len(collection['owned_synergists'])}/{len(SYNERGISTS)}\n"
            msg += f"━━━━━━━━━━━━\n"
            
            # 进度条
            bar_length = 20
            filled = int(collection['percentage'] / 100 * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            msg += f"[{bar}] {collection['percentage']}%"

            await send_text(msg, stream_id=self.stream_id)
            return True, "ok"

        except Exception as e:
            logger.error(f"我的图鉴失败: {e}", exc_info=True)
            await send_text(f"查询失败: {str(e)}", stream_id=self.stream_id)
            return False, str(e)


class MyValkyrieCommand(BaseCommand):
    """我的女武神"""
    command_name: str = "我的女武神"
    command_description: str = "查询女武神详情"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"

    @classmethod
    def match(cls, parts: list[str]) -> int:
        if not parts:
            return 0
        if parts[0] == "我的女武神":
            return 1
        return 0

    @cmd_route()
    async def handle_root(self, query: str = "") -> tuple[bool, str]:
        try:
            user_id = str(self._message.sender_id) if self._message else ""
            if not user_id:
                await send_text("无法识别用户身份", stream_id=self.stream_id)
                return False, "no user"

            info = await get_stream_info(self.stream_id)
            group_id = str(info.get("group_id", "")) if isinstance(info, dict) else ""

            query = query.strip()
            if not query:
                await send_text("💡 格式：/我的女武神 <ID/名称>", stream_id=self.stream_id)
                return True, "no query"

            result = valkyrie_handler.query_valkyrie(user_id, group_id, query)

            if "error" in result:
                await send_text(f"❌ {result['error']}", stream_id=self.stream_id)
                return True, "error"

            valkyrie = result["valkyrie"]
            has = valkyrie_handler.has_valkyrie(user_id, group_id, valkyrie[0])
            owned_icon = "✅" if has else "❌"

            if valkyrie[0] < 800:
                # 女武神装甲
                star_map = {"B": 2, "A": 3, "S": 4}
                stars = "⭐" * star_map.get(valkyrie[3], 0)
                
                msg = f"📊 女武神详情\n"
                msg += f"━━━━━━━━━━━━\n"
                msg += f"🏷️ ID：{valkyrie[0]}\n"
                msg += f"📛 装甲名：{valkyrie[1]}\n"
                msg += f"👤 所属角色：{valkyrie[2]}\n"
                msg += f"⭐ 等级：{valkyrie[3]} {stars}\n"
                msg += f"⚡ 属性：{valkyrie[4]}\n"
                if valkyrie[5]:
                    msg += f"🌠 星环分野：{valkyrie[5]}\n"
                msg += f"📦 拥有状态：{owned_icon}\n"
                msg += f"━━━━━━━━━━━━\n"
                msg += f"🎰 被抽取次数：{result['pull_count']}\n"
                msg += f"📌 被设为今日：{result['set_count']}\n"
                msg += f"━━━━━━━━━━━━\n"
                
                if not has:
                    msg += f"💡 发送 /抽取女武神 尝试获取"
            else:
                msg = f"📊 详情查询\n"
                msg += f"━━━━━━━━━━━━\n"
                msg += f"🏷️ ID：{valkyrie[0]}\n"
                msg += f"📛 名称：{valkyrie[1]}\n"
                msg += f"⭐ 等级：{valkyrie[2]}\n"
                msg += f"📦 拥有状态：{owned_icon}\n"
                msg += f"━━━━━━━━━━━━\n"
                msg += f"🎰 被抽取次数：{result['pull_count']}\n"
                msg += f"📌 被设为今日：{result['set_count']}\n"

            await send_text(msg, stream_id=self.stream_id)
            return True, "ok"

        except Exception as e:
            logger.error(f"我的女武神失败: {e}", exc_info=True)
            await send_text(f"查询失败: {str(e)}", stream_id=self.stream_id)
            return False, str(e)
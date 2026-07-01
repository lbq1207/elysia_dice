"""
帮助命令
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.app.plugin_system.api.log_api import get_logger
from src.app.plugin_system.api.send_api import send_text
from src.app.plugin_system.base import BaseCommand, cmd_route
from src.app.plugin_system.types import PermissionLevel, ChatType

if TYPE_CHECKING:
    from ..plugin import ElysiaDicePlugin

logger = get_logger("elysia_dice.help_command")

HELP_CONTENT = """🌸 爱莉喵骰娘 - 帮助指南 🌸
━━━━━━━━━━━━

📌 0. 帮助系统
  /帮助 & /help   - 查看帮助指南

📌 1. 签到系统
  /签到           - 每日签到，获得花花与好感度
  /花花           - 查询当前花花数量
  /排行           - 查看群内好感度排行榜

📌 2. 商店与抽奖系统
  /商店           - 查看可购买物品
  /购买 <物品> [数量] - 购买物品（使用花花）
  /抽奖           - 每日抽奖（消耗花花）

📌 3. 背包与好感度系统
  /背包           - 查看背包物品
  /好感度         - 查询当前好感度
  /赠送 <@用户> <物品> [数量] - 赠送物品给他人
  /转让 <@用户> <花花数量>    - 转让花花给他人

📌 4. 模拟抽卡与水晶系统
  /水晶           - 查询当前水晶数量
  /获取水晶       - 每日领取免费水晶
  /补给           - 查看补给菜单
  /角色补给A（或B） & /跃升补给 - 角色补给
  /装备补给A（或B） & /跃升武装 - 装备补给
  /协同补给       - 协同补给
  /服装补给       - 服装补给
  💡 格式：/角色补给A [次数]（默认单抽，10次=十连）

📌 5. 女武神抽取系统
  /抽取女武神     - 随机抽取女武神（每日10次）
  /今日女武神 <ID/名称> - 设置今日女武神（每日最多3个）
  /今日女武神     - 查看已设置的今日女武神
  /全图鉴 [页码]  - 查看全部女武神/人偶/协同者图鉴
  /图鉴 & /我的图鉴 - 查看我的收集进度
  /我的女武神 <ID/名称> - 查询女武神详情

📌 6. 群友老婆系统
  /今日群友 & /群友老婆 & /群老婆 - 随机抽取今日群友老婆
  /今日群友 换    - 更换群友（每日最多3次）
  /结婚 @对方 & /申请结婚 @对方 - 向对方申请结婚
  /同意           - 同意结婚申请
  /拒绝           - 拒绝结婚申请

━━━━━━━━━━━━
💡 提示：
  • 所有次数每日0点重置
  • /set （/elyset）和 /get （/elyget）为开发者工具（仅管理员可用）
  • 各补给保底规则详见对应命令说明

🌸 祝你在爱莉的爱之世界中玩得开心！🌸"""


class HelpCommand(BaseCommand):
    """帮助命令 - /help"""
    command_name: str = "help"
    command_description: str = "查看帮助指南"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"

    @classmethod
    def match(cls, parts: list[str]) -> int:
        if not parts:
            return 0
        if parts[0] in ("help", "帮助"):
            return 1
        return 0

    @cmd_route()
    async def handle_root(self, section: str = "") -> tuple[bool, str]:
        """处理帮助命令"""
        try:
            section = section.strip()

            if section:
                # 分部帮助
                section_help = self._get_section_help(section)
                if section_help:
                    await send_text(section_help, stream_id=self.stream_id)
                else:
                    await send_text(
                        f"❌ 未找到「{section}」相关帮助\n"
                        f"可用分类：签到、商店、背包、抽卡、女武神、群友\n"
                        f"💡 发送 /帮助 查看完整指南",
                        stream_id=self.stream_id
                    )
            else:
                # 完整帮助
                await send_text(HELP_CONTENT, stream_id=self.stream_id)

            return True, "ok"

        except Exception as e:
            logger.error(f"帮助命令失败: {e}", exc_info=True)
            await send_text(f"获取帮助失败: {str(e)}", stream_id=self.stream_id)
            return False, str(e)

    @staticmethod
    def _get_section_help(section: str) -> str:
        """获取分部帮助"""
        section = section.lower()

        sections = {
            "签到": """📌 签到系统
━━━━━━━━━━━━
/签到 - 每日签到
  • 每天可签到1次，0点重置
  • 签到获得花花奖励
  • 连续签到可获得额外奖励
  • 签到增加好感度

/花花 - 查询花花
  • 查看当前拥有的花花数量
  • 花花可用于商店购买、抽奖等

/排行 - 好感度排行榜
  • 查看群内用户好感度排名
  • 好感度通过签到、赠送等获得
━━━━━━━━━━━━""",

            "商店": """📌 商店与抽奖系统
━━━━━━━━━━━━
/商店 - 查看商店物品
  • 使用花花购买各种物品

/购买 <物品> [数量] - 购买物品
  • 例：/购买 蒸蛋 5
  • 物品会存入背包

/抽奖 - 每日抽奖
  • 每天可抽奖多次
  • 消耗花花，获得随机物品
━━━━━━━━━━━━""",

            "背包": """📌 背包与好感度系统
━━━━━━━━━━━━
/背包 - 查看背包
  • 查看所有拥有的物品

/好感度 - 查询好感度
  • 查看当前好感度数值
  • 不同好感度范围会有相应的评级
  • 好感度每月1日、16日重置

/赠送 <@用户> <物品> [数量] - 赠送物品
  • 例：/赠送 蒸蛋 3
  • 赠送会增加爱莉对你的好感度

/转让 <@用户> <数量> - 转让花花
  • 例：/转让 @小明 100
  • 将花花转给其他用户
━━━━━━━━━━━━""",

            "抽卡": """📌 模拟抽卡与水晶系统
━━━━━━━━━━━━
/水晶 - 查询水晶
  • 查看当前水晶数量

/获取水晶 - 领取水晶
  • 每日可领取免费水晶
  • 水晶用于模拟抽卡

补给卡池：
  /角色补给A [次数] - 「愈生佑翎」角色补给
  /角色补给B [次数] - 「嗨♪爱愿妖精♥」角色补给
  /装备补给A [次数] - 「愈生佑翎」装备补给
  /装备补给B [次数] - 「嗨♪爱愿妖精♥」装备补给
  /协同补给 [次数]  - S级协同者「希娜狄雅」
  /跃升补给 [次数]  - 「一客逍游」跃升补给
  /跃升武装 [次数]  - 「一客逍游」跃升武装
  /服装补给         - 「霁月婵娟」服装补给

价格：
  • 单抽：280水晶
  • 十连：2800水晶
  • 服装补给费用递增（首次免费）

保底规则：
  • 角色补给：90次保底S级，10次保底A级
  • 装备补给：60次保底UP武器，10次保底4星
  • 协同补给：60次保底S级协同者
  • 跃升补给：独立保底，每10次得晋升印章
  • 跃升武装：独立保底，每10次得840水晶
  • 服装补给：10次抽完重置奖池

继承规则：
  • 角色补给A/B共享保底
  • 装备补给A/B共享保底
  • 跃升补给/武装独立保底
━━━━━━━━━━━━""",

            "女武神": """📌 女武神抽取系统
━━━━━━━━━━━━
/抽取女武神 - 随机抽取女武神
  • 每日最多10次
  • 第1次免费
  • 第2次5花花，第3-10次10花花
  • 可抽到女武神装甲、武装人偶、协同者

/今日女武神 <ID/名称> - 设置今日女武神
  • 每日最多设置3个
  • 例：/今日女武神 217
  • 例：/今日女武神 愈生佑翎

/今日女武神 - 查看已设置的女武神

/全图鉴 [页码] - 查看完整图鉴
  • 包含所有女武神装甲、人偶、协同者
  • 每页显示30个

/图鉴 或 /我的图鉴 - 查看收集进度
  • 显示已收集/总数
  • 显示收集百分比

/我的女武神 <ID/名称> - 查询详情
  • 显示装甲名、所属角色、等级
  • 显示属性、星环分野
  • 显示被抽到次数、被设今日次数
━━━━━━━━━━━━""",

            "群友": """📌 群友老婆系统
━━━━━━━━━━━━
/今日群友 - 抽取今日群友老婆
  • 也可用 /群友老婆 或 /群老婆
  • 从群成员中随机抽取

/今日群友 换 - 更换群友
  • 每日最多3次
  • 第1次免费
  • 第2次10花花，第3次20花花

/结婚 @对方 - 申请结婚
  • 也可用 /申请结婚 或 /申请
  • 艾特对方发起结婚申请

/同意 - 同意结婚申请
  • 同意后婚姻关系持续到当日结束

/拒绝 - 拒绝结婚申请
  • 拒绝后对方可重新选择

规则说明：
  • 被抽中的群友会被锁定
  • 已婚用户无法被其他人抽取
  • 婚姻关系当日有效
━━━━━━━━━━━━""",
        }

        return sections.get(section, "")


class HelpCNCommand(HelpCommand):
    """帮助命令 - /帮助"""
    command_name: str = "帮助"
    command_description: str = "查看帮助指南（中文）"
    permission_level: PermissionLevel = PermissionLevel.USER
    chat_type: ChatType = ChatType.ALL
    plugin: "ElysiaDicePlugin"

    @classmethod
    def match(cls, parts: list[str]) -> int:
        if not parts:
            return 0
        if parts[0] in ("help", "帮助"):
            # 确保 /帮助 匹配这个，/help 匹配上面的
            # 这里通过优先级处理：如果第一个词是"帮助"，优先匹配这个
            if parts[0] == "帮助":
                return 2  # 更高优先级
            return 0
        return 0
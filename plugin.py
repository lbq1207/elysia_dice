"""
elysia_dice 插件入口
"""
from __future__ import annotations

from src.core.components.loader import register_plugin
from src.core.components.base import BasePlugin
from src.app.plugin_system.api.log_api import get_logger

from .commands.sign_command import SignCommand
from .commands.query_command import QueryCommand
from .commands.help_command import HelpCommand, HelpCNCommand
from .commands.dev_command import SetCommand, GetCommand, ElySetCommand, ElyGetCommand
from .commands.shop_command import ShopCommand, BuyCommand, LotteryCommand, InventoryCommand, GiftCommand
from .commands.favor_command import FavorCommand, RankCommand
from .commands.transfer_command import TransferCommand
from .commands.crystal_command import SupplyCommand, GetCrystalCommand, CrystalQueryCommand
from .commands.supply_command import (
    RoleSupplyACommand, RoleSupplyBCommand,
    EquipSupplyACommand, EquipSupplyBCommand,
    SynergySupplyCommand,
    AdvancedSupplyCommand, AdvancedArmamentCommand,
    CostumeSupplyCommand,
)
from .commands.valkyrie_command import (
    PullValkyrieCommand, TodayValkyrieCommand,
    FullCollectionCommand, MyCollectionCommand,
    MyValkyrieCommand,
)
from .commands.today_groupmate_command import TodayGroupmateCommand, ProposeCommand, AcceptCommand, RejectCommand

logger = get_logger("elysia_dice")

__version__ = "1.0.0"
__plugin_name__ = "爱莉喵骰娘"


@register_plugin
class ElysiaDicePlugin(BasePlugin):
    plugin_name = "elysia_dice"
    plugin_version = "1.0.0"
    plugin_description = "多功能骰娘插件"
    plugin_author = "lbq1207"

    def get_components(self) -> list[type]:
        return [
            SignCommand, QueryCommand,
            HelpCommand, HelpCNCommand,
            SetCommand, GetCommand, ElySetCommand, ElyGetCommand,
            ShopCommand, BuyCommand, LotteryCommand, GiftCommand, InventoryCommand,
            FavorCommand, RankCommand, TransferCommand,
            SupplyCommand, GetCrystalCommand, CrystalQueryCommand,
            RoleSupplyACommand, RoleSupplyBCommand, EquipSupplyACommand, EquipSupplyBCommand,
            SynergySupplyCommand, AdvancedSupplyCommand, AdvancedArmamentCommand, CostumeSupplyCommand,
            PullValkyrieCommand, TodayValkyrieCommand, FullCollectionCommand, MyCollectionCommand, MyValkyrieCommand,
            TodayGroupmateCommand, ProposeCommand, AcceptCommand, RejectCommand,
        ]

    async def on_plugin_loaded(self):
        logger.info(f"✅ {__plugin_name__} v{__version__} 已加载")
        from .handlers.auto_record import auto_record
        count = 0
        for cmd_cls in self.get_components():
            if hasattr(cmd_cls, 'handle_root'):
                cmd_cls.handle_root = auto_record(cmd_cls.handle_root)
                count += 1
        logger.info(f"📝 已给 {count} 个命令注入用户自动记录")
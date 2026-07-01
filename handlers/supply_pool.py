"""
崩坏3补给池配置与抽卡逻辑
支持：角色补给、装备补给、协同补给（后续可扩充：服装、扩充、家园）
"""
import random
import bisect
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import json

from src.app.plugin_system.api.log_api import get_logger

logger = get_logger("elysia_dice.supply_pool")

SEPARATE_BY_GROUP = True


def _make_key(user_id: str, group_id: str = "") -> str:
    if SEPARATE_BY_GROUP and group_id:
        return f"{group_id}:{user_id}"
    return user_id


# ==================== 补给类型枚举 ====================

class SupplyType(Enum):
    """补给类型"""
    ROLE = "role"           # 角色补给
    EQUIP = "equip"         # 装备补给
    SYNERGY = "synergy"     # 协同补给
    # 后续扩充：
    # COSTUME = "costume"   # 服装补给
    # EXPAND = "expand"     # 扩充补给
    # HOME = "home"         # 家园补给


# ==================== 数据模型 ====================

@dataclass
class SupplyItem:
    """补给物品"""
    name: str
    quality: str      # S/A/4星/3星/2星
    item_type: str    # 角色卡/武器/圣痕/协同者/养成材料/通用材料
    probability: float
    quantity: int = 1


@dataclass
class PoolConfig:
    """补给池配置"""
    pool_id: str
    pool_name: str
    supply_type: SupplyType
    # 主要UP物品
    up_item_name: str
    up_item_prob: float
    # A级UP
    a_up_items: List[str] = field(default_factory=list)
    a_up_prob: float = 0.0
    # 物品列表
    items: List[SupplyItem] = field(default_factory=list)
    # 保底配置
    s_pity: int = 90
    a_pity: int = 10
    cost_per_pull: int = 280


@dataclass
class PullResult:
    """单抽结果"""
    item: SupplyItem
    pity_counter: int
    a_pity_counter: int
    is_s_pity: bool = False
    is_a_pity: bool = False


@dataclass
class MultiPullResult:
    """多抽结果"""
    results: List[PullResult]
    final_pity: int
    final_a_pity: int
    total_cost: int
    s_count: int
    a_count: int
    up_s_count: int


# ==================== 共用物品池 ====================

# --- 角色补给共用3星武器(23个) ---
SHARED_ROLE_WEAPONS_3: List[SupplyItem] = [
    SupplyItem("水妖精I型", "3星", "武器", 0.4728),
    SupplyItem("水妖精II型", "3星", "武器", 0.4728),
    SupplyItem("火妖精I型", "3星", "武器", 0.4728),
    SupplyItem("火妖精II型", "3星", "武器", 0.4728),
    SupplyItem("苗刀·电魂", "3星", "武器", 0.4728),
    SupplyItem("苗刀·雷妖", "3星", "武器", 0.4728),
    SupplyItem("脉冲太刀17式", "3星", "武器", 0.4728),
    SupplyItem("脉冲太刀19式", "3星", "武器", 0.4728),
    SupplyItem("马尔可夫A型", "3星", "武器", 0.4728),
    SupplyItem("马尔可夫C型", "3星", "武器", 0.4728),
    SupplyItem("阴极子炮07式", "3星", "武器", 0.4728),
    SupplyItem("阴极子炮09式", "3星", "武器", 0.4728),
    SupplyItem("氮素结晶剑", "3星", "武器", 0.4728),
    SupplyItem("超重剑·冲锋", "3星", "武器", 0.4728),
    SupplyItem("电离共振剑", "3星", "武器", 0.4728),
    SupplyItem("超重剑·王蛇", "3星", "武器", 0.4728),
    SupplyItem("黑色粉碎者", "3星", "武器", 0.4728),
    SupplyItem("火天使", "3星", "武器", 0.4727),
    SupplyItem("雷天使", "3星", "武器", 0.4727),
    SupplyItem("CAS-X圣徒", "3星", "武器", 0.4727),
    SupplyItem("白星驱逐者", "3星", "武器", 0.4727),
    SupplyItem("黑曜切割", "3星", "武器", 0.4727),
    SupplyItem("等离子长枪", "3星", "武器", 0.4727),
]

# --- 角色补给共用3星圣痕(36个) ---
SHARED_ROLE_STIGMATA_3: List[SupplyItem] = [
    SupplyItem("巴托里·伊丽莎白（上）", "3星", "圣痕", 0.3783),
    SupplyItem("巴托里·伊丽莎白（中）", "3星", "圣痕", 0.3783),
    SupplyItem("巴托里·伊丽莎白（下）", "3星", "圣痕", 0.3783),
    SupplyItem("呼邪（上）", "3星", "圣痕", 0.3783),
    SupplyItem("呼邪（中）", "3星", "圣痕", 0.3783),
    SupplyItem("呼邪（下）", "3星", "圣痕", 0.3783),
    SupplyItem("阿提拉（上）", "3星", "圣痕", 0.3782),
    SupplyItem("阿提拉（中）", "3星", "圣痕", 0.3782),
    SupplyItem("阿提拉（下）", "3星", "圣痕", 0.3782),
    SupplyItem("坂本龙马（上）", "3星", "圣痕", 0.3782),
    SupplyItem("坂本龙马（中）", "3星", "圣痕", 0.3782),
    SupplyItem("坂本龙马（下）", "3星", "圣痕", 0.3782),
    SupplyItem("尼古拉·特斯拉（上）", "3星", "圣痕", 0.3782),
    SupplyItem("尼古拉·特斯拉（中）", "3星", "圣痕", 0.3782),
    SupplyItem("尼古拉·特斯拉（下）", "3星", "圣痕", 0.3782),
    SupplyItem("查理曼（上）", "3星", "圣痕", 0.3782),
    SupplyItem("查理曼（中）", "3星", "圣痕", 0.3782),
    SupplyItem("查理曼（下）", "3星", "圣痕", 0.3782),
    SupplyItem("奥吉尔（上）", "3星", "圣痕", 0.3782),
    SupplyItem("奥吉尔（中）", "3星", "圣痕", 0.3782),
    SupplyItem("奥吉尔（下）", "3星", "圣痕", 0.3782),
    SupplyItem("时雨绮罗（上）", "3星", "圣痕", 0.3782),
    SupplyItem("时雨绮罗（中）", "3星", "圣痕", 0.3782),
    SupplyItem("时雨绮罗（下）", "3星", "圣痕", 0.3782),
    SupplyItem("里纳尔多（上）", "3星", "圣痕", 0.3782),
    SupplyItem("里纳尔多（中）", "3星", "圣痕", 0.3782),
    SupplyItem("里纳尔多（下）", "3星", "圣痕", 0.3782),
    SupplyItem("伽利略（上）", "3星", "圣痕", 0.3782),
    SupplyItem("伽利略（中）", "3星", "圣痕", 0.3782),
    SupplyItem("伽利略（下）", "3星", "圣痕", 0.3782),
    SupplyItem("芥川龙之介（上）", "3星", "圣痕", 0.3782),
    SupplyItem("芥川龙之介（中）", "3星", "圣痕", 0.3782),
    SupplyItem("芥川龙之介（下）", "3星", "圣痕", 0.3782),
    SupplyItem("罗尔德·阿蒙森（上）", "3星", "圣痕", 0.3782),
    SupplyItem("罗尔德·阿蒙森（中）", "3星", "圣痕", 0.3782),
    SupplyItem("罗尔德·阿蒙森（下）", "3星", "圣痕", 0.3782),
]

# --- 角色补给共用材料(5个) ---
SHARED_ROLE_MATERIALS: List[SupplyItem] = [
    SupplyItem("高级技能材料", "4星", "养成材料", 9.455, 3),
    SupplyItem("特级学习芯片", "4星", "养成材料", 10.8739, 5),
    SupplyItem("高级学习芯片", "3星", "养成材料", 10.8739, 10),
    SupplyItem("星石", "4星", "通用材料", 11.8189, 500),
    SupplyItem("金币", "2星", "通用材料", 14.8449, 50000),
]

# --- 装备/协同补给共用3星武器(23个, 概率不同) ---
SHARED_EQUIP_WEAPONS_3: List[SupplyItem] = [
    SupplyItem("水妖精I型", "3星", "武器", 0.4654),
    SupplyItem("水妖精II型", "3星", "武器", 0.4654),
    SupplyItem("火妖精I型", "3星", "武器", 0.4654),
    SupplyItem("火妖精II型", "3星", "武器", 0.4654),
    SupplyItem("苗刀·电魂", "3星", "武器", 0.4654),
    SupplyItem("苗刀·雷妖", "3星", "武器", 0.4654),
    SupplyItem("脉冲太刀17式", "3星", "武器", 0.4654),
    SupplyItem("脉冲太刀19式", "3星", "武器", 0.4654),
    SupplyItem("马尔可夫A型", "3星", "武器", 0.4654),
    SupplyItem("马尔可夫C型", "3星", "武器", 0.4654),
    SupplyItem("阴极子炮07式", "3星", "武器", 0.4654),
    SupplyItem("阴极子炮09式", "3星", "武器", 0.4653),
    SupplyItem("氮素结晶剑", "3星", "武器", 0.4653),
    SupplyItem("超重剑·冲锋", "3星", "武器", 0.4653),
    SupplyItem("电离共振剑", "3星", "武器", 0.4653),
    SupplyItem("超重剑·王蛇", "3星", "武器", 0.4653),
    SupplyItem("黑色粉碎者", "3星", "武器", 0.4653),
    SupplyItem("火天使", "3星", "武器", 0.4653),
    SupplyItem("雷天使", "3星", "武器", 0.4653),
    SupplyItem("CAS-X圣徒", "3星", "武器", 0.4653),
    SupplyItem("白星驱逐者", "3星", "武器", 0.4653),
    SupplyItem("黑曜切割", "3星", "武器", 0.4653),
    SupplyItem("等离子长枪", "3星", "武器", 0.4653),
]

# --- 装备/协同补给共用3星圣痕(36个, 概率不同) ---
SHARED_EQUIP_STIGMATA_3: List[SupplyItem] = [
    SupplyItem("巴托里·伊丽莎白（上）", "3星", "圣痕", 0.3723),
    SupplyItem("巴托里·伊丽莎白（中）", "3星", "圣痕", 0.3723),
    SupplyItem("巴托里·伊丽莎白（下）", "3星", "圣痕", 0.3723),
    SupplyItem("呼邪（上）", "3星", "圣痕", 0.3723),
    SupplyItem("呼邪（中）", "3星", "圣痕", 0.3723),
    SupplyItem("呼邪（下）", "3星", "圣痕", 0.3723),
    SupplyItem("阿提拉（上）", "3星", "圣痕", 0.3723),
    SupplyItem("阿提拉（中）", "3星", "圣痕", 0.3723),
    SupplyItem("阿提拉（下）", "3星", "圣痕", 0.3723),
    SupplyItem("坂本龙马（上）", "3星", "圣痕", 0.3723),
    SupplyItem("坂本龙马（中）", "3星", "圣痕", 0.3723),
    SupplyItem("坂本龙马（下）", "3星", "圣痕", 0.3723),
    SupplyItem("尼古拉·特斯拉（上）", "3星", "圣痕", 0.3723),
    SupplyItem("尼古拉·特斯拉（中）", "3星", "圣痕", 0.3723),
    SupplyItem("尼古拉·特斯拉（下）", "3星", "圣痕", 0.3723),
    SupplyItem("查理曼（上）", "3星", "圣痕", 0.3723),
    SupplyItem("查理曼（中）", "3星", "圣痕", 0.3723),
    SupplyItem("查理曼（下）", "3星", "圣痕", 0.3723),
    SupplyItem("奥吉尔（上）", "3星", "圣痕", 0.3723),
    SupplyItem("奥吉尔（中）", "3星", "圣痕", 0.3723),
    SupplyItem("奥吉尔（下）", "3星", "圣痕", 0.3723),
    SupplyItem("时雨绮罗（上）", "3星", "圣痕", 0.3723),
    SupplyItem("时雨绮罗（中）", "3星", "圣痕", 0.3723),
    SupplyItem("时雨绮罗（下）", "3星", "圣痕", 0.3723),
    SupplyItem("里纳尔多（上）", "3星", "圣痕", 0.3723),
    SupplyItem("里纳尔多（中）", "3星", "圣痕", 0.3723),
    SupplyItem("里纳尔多（下）", "3星", "圣痕", 0.3723),
    SupplyItem("伽利略（上）", "3星", "圣痕", 0.3722),
    SupplyItem("伽利略（中）", "3星", "圣痕", 0.3722),
    SupplyItem("伽利略（下）", "3星", "圣痕", 0.3722),
    SupplyItem("芥川龙之介（上）", "3星", "圣痕", 0.3722),
    SupplyItem("芥川龙之介（中）", "3星", "圣痕", 0.3722),
    SupplyItem("芥川龙之介（下）", "3星", "圣痕", 0.3722),
    SupplyItem("罗尔德·阿蒙森（上）", "3星", "圣痕", 0.3722),
    SupplyItem("罗尔德·阿蒙森（中）", "3星", "圣痕", 0.3722),
    SupplyItem("罗尔德·阿蒙森（下）", "3星", "圣痕", 0.3723),
]


# ==================== 补给池定义 ====================

# --- 角色补给A ---
ROLE_POOL_A = PoolConfig(
    pool_id="role_a",
    pool_name="愈生佑翎",
    supply_type=SupplyType.ROLE,
    up_item_name="愈生佑翎角色卡",
    up_item_prob=1.5000,
    a_up_items=["幻海梦蝶角色卡"],
    a_up_prob=8.0717,
    items=[
        SupplyItem("愈生佑翎角色卡", "S", "角色卡", 1.5000),
        SupplyItem("幻海梦蝶角色卡", "A", "角色卡", 8.0717),
        SupplyItem("雪地狙击角色卡", "A", "角色卡", 2.6907),
        SupplyItem("银狼的黎明角色卡", "A", "角色卡", 2.6907),
        SupplyItem("驱动装·山吹角色卡", "A", "角色卡", 2.6907),
    ] + SHARED_ROLE_WEAPONS_3 + SHARED_ROLE_STIGMATA_3 + SHARED_ROLE_MATERIALS,
    s_pity=90,
    a_pity=10,
    cost_per_pull=280,
)

# --- 角色补给B ---
ROLE_POOL_B = PoolConfig(
    pool_id="role_b",
    pool_name="嗨♪爱愿妖精♥",
    supply_type=SupplyType.ROLE,
    up_item_name="嗨♪爱愿妖精♥角色卡",
    up_item_prob=1.5000,
    a_up_items=["月下初拥角色卡"],
    a_up_prob=8.0717,
    items=[
        SupplyItem("嗨♪爱愿妖精♥角色卡", "S", "角色卡", 1.5000),
        SupplyItem("月下初拥角色卡", "A", "角色卡", 8.0717),
        SupplyItem("女武神·强袭角色卡", "A", "角色卡", 2.6907),
        SupplyItem("极地战刃角色卡", "A", "角色卡", 2.6907),
        SupplyItem("融核装·深红角色卡", "A", "角色卡", 2.6907),
    ] + SHARED_ROLE_WEAPONS_3 + SHARED_ROLE_STIGMATA_3 + SHARED_ROLE_MATERIALS,
    s_pity=90,
    a_pity=10,
    cost_per_pull=280,
)

# --- 装备补给A ---
EQUIP_POOL_A = PoolConfig(
    pool_id="equip_a",
    pool_name="垂曦净蕊·花愈朝夕",
    supply_type=SupplyType.EQUIP,
    up_item_name="垂曦净蕊",
    up_item_prob=2.4870,
    items=[
        SupplyItem("垂曦净蕊", "4星", "武器", 2.4870),
        SupplyItem("希儿·晨蕊摇光（上）", "4星", "圣痕", 4.8620),
        SupplyItem("希儿·花寄嘱念（中）", "4星", "圣痕", 4.8620),
        SupplyItem("希儿·芳诲传薪（下）", "4星", "圣痕", 4.8620),
    ] + SHARED_EQUIP_WEAPONS_3 + SHARED_EQUIP_STIGMATA_3 + [
        SupplyItem("爱因斯坦环磁机", "4星", "养成材料", 9.3072, 20),
        SupplyItem("爱因斯坦环磁机", "4星", "养成材料", 6.9802, 15),
        SupplyItem("爱因斯坦环磁机", "4星", "养成材料", 4.6541, 10),
        SupplyItem("以太燃素", "4星", "养成材料", 3.7231, 25),
        SupplyItem("相转移镜面", "4星", "养成材料", 5.5841, 2),
        SupplyItem("双子灵魂结晶", "4星", "养成材料", 6.5151, 3),
        SupplyItem("灵魂结晶", "3星", "养成材料", 6.5151, 3),
        SupplyItem("流体合金", "2星", "养成材料", 6.9801, 8),
        SupplyItem("金币", "2星", "通用材料", 8.5630, 50000),
    ],
    s_pity=60,
    a_pity=10,
    cost_per_pull=280,
)

# --- 装备补给B ---
EQUIP_POOL_B = PoolConfig(
    pool_id="equip_b",
    pool_name="澄爱挚语·芳时晏然",
    supply_type=SupplyType.EQUIP,
    up_item_name="澄爱挚语",
    up_item_prob=2.4870,
    items=[
        SupplyItem("澄爱挚语", "4星", "武器", 2.4870),
        SupplyItem("爱莉希雅·悠然漫话（上）", "4星", "圣痕", 4.8620),
        SupplyItem("爱莉希雅·翩然流光（中）", "4星", "圣痕", 4.8620),
        SupplyItem("爱莉希雅·焕然愿景（下）", "4星", "圣痕", 4.8620),
    ] + SHARED_EQUIP_WEAPONS_3 + SHARED_EQUIP_STIGMATA_3 + [
        SupplyItem("爱因斯坦环磁机", "4星", "养成材料", 9.3072, 20),
        SupplyItem("爱因斯坦环磁机", "4星", "养成材料", 6.9802, 15),
        SupplyItem("爱因斯坦环磁机", "4星", "养成材料", 4.6541, 10),
        SupplyItem("以太燃素", "4星", "养成材料", 3.7231, 25),
        SupplyItem("相转移镜面", "4星", "养成材料", 5.5841, 2),
        SupplyItem("双子灵魂结晶", "4星", "养成材料", 6.5151, 3),
        SupplyItem("灵魂结晶", "3星", "养成材料", 6.5151, 3),
        SupplyItem("流体合金", "2星", "养成材料", 6.9801, 8),
        SupplyItem("金币", "2星", "通用材料", 8.5630, 50000),
    ],
    s_pity=60,
    a_pity=10,
    cost_per_pull=280,
)

# --- 协同补给 ---
SYNERGY_POOL = PoolConfig(
    pool_id="synergy",
    pool_name="希娜狄雅",
    supply_type=SupplyType.SYNERGY,
    up_item_name="希娜狄雅",
    up_item_prob=2.4870,
    items=[
        SupplyItem("希娜狄雅", "S", "协同者", 2.4870),
        SupplyItem("协同终端", "4星", "养成材料", 5.8349, 8),
        SupplyItem("爱因斯坦环磁机", "4星", "养成材料", 4.3759, 30),
        SupplyItem("超导金属氢", "4星", "养成材料", 4.3759, 60),
    ] + SHARED_EQUIP_WEAPONS_3 + SHARED_EQUIP_STIGMATA_3 + [
        SupplyItem("协同终端", "4星", "养成材料", 6.7009, 2),
        SupplyItem("高级技能材料", "4星", "养成材料", 7.4458, 3),
        SupplyItem("特级学习芯片", "4星", "养成材料", 7.4458, 5),
        SupplyItem("高级学习芯片", "3星", "养成材料", 7.4458, 10),
        SupplyItem("星石", "4星", "通用材料", 14.8915, 500),
        SupplyItem("金币", "2星", "通用材料", 14.8915, 50000),
    ],
    s_pity=60,
    a_pity=10,
    cost_per_pull=280,
)


# ==================== 补给池注册表 ====================

# 按补给类型分组
SUPPLY_POOLS: Dict[str, PoolConfig] = {
    "role_a": ROLE_POOL_A,
    "role_b": ROLE_POOL_B,
    "equip_a": EQUIP_POOL_A,
    "equip_b": EQUIP_POOL_B,
    "synergy": SYNERGY_POOL,
}

# 保底类型映射：同一补给类型的A/B池共享保底
PITY_GROUP_MAP: Dict[SupplyType, str] = {
    SupplyType.ROLE: "role",
    SupplyType.EQUIP: "equip",
    SupplyType.SYNERGY: "synergy",
}

# 别名映射
POOL_ALIASES: Dict[str, str] = {
    "角色补给a": "role_a",
    "角色补给b": "role_b",
    "装备补给a": "equip_a",
    "装备补给b": "equip_b",
    "协同补给": "synergy",
}


# ==================== 用户保底数据管理 ====================

class PityManager:
    """保底计数器管理（按补给类型分组）"""

    def __init__(self):
        self.data_dir = Path("data/elysia_dice")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.pity_file = self.data_dir / "supply_pity.json"
        self.pity_data = self._load()

    def _load(self) -> dict:
        try:
            if self.pity_file.exists():
                with open(self.pity_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载保底数据失败: {e}")
        return {}

    def _save(self) -> bool:
        try:
            with open(self.pity_file, 'w', encoding='utf-8') as f:
                json.dump(self.pity_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存保底数据失败: {e}")
            return False

    def _get_pity_key(self, pity_group: str) -> str:
        """获取保底组的存储键"""
        return f"__pity_group__{pity_group}"

    def get_pity(self, user_id: str, group_id: str, supply_type: SupplyType) -> Tuple[int, int]:
        """获取 (S保底计数, A保底计数)"""
        user_key = _make_key(user_id, group_id)
        pity_group = PITY_GROUP_MAP.get(supply_type, supply_type.value)
        pity_key = self._get_pity_key(pity_group)

        if user_key not in self.pity_data:
            self.pity_data[user_key] = {}
        if pity_key not in self.pity_data[user_key]:
            self.pity_data[user_key][pity_key] = {"s_pity": 0, "a_pity": 0}
            self._save()

        entry = self.pity_data[user_key][pity_key]
        return entry.get("s_pity", 0), entry.get("a_pity", 0)

    def set_pity(self, user_id: str, group_id: str, supply_type: SupplyType, s_pity: int, a_pity: int) -> None:
        """设置保底计数"""
        user_key = _make_key(user_id, group_id)
        pity_group = PITY_GROUP_MAP.get(supply_type, supply_type.value)
        pity_key = self._get_pity_key(pity_group)

        if user_key not in self.pity_data:
            self.pity_data[user_key] = {}
        self.pity_data[user_key][pity_key] = {"s_pity": s_pity, "a_pity": a_pity}
        self._save()

    def reset_pity(self, user_id: str, group_id: str, supply_type: Optional[SupplyType] = None) -> None:
        """重置保底计数"""
        user_key = _make_key(user_id, group_id)
        if user_key not in self.pity_data:
            return

        if supply_type is None:
            # 重置所有类型
            self.pity_data[user_key] = {}
        else:
            pity_group = PITY_GROUP_MAP.get(supply_type, supply_type.value)
            pity_key = self._get_pity_key(pity_group)
            if pity_key in self.pity_data[user_key]:
                del self.pity_data[user_key][pity_key]
        self._save()

    def reset_all_pity(self, group_id: str = "", supply_type: Optional[SupplyType] = None) -> int:
        """重置所有用户保底"""
        count = 0
        prefix = f"{group_id}:" if (SEPARATE_BY_GROUP and group_id) else ""

        if supply_type:
            pity_group = PITY_GROUP_MAP.get(supply_type, supply_type.value)
            pity_key = self._get_pity_key(pity_group)

        for user_key in list(self.pity_data.keys()):
            if prefix and not user_key.startswith(prefix):
                continue
            if supply_type:
                if pity_key in self.pity_data[user_key]:
                    del self.pity_data[user_key][pity_key]
                    count += 1
            else:
                self.pity_data[user_key] = {}
                count += 1

        self._save()
        scope = f"群{group_id}" if (SEPARATE_BY_GROUP and group_id) else "全局"
        type_str = supply_type.value if supply_type else "全部"
        logger.info(f"已重置 {scope} {count} 个用户的{type_str}补给保底")
        return count


pity_manager = PityManager()


# ==================== 抽卡核心逻辑 ====================

class SupplyEngine:
    """补给抽卡引擎"""

    @classmethod
    def get_pool(cls, pool_key: str) -> Optional[PoolConfig]:
        """获取补给池配置"""
        return SUPPLY_POOLS.get(pool_key)

    @classmethod
    def resolve_pool(cls, query: str) -> Optional[str]:
        """通过别名解析补给池key"""
        query_lower = query.lower().strip()
        # 先精确匹配
        if query_lower in POOL_ALIASES:
            return POOL_ALIASES[query_lower]
        if query_lower in SUPPLY_POOLS:
            return query_lower
        return None

    @classmethod
    def get_all_pool_ids(cls) -> List[str]:
        return list(SUPPLY_POOLS.keys())

    @classmethod
    def get_all_alias_names(cls) -> List[str]:
        return list(POOL_ALIASES.keys())

    @classmethod
    def _build_cdf(cls, items: List[SupplyItem]) -> List[Tuple[float, SupplyItem]]:
        """构建累积概率分布"""
        cdf = []
        cumulative = 0.0
        for item in items:
            cumulative += item.probability
            cdf.append((cumulative, item))
        return cdf

    @classmethod
    def _normalize_probs(cls, items: List[SupplyItem]) -> List[SupplyItem]:
        """归一化概率到100%"""
        total = sum(item.probability for item in items)
        if total == 0:
            return items
        return [
            SupplyItem(
                name=item.name,
                quality=item.quality,
                item_type=item.item_type,
                probability=item.probability * 100.0 / total,
                quantity=item.quantity,
            )
            for item in items
        ]

    @classmethod
    def _filter_by_quality(cls, items: List[SupplyItem], qualities: List[str]) -> List[SupplyItem]:
        """按品质筛选物品"""
        return [item for item in items if item.quality in qualities]

    @classmethod
    def _get_s_quality(cls, pool_config: PoolConfig) -> str:
        """获取补给池的"顶级"品质"""
        if pool_config.supply_type == SupplyType.ROLE:
            return "S"
        elif pool_config.supply_type == SupplyType.SYNERGY:
            return "S"
        else:
            return "4星"

    @classmethod
    def _get_a_quality(cls, pool_config: PoolConfig) -> List[str]:
        """获取补给池的"次级"品质"""
        if pool_config.supply_type == SupplyType.ROLE:
            return ["S", "A"]
        elif pool_config.supply_type == SupplyType.SYNERGY:
            return ["S", "4星"]
        else:
            return ["4星"]

    @classmethod
    def _single_pull(
        cls,
        pool_config: PoolConfig,
        current_s_pity: int,
        current_a_pity: int,
    ) -> PullResult:
        """执行单抽"""
        full_pool = list(pool_config.items)
        s_quality = cls._get_s_quality(pool_config)
        a_qualities = cls._get_a_quality(pool_config)

        # 检查S保底
        if current_s_pity >= pool_config.s_pity - 1:
            up_item = next(
                (item for item in full_pool if item.name == pool_config.up_item_name),
                [item for item in full_pool if item.quality == s_quality][0]
            )
            return PullResult(
                item=up_item,
                pity_counter=0,
                a_pity_counter=0,
                is_s_pity=True,
                is_a_pity=False,
            )

        # 检查A保底
        if current_a_pity >= pool_config.a_pity - 1:
            a_plus_pool = cls._filter_by_quality(full_pool, a_qualities)
            normalized_pool = cls._normalize_probs(a_plus_pool)
            cdf = cls._build_cdf(normalized_pool)
            roll = random.uniform(0, 100)
            idx = bisect.bisect_left([p[0] for p in cdf], roll)
            selected = cdf[min(idx, len(cdf) - 1)][1]

            if selected.quality == s_quality:
                new_s_pity = 0
                new_a_pity = 0
            else:
                new_s_pity = current_s_pity + 1
                new_a_pity = 0

            return PullResult(
                item=selected,
                pity_counter=new_s_pity,
                a_pity_counter=new_a_pity,
                is_s_pity=False,
                is_a_pity=True,
            )

        # 普通抽取
        cdf = cls._build_cdf(full_pool)
        roll = random.uniform(0, 100)
        idx = bisect.bisect_left([p[0] for p in cdf], roll)
        selected = cdf[min(idx, len(cdf) - 1)][1]

        if selected.quality == s_quality:
            new_s_pity = 0
            new_a_pity = 0
        elif selected.quality in a_qualities:
            new_s_pity = current_s_pity + 1
            new_a_pity = 0
        else:
            new_s_pity = current_s_pity + 1
            new_a_pity = current_a_pity + 1

        return PullResult(
            item=selected,
            pity_counter=new_s_pity,
            a_pity_counter=new_a_pity,
            is_s_pity=False,
            is_a_pity=False,
        )

    @classmethod
    def pull(
        cls,
        pool_key: str,
        count: int,
        user_id: str,
        group_id: str,
    ) -> Optional[MultiPullResult]:
        """执行补给抽取"""
        pool_config = cls.get_pool(pool_key)
        if pool_config is None:
            return None

        if count < 1 or count > 10:
            return None

        s_pity, a_pity = pity_manager.get_pity(user_id, group_id, pool_config.supply_type)

        results: List[PullResult] = []
        current_s = s_pity
        current_a = a_pity
        s_count = 0
        a_count = 0
        up_s_count = 0
        s_quality = cls._get_s_quality(pool_config)
        a_qualities = cls._get_a_quality(pool_config)

        for _ in range(count):
            result = cls._single_pull(pool_config, current_s, current_a)
            results.append(result)
            current_s = result.pity_counter
            current_a = result.a_pity_counter

            if result.item.quality == s_quality:
                s_count += 1
                if result.item.name == pool_config.up_item_name:
                    up_s_count += 1
            elif result.item.quality in a_qualities:
                a_count += 1

        pity_manager.set_pity(user_id, group_id, pool_config.supply_type, current_s, current_a)

        total_cost = count * pool_config.cost_per_pull

        return MultiPullResult(
            results=results,
            final_pity=current_s,
            final_a_pity=current_a,
            total_cost=total_cost,
            s_count=s_count,
            a_count=a_count,
            up_s_count=up_s_count,
        )


# ==================== 格式化输出 ====================

def _get_top_label(supply_type: SupplyType, quality: str) -> str:
    """获取出货标签"""
    if supply_type == SupplyType.ROLE:
        if quality == "S":
            return "🌟 S级"
        elif quality == "A":
            return "⭐ A级"
    elif supply_type == SupplyType.EQUIP:
        if quality == "4星":
            return "💠 4星"
    elif supply_type == SupplyType.SYNERGY:
        if quality == "S":
            return "🌟 S级"
        elif quality == "4星":
            return "💠 4星"
    return f"[{quality}]"


def format_pull_result(result: MultiPullResult, pool_config: PoolConfig, current_crystal: int) -> str:
    """格式化抽取结果为消息文本"""
    lines = []
    lines.append(f"🎰 {pool_config.pool_name} 补给结果")
    lines.append("━" * 20)

    display_count = min(10, len(result.results))
    for i, pull in enumerate(result.results[:display_count], 1):
        item = pull.item
        qty_str = f" ×{item.quantity}" if item.quantity > 1 else ""
        tag = ""
        if pull.is_s_pity:
            tag = " ⬅保底触发！"
        elif pull.is_a_pity:
            tag = " ⬅A保底触发！"
        quality_label = _get_top_label(pool_config.supply_type, item.quality)
        lines.append(f"{i}. {quality_label} {item.name}{qty_str}{tag}")

    lines.append("━" * 20)

    s_quality = SupplyEngine._get_s_quality(pool_config)

    if result.s_count > 0:
        lines.append(f"{_get_top_label(pool_config.supply_type, s_quality)} 出货: {result.s_count} 次")
        if result.up_s_count > 0:
            lines.append(f"🎯 UP出货: {result.up_s_count} 次")
    if result.a_count > 0:
        a_label = "A级" if pool_config.supply_type == SupplyType.ROLE else "4星"
        lines.append(f"⭐ {a_label}出货: {result.a_count} 次")

    lines.append(f"💎 消耗水晶: {result.total_cost}")
    lines.append(f"💎 剩余水晶: {current_crystal}")
    lines.append(f"📊 保底计数: {result.final_pity}/{pool_config.s_pity}")

    return "\n".join(lines)


# ==================== 开发工具接口 ====================

def reset_user_pity(user_id: str, group_id: str, supply_type: Optional[SupplyType] = None) -> None:
    """重置指定用户保底"""
    pity_manager.reset_pity(user_id, group_id, supply_type)


def reset_all_pity(group_id: str = "", supply_type: Optional[SupplyType] = None) -> int:
    """重置所有用户保底"""
    return pity_manager.reset_all_pity(group_id, supply_type)


def get_all_supply_types() -> List[SupplyType]:
    """获取所有补给类型"""
    return list(SupplyType)
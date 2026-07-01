# 🌸 爱莉喵骰娘 (Elysia Dice)

> 以《崩坏3》爱莉希雅为主题的多功能群聊机器人插件  
> 基于 Neo-MoFox 框架，一站式满足养成、抽卡、社交需求
> 更多功能持续开发中……

---

## ✨ 功能概览

### 🏠 签到与货币
| 命令 | 说明 |
|------|------|
| `/签到` | 每日签到，获得花花与好感度 |
| `/花花` | 查看当前花花余额 |
| `/排行` | 好感度排行榜 |

### 📦 背包与商店
| 命令 | 说明 |
|------|------|
| `/商店` | 查看可购买物品 |
| `/购买 <物品> [数量]` | 使用花花购买 |
| `/背包` | 查看背包物品 |
| `/赠送 @用户 <物品> [数量]` | 赠送物品给他人 |
| `/转让 @用户 <数量>` | 转让花花 |
| `/抽奖` | 每日抽奖 |

### 💎 模拟抽卡（崩坏3补给系统）
| 命令 | 说明 |
|------|------|
| `/水晶` | 查看水晶 |
| `/获取水晶` | 每日领取免费水晶 |
| `/角色补给A/B [次数]` | 角色补给（280水晶/抽） |
| `/装备补给A/B [次数]` | 装备补给 |
| `/协同补给 [次数]` | 协同者补给 |
| `/跃升补给 [次数]` | 跃升补给 |
| `/跃升武装 [次数]` | 跃升武装 |
| `/服装补给` | 服装补给 |

> 💡 支持单抽/十连，保底继承，详细规则见 `/帮助 抽卡`

### ⚔️ 女武神系统
| 命令 | 说明 |
|------|------|
| `/抽取女武神` | 随机抽取（每日10次） |
| `/今日女武神 <ID/名称>` | 设为今日展示 |
| `/全图鉴 [页码]` | 浏览完整图鉴 |
| `/图鉴` | 查看收集进度 |
| `/我的女武神 <ID/名称>` | 查询详情 |

### 💝 群友老婆 & 结婚系统
| 命令 | 说明 |
|------|------|
| `/今日群友` | 随机抽取今日群友老婆 |
| `/今日群友 换` | 更换（最多3次，消耗花花） |
| `/结婚 @对方` | 向今日群友求婚 |
| `/同意` | 同意求婚 |
| `/拒绝` | 拒绝求婚 |

> 🔒 被抽中后双向锁定 | 💍 婚姻当日有效 | 💔 更换自动解除

---

## 🚀 快速开始

1. 将插件放入 `plugins/elysia_dice/`
2. 启动机器人，插件自动初始化
3. 发送 `/帮助` 查看完整指南

---

## 🔧 开发者工具

| 命令 | 说明 |
|------|------|
| `/set currency <ID> <数量>` | 设置花花 |
| `/set crystal <ID> <数量>` | 设置水晶 |
| `/set favor <ID> <数量>` | 设置好感度 |
| `/set item <ID> <物品> [数量]` | 添加物品 |
| `/set reset all [ID]` | 重置数据 |
| `/set reset 群友 <ID>` | 重置群友关系 |
| `/set reset 补给 [类型] [ID]` | 重置补给保底 |
| `/set reset 女武神 [ID]` | 重置女武神数据 |

> ⚠️ 仅限 `DEVELOPER_IDS` 中配置的QQ号使用，可在 `handlers/dev_tools.py` 修改

---

## 📁 插件结构

```
elysia_dice/
├── plugin.py # 插件入口
├── config.py
├── manifest.json # 识别插件的关键文件
├── commands/
│ ├── help_command.py # /帮助
│ ├── sign_command.py # /签到 /花花 /排行
│ ├── shop_command.py # /商店 /购买 /抽奖
│ ├── query_command.py # /查询
│ ├── favor_command.py # /背包 /好感度 /赠送
│ ├── transfer_command.py # /转让
│ ├── crystal_command.py # /水晶 /获取水晶
│ ├── supply_command.py # 各补给命令
│ ├── valkyrie_command.py # 女武神命令
│ ├── today_groupmate_command.py # /今日群友 /结婚
│ └── dev_command.py # /set /elyset
├── handlers/
│ ├── __init__.py
│ ├── message.py
│ ├── sign.py
│ ├── currency.py
│ ├── shop.py
│ ├── favor.py
│ ├── crystal.py
│ ├── supply_pool.py
│ ├── gacha_handler.py
│ ├── valkyrie_handler.py
│ ├── marriage_manager.py
│ ├── groupmate_handler.py
│ ├── member_collector.py
│ ├── auto_record.py
│ └── dev_tools.py
└── data/
  ├── gacha_pools.py
  └── valkyrie_data.py
└── elysia_dice/ # 数据存储目录（自动创建）
```

---

## ⚙️ 配置

编辑 `handlers/dev_tools.py`：

```python
DEVELOPER_IDS = ["你的QQ号"]
📖 依赖
Neo-MoFox 框架
Python 3.10+
标准库：json, random, time, pathlib
📜 许可
MIT License

🌸 “愿你的每一天都充满爱莉的爱~”

"""
群成员收集器
"""
import json
import time
from pathlib import Path
from src.app.plugin_system.api.log_api import get_logger

logger = get_logger("elysia_dice.member_collector")
DATA_FILE = Path("data/elysia_dice/group_members.json")


def _load() -> dict:
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        if DATA_FILE.exists():
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"加载失败: {e}")
    return {}


def _save(data: dict):
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存失败: {e}")


def _get_date() -> str:
    return time.strftime("%Y%m%d")


def _get_month() -> str:
    return time.strftime("%Y%m")


def cleanup(data: dict) -> dict:
    today = _get_date()
    month = _get_month()
    for gid in list(data.keys()):
        g = data[gid]
        if g.get("_month") != month:
            data[gid] = {"_month": month, "_date": today}
        else:
            g["_date"] = today
            g.pop("_nicks", None)
    return data


def record_user(group_id: str, user_id: str, nickname: str = ""):
    data = _load()
    data = cleanup(data)
    if group_id not in data:
        data[group_id] = {"_month": _get_month(), "_date": _get_date()}
    g = data[group_id]
    if g.get("_month") != _get_month():
        g.clear()
        g["_month"] = _get_month()
        g["_date"] = _get_date()
    uid = str(user_id)
    g[uid] = g.get(uid, 0) + 1
    if nickname:
        g.setdefault("_nicks", {})[uid] = nickname
    _save(data)


def get_members(group_id: str) -> list[str]:
    data = _load()
    data = cleanup(data)
    g = data.get(group_id, {})
    if g.get("_month") != _get_month():
        return []
    return [k for k in g if not k.startswith("_")]


def get_nickname(group_id: str, user_id: str) -> str:
    data = _load()
    data = cleanup(data)
    g = data.get(group_id, {})
    return g.get("_nicks", {}).get(str(user_id), "")


def get_member_count(group_id: str) -> int:
    return len(get_members(group_id))
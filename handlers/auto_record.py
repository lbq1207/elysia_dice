"""
自动记录装饰器
"""
from functools import wraps
from src.app.plugin_system.api.stream_api import get_stream_info
from src.app.plugin_system.api.log_api import get_logger
from .member_collector import record_user

logger = get_logger("elysia_dice.auto_record")


def auto_record(handle_func):
    @wraps(handle_func)
    async def wrapper(self, *args, **kwargs):
        try:
            message = getattr(self, '_message', None)
            if message:
                uid = str(getattr(message, 'sender_id', ''))
                sid = getattr(self, 'stream_id', '')
                if uid and sid:
                    info = await get_stream_info(sid)
                    gid = str(info.get("group_id", "")) if isinstance(info, dict) else ""
                    if gid:
                        nickname = ""
                        raw = getattr(message, 'raw_event', {})
                        if isinstance(raw, dict):
                            sender = raw.get("sender", {})
                            if isinstance(sender, dict):
                                nickname = sender.get("card", "") or sender.get("nickname", "")
                        record_user(gid, uid, nickname)
        except Exception:
            pass
        return await handle_func(self, *args, **kwargs)
    return wrapper
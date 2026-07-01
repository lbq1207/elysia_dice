from src.app.plugin_system.api.send_api import send_text
from src.app.plugin_system.api.log_api import get_logger

logger = get_logger("elysia_dice.message")

# 版本信息
__version__ = "1.0.0"


async def handle_test() -> str:
    """处理测试命令"""
    try:
        result = (
            "🎲 爱莉喵骰娘插件运行正常！\n"
            f"当前版本: {__version__}\n"
            "💡 可用命令：\n"
            "  /签到 - 每日签到获取花花\n"
        )
        logger.info("测试命令执行成功")
        return result
        
    except Exception as e:
        logger.error(f"测试处理失败: {e}")
        return "❌ 插件内部错误，请联系管理员。"


async def format_response(success: bool, message: str) -> str:
    """格式化响应消息"""
    if success:
        return f"✅ {message}"
    else:
        return f"❌ {message}"
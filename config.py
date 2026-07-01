from src.core.components.base.config import BaseConfig, config_section, Field, SectionBase


class ElysiaDiceConfig(BaseConfig):
    """骰娘插件配置"""
    config_name = "config"
    config_description = "爱莉喵骰娘插件配置"
    
    @config_section("currency")
    class CurrencySection(SectionBase):
        """货币系统配置"""
        currency_name: str = Field(default="花花", description="货币名称")
        currency_emoji: str = Field(default="❀", description="货币图标")
    
    @config_section("debug")
    class DebugSection(SectionBase):
        """调试配置"""
        debug_mode: bool = Field(default=False, description="是否启用调试模式")
    
    sign: SignSection = Field(default_factory=SignSection)
    currency: CurrencySection = Field(default_factory=CurrencySection)
    debug: DebugSection = Field(default_factory=DebugSection)
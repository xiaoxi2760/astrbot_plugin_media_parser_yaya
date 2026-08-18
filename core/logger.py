"""日志初始化模块，导出全局可复用日志实例。"""

try:
    from astrbot.api import logger as _astrbot_logger

    # 直接使用 AstrBot 的插件级 logger（Proxy 按调用模块自动路由到
    # astrbot.plugin.<plugin_name>），不要 getChild 包装，否则日志
    # 记录会丢失 AstrBot 附加的 plugin_tag 字段，导致日志格式化崩溃。
    logger = _astrbot_logger
except ImportError:
    import logging

    logger = logging.getLogger("astrbot_plugin_media_parser")

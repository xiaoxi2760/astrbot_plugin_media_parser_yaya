"""小工具函数（从 rika utils_parser 精简）。"""


def fmt_duration(duration: float) -> str:
    """格式化媒体时长为「X分Y秒」，超过 1 小时显示为「X小时Y分Z秒」。"""
    total_seconds = max(int(duration), 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}小时{minutes}分{seconds}秒"
    if minutes:
        return f"{minutes}分{seconds}秒"
    return f"{seconds}秒"

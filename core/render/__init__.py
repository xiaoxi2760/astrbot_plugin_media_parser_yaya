"""卡片渲染入口：转发到 rika 风格渲染器。

旧版渲染器（assets/data/font/renderer）已移除，统一使用 core/rika_render。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from ..logger import logger


async def render_card(
    metadata: Dict[str, Any],
    *,
    save_dir: str,
    custom_font: str = "",
    theme: str = "dark",
    layout: str = "standard",
    width: int = 800,
    cover_full_size: bool = False,
    show_play_button: bool = False,
) -> Optional[Path]:
    """渲染卡片并保存到 save_dir，成功返回文件路径，失败返回 None。

    返回的卡片文件由调用方负责清理（加入临时文件清理列表）。
    """
    try:
        from ..rika_render import render_card_rika

        return await render_card_rika(
            metadata,
            save_dir=save_dir,
            custom_font=custom_font,
            theme=theme,
            layout=layout,
            width=width,
            cover_full_size=cover_full_size,
            show_play_button=show_play_button,
        )
    except Exception as e:
        logger.warning(
            f"卡片渲染失败: {metadata.get('url', '')}, "
            f"错误: {e}"
        )
        return None

"""rika 风格卡片渲染器（移植自 astrbot_plugin_rika_share，MIT）。"""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from ..logger import logger
from .adapter import build_parse_result
from .data import ParseResult
from .render import ShareCardRenderer

__all__ = ["ShareCardRenderer", "ParseResult", "build_parse_result", "render_card_rika"]


async def render_card_rika(
    metadata: Dict[str, Any],
    *,
    save_dir: str,
    custom_font: str = "",
    theme: str = "dark",
    layout: str = "standard",
    width: int = 800,
    cover_full_size: bool = False,
    show_play_button: bool = False,
    cache_key: Optional[str] = None,
) -> Optional[Path]:
    """用 rika 渲染器渲染卡片，成功返回 PNG 路径，失败返回 None。"""
    try:
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)

        metadata["_render_save_dir"] = str(save_path)
        result = build_parse_result(metadata, save_dir=save_path)
        if not (result.title or result.text or result.author):
            return None

        font_path = custom_font
        if not font_path or not Path(font_path).is_file():
            font_path = None
        renderer = ShareCardRenderer(
            cache_dir=save_path,
            enabled=True,
            width=width,
            theme=theme,
            layout=layout,
            font_path=font_path,
            cover_full_size=cover_full_size,
            show_play_button=show_play_button,
        )
        key = cache_key or str(metadata.get("url") or "")
        return await renderer.render(result, cache_key=key)
    except Exception as e:
        logger.warning(f"rika 卡片渲染失败: {metadata.get('url', '')}, 错误: {e}")
        return None

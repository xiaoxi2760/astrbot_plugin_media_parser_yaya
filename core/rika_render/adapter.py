"""适配层：把 yaya 的 MediaMetadata 转换为 rika 的 ParseResult。

优先复用 DownloadManager 已下载的本地文件（file_paths），
缺失的头像/封面再通过 PathTask 惰性下载。
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..logger import logger
from .data import Author, ImageContent, ParseResult, Platform, VideoContent
from .task import PathTask

PLATFORM_DISPLAY_NAMES: Dict[str, str] = {
    "bilibili": "哔哩哔哩",
    "douyin": "抖音",
    "kuaishou": "快手",
    "weibo": "微博",
    "xiaohongshu": "小红书",
    "twitter": "推特",
    "tiktok": "TikTok",
    "pixiv": "Pixiv",
    "toutiao": "今日头条",
    "xianyu": "闲鱼",
    "xiaoheihe": "小黑盒",
    "youtube": "YouTube",
}


def _parse_timestamp(value: Any) -> Optional[int]:
    """把 yaya 的字符串时间戳（或数字）转成秒级 int。"""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        numeric = float(text)
        if numeric > 0:
            return int(numeric) if numeric < 10**12 else int(numeric / 1000)
    except (TypeError, ValueError):
        pass
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
    ):
        try:
            parsed = datetime.strptime(text, fmt)
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone().replace(tzinfo=None)
            return int(parsed.timestamp())
        except (ValueError, OverflowError):
            continue
    return None


def _normalize_urls(value: Any) -> List[str]:
    """把各种形态的 URL 字段展平为字符串列表。"""
    urls: List[str] = []
    if isinstance(value, str):
        value = value.strip()
        if value:
            urls.append(value)
    elif isinstance(value, (list, tuple)):
        for item in value:
            urls.extend(_normalize_urls(item))
    elif isinstance(value, dict):
        for item in value.values():
            urls.extend(_normalize_urls(item))
    return urls


def _as_local_path_task(path: Optional[str]) -> Optional[PathTask]:
    """本地已下载文件：立即 resolve 的 PathTask。"""
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        return None

    async def _resolve() -> Path:
        return p

    return PathTask(_resolve())


def _as_download_path_task(
    urls: List[str],
    save_dir: Path,
    metadata: Dict[str, Any],
) -> Optional[PathTask]:
    """URL 下载：惰性 PathTask（复用 yaya 封面下载逻辑）。"""
    candidates = [u for u in urls if isinstance(u, str) and u.strip()]
    if not candidates:
        return None
    from .downloader import download_first_to_cache

    save_dir.mkdir(parents=True, exist_ok=True)
    task = download_first_to_cache(
        candidates,
        cache_dir=save_dir,
        metadata=metadata,
        kind="avatar",
    )
    return PathTask(task)


def build_parse_result(
    metadata: Dict[str, Any],
    *,
    save_dir: Optional[Path] = None,
) -> ParseResult:
    """把 yaya 的 MediaMetadata 转为 rika 的 ParseResult。"""
    platform_name = str(metadata.get("platform") or "").strip().lower() or "website"
    platform = Platform(
        name=platform_name,
        display_name=PLATFORM_DISPLAY_NAMES.get(platform_name, platform_name),
    )

    save_path = Path(save_dir) if save_dir else Path(
        str(metadata.get("_render_save_dir") or ".")
    )

    # 作者
    author: Optional[Author] = None
    author_name = str(metadata.get("author") or "").strip()
    if author_name:
        avatar_task = _as_local_path_task(metadata.get("avatar_path"))
        if avatar_task is None:
            avatar_task = _as_download_path_task(
                _normalize_urls(metadata.get("avatar_url")),
                save_path,
                metadata,
            )
        author = Author(name=author_name, avatar=avatar_task)

    title = str(metadata.get("title") or "").strip() or None
    text = str(metadata.get("desc") or "").strip() or None
    url = str(metadata.get("url") or metadata.get("source_url") or "").strip() or None
    timestamp = _parse_timestamp(metadata.get("timestamp"))

    # 媒体内容
    contents: List[Any] = []
    graphics: List[Any] = []
    extra: Dict[str, Any] = {}

    video_urls = metadata.get("video_urls") or []
    image_urls = metadata.get("image_urls") or []
    file_paths = metadata.get("file_paths") or []
    video_count = metadata.get("video_count", len(video_urls))

    # 封面：优先已下载的封面路径，其次 video_cover_urls，其次视频首帧路径
    cover_path = metadata.get("_cover_path") or metadata.get("cover_path")
    cover_task = _as_local_path_task(cover_path)
    if cover_task is None:
        cover_task = _as_download_path_task(
            _normalize_urls(metadata.get("video_cover_urls")),
            save_path,
            metadata,
        )

    duration_ms = metadata.get("timelength_ms")
    try:
        duration = float(duration_ms) / 1000.0 if duration_ms else None
    except (TypeError, ValueError):
        duration = None
    if duration:
        extra["duration"] = duration

    is_video = bool(video_urls) or bool(metadata.get("video_cover_only"))
    image_contents: List[ImageContent] = []
    for idx, url_list in enumerate(image_urls):
        if not url_list or not isinstance(url_list, list):
            continue
        task = None
        file_idx = video_count + idx
        if file_idx < len(file_paths) and file_paths[file_idx]:
            task = _as_local_path_task(str(file_paths[file_idx]))
        if task is None:
            candidates = [u for u in url_list if isinstance(u, str) and u.strip()]
            if candidates:
                from .downloader import download_first_to_cache

                save_path.mkdir(parents=True, exist_ok=True)
                task = PathTask(
                    download_first_to_cache(
                        candidates,
                        cache_dir=save_path,
                        metadata=metadata,
                        kind="image",
                    )
                )
        if task is not None:
            image_contents.append(ImageContent(path_task=task))

    if is_video:
        # 视频：只需封面做 hero
        video_task = cover_task
        if video_task is None and image_contents:
            video_task = image_contents[0].path_task
        contents.append(
            VideoContent(
                path_task=video_task,
                cover=cover_task,
                duration=duration,
            )
        )
        extra["content_type"] = "视频"
    elif image_contents:
        contents.extend(image_contents)
        extra["content_type"] = "图文"
    elif video_count:
        contents.append(
            VideoContent(
                path_task=cover_task,
                cover=cover_task,
                duration=duration,
            )
        )
        extra["content_type"] = "视频"

    # 渲染器需要的统计/在线/限制提示字段
    stats_line = str(metadata.get("stats_line") or "").strip()
    if stats_line:
        extra["stats_line"] = stats_line

    bvid = str(metadata.get("bvid") or "").strip()
    if bvid:
        extra["bvid"] = bvid
    online = str(metadata.get("online") or "").strip()
    if online:
        extra["online"] = online
    warnings = metadata.get("limit_warnings") or []
    if warnings:
        extra["limit_warnings"] = list(warnings)

    return ParseResult(
        platform=platform,
        author=author,
        title=title,
        text=text,
        timestamp=timestamp,
        url=url,
        contents=contents,
        graphics=graphics,
        extra=extra,
    )

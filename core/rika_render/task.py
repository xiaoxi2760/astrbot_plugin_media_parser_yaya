"""异步路径包装 - 用于延迟获取下载结果"""

import asyncio
from pathlib import Path
from collections.abc import Callable, Coroutine
from typing import Any

from ..logger import logger


class PathTask:
    __slots__ = ("_path", "_task")

    def __init__(
        self,
        task: asyncio.Task[Path] | Coroutine[Any, Any, Path],
    ):
        if isinstance(task, asyncio.Task):
            self._task: asyncio.Task[Path] = task
        else:
            self._task = asyncio.create_task(task)
        self._path: Path | None = None

    async def get(self) -> Path:
        if self._path is not None:
            return self._path
        self._path = await self._task
        return self._path

    async def safe_get(
        self,
        on_error: Callable[[Exception], None] | None = None,
    ) -> Path | None:
        try:
            return await self.get()
        except Exception as e:
            logger.debug(f"PathTask 获取失败 | task={self._task.get_name()}")
            if on_error is not None:
                on_error(e)
            return None

    @property
    async def uri(self) -> str | None:
        path = await self.safe_get()
        return path.as_uri() if path else None

    def __repr__(self) -> str:
        if self._path is not None:
            return f"PathTask(path={self._path.name})"
        else:
            return f"PathTask(task={self._task.get_name()}, done={self._task.done()})"

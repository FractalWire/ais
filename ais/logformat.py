from __future__ import annotations
from typing import List, Dict, Any
import logging


class Message():
    def __init__(self, fmt: str, args: List[Any]) -> None:
        self.fmt = fmt
        self.args = args

    def __str__(self) -> str:
        return self.fmt.format(*self.args)


class StyleAdapter(logging.LoggerAdapter):
    """A style adapter allowing log with format style {}"""

    def __init__(self, logger: logging.Logger, extra: Dict[Any, Any] = None) -> None:
        super().__init__(logger, extra or {})

    def log(self, level: int, msg: str, *args, **kwargs) -> None:
        if self.isEnabledFor(level):
            msg, kwargs = self.process(msg, kwargs)
            self.logger._log(level, Message(msg, args), (), **kwargs)

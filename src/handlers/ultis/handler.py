from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Optional

import pandas as pd

from src.Domain.Package import Package
from src.Domain.Parameters import Parameters


class Handler(ABC):

    @abstractmethod
    def set_next(self, handler: Handler) -> Handler:
        pass

    @abstractmethod
    def handle(self, request) -> Optional[str]:
        pass


class IterHander(Handler):
    _next_handler: Handler = None

    def set_next(self, handler: Handler) -> Handler:
        self._next_handler = handler
        return handler

    @abstractmethod
    def handle(self, df: pd.DataFrame, col_alvo: str, nome_amigavel: str) -> pd.DataFrame:
        if self._next_handler:
            return self._next_handler.handle(df, col_alvo, nome_amigavel)
        return df
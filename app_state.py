from dataclasses import dataclass, field

import pandas as pd


@dataclass
class AppState:
    rodando: bool = False
    etapa3_ativa: bool = False
    autenticado: bool = False
    usuario: str = ""
    df: pd.DataFrame | None = None
    pares: list[dict] = field(default_factory=list)
    decisoes: dict[str, dict] = field(default_factory=dict)
    indice_atual: int = 0
    arquivo_etapa3_atual: str = ""

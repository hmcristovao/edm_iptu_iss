from dataclasses import dataclass, field

import pandas as pd


@dataclass
class AppState:
    rodando: bool = False
    etapa3_ativa: bool = False
    autenticado: bool = False
    usuario: str = ""
    upload_entrada_iniciado: bool = False
    arquivos_entrada_carregados: list[str] = field(default_factory=list)
    df: pd.DataFrame | None = None
    pares: list[dict] = field(default_factory=list)
    decisoes: dict[str, dict] = field(default_factory=dict)
    indice_atual: int = 0

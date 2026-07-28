from dataclasses import dataclass, field

import pandas as pd


@dataclass
class AppState:
    rodando: bool = False
    etapa3_ativa: bool = False
    autenticado: bool = False
    pasta_trabalho_selecionada: bool = False
    usuario: str = ""
    df: pd.DataFrame | None = None
    pares: list[dict] = field(default_factory=list)
    decisoes: dict[str, dict] = field(default_factory=dict)
    indice_atual: int = 0
    total_grupos_revisao: int = 0
    offset_grupos_revisao: int = 0
    carregando_lote_revisao: bool = False
    arquivo_revisao_atual: str = ""

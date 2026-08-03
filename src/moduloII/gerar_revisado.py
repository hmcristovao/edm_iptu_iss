import json
import os
import sys
import traceback
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.moduloII.app_config import AppPaths
from src.moduloII.services import RevisaoService


PREFIXO_RESULTADO = "RESULTADO_ARQUIVO_REVISADO_JSON="


def gerar_arquivo_revisado(arquivo_saida: str | None = None) -> dict:
    paths = AppPaths()
    service = RevisaoService(paths)
    saida = arquivo_saida or os.environ.get("AVALIADOR_ARQUIVO_REVISAO_SAIDA") or paths.arquivo_integracao_parcial

    print(f"Carregando {paths.arquivo_enriquecimento}...")
    df = service.carregar_dados()

    print("Carregando decisoes da revisao humana...")
    decisoes = service.carregar_decisoes()

    print(f"Aplicando {len(decisoes)} decisao(oes) e salvando {saida}...")
    service.salvar_arquivo_revisado(df, decisoes, saida)

    return {
        "saida": saida,
        "linhas_entrada": len(df),
        "decisoes": len(decisoes),
    }


def main():
    try:
        resultado = gerar_arquivo_revisado()
    except Exception:
        traceback.print_exc()
        raise

    print(PREFIXO_RESULTADO + json.dumps(resultado, ensure_ascii=False, separators=(",", ":")))


if __name__ in {"__main__", "__mp_main__"}:
    main()

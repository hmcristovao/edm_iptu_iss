import multiprocessing
import sys


def executar_pipeline(nome: str) -> int:
    if nome == "moduloII.preparacao":
        from src.moduloII import preparacao

        pipeline = preparacao.main
    elif nome == "moduloII.enriquecimento":
        from src.moduloII import enriquecimento

        pipeline = enriquecimento.main
    elif nome == "moduloII.gerar_revisado":
        from src.moduloII import gerar_revisado

        pipeline = gerar_revisado.main
    elif nome == "moduloIII.reassociacao":
        from src.moduloIII import reassociacao

        pipeline = reassociacao.main
    elif nome == "moduloIV.base_imobiliario":
        from src.moduloIV import base_imobiliario

        pipeline = base_imobiliario.main
    else:
        print(f"Pipeline desconhecido: {nome}.", file=sys.stderr, flush=True)
        return 2

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(line_buffering=True)

    pipeline()
    return 0


if __name__ in {"__main__", "__mp_main__"}:
    multiprocessing.freeze_support()
    if len(sys.argv) >= 3 and sys.argv[1] == "--run-pipeline":
        raise SystemExit(executar_pipeline(sys.argv[2]))

    from src.views.app_nicegui import IntegracaoEnriquecimentoApp

    IntegracaoEnriquecimentoApp().run()

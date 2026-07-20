import os
from pathlib import Path
from typing import Callable

from src.moduloII.app_config import AppPaths


class ProcessamentoLegadoService:
    def __init__(self, paths: AppPaths):
        self.paths = paths

    def listar_parametros(self) -> list[Path]:
        if not self.paths.work_dir.is_dir():
            return []

        pastas_ignoradas = [
            self.paths.resolver(self.paths.pasta_gerados),
            self.paths.resolver("parametros"),
        ]
        return sorted(
            arquivo
            for arquivo in self.paths.work_dir.rglob("parametros_*.txt")
            if not any(self._esta_dentro_de(arquivo, pasta) for pasta in pastas_ignoradas)
        )

    def _esta_dentro_de(self, arquivo: Path, pasta: Path) -> bool:
        try:
            arquivo.resolve().relative_to(pasta.resolve())
            return True
        except ValueError:
            return False

    def executar(self, chave: str, ao_progredir: Callable[[str], None]) -> dict:
        from src.moduloI.Domain.Package import Package
        from src.moduloI.handlers.Pseudonymization_handler import PseudonymizationHandler
        from src.moduloI.handlers.adapters.anomizador.anonimizador_reversivel_adaptado import AnonimizadorReversivel
        from src.moduloI.handlers.export_handler import ExportHandler
        from src.moduloI.handlers.extractor_handler import ExtractorHandler
        from src.moduloI.handlers.standardization_handler import StandardizationHandler
        from src.moduloI.usecase.leitor import ParameterReader

        arquivos = self.listar_parametros()
        total = len(arquivos)
        if total == 0:
            raise FileNotFoundError("Nenhum arquivo parametros_*.txt foi encontrado na pasta de trabalho.")

        os.environ["key"] = chave
        os.environ["DATA_PATH"] = str(self.paths.work_dir / "_entrada")

        extractor = ExtractorHandler()
        standardizer = StandardizationHandler()
        pseudo = PseudonymizationHandler(AnonimizadorReversivel())
        exporter = ExportHandler()

        extractor.set_next(standardizer)
        standardizer.set_next(pseudo)
        pseudo.set_next(exporter)

        erros = []
        ao_progredir(f"Iniciando processamento legado: {total} arquivo(s) de parametros.")

        for indice, arquivo in enumerate(arquivos, start=1):
            ao_progredir(f"Processando {indice}/{total}: {arquivo.name}")
            try:
                parametros = ParameterReader(arquivo).ler_arquivo()
                pacote = Package(parametros)
                extractor.handle(request=pacote)
            except Exception as erro:
                erros.append(f"{arquivo.name}: {erro}")
                ao_progredir(f"Erro em {arquivo.name}: {erro}")

        ao_progredir(
            f"Processamento legado concluido: {exporter.iteracao} CSV(s) exportado(s), "
            f"{len(erros)} erro(s)."
        )

        return {
            "parametros": total,
            "csvs_exportados": exporter.iteracao,
            "erros": erros,
            "saida": self.paths.pasta_dados_processados,
        }

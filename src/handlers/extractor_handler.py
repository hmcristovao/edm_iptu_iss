import logging
from pathlib import Path

import pandas as pd

from src.Domain import Parameters
from src.Domain.Package import Package
from src.errors.extract_error import (
    NotFoundExtensionError,
    NotFoundPathError,
    UnknownExtensioError,
)
from src.handlers.Handler import AbstractHandler


class ExtractorHandler(AbstractHandler):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def __remover_rodape_por_quantidade(
        self,
        df: pd.DataFrame,
        footer,
    ) -> pd.DataFrame:
        if not footer:
            return df

        footer = int(footer)

        if footer <= 0:
            return df

        if footer >= len(df):
            return df.iloc[0:0]

        return df.iloc[:-footer]

    def __listar_arquivos(self, caminho_base: Path, formato: str) -> list[Path]:
        formato = formato.lower().strip().lstrip(".")

        if formato == "xls":
            return sorted(caminho_base.glob("*.xls"))

        if formato == "xlsx":
            return sorted(caminho_base.glob("*.xlsx"))

        if formato == "csv":
            return sorted(caminho_base.glob("*.csv"))

        return []

    def __ler_arquivo(self, arquivo: Path, parameter: Parameters) -> pd.DataFrame:
        extensao_real = arquivo.suffix.lower().lstrip(".")

        if extensao_real == "xlsx":
            return pd.read_excel(
                arquivo,
                header=parameter.header,
                engine="openpyxl",
            )

        if extensao_real == "xls":
            return pd.read_excel(
                arquivo,
                header=parameter.header,
                engine="xlrd",
            )

        if extensao_real == "csv":
            return pd.read_csv(
                arquivo,
                sep=parameter.sep,
                header=parameter.header,
                encoding="utf-8",
                on_bad_lines="skip",
            )

        raise ValueError(f"Formato não suportado: {arquivo.suffix}")

    def _carregarUnirArquivos(self, parameter: Parameters) -> pd.DataFrame:
        caminho_base = Path(parameter.pasta).resolve()
        formato = parameter.formato.lower().strip().lstrip(".")

        self.logger.info(f"Buscando em: {parameter.pasta}")
        self.logger.info(f"Caminho resolvido: {caminho_base}")

        if not caminho_base.exists():
            self.logger.error(f"ERRO: O caminho {caminho_base} não existe.")
            return pd.DataFrame()

        arquivos = self.__listar_arquivos(caminho_base, formato)

        self.logger.info(f"Formato declarado no parâmetro: {formato}")
        self.logger.info(f"Quantidade de arquivos encontrados: {len(arquivos)}")

        dfs = []

        for arquivo in arquivos:
            try:
                self.logger.info(f"Tentando extração: {arquivo.name}")

                df = self.__ler_arquivo(arquivo, parameter)

                if not df.empty:
                    df = self.__remover_rodape_por_quantidade(
                        df,
                        parameter.footer,
                    )
                    dfs.append(df)

                    self.logger.info(
                        f"Sucesso: {arquivo.name} carregado com {len(df)} linhas."
                    )
                else:
                    self.logger.warning(
                        f"Aviso: o arquivo {arquivo.name} resultou em um DataFrame vazio."
                    )

            except Exception as e:
                self.logger.error(f"Erro crítico ao ler {arquivo.name}: {e}")

        if not dfs:
            return pd.DataFrame()

        return pd.concat(dfs, ignore_index=True)

    def handle(self, request: Package) -> Package:
        if request.parameters.formato is None:
            raise NotFoundExtensionError(
                "Não encontrado formato no package para processamento"
            )

        if request.parameters.pasta is None:
            raise NotFoundPathError(
                "Não encontrada pasta para processamento"
            )

        formato = request.parameters.formato.lower().strip().lstrip(".")

        if formato not in ["csv", "xlsx", "xls"]:
            raise UnknownExtensioError(
                "Formato da extensão não tratado"
            )

        df = self._carregarUnirArquivos(request.parameters)

        package = Package(request.parameters, df)
        return super().handle(package)
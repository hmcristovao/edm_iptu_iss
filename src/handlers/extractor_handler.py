import logging
from pathlib import Path
from typing import Any, Optional
import pandas as pd
import glob
import os

from colorlog import exception
from numpy.f2py.auxfuncs import throw_error
from pyparsing import Empty

from src.Domain import Parameters
from src.Domain.Package import Package
from src.errors.extract_error import NotFoundExtensionError, ExtractError, NotFoundPathError, UnknownExtensioError
from src.handlers.Handler import AbstractHandler


class ExtractorHandler(AbstractHandler):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def __removerRodapePorQuantidade(self, df, footer):
        if not footer:
            return df

        footer = int(footer)

        if footer <= 0:
            return df

        if footer >= len(df):
            return df.iloc[0:0]

        return df.iloc[:-footer]
    def _carregarUnirXlsx(self,parameter:Parameters):
        raiz_projeto = Path(__file__).resolve().parent.parent.parent
        caminho_base = (raiz_projeto / parameter.pasta).resolve()

        self.logger.info(f"Buscando em: {caminho_base}")  # Debug para conferir o caminho final

        # 2. Busca os arquivos usando pathlib (mais moderno que glob.glob)
        arquivos = list(caminho_base.glob(f"*.{parameter.formato}"))

        dfs = []
        for arquivo in arquivos:
            try:
                if parameter.formato == "xlsx":
                    df = pd.read_excel(arquivo)

                    df = pd.read_excel(arquivo, header=parameter.header)
                    df = self.__removerRodapePorQuantidade(df, parameter.footer)

                    dfs.append(df)
                    self.logger.info(f"Arquivo carregado: {arquivo.name}")
                if parameter.formato == "csv":
                    df = pd.read_csv(arquivo,sep=parameter.seq)

                    df = pd.read_excel(arquivo, header=parameter.header)
                    df = self.__removerRodapePorQuantidade(df, parameter.footer)

                    dfs.append(df)
                    self.logger.info(f"Arquivo carregado: {arquivo.name}")
            except Exception as e:
                self.logger.error(f"Erro ao ler o arquivo {arquivo}: {e}")


        if not dfs:
            self.logger.warning(f"Aviso: Nenhum arquivo de extensão {parameter.formato} encontrado em: {caminho_base}")
            return pd.DataFrame()

        return pd.concat(dfs, ignore_index=True)

    def handle(self, request: Package) -> Package:
        if request.parameters.formato is None:
            raise NotFoundExtensionError('Não encontrado formato no package para processamento')

        if request.parameters.pasta is None:
            raise NotFoundPathError('Não encontrado pasta para processamento')

        if request.parameters.formato not in ["csv","xlsx"]:
            raise UnknownExtensioError('Formato da extensão não Tratada')


        df = self._carregarUnirXlsx(request.parameters)

        package = Package(request.parameters ,df)
        return super().handle(package)



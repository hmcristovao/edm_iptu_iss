import logging
from pathlib import Path
from typing import Any, Optional
import pandas as pd
import re
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

    def _carregarUnirXlsx(self, parameter: Parameters):
        raiz_projeto = Path(__file__).resolve().parents[2]  # parents[2] sobe 3 níveis
        caminho_base = Path(f"{raiz_projeto}{str(parameter.pasta).replace(".", "")}").resolve()

        self.logger.info(f"Buscando em: {parameter.pasta}")

        arquivos = list(caminho_base.glob(f"*.{parameter.formato}"))
        dfs = []

        for arquivo in arquivos:
            try:
                if parameter.formato in ["xlsx"]:
                    # Usa xlrd para xls e openpyxl para xlsx automaticamente
                    engine = 'xlrd' if parameter.formato == "xls" else 'openpyxl'
                    df = pd.read_excel(arquivo, header=parameter.header, engine=engine)
                elif parameter.formato == "xls":
                    try:
                        # 1. Tentativa padrão (Binário)
                        self.logger.info(f"Tentando extração {arquivo.name}")
                        df = pd.read_excel(arquivo, header=parameter.header, engine='xlrd')
                    except Exception:
                        self.logger.info(f"Tentando extração profunda de XML em {arquivo.name}")
                        try:
                            # 2. Tentativa via BeautifulSoup (Lida melhor com a bagunça de tags do Excel)
                            from bs4 import BeautifulSoup

                            with open(arquivo, 'r', encoding='utf-8', errors='ignore') as f:
                                soup = BeautifulSoup(f.read(), 'xml')

                            rows_data = []
                            # Procuramos todas as linhas da tabela
                            for row in soup.find_all('Row'):
                                # Para cada linha, pegamos o texto de cada célula (<Data>)
                                cells = [cell.get_text() for cell in row.find_all('Data')]
                                if cells:
                                    rows_data.append(cells)

                            if rows_data:
                                df = pd.DataFrame(rows_data)
                                # Ajusta o Header conforme o parâmetro
                                header_idx = parameter.header if parameter.header is not None else 0
                                if len(df) > header_idx:
                                    df.columns = df.iloc[header_idx]
                                    df = df.iloc[header_idx + 1:].reset_index(drop=True)
                            else:
                                # 3. Tentativa via HTML (Caso o arquivo seja um <table> disfarçado)
                                dfs_html = pd.read_html(str(arquivo))
                                df = dfs_html[0]

                        except Exception as e:
                            self.logger.error(f"Falha total ao processar {arquivo.name}: {e}")
                            continue
                elif parameter.formato == "csv":
                    df = pd.read_csv(arquivo, sep=parameter.sep, header=parameter.header)

                else:
                    continue

                df = self.__removerRodapePorQuantidade(df, parameter.footer)
                dfs.append(df)
                self.logger.info(f"Arquivo carregado: {arquivo.name}")

            except Exception as e:
                self.logger.error(f"Erro ao ler o arquivo {arquivo.name}: {e}")

        if not dfs:
            self.logger.warning(f"Aviso: Nenhum arquivo {parameter.formato} encontrado em: {caminho_base}")
            return pd.DataFrame()

        return pd.concat(dfs, ignore_index=True)

    def handle(self, request: Package) -> Package:
        if request.parameters.formato is None:
            raise NotFoundExtensionError('Não encontrado formato no package para processamento')

        if request.parameters.pasta is None:
            raise NotFoundPathError('Não encontrado pasta para processamento')

        if request.parameters.formato not in ["csv","xlsx","xls"]:
            raise UnknownExtensioError('Formato da extensão não Tratada')


        df = self._carregarUnirXlsx(request.parameters)

        package = Package(request.parameters ,df)
        return super().handle(package)



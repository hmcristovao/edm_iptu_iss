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

        self.logger.info(f"Buscando em: {caminho_base}")

        arquivos = list(caminho_base.glob(f"*.{parameter.formato}"))
        dfs = []

        for arquivo in arquivos:
            try:
                if parameter.formato in ["xlsx"]:
                    # Usa xlrd para xls e openpyxl para xlsx automaticamente
                    engine = 'xlrd' if parameter.formato == "xls" else 'openpyxl'
                    df = pd.read_excel(arquivo, header=parameter.header, engine=engine)
                elif parameter.formato == "xls":
                    df = None  # Inicializa para evitar o erro de 'local variable'
                    try:
                        import xml.etree.ElementTree as ET
                        # Tenta o parser manual
                        tree = ET.parse(str(arquivo))
                        root = tree.getroot()

                        for el in root.iter():
                            if '}' in el.tag:
                                el.tag = el.tag.split('}', 1)[1]

                        rows_data = []
                        for row in root.findall(".//Row"):
                            cells = [cell.findtext("Data") for cell in row.findall("Cell")]
                            if cells:
                                rows_data.append(cells)

                        if rows_data:
                            df = pd.DataFrame(rows_data)
                            header_idx = parameter.header if parameter.header is not None else 0
                            df.columns = df.iloc[header_idx]
                            df = df.iloc[header_idx + 1:].reset_index(drop=True)

                    except Exception as e:
                        self.logger.warning(f"Parser XML falhou em {arquivo.name}. Tentando extração via Regex...")

                        # Garimpo de Texto (Precisa do 'import re' no topo!)
                        with open(arquivo, 'r', encoding='latin-1', errors='ignore') as f:
                            conteudo = f.read()

                        padrao = r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{3}\.\d{3}\.\d{3}-\d{2}|\d{14}|\d{11})'
                        documentos = list(set(re.findall(padrao, conteudo)))

                        if documentos:
                            df = pd.DataFrame(documentos,
                                              columns=['CPF/CNPJ'])  # Nome esperado pelo StandardizationHandler
                            df['origem_arquivo'] = arquivo.name
                        else:
                            self.logger.error(f"Nenhum documento encontrado em {arquivo.name}")
                            continue  # Pula para o próximo arquivo

                    if df is None:
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



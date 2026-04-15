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
        caminho_base = Path(parameter.pasta).resolve()

        self.logger.info(f"Buscando em: {parameter.pasta}")
        self.logger.info(f"Caminho Resolvido: {caminho_base}")

        if not caminho_base.exists():
            self.logger.error(f"ERRO: O caminho {caminho_base} não existe!")
            return pd.DataFrame()

        arquivos = list(caminho_base.glob(f"*.{parameter.formato}"))
        if not arquivos:
            arquivos = list(caminho_base.glob(f"*.[xX][lL][sS]*"))

        dfs = []
        self.logger.info(f"Quantidade de arquivos encontrados: {len(arquivos)}")

        for arquivo in arquivos:
            try:
                self.logger.info(f"Tentando extração: {arquivo.name}")
                df = pd.DataFrame()
                ext = parameter.formato.lower()

                if ext == "xlsx":
                    df = pd.read_excel(arquivo, header=parameter.header, engine='openpyxl')

                elif ext == "xls":
                    try:
                        # 1. Tentativa padrão para XLS binário
                        df = pd.read_excel(arquivo, header=parameter.header, engine='xlrd')
                    except Exception:
                        self.logger.info(f"Detectado formato não binário em {arquivo.name}. Iniciando extração XML...")
                        try:
                            # 2. Extração profunda de XML (SpreadsheetML)
                            from bs4 import BeautifulSoup

                            with open(arquivo, 'r', encoding='utf-8', errors='ignore') as f:
                                # Lê o arquivo forçando o parser 'xml'
                                soup = BeautifulSoup(f.read(), 'xml')

                            linhas_extraidas = []
                            # Busca todas as tags de linha do Excel XML
                            for row in soup.find_all('Row'):
                                # Pega o texto de cada célula dentro da linha
                                cells = [cell.get_text(strip=True) for cell in row.find_all('Data')]
                                if cells:
                                    linhas_extraidas.append(cells)

                            if linhas_extraidas:
                                df = pd.DataFrame(linhas_extraidas)
                                # Ajusta o cabeçalho
                                if parameter.header is not None and int(parameter.header) >= 0:
                                    h_idx = int(parameter.header)
                                    if len(df) > h_idx:
                                        df.columns = df.iloc[h_idx]
                                        df = df.iloc[h_idx + 1:].reset_index(drop=True)
                            else:
                                # 3. Fallback final para HTML
                                self.logger.info(f"Nenhuma tag XML <Data> encontrada. Tentando extração HTML.")
                                dfs_html = pd.read_html(str(arquivo))
                                if dfs_html:
                                    df = dfs_html[0]
                                    if parameter.header is not None and parameter.header > 0:
                                        df.columns = df.iloc[parameter.header]
                                        df = df.iloc[parameter.header + 1:].reset_index(drop=True)
                        except ImportError:
                            self.logger.error(
                                "Biblioteca 'beautifulsoup4' e 'lxml' não encontradas. Instale-as com: pip install beautifulsoup4 lxml")
                        except Exception as e_xml:
                            self.logger.error(f"Falha total ao ler {arquivo.name} via XML/HTML: {e_xml}")

                elif ext == "csv":
                    df = pd.read_csv(arquivo, sep=parameter.sep, header=parameter.header, encoding='utf-8',
                                     on_bad_lines='skip')

                if not df.empty:
                    df = self.__removerRodapePorQuantidade(df, parameter.footer)
                    dfs.append(df)
                    self.logger.info(f"Sucesso: {arquivo.name} carregado com {len(df)} linhas.")
                else:
                    self.logger.warning(f"Aviso: O arquivo {arquivo.name} resultou em um DataFrame vazio.")

            except Exception as e:
                self.logger.error(f"Erro crítico ao ler {arquivo.name}: {e}")

        if not dfs:
            return pd.DataFrame()

        return pd.concat([d for d in dfs if not d.empty], ignore_index=True)

    def handle(self, request: Package) -> Package:
        if request.parameters.formato is None:
            raise NotFoundExtensionError('Não encontrado formato no package para processamento')

        if request.parameters.pasta is None:
            raise NotFoundPathError('Não encontrado pasta para processamento')

        if request.parameters.formato not in ["csv", "xlsx", "xls"]:
            raise UnknownExtensioError('Formato da extensão não Tratada')

        df = self._carregarUnirXlsx(request.parameters)

        package = Package(request.parameters, df)
        return super().handle(package)
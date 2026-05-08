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

        if not caminho_base.exists():
            self.logger.error(f"ERRO: O caminho {caminho_base} não existe!")
            return pd.DataFrame()

        arquivos = list(caminho_base.glob(f"*.{parameter.formato}"))
        if not arquivos:
            arquivos = list(caminho_base.glob(f"*.[xX][lL][sS]*"))

        dfs = []
        self.logger.info(f"Quantidade de arquivos encontrados: {len(arquivos)}")

        for arquivo in arquivos:
            df = None
            try:
                self.logger.info(f"Tentando extração: {arquivo.name}")
                ext = parameter.formato.lower()

                # 1. TRATAMENTO PARA XLSX
                if ext == "xlsx":
                    df = pd.read_excel(arquivo, header=parameter.header, engine='openpyxl')

                # 2. TRATAMENTO PARA XLS (Onde reside o problema da Saúde)
                elif ext == "xls":
                    # Tentativa A: Binário (Excel 97-2003 real)
                    try:
                        df = pd.read_excel(arquivo, header=parameter.header, engine='xlrd')
                    except Exception:
                        # Tentativa B: Se falhou, o arquivo é texto (HTML ou XML)
                        self.logger.info(f"Falha binária em {arquivo.name}. Tentando leitura como texto...")
                        with open(arquivo, 'r', encoding='utf-8', errors='ignore') as f:
                            conteudo = f.read()

                        # B.1 - Tenta ler como HTML (Cura o erro 'File is not a zip file')
                        try:
                            dfs_html = pd.read_html(conteudo)
                            if dfs_html:
                                df = dfs_html[0]
                                self.logger.info(f"Sucesso: {arquivo.name} lido como HTML.")
                        except Exception:
                            pass

                        # B.2 - Tenta ler como XML Spreadsheet 2003 (BeautifulSoup)
                        if df is None:
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(conteudo, 'xml')
                            linhas = [[cell.get_text(strip=True) for cell in row.find_all(['Data', 'Cell'])]
                                      for row in soup.find_all('Row')]
                            linhas = [l for l in linhas if any(l)]

                            if linhas:
                                df = pd.DataFrame(linhas)
                                h_idx = int(float(parameter.header)) if parameter.header is not None else 0
                                if len(df) > h_idx:
                                    df.columns = df.iloc[h_idx]
                                    df = df.iloc[h_idx + 1:].reset_index(drop=True)
                                self.logger.info(f"Sucesso: {arquivo.name} lido como XML.")

                # 3. TRATAMENTO PARA CSV
                elif ext == "csv":
                    df = pd.read_csv(arquivo, sep=parameter.sep, header=parameter.header,
                                     encoding='utf-8', on_bad_lines='skip')

                # --- BLINDAGEM ANTI-FLOAT (Para SAAE e outros) ---
                if df is not None and not df.empty:
                    # Resolve colunas duplicadas (Comum no Econômico/Imobiliário)
                    df = df.loc[:, ~df.columns.duplicated()]

                    # Converte tudo para string e limpa NaNs (Resolve o erro do len() no CPF)
                    df = df.astype(str).replace(['nan', 'NaN', 'None', '<NA>', 'nan.0'], '')

                    # Limpeza de nomes de colunas (Unnamed) e espaços
                    df.columns = [str(c).strip() for c in df.columns]
                    df = df.loc[:, ~df.columns.str.contains('^Unnamed|^nan', case=False)]

                    # Trim em todas as células
                    df = df.apply(lambda x: x.str.strip() if hasattr(x, 'str') else x)

                    df = self.__removerRodapePorQuantidade(df, parameter.footer)
                    dfs.append(df)
                else:
                    self.logger.warning(f"Arquivo {arquivo.name} ignorado (vazio ou formato incompatível).")

            except Exception as e:
                self.logger.error(f"Erro ao processar {arquivo.name}: {e}")

        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

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
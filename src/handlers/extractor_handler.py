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

        # Melhorando a busca de arquivos para ser case-insensitive
        arquivos = list(caminho_base.glob(f"*.[xX][lL][sS]*")) if parameter.formato.lower() in ['xls',
                                                                                                'xlsx'] else list(
            caminho_base.glob(f"*.{parameter.formato}"))

        dfs = []
        self.logger.info(f"Quantidade de arquivos encontrados: {len(arquivos)}")

        for arquivo in arquivos:
            # 1. IGNORAR ARQUIVOS TEMPORÁRIOS E DE TRAVAMENTO DO EXCEL
            #if arquivo.name.startswith("~") or arquivo.name.startswith(".~"):
            #    self.logger.warning(f"Ignorando arquivo temporário: {arquivo.name}")
            #    continue

            df = None
            try:
                self.logger.info(f"Tentando extração: {arquivo.name}")

                # CORREÇÃO: Captura a extensão real do arquivo atual ignorando o parâmetro genérico
                ext = arquivo.suffix.lower().strip('.')

                # Mantém a compatibilidade forçada se for csv
                if parameter.formato.lower() == "csv":
                    ext = "csv"

                if ext == "xlsx":
                    df = pd.read_excel(arquivo, header=parameter.header, engine='openpyxl')

                elif ext == "xls":
                    # --- ESTRATÉGIA DE DESCOBERTA DE TIPO (SNIFFING) ---
                    # Lemos o início do arquivo em binário para identificar a assinatura real
                    tipo_detectado = "binario"

                    try:
                        with open(arquivo, 'rb') as f:
                            header_bytes = f.read(500)
                            if b'<?xml' in header_bytes:
                                tipo_detectado = "xml"
                            elif b'<table' in header_bytes.lower() or b'<html' in header_bytes.lower():
                                tipo_detectado = "html"
                    except Exception as e:
                        self.logger.error(f"Erro ao ler cabeçalho de {arquivo.name}: {e}")

                    # --- EXECUÇÃO DA EXTRAÇÃO BASEADA NO TIPO ---
                    if tipo_detectado == "xml":
                        self.logger.info(f"Processando como XML Spreadsheet 2003: {arquivo.name}")
                        with open(arquivo, 'r', encoding='utf-8', errors='ignore') as f:
                            conteudo = f.read()

                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(conteudo, 'xml')
                        linhas = []

                        # Procura por Row com ou sem namespace
                        for row in soup.find_all(['Row', 'ss:Row']):
                            celulas = [c.get_text(strip=True) for c in
                                       row.find_all(['Data', 'ss:Data', 'Cell', 'ss:Cell'])]
                            if any(celulas):
                                linhas.append(celulas)

                        if linhas:
                            df = pd.DataFrame(linhas)
                            h_idx = int(parameter.header) if parameter.header is not None else 0

                            if len(df) > h_idx:
                                df.columns = df.iloc[h_idx]
                                df = df.iloc[h_idx + 1:].reset_index(drop=True)

                    elif tipo_detectado == "html":
                        self.logger.info(f"Processando como HTML: {arquivo.name}")
                        from io import StringIO

                        with open(arquivo, 'r', encoding='utf-8', errors='ignore') as f:
                            conteudo = f.read()

                        dfs_html = pd.read_html(StringIO(conteudo))
                        if dfs_html:
                            df = dfs_html[0]

                    else:
                        # Se for binário real (BIFF8), usamos o xlrd
                        try:
                            # Forçamos o motor xlrd para evitar que o pandas tente zip/openpyxl
                            df = pd.read_excel(arquivo, header=parameter.header, engine='xlrd')
                        except Exception as e:
                            self.logger.error(f"Falha total no XLS binário {arquivo.name}: {e}")

                elif ext == "csv":
                    df = pd.read_csv(arquivo, sep=parameter.sep, header=parameter.header, encoding='utf-8',
                                     on_bad_lines='skip')

                # --- BLINDAGEM FINAL (Evita o erro 'float has no len()') ---
                if df is not None and not df.empty:
                    # Remove colunas fantasmas e limpa nomes
                    df = df.loc[:, ~df.columns.duplicated()]
                    df.columns = [str(c).strip() for c in df.columns]
                    df = df.loc[:, ~df.columns.str.contains('^Unnamed|^nan', case=False)]

                    # CONVERSÃO CRÍTICA: Transforma TUDO em string e limpa lixo de float
                    df = df.fillna('').astype(str).replace(['nan', 'NaN', 'None', '<NA>', 'nan.0'], '')

                    # Trim em todas as células
                    df = df.apply(lambda x: x.str.strip())

                    df = self.__removerRodapePorQuantidade(df, parameter.footer)
                    dfs.append(df)
                else:
                    self.logger.warning(f"Arquivo {arquivo.name} resultou em DataFrame vazio.")

            except Exception as e:
                self.logger.error(f"Erro fatal ao processar {arquivo.name}: {e}")

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
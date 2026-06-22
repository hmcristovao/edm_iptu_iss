import logging
import re
import pandas as pd
from src.moduloI.handlers.ultis.handler import IterHander


class MultivariablesHanderBuilder:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def build(self, df: pd.DataFrame, col_alvo: str, nome_amigavel: str) -> pd.DataFrame:
        # Instanciação dos elos
        cpf_h = CPFHandler()
        cnpj_h = CNPJHandler()
        cpf_v_h = CPFValidoHandler()
        cnpj_v_h = CNPJValidoHandler()

        # Montagem da Chain of Responsibility
        cpf_h.set_next(cnpj_h).set_next(cpf_v_h).set_next(cnpj_v_h)

        # Início do processamento
        resultado = cpf_h.handle(df, col_alvo, nome_amigavel)

        if nome_amigavel not in resultado.columns:
            self.logger.warning(
                f"Atenção: Nenhuma regra aplicada para criar '{nome_amigavel}' a partir de '{col_alvo}'"
            )

        return resultado


# --- Handlers de Limpeza ---

class CPFHandler(IterHander):
    def handle(self, df: pd.DataFrame, col_alvo: str, nome_amigavel: str) -> pd.DataFrame:
        nome_lower = nome_amigavel.lower()
        if "cpf" in nome_lower and "valido" not in nome_lower:
            # astype(str) impede erro de float, .replace trata o conteúdo
            serie_limpa = df[col_alvo].astype(str).str.replace(r"\D", "", regex=True)
            # Garante que valores 'nan' ou vazios fiquem em branco
            df[nome_amigavel] = serie_limpa.where((serie_limpa.str.len() == 11) & (serie_limpa != "nan"), "")
            logging.getLogger(self.__class__.__name__).info(f"Sucesso: Limpeza CPF -> {nome_amigavel}")
            return df
        return super().handle(df, col_alvo, nome_amigavel)


class CNPJHandler(IterHander):
    def handle(self, df: pd.DataFrame, col_alvo: str, nome_amigavel: str) -> pd.DataFrame:
        nome_lower = nome_amigavel.lower()
        if "cnpj" in nome_lower and "valido" not in nome_lower:
            serie_limpa = df[col_alvo].astype(str).str.replace(r"\D", "", regex=True)
            df[nome_amigavel] = serie_limpa.where((serie_limpa.str.len() == 14) & (serie_limpa != "nan"), "")
            logging.getLogger(self.__class__.__name__).info(f"Sucesso: Limpeza CNPJ -> {nome_amigavel}")
            return df
        return super().handle(df, col_alvo, nome_amigavel)


# --- Handlers de Validação ---

class CPFValidoHandler(IterHander):
    def _validar_cpf(self, cpf: str) -> str:
        # Limpeza e verificação de tipo dentro da função
        cpf = re.sub(r'\D', '', str(cpf))
        if not cpf or cpf.lower() == 'nan' or len(cpf) != 11 or cpf == cpf[0] * 11:
            return "N"

        try:
            for i in range(9, 11):
                soma = sum(int(cpf[num]) * ((i + 1) - num) for num in range(i))
                digito = (soma * 10 % 11) % 10
                if digito != int(cpf[i]): return "N"
            return "S"
        except (ValueError, IndexError):
            return "N"

    def handle(self, df: pd.DataFrame, col_alvo: str, nome_amigavel: str) -> pd.DataFrame:
        if "cpf" in nome_amigavel.lower() and "valido" in nome_amigavel.lower():
            df[nome_amigavel] = df[col_alvo].apply(self._validar_cpf)
            logging.getLogger(self.__class__.__name__).info(f"Sucesso: Validação CPF -> {nome_amigavel}")
            return df
        return super().handle(df, col_alvo, nome_amigavel)


class CNPJValidoHandler(IterHander):
    def _validar_cnpj(self, cnpj: str) -> str:
        cnpj = re.sub(r'\D', '', str(cnpj))
        if not cnpj or cnpj.lower() == 'nan' or len(cnpj) != 14 or cnpj == cnpj[0] * 14:
            return "N"

        def calcular_digito(fatia, pesos):
            soma = sum(int(digit) * weight for digit, weight in zip(fatia, pesos))
            resto = soma % 11
            return 0 if resto < 2 else 11 - resto

        try:
            pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
            pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

            if calcular_digito(cnpj[:12], pesos1) != int(cnpj[12]): return "N"
            if calcular_digito(cnpj[:13], pesos2) != int(cnpj[13]): return "N"
            return "S"
        except (ValueError, IndexError):
            return "N"

    def handle(self, df: pd.DataFrame, col_alvo: str, nome_amigavel: str) -> pd.DataFrame:
        if "cnpj" in nome_amigavel.lower() and "valido" in nome_amigavel.lower():
            df[nome_amigavel] = df[col_alvo].apply(self._validar_cnpj)
            logging.getLogger(self.__class__.__name__).info(f"Sucesso: Validação CNPJ -> {nome_amigavel}")
            return df
        return super().handle(df, col_alvo, nome_amigavel)

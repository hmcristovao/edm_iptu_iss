import logging
import pandas as pd
from src.handlers.ultis.handler import IterHander

class MultivariablesHanderBuilder:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def build(self, df: pd.DataFrame, col_alvo: str, nome_amigavel: str) -> pd.DataFrame:
        # Instanciação dos elos
        cpf_h = CPFHandler()
        cnpj_h = CNPJHandler()
        cpf_v_h = CPFValidoHandler()
        cnpj_v_h = CNPJValidoHandler()

        # Montagem da Corrente (Chain of Responsibility)
        # O set_next deve retornar o próximo handler para permitir encadeamento
        cpf_h.set_next(cnpj_h)
        cnpj_h.set_next(cpf_v_h)
        cpf_v_h.set_next(cnpj_v_h)

        # Início do processamento
        resultado = cpf_h.handle(df, col_alvo, nome_amigavel)

        if nome_amigavel not in resultado.columns:
            self.logger.warning(
                f"Atenção: Nenhuma regra aplicada para criar '{nome_amigavel}' a partir de '{col_alvo}'"
            )

        return resultado

# --- Handlers de Limpeza (Apenas removem caracteres e formatam) ---

class CPFHandler(IterHander):
    def handle(self, df: pd.DataFrame, col_alvo: str, nome_amigavel: str) -> pd.DataFrame:
        nome_lower = nome_amigavel.lower()
        # Regra: Tem 'cpf', mas NÃO tem 'valido'
        if "cpf" in nome_lower and "valido" not in nome_lower:
            serie_limpa = df[col_alvo].astype(str).str.replace(r"\D", "", regex=True)
            df[nome_amigavel] = serie_limpa.where(serie_limpa.str.len() == 11, "")
            logging.getLogger(self.__class__.__name__).info(f"Sucesso: Limpeza CPF -> {nome_amigavel}")
            return df
        return super().handle(df, col_alvo, nome_amigavel)

class CNPJHandler(IterHander):
    def handle(self, df: pd.DataFrame, col_alvo: str, nome_amigavel: str) -> pd.DataFrame:
        nome_lower = nome_amigavel.lower()
        # Regra: Tem 'cnpj', mas NÃO tem 'valido'
        if "cnpj" in nome_lower and "valido" not in nome_lower:
            serie_limpa = df[col_alvo].astype(str).str.replace(r"\D", "", regex=True)
            df[nome_amigavel] = serie_limpa.where(serie_limpa.str.len() == 14, "")
            logging.getLogger(self.__class__.__name__).info(f"Sucesso: Limpeza CNPJ -> {nome_amigavel}")
            return df
        return super().handle(df, col_alvo, nome_amigavel)

# --- Handlers de Validação (Contêm a lógica de cálculo de dígito) ---

class CPFValidoHandler(IterHander):
    def _validar_cpf(self, cpf: str) -> str:
        if not cpf or len(cpf) != 11 or cpf == cpf[0] * 11:
            return "N"
        for i in range(9, 11):
            soma = sum(int(cpf[num]) * ((i + 1) - num) for num in range(i))
            digito = (soma * 10 % 11) % 10
            if digito != int(cpf[i]): return "N"
        return "S"

    def handle(self, df: pd.DataFrame, col_alvo: str, nome_amigavel: str) -> pd.DataFrame:
        nome_lower = nome_amigavel.lower()
        # Regra: Tem 'cpf' E tem 'valido'
        if "cpf" in nome_lower and "valido" in nome_lower:
            serie_limpa = df[col_alvo].astype(str).str.replace(r"\D", "", regex=True)
            df[nome_amigavel] = serie_limpa.apply(self._validar_cpf)
            logging.getLogger(self.__class__.__name__).info(f"Sucesso: Validação CPF -> {nome_amigavel}")
            return df
        return super().handle(df, col_alvo, nome_amigavel)

class CNPJValidoHandler(IterHander):
    def _validar_cnpj(self, cnpj: str) -> str:
        if not cnpj or len(cnpj) != 14 or cnpj == cnpj[0] * 14:
            return "N"
        pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        for i in range(12, 14):
            soma = sum(int(cnpj[num]) * (pesos[num - (i - 12)]) for num in range(i))
            digito = (soma % 11)
            digito = 0 if digito < 2 else 11 - digito
            if digito != int(cnpj[i]): return "N"
            pesos.insert(0, 6)
        return "S"

    def handle(self, df: pd.DataFrame, col_alvo: str, nome_amigavel: str) -> pd.DataFrame:
        nome_lower = nome_amigavel.lower()
        # Regra: Tem 'cnpj' E tem 'valido'
        if "cnpj" in nome_lower and "valido" in nome_lower:
            serie_limpa = df[col_alvo].astype(str).str.replace(r"\D", "", regex=True)
            df[nome_amigavel] = serie_limpa.apply(self._validar_cnpj)
            logging.getLogger(self.__class__.__name__).info(f"Sucesso: Validação CNPJ -> {nome_amigavel}")
            return df
        return super().handle(df, col_alvo, nome_amigavel)
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

        # Montagem da Corrente
        cpf_h.set_next(cnpj_h) \
            .set_next(cpf_v_h) \
            .set_next(cnpj_v_h)

        # Guarda as colunas atuais para comparar depois
        colunas_antes = set(df.columns)

        # Início do processamento
        resultado = cpf_h.handle(df, col_alvo, nome_amigavel)

        # VERIFICAÇÃO: Se a coluna nome_amigavel não existe no resultado,
        # significa que nenhum handler a processou.
        if nome_amigavel not in resultado.columns:
            self.logger.warning(
                f"Atenção: Nenhuma regra aplicada para criar '{nome_amigavel}' a partir de '{col_alvo}'"
            )

        return resultado

# --- Handlers ---

class CPFHandler(IterHander):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def handle(self, df: pd.DataFrame, col_alvo: str, nome_amigavel: str) -> pd.DataFrame:
        if nome_amigavel == "cpf":  # Verificando pelo nome da coluna que se deseja gerar
            serie_limpa = df[col_alvo].astype(str).str.replace(r"\D", "", regex=True)
            df[nome_amigavel] = serie_limpa.where(serie_limpa.str.len() == 11, "")
            self.logger.info(f"Sucesso: Criada coluna CPF a partir de {col_alvo}")
            return df
        return super().handle(df, col_alvo, nome_amigavel)


class CNPJHandler(IterHander):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def handle(self, df: pd.DataFrame, col_alvo: str, nome_amigavel: str) -> pd.DataFrame:
        if nome_amigavel == "cnpj":
            serie_limpa = df[col_alvo].astype(str).str.replace(r"\D", "", regex=True)
            df[nome_amigavel] = serie_limpa.where(serie_limpa.str.len() == 14, "")
            self.logger.info(f"Sucesso: Criada coluna CNPJ a partir de {col_alvo}")
            return df
        return super().handle(df, col_alvo, nome_amigavel)


class CPFValidoHandler(IterHander):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def _validar_cpf(self, cpf: str) -> str:
        if not cpf or len(cpf) != 11 or cpf == cpf[0] * 11:
            return "N"
        for i in range(9, 11):
            soma = sum(int(cpf[num]) * ((i + 1) - num) for num in range(i))
            digito = (soma * 10 % 11) % 10
            if digito != int(cpf[i]): return "N"
        return "S"

    def handle(self, df: pd.DataFrame, col_alvo: str, nome_amigavel: str) -> pd.DataFrame:
        if nome_amigavel == "cpfValido":
            serie_limpa = df[col_alvo].astype(str).str.replace(r"\D", "", regex=True)
            df[nome_amigavel] = serie_limpa.apply(self._validar_cpf)
            self.logger.info(f"Sucesso: Criada coluna cpf valido a partir de {col_alvo}")
            return df
        return super().handle(df, col_alvo, nome_amigavel)


class CNPJValidoHandler(IterHander):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

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
        if nome_amigavel == "cnpjValido":
            serie_limpa = df[col_alvo].astype(str).str.replace(r"\D", "", regex=True)
            df[nome_amigavel] = serie_limpa.apply(self._validar_cnpj)
            self.logger.info(f"Sucesso: Criada coluna cnpj valido a partir de {col_alvo}")
            return df
        return super().handle(df, col_alvo, nome_amigavel)
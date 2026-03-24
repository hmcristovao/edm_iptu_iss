import logging

from src.Domain.Package import Package
from src.handlers.Handler import AbstractHandler
from src.handlers.adapters.anomizador.IAnomizador import AnomizadorAdapter


class PseudonymizationHandler(AbstractHandler):
    def __init__(self, anonymity:AnomizadorAdapter):
        super().__init__()
        self.anon = anonymity
        self.logger = logging.getLogger(self.__class__.__name__)
    def anonimizar(self, df, colDado, colValido):
        def processar(row):
            valor = row[colDado]
            valido = row[colValido]
            if valido == "S" and isinstance(valor, str) and valor.strip() != "":
                return self.anon.encrypt(valor)
            return valor

        df[colDado] = df.apply(processar, axis=1)
        return df

    def desanonimizar(self, df, colDado, colValido):
        def processar(row):
            valor = row[colDado]
            valido = row[colValido]
            if valido == "S" and isinstance(valor, str) and valor.strip() != "":
                try:
                    return self.anon.decrypt(valor)
                except Exception:
                    return valor
            return valor

        df[colDado] = df.apply(processar, axis=1)
        return df

    def handle(self, request: Package) -> Package:
        df = request.datas
        self.logger.info(f'Iniciando Pseudonimização dinâmica - {request.parameters.sufixo}')

        # 1. Mapeamento de possíveis nomes vs validações
        # Adicione aqui os padrões que você costuma usar
        mapeamento = {
            "cpf": "cpfValido",
            "CPF": "cpfValido",
            "cnpj": "cnpjValido",
            "numCpf": "cpfValido",  # Caso você use numCpf no TXT
            "numCnpj": "cnpjValido"
        }

        # 2. Itera sobre as colunas que REALMENTE existem no DF
        colunas_encontradas = [col for col in df.columns if col in mapeamento]

        if not colunas_encontradas:
            self.logger.warning("Nenhuma coluna de documento (CPF/CNPJ) encontrada para pseudonimizar.")
            return super().handle(request)

        for col in colunas_encontradas:
            col_valida = mapeamento[col]

            # Só tenta anonimizar se a coluna de 'Validação' também existir
            if col_valida in df.columns:
                self.logger.info(f"Processando coluna: {col} usando validação: {col_valida}")
                df = self.anonimizar(df, col, col_valida)
            else:
                self.logger.warning(f"Pulo: Coluna {col} encontrada, mas {col_valida} está ausente.")

        request.datas = df
        return super().handle(request)
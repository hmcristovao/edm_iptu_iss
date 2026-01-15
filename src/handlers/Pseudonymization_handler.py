import logging

from src.Domain.Package import Package
from src.handlers.Handler import AbstractHandler


class PseudonymizationHandler(AbstractHandler):
    def __init__(self):
        super().__init__()
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
        self.logger.info(f'Pseudonizando - {request.parameters.sufixo}')
        df = self.anonimizar(df, "cpf", "cpfValido")
        request.datas = self.anonimizar(df, "cnpj", "cnpjValido")

        return super().handle(request)
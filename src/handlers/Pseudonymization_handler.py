import logging
from src.Domain.Package import Package
from src.handlers.Handler import AbstractHandler
from src.handlers.adapters.anomizador.IAnomizador import AnomizadorAdapter

class PseudonymizationHandler(AbstractHandler):
    def __init__(self, anonymity: AnomizadorAdapter):
        super().__init__()
        self.anon = anonymity
        self.logger = logging.getLogger(self.__class__.__name__)

    def anonimizar(self, df, col_dado, col_valido):
        def processar(row):
            valor = row[col_dado]
            valido = row[col_valido]
            # Garante que o valor existe, é string e a validação é "S"
            if valido == "S" and isinstance(valor, str) and valor.strip():
                return self.anon.encrypt(valor)
            return valor

        df[col_dado] = df.apply(processar, axis=1)
        return df

    def handle(self, request: Package) -> Package:
        df = request.datas
        self.logger.info(df.columns)
        sufixo = request.parameters.sufixo[0]
        self.logger.info(f'Iniciando Pseudonimização dinâmica - {sufixo}')

        # 1. Identifica colunas de dados (ex: 'cpfEconomico', 'numCpf')
        colunas_documento = [
            col for col in df.columns
            if col is not None and ('cpf' in str(col).lower() or 'cnpj' in str(col).lower())
        ]

        for col in colunas_documento:
            tipo = "cpf" if "cpf" in str(col).lower() else "cnpj"

            # 2. Busca flexível pela coluna de validação
            # Procura uma coluna que contenha 'cpf' + 'valido' (ou cnpj)
            col_valida = None
            for c in df.columns:
                if c is not None and tipo in str(c).lower():
                    col_valida = c
                    break

            # 3. Executa a anonimização se encontrou o par
            if col_valida:
                self.logger.info(f"Casamento encontrado: Dado '{col}' com Validação '{col_valida}'")
                df = self.anonimizar(df, col, col_valida)
            else:
                self.logger.warning(
                    f"Coluna '{col}' ignorada: Nenhuma coluna de validação para {tipo} encontrada no DF.")

        request.datas = df
        return super().handle(request)
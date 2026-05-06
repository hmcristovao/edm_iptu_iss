import logging
import pandas as pd
from src.Domain.Package import Package
from src.handlers.Handler import AbstractHandler
from src.handlers.adapters.anomizador.IAnomizador import AnomizadorAdapter


class PseudonymizationHandler(AbstractHandler):
    def __init__(self, anonymity: AnomizadorAdapter):
        super().__init__()
        self.anon = anonymity
        self.logger = logging.getLogger(self.__class__.__name__)

    def anonimizar(self, df, col_dado, col_valido):
        """
        Aplica a criptografia apenas se a coluna de validação contiver 'S'.
        """

        def processar(row):
            valor = row[col_dado]
            valido = row[col_valido]

            # Normaliza o valor de validação (remove espaços e coloca em maiúsculo)
            status = str(valido).strip().upper() if pd.notna(valido) else ""

            # Condição para criptografar
            if status == "S" and isinstance(valor, str) and valor.strip():
                return self.anon.encrypt(valor)
            return valor

        self.logger.info(f"Executando criptografia em '{col_dado}' baseado em '{col_valido}'")
        df[col_dado] = df.apply(processar, axis=1)
        return df

    def handle(self, request: Package) -> Package:
        df = request.datas

        # Remove colunas "Unnamed"
        unnamed = [col for col in df.columns if "Unnamed:" in str(col).lower()]

        if unnamed:
            self.logger.warning(f"possivel mal formatacao na especificacao do head: {unnamed}")

        sufixo = request.parameters.sufixo[0]
        self.logger.info(f'--- Iniciando Pseudonimização dinâmica - {sufixo} ---')

        # 1. Identifica colunas que realmente contêm CPF/CNPJ
        colunas_documento = [
            col for col in df.columns
            if col is not None
               and ('cpf' in str(col).lower() or 'cnpj' in str(col).lower())
               and 'valido' not in str(col).lower()
        ]

        for col in colunas_documento:
            col_lower = str(col).lower()
            tipo = "cpf" if "cpf" in col_lower else "cnpj"

            # 2. Busca coluna de validação correspondente
            col_valida = None

            for c in df.columns:
                c_nome = str(c).lower()

                if (
                        c != col
                        and tipo in c_nome
                        and 'valid' in c_nome
                ):
                    col_valida = c
                    break

            # 3. Executa anonimização
            if col_valida:
                self.logger.info(
                    f"Anonimizando colunas: {col} / {col_valida}"
                )
                df = self.anonimizar(df, col, col_valida)
            else:
                self.logger.warning(
                    f"Coluna '{col}' ignorada: validação não encontrada."
                )

        request.datas = df
        return super().handle(request)
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
        sufixo = request.parameters.sufixo[0]
        self.logger.info(f'--- Iniciando Pseudonimização dinâmica - {sufixo} ---')

        # 1. Identifica colunas que REALMENTE contêm dados (CPF/CNPJ)
        # Filtramos para ignorar colunas que já são de validação (ex: cpfValido)
        colunas_documento = [
            col for col in df.columns
            if col is not None
               and ('cpf' in str(col).lower() or 'cnpj' in str(col).lower())
               and 'valido' not in str(col).lower()
        ]

        for col in colunas_documento:
            col_lower = str(col).lower()
            tipo = "cpf" if "cpf" in col_lower else "cnpj"

            # 2. Busca refinada pela coluna de validação correspondente
            col_valida = None
            for c in df.columns:
                c_nome = str(c).lower()

                # Regras para ser a coluna de validação correta:
                # - Deve ser uma coluna diferente da de dado (c != col)
                # - Deve conter o tipo (cpf ou cnpj)
                # - Deve conter o termo 'valido' ou 'validacao'
                if c != col and tipo in c_nome and ('valid' in c_nome):
                    col_valida = c
                    break

            # 3. Executa se o par foi encontrado corretamente
            if col_valida:
                df = self.anonimizar(df, col, col_valida)
            else:
                self.logger.warning(
                    f"Coluna '{col}' ignorada: Nenhuma coluna de validação específica encontrada para {tipo}."
                )

        request.datas = df
        return super().handle(request)
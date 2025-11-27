import pandas as pd
import glob
import os
from Anonimizador import AnonimizadorReversivel


class ProcessadorSaae:
    def __init__(self, pasta):
        self.pasta = pasta
        self.anon = AnonimizadorReversivel()

    # ----------------------------------------------------------------------
    # Carregar e unir XLSX
    # ----------------------------------------------------------------------
    def carregarUnirXlsx(self):
        arquivos = glob.glob(os.path.join(self.pasta, "*.xlsx"))

        dfs = []
        for arquivo in arquivos:
            df = pd.read_excel(arquivo, header=2)
            dfs.append(df)

        dfUnido = pd.concat(dfs, ignore_index=True)
        return dfUnido

    # ----------------------------------------------------------------------
    # Validação CPF e CNPJ
    # ----------------------------------------------------------------------
    @staticmethod
    def validarCpf(cpf: str) -> bool:
        cpf = ''.join(filter(str.isdigit, str(cpf)))

        if len(cpf) != 11:
            return False
        if cpf == cpf[0] * 11:
            return False

        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        d1 = (soma * 10) % 11
        d1 = 0 if d1 == 10 else d1

        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        d2 = (soma * 10) % 11
        d2 = 0 if d2 == 10 else d2

        return cpf[-2:] == f"{d1}{d2}"

    @staticmethod
    def validarCnpj(cnpj: str) -> bool:
        cnpj = ''.join(filter(str.isdigit, str(cnpj)))

        if len(cnpj) != 14:
            return False
        if cnpj == cnpj[0] * 14:
            return False

        pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        pesos2 = [6] + pesos1

        soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
        d1 = 11 - (soma % 11)
        d1 = 0 if d1 >= 10 else d1

        soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
        d2 = 11 - (soma % 11)
        d2 = 0 if d2 >= 10 else d2

        return cnpj[-2:] == f"{d1}{d2}"

    # ----------------------------------------------------------------------
    # Padronizar colunas
    # ----------------------------------------------------------------------
    def padronizarColunas(self, df):
        df = df.copy()

        rename_map = {
            "Ligação": "codigoLigacao",
            "Cliente": "nomeCliente",
            "Documento": "Documento",
            "Contato": "telefone",
            "Tipo do logradouro": "tipoLogradouro",
            "Logradouro": "logradouro",
            "Número": "numero",
            "Bairro": "bairro",
            "Complemento": "complemento",
            "CEP": "cep",
        }

        df = df.rename(columns={orig: dest for orig, dest in rename_map.items() if orig in df.columns})

        if "Documento" in df.columns:
            doc_series = df["Documento"].astype(str).str.replace(r"\D", "", regex=True)

            df["cpf"] = doc_series.where(doc_series.str.len() == 11, "")
            df["cnpj"] = doc_series.where(doc_series.str.len() == 14, "")

            df["cpfValido"] = df["cpf"].apply(lambda x: "S" if self.validarCpf(x) else "N")
            df["cnpjValido"] = df["cnpj"].apply(lambda x: "S" if self.validarCnpj(x) else "N")

            df = df.drop(columns=["Documento"])
        else:
            df["cpf"] = ""
            df["cnpj"] = ""
            df["cpfValido"] = "N"
            df["cnpjValido"] = "N"

        colunas_finais = [
            "nomeCliente",
            "cpf", "cpfValido", "cnpj", "cnpjValido",
            "telefone",
            "tipoLogradouro",
            "logradouro",
            "numero",
            "bairro",
            "complemento",
            "cep",
            "codigoLigacao",
        ]

        for col in colunas_finais:
            if col not in df.columns:
                df[col] = "N" if col in ("cpfValido", "cnpjValido") else ""

        outras = [c for c in df.columns if c not in colunas_finais]
        df = df[colunas_finais + outras]

        return df

    # ----------------------------------------------------------------------
    # Anonimizar e desanonimizar
    # ----------------------------------------------------------------------
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

    # ----------------------------------------------------------------------
    # Pipeline completo
    # ----------------------------------------------------------------------
    def processar(self, salvar=True):
        df = self.carregarUnirXlsx()
        df = self.padronizarColunas(df)

        df = self.anonimizar(df, "cpf", "cpfValido")
        df = self.anonimizar(df, "cnpj", "cnpjValido")

        df = self.desanonimizar(df, "cpf", "cpfValido")
        df = self.desanonimizar(df, "cnpj", "cnpjValido")

        if salvar:
            out_csv = os.path.join(self.pasta, "Saae.csv")
            df.to_csv(out_csv, index=False)
            print("Arquivos gerados:")
            print(out_csv)

        return df
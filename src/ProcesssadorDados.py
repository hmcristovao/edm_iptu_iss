import pandas as pd
import glob
import os
import re
from Anonimizador import AnonimizadorReversivel


class ProcessadorDados:
    def __init__(self, config, info):
        self.info = info
        self.config = config.sort_values("ordem")
        self.anon = AnonimizadorReversivel()

        # 🔹 Registro de validadores por tipo de documento
        self.validadores = {
            "cpf": self.validarCpf,
            "cnpj": self.validarCnpj
        }

    # ----------------------------------------------------------------------
    # Remover rodapé por quantidade de linhas
    # ----------------------------------------------------------------------
    def removerRodapePorQuantidade(self, df, footer):
        if not footer:
            return df

        footer = int(footer)

        if footer <= 0:
            return df

        if footer >= len(df):
            return df.iloc[0:0]

        return df.iloc[:-footer]

    # ----------------------------------------------------------------------
    # Carregar e unir arquivos XLSX
    # ----------------------------------------------------------------------
    def carregarArquivosXlsx(self):
        arquivos = glob.glob(os.path.join(self.info["pasta"], "*.xlsx"))
        dfs = []

        for arquivo in arquivos:
            if os.path.basename(arquivo).startswith("~$"):
                continue

            df = pd.read_excel(arquivo, header=int(self.info["header"]))
            df = self.removerRodapePorQuantidade(df, self.info.get("footer", 0))
            dfs.append(df)

        if not dfs:
            raise RuntimeError("Nenhum XLSX válido encontrado.")

        return pd.concat(dfs, ignore_index=True)

    # ----------------------------------------------------------------------
    # Utilidades
    # ----------------------------------------------------------------------
    def extrairDigitos(self, valor):
        if pd.isna(valor):
            return ""
        return re.sub(r"\D", "", str(valor))

    # ----------------------------------------------------------------------
    # Mapeamento semântico de documentos
    # ----------------------------------------------------------------------
    def extrairMapeamentoDocumento(self, colunas):
        mapa = {}

        for c in colunas:
            nome = c.lower()

            if "cpf" in nome and "val" not in nome:
                mapa["cpf"] = c
            elif "cpf" in nome and "val" in nome:
                mapa["cpfValido"] = c
            elif "cnpj" in nome and "val" not in nome:
                mapa["cnpj"] = c
            elif "cnpj" in nome and "val" in nome:
                mapa["cnpjValido"] = c

        return mapa

    # ----------------------------------------------------------------------
    # Validações desacopladas
    # ----------------------------------------------------------------------
    @staticmethod
    def validarCpf(cpf: str) -> bool:
        cpf = ''.join(filter(str.isdigit, str(cpf)))
        if len(cpf) != 11 or cpf == cpf[0] * 11:
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
        if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
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
    # Padronização baseada em config
    # ----------------------------------------------------------------------
    def mapearEstrutura(self, df):
        resultado = pd.DataFrame()

        for _, row in self.config.iterrows():
            origem = row["nome"]
            destinos = row["colunas"]

            if any("cpf" in c.lower() or "cnpj" in c.lower() for c in destinos):
                mapa = self.extrairMapeamentoDocumento(destinos)
                doc = df[origem].fillna("").apply(self.extrairDigitos)

                for tipo, col in [("cpf", 11), ("cnpj", 14)]:
                    valores = doc.where(doc.str.len() == col, "")
                    resultado[mapa[tipo]] = valores
                    validador = self.validadores[tipo]
                    resultado[mapa[f"{tipo}Valido"]] = valores.apply(lambda x: "S" if validador(x) else "N")

            else:
                resultado[destinos[0]] = df[origem]

        extras = df.drop(columns=[c for c in self.config["nome"] if c in df], errors="ignore")
        return pd.concat([resultado, extras], axis=1)

    # ----------------------------------------------------------------------
    # Anonimização
    # ----------------------------------------------------------------------
    def anonimizarColuna(self, df, colDado, colValido):
        df[colDado] = df.apply(
            lambda r: self.anon.encrypt(r[colDado])
            if r[colValido] == "S" and isinstance(r[colDado], str) and r[colDado].strip()
            else r[colDado],
            axis=1
        )
        return df

    def desanonimizarColuna(self, df, colDado, colValido):
        def processar(r):
            if r[colValido] == "S" and isinstance(r[colDado], str) and r[colDado].strip():
                try:
                    return self.anon.decrypt(r[colDado])
                except Exception:
                    return r[colDado]
            return r[colDado]

        df[colDado] = df.apply(processar, axis=1)
        return df

    # ----------------------------------------------------------------------
    # Pipeline
    # ----------------------------------------------------------------------
    def executarPipeline(self, salvar=True):
        df = self.carregarArquivosXlsx()
        df = self.mapearEstrutura(df)

        for tipo in self.validadores.keys():
            df = self.anonimizarColuna(df, tipo, f"{tipo}Valido")
            # df = self.desanonimizarColuna(df, tipo, f"{tipo}Valido")

        if salvar:
            caminho = os.path.join(self.info["pasta"], self.info["saida"])
            df.to_csv(caminho, index=False)
            print("Arquivo gerado:", caminho)

        return df

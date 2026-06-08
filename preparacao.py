from functools import reduce
from contextlib import contextmanager
import os
import re
import sys

import pandas as pd


CODE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.environ.get("AVALIADOR_WORKDIR", CODE_DIR)
PASTA_DADOS = "."
PASTA_GERADOS = "arquivos_gerados"
PASTA_LOGS = "logs"
ARQUIVO_FINAL = os.path.join(PASTA_GERADOS, "integracao_base.csv")
ARQUIVO_LOG_TXT = os.path.join(PASTA_LOGS, "integracao_preparacao_log.txt")


def caminho_projeto(caminho: str) -> str:
    if os.path.isabs(caminho):
        return caminho

    return os.path.join(BASE_DIR, caminho)


def garantir_pasta(caminho: str):
    os.makedirs(caminho_projeto(caminho), exist_ok=True)


class Tee:
    def __init__(self, *arquivos):
        self.arquivos = arquivos

    def write(self, texto):
        for indice, arquivo in enumerate(self.arquivos):
            texto_saida = texto

            if indice > 0 and "\r" in texto_saida:
                if "\n" not in texto_saida:
                    continue

                texto_saida = texto_saida.split("\r")[-1]

            arquivo.write(texto_saida)
            arquivo.flush()

    def flush(self):
        for arquivo in self.arquivos:
            arquivo.flush()


@contextmanager
def registrar_log_terminal(caminho_log: str):
    stdout_original = sys.stdout
    stderr_original = sys.stderr

    garantir_pasta(os.path.dirname(caminho_log))

    with open(caminho_projeto(caminho_log), "w", encoding="utf-8") as arquivo_log:
        sys.stdout = Tee(stdout_original, arquivo_log)
        sys.stderr = Tee(stderr_original, arquivo_log)

        try:
            yield
        finally:
            sys.stdout = stdout_original
            sys.stderr = stderr_original


def encontrar_coluna(df: pd.DataFrame, nome_tabela: str, padrao: str, excluir=()):
    regex = re.compile(padrao, re.IGNORECASE)
    termos_excluidos = tuple(termo.lower() for termo in excluir)

    for coluna in df.columns:
        coluna_lower = coluna.lower()

        if any(termo in coluna_lower for termo in termos_excluidos):
            continue

        if regex.fullmatch(coluna):
            return coluna

    return None


def encontrar_colunas_chave(df: pd.DataFrame, nome_tabela: str):
    nome = re.escape(nome_tabela)

    col_cpfcnpj = encontrar_coluna(
        df,
        nome_tabela,
        rf".*cpf.*cnpj.*{nome}.*",
        excluir=("valido",),
    )
    col_cpf = encontrar_coluna(
        df,
        nome_tabela,
        rf".*cpf.*{nome}.*",
        excluir=("cnpj", "valido"),
    )
    col_cnpj = encontrar_coluna(
        df,
        nome_tabela,
        rf".*cnpj.*{nome}.*",
        excluir=("cpf", "valido"),
    )
    col_cpf_valido = encontrar_coluna(
        df,
        nome_tabela,
        rf".*cpf.*valido.*{nome}.*",
    )
    col_cnpj_valido = encontrar_coluna(
        df,
        nome_tabela,
        rf".*cnpj.*valido.*{nome}.*",
    )

    return col_cpf, col_cnpj, col_cpfcnpj, col_cpf_valido, col_cnpj_valido


def normalizar_documento(serie: pd.Series) -> pd.Series:
    documento = serie.fillna("").astype(str).str.strip()

    return documento.mask(documento.str.lower().isin(("nan", "none", "null")), "")


def chave_com_prefixo(serie: pd.Series, prefixo: str) -> pd.Series:
    documento = normalizar_documento(serie)

    return prefixo + "_" + documento


def tornar_colunas_unicas(df: pd.DataFrame, sufixo: str) -> pd.DataFrame:
    df = df.copy()
    colunas = []
    vistas = {}

    for coluna in df.columns:
        if coluna == "merge_key":
            colunas.append(coluna)
            continue

        vistas[coluna] = vistas.get(coluna, 0) + 1

        if vistas[coluna] == 1:
            colunas.append(coluna)
        else:
            colunas.append(f"{coluna}_{sufixo}_{vistas[coluna]}")

    df.columns = colunas

    return df


def renomear_colunas_conflitantes(lista_dfs: list[pd.DataFrame]) -> list[pd.DataFrame]:
    contagem_colunas = {}

    for df in lista_dfs:
        for coluna in df.columns:
            if coluna == "merge_key":
                continue

            contagem_colunas[coluna] = contagem_colunas.get(coluna, 0) + 1

    dfs_renomeados = []

    for indice, df in enumerate(lista_dfs, start=1):
        sufixo = f"base{indice}"
        df = tornar_colunas_unicas(df, sufixo)
        renomear = {
            coluna: f"{coluna}_{sufixo}"
            for coluna in df.columns
            if coluna != "merge_key" and contagem_colunas.get(coluna, 0) > 1
        }
        dfs_renomeados.append(df.rename(columns=renomear))

    return dfs_renomeados


def pivotar_registros_repetidos(df: pd.DataFrame, nome_tabela: str):
    df = tornar_colunas_unicas(df, nome_tabela)

    if df.empty:
        return df, 0

    ocorrencias_por_chave = df.groupby("merge_key", dropna=False).size()
    maior_ocorrencia = int(ocorrencias_por_chave.max())

    if maior_ocorrencia <= 1:
        return df, maior_ocorrencia

    colunas_valores = [coluna for coluna in df.columns if coluna != "merge_key"]
    df = df.copy()
    df["_ordem_merge"] = df.groupby("merge_key", dropna=False).cumcount() + 1

    df_pivotado = df.pivot(
        index="merge_key",
        columns="_ordem_merge",
        values=colunas_valores,
    )

    df_pivotado.columns = [
        f"{coluna}_{ordem}"
        for coluna, ordem in df_pivotado.columns.to_flat_index()
    ]

    return df_pivotado.reset_index(), maior_ocorrencia


def ler_csvs(pasta_dados: str) -> dict:
    dataframes = {}
    pasta = caminho_projeto(pasta_dados)

    if not os.path.isdir(pasta):
        raise FileNotFoundError(f"Pasta de entrada nao encontrada: {pasta_dados}")

    for arquivo in os.listdir(pasta):
        if not arquivo.endswith(".csv"):
            continue

        caminho = os.path.join(pasta, arquivo)

        try:
            df = pd.read_csv(
                caminho,
                sep=";",
                encoding="utf-8",
                dtype=str,
            )

            nome_base = arquivo.replace(".csv", "")
            dataframes[nome_base] = df

            print(f"{arquivo} carregado ({len(df)} linhas)")

        except Exception as e:
            print(f"Erro ao ler {arquivo}: {e}")

    return dataframes


def filtrar_validos(df: pd.DataFrame, nome_tabela: str):
    df = df.copy()
    col_cpf, col_cnpj, col_cpfcnpj, col_cpf_valido, col_cnpj_valido = encontrar_colunas_chave(
        df,
        nome_tabela,
    )
    mascaras_validas = []

    if col_cpf and col_cpf_valido:
        mascaras_validas.append((normalizar_documento(df[col_cpf]) != "") & (df[col_cpf_valido] == "S"))

    if col_cnpj and col_cnpj_valido:
        mascaras_validas.append((normalizar_documento(df[col_cnpj]) != "") & (df[col_cnpj_valido] == "S"))

    if col_cpfcnpj and col_cpf_valido:
        mascaras_validas.append((normalizar_documento(df[col_cpfcnpj]) != "") & (df[col_cpf_valido] == "S"))

    if col_cpfcnpj and col_cnpj_valido:
        mascaras_validas.append((normalizar_documento(df[col_cpfcnpj]) != "") & (df[col_cnpj_valido] == "S"))

    if mascaras_validas:
        mascara_valida = reduce(lambda left, right: left | right, mascaras_validas)
        df_validos = df[mascara_valida]
        df_invalidos = df[~mascara_valida]

        return df_validos, df_invalidos

    if col_cpfcnpj:
        return df, pd.DataFrame()

    return pd.DataFrame(), df


def criar_merge_key(df: pd.DataFrame, nome_tabela: str):
    if df.empty:
        return None

    df = df.copy()
    col_cpf, col_cnpj, col_cpfcnpj, col_cpf_valido, col_cnpj_valido = encontrar_colunas_chave(
        df,
        nome_tabela,
    )
    df["merge_key"] = ""

    if col_cpf:
        mascara_cpf = normalizar_documento(df[col_cpf]) != ""

        if col_cpf_valido:
            mascara_cpf = mascara_cpf & (df[col_cpf_valido] == "S")

        df.loc[mascara_cpf, "merge_key"] = chave_com_prefixo(df.loc[mascara_cpf, col_cpf], "CPF")

    if col_cnpj:
        mascara_cnpj = (df["merge_key"] == "") & (normalizar_documento(df[col_cnpj]) != "")

        if col_cnpj_valido:
            mascara_cnpj = mascara_cnpj & (df[col_cnpj_valido] == "S")

        df.loc[mascara_cnpj, "merge_key"] = chave_com_prefixo(df.loc[mascara_cnpj, col_cnpj], "CNPJ")

    if col_cpfcnpj:
        mascara_documento = (df["merge_key"] == "") & (normalizar_documento(df[col_cpfcnpj]) != "")

        if col_cpf_valido:
            mascara_cpfcnpj = mascara_documento & (df[col_cpf_valido] == "S")
            df.loc[mascara_cpfcnpj, "merge_key"] = chave_com_prefixo(
                df.loc[mascara_cpfcnpj, col_cpfcnpj],
                "CPF",
            )

        if col_cnpj_valido:
            mascara_cpfcnpj = mascara_documento & (df["merge_key"] == "") & (df[col_cnpj_valido] == "S")
            df.loc[mascara_cpfcnpj, "merge_key"] = chave_com_prefixo(
                df.loc[mascara_cpfcnpj, col_cpfcnpj],
                "CNPJ",
            )

        if not col_cpf_valido and not col_cnpj_valido:
            df.loc[mascara_documento, "merge_key"] = chave_com_prefixo(
                df.loc[mascara_documento, col_cpfcnpj],
                "DOC",
            )

    if not col_cpf and not col_cnpj and not col_cpfcnpj:
        return None

    df["merge_key"] = df["merge_key"].fillna("").astype(str).str.strip()
    df = df[df["merge_key"] != ""]

    if df.empty:
        return None

    return df


def listar_colunas_detectadas(*colunas):
    colunas_detectadas = [coluna for coluna in colunas if coluna]

    if not colunas_detectadas:
        return "nenhuma"

    return ", ".join(colunas_detectadas)


def imprimir_log_tabela(
    nome_tabela: str,
    total_linhas: int,
    colunas_documento: str,
    colunas_validacao: str,
    qtd_validos: int,
    qtd_invalidos: int,
    qtd_mergeadas: int,
    qtd_chaves_unicas: int,
    qtd_apos_pivot: int,
    maior_ocorrencia: int,
):
    qtd_nao_mergeadas = total_linhas - qtd_mergeadas

    print(f"\n[{nome_tabela}]")
    print(f"  Linhas lidas: {total_linhas}")
    print(f"  Colunas de documento detectadas: {colunas_documento}")
    print(f"  Colunas de validacao detectadas: {colunas_validacao}")
    print(f"  Linhas com documento valido: {qtd_validos}")
    print(f"  Linhas sem documento valido: {qtd_invalidos}")
    print(f"  Linhas enviadas ao merge: {qtd_mergeadas}")
    print(f"  Linhas nao mergeadas: {qtd_nao_mergeadas}")
    print(f"  Chaves unicas no merge: {qtd_chaves_unicas}")
    print(f"  Maior quantidade de linhas por chave: {maior_ocorrencia}")
    print(f"  Linhas apos pivotamento: {qtd_apos_pivot}")


def preparar_bases(dataframes: dict):
    lista_validos = []
    lista_invalidos = []

    for nome, df in dataframes.items():
        col_cpf, col_cnpj, col_cpfcnpj, col_cpf_valido, col_cnpj_valido = encontrar_colunas_chave(df, nome)
        df_validos, df_invalidos = filtrar_validos(df, nome)
        df_preparado = criar_merge_key(df_validos, nome)

        if df_preparado is not None:
            df_pivotado, maior_ocorrencia = pivotar_registros_repetidos(df_preparado, nome)
            lista_validos.append(df_pivotado)
        else:
            df_pivotado = None
            maior_ocorrencia = 0

        if not df_invalidos.empty:
            lista_invalidos.append(df_invalidos)

        qtd_mergeadas = 0 if df_preparado is None else len(df_preparado)
        qtd_chaves_unicas = 0 if df_preparado is None else df_preparado["merge_key"].nunique()
        qtd_apos_pivot = 0 if df_pivotado is None else len(df_pivotado)

        imprimir_log_tabela(
            nome_tabela=nome,
            total_linhas=len(df),
            colunas_documento=listar_colunas_detectadas(col_cpf, col_cnpj, col_cpfcnpj),
            colunas_validacao=listar_colunas_detectadas(col_cpf_valido, col_cnpj_valido),
            qtd_validos=len(df_validos),
            qtd_invalidos=len(df_invalidos),
            qtd_mergeadas=qtd_mergeadas,
            qtd_chaves_unicas=qtd_chaves_unicas,
            qtd_apos_pivot=qtd_apos_pivot,
            maior_ocorrencia=maior_ocorrencia,
        )

    return lista_validos, lista_invalidos


def merge_progressivo(lista_dfs: list):
    if not isinstance(lista_dfs, list):
        raise TypeError(f"Esperado lista, recebido {type(lista_dfs)}")

    if len(lista_dfs) == 0:
        raise ValueError("Nenhum DataFrame valido para merge")

    lista_dfs = renomear_colunas_conflitantes(lista_dfs)

    return reduce(
        lambda left, right: pd.merge(left, right, on="merge_key", how="outer"),
        lista_dfs,
    )


def append_invalidos(df_final: pd.DataFrame, lista_invalidos: list[pd.DataFrame]):
    if len(lista_invalidos) == 0:
        return df_final

    df_invalidos = pd.concat(lista_invalidos, ignore_index=True)

    print(f"Adicionando {len(df_invalidos)} registros invalidos ao final")

    df_final = tornar_colunas_unicas(df_final, "final")
    df_invalidos = tornar_colunas_unicas(df_invalidos, "invalidos")

    return pd.concat([df_final, df_invalidos], ignore_index=True)


def main():
    garantir_pasta(PASTA_GERADOS)
    print("Iniciando leitura dos dados\n")

    dataframes = ler_csvs(PASTA_DADOS)
    lista_validos, lista_invalidos = preparar_bases(dataframes)

    print(f"\nBases validas para merge: {len(lista_validos)}")

    df_final = merge_progressivo(lista_validos)
    df_final = append_invalidos(df_final, lista_invalidos)

    print("\nResultado final:")
    print(df_final.shape)
    print(df_final.head())

    df_final.to_csv(caminho_projeto(ARQUIVO_FINAL), sep=";", encoding="utf-8-sig", index=False)


if __name__ == "__main__":
    with registrar_log_terminal(ARQUIVO_LOG_TXT):
        main()

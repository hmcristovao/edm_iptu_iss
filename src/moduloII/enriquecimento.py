import json
import os
import re
import sys
import unicodedata
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager

import pandas as pd
import recordlinkage

try:
    from tqdm import tqdm
except ImportError:
    class tqdm:
        def __init__(self, iterable, **kwargs):
            self.iterable = iterable

        def __iter__(self):
            return iter(self.iterable)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

        def set_postfix(self, **kwargs):
            return None


CODE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.environ.get("AVALIADOR_WORKDIR", CODE_DIR)
PASTA_GERADOS = "arquivos_gerados"
PASTA_LOGS = "logs"
ARQUIVO_ENTRADA = os.path.join(PASTA_GERADOS, "integracao_base.csv")
ARQUIVO_SAIDA = os.path.join(PASTA_GERADOS, "integracao_enriquecida.csv")
ARQUIVO_LOG_MERGES = os.path.join(PASTA_GERADOS, "integracao_log_merges.csv")
ARQUIVO_LOG_TXT = os.path.join(PASTA_LOGS, "integracao_enriquecimento_log.txt")
ARQUIVO_DECISOES_REVISAO = os.path.join(PASTA_GERADOS, "revisao_merges_decisoes.csv")
ARQUIVO_CONFIGURACAO = "integracao_config.json"
COLUNA_REVISAO = "id_revisao"
COLUNA_SCORE_REVISAO = "score_revisao"


def caminho_projeto(caminho: str) -> str:
    if os.path.isabs(caminho):
        return caminho

    return os.path.join(BASE_DIR, caminho)


def garantir_pasta(caminho: str):
    os.makedirs(caminho_projeto(caminho), exist_ok=True)


def garantir_pasta_arquivo(caminho_arquivo: str):
    pasta = os.path.dirname(caminho_arquivo)
    if pasta:
        garantir_pasta(pasta)


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

    garantir_pasta_arquivo(caminho_log)

    with open(caminho_projeto(caminho_log), "w", encoding="utf-8") as arquivo_log:
        sys.stdout = Tee(stdout_original, arquivo_log)
        sys.stderr = Tee(stderr_original, arquivo_log)

        try:
            yield
        finally:
            sys.stdout = stdout_original
            sys.stderr = stderr_original

# Para ajustar as regras, altere as variáveis threshold_ e o vetor PARAMETROS_COMPARACAO.
# comparacao: "exact" ou "string";
# metodo: usado quando comparacao="string".
# threshold_apoio: permite que o campo autorize merge automatico quando bater.
# apoio_com: exige que outro campo tambem bata;
# use threshold_dependencia no campo dependente.

THRESHOLD_SIMILARIDADE = 85
THRESHOLD_REVISAR = 80

THRESHOLD_APOIO_NOME = 96
THRESHOLD_APOIO_TELEFONE = 98
THRESHOLD_APOIO_EMAIL = 100
THRESHOLD_APOIO_NASCIMENTO = 100
THRESHOLD_APOIO_ENDERECO = 98
THRESHOLD_APOIO_NUMERO = 100
THRESHOLD_APOIO_IDENTIFICADOR_DOCUMENTO = 98

MAX_PARES_POR_VALOR_BLOCO = 1500000
MAX_WORKERS_COMPARACAO = min(6, max(1, (os.cpu_count() or 2) - 1))

_PERFIS_INVALIDOS_WORKER = None
_PERFIS_VALIDOS_WORKER = None


def aplicar_configuracao_externa():
    global THRESHOLD_SIMILARIDADE
    global THRESHOLD_REVISAR
    global THRESHOLD_APOIO_NOME
    global THRESHOLD_APOIO_TELEFONE
    global THRESHOLD_APOIO_EMAIL
    global THRESHOLD_APOIO_NASCIMENTO
    global THRESHOLD_APOIO_ENDERECO
    global THRESHOLD_APOIO_NUMERO
    global THRESHOLD_APOIO_IDENTIFICADOR_DOCUMENTO
    global MAX_PARES_POR_VALOR_BLOCO
    global MAX_WORKERS_COMPARACAO

    try:
        with open(os.path.join(CODE_DIR, ARQUIVO_CONFIGURACAO), "r", encoding="utf-8") as arquivo:
            config = json.load(arquivo)
    except FileNotFoundError:
        return
    except (json.JSONDecodeError, OSError) as erro:
        print(f"Configuracao externa ignorada: {erro}")
        return

    THRESHOLD_SIMILARIDADE = int(config.get("threshold_similaridade", THRESHOLD_SIMILARIDADE))
    THRESHOLD_REVISAR = int(config.get("threshold_revisar", THRESHOLD_REVISAR))
    THRESHOLD_APOIO_NOME = int(config.get("threshold_apoio_nome", THRESHOLD_APOIO_NOME))
    THRESHOLD_APOIO_TELEFONE = int(config.get("threshold_apoio_telefone", THRESHOLD_APOIO_TELEFONE))
    THRESHOLD_APOIO_EMAIL = int(config.get("threshold_apoio_email", THRESHOLD_APOIO_EMAIL))
    THRESHOLD_APOIO_NASCIMENTO = int(config.get("threshold_apoio_nascimento", THRESHOLD_APOIO_NASCIMENTO))
    THRESHOLD_APOIO_ENDERECO = int(config.get("threshold_apoio_endereco", THRESHOLD_APOIO_ENDERECO))
    THRESHOLD_APOIO_NUMERO = int(config.get("threshold_apoio_numero", THRESHOLD_APOIO_NUMERO))
    THRESHOLD_APOIO_IDENTIFICADOR_DOCUMENTO = int(
        config.get("threshold_apoio_identificador_documento", THRESHOLD_APOIO_IDENTIFICADOR_DOCUMENTO)
    )
    MAX_PARES_POR_VALOR_BLOCO = int(config.get("max_pares_por_valor_bloco", MAX_PARES_POR_VALOR_BLOCO))
    MAX_WORKERS_COMPARACAO = max(1, int(config.get("max_workers_comparacao", MAX_WORKERS_COMPARACAO)))

    print(f"Configuracao carregada de {ARQUIVO_CONFIGURACAO}")


aplicar_configuracao_externa()

PARAMETROS_COMPARACAO = [
    {
        "nome": "nome",
        "padrao_colunas": r"^(nome|parceiro|cliente|individuo|responsavel|responsavelPelaFamilia|parceiroNegocios)",
        "tipo": "texto",
        "peso": 3.5,
        "comparacao": "string",
        "metodo": "jarowinkler",
        "threshold_apoio": THRESHOLD_APOIO_NOME,
    },
    {
        "nome": "data_nascimento",
        "padrao_colunas": r"(dataNascimento)",
        "tipo": "data",
        "peso": 2.5,
        "comparacao": "exact",
        "threshold_apoio": THRESHOLD_APOIO_NASCIMENTO,
    },
    {
        "nome": "telefone",
        "padrao_colunas": r"(telefone|telefones|celular|contato)",
        "tipo": "telefone",
        "peso": 2.0,
        "comparacao": "string",
        "metodo": "levenshtein",
        "threshold_apoio": THRESHOLD_APOIO_TELEFONE,
    },
    {
        "nome": "email",
        "padrao_colunas": r"(email|e-mail)",
        "tipo": "email",
        "peso": 2.0,
        "comparacao": "exact",
        "threshold_apoio": THRESHOLD_APOIO_EMAIL,
    },
    {
        "nome": "cep",
        "padrao_colunas": r"^cep",
        "tipo": "cep",
        "peso": 1.8,
        "comparacao": "exact",
    },
    {
        "nome": "endereco",
        "padrao_colunas": r"^(endereco|logradouro|rua|tipoLogradouro|complemento)",
        "tipo": "texto",
        "peso": 1.7,
        "comparacao": "string",
        "metodo": "jarowinkler",
        "threshold_apoio": THRESHOLD_APOIO_ENDERECO,
        "apoio_com": ["numero"],
    },
    {
        "nome": "numero",
        "padrao_colunas": r"^(numero|enderecoNumero)",
        "tipo": "numero",
        "peso": 1.2,
        "comparacao": "exact",
        "threshold_dependencia": THRESHOLD_APOIO_NUMERO,
    },
    {
        "nome": "bairro",
        "padrao_colunas": r"^bairro",
        "tipo": "texto_curto",
        "peso": 1.2,
        "comparacao": "string",
        "metodo": "jarowinkler",
    },
    {
        "nome": "cidade",
        "padrao_colunas": r"^(cidade|municipio|localidade|descricaoLocalidade|uf|pais|estado(?!Civil))",
        "tipo": "texto_curto",
        "peso": 1.0,
        "comparacao": "string",
        "metodo": "jarowinkler",
    },
    {
        "nome": "identificador_documento",
        "padrao_colunas": r"^(rg(?!Data|Orgao|Estado)|cns|nis|pis|tituloEleitor|ctpsNumero|ctpsSerie)",
        "tipo": "codigo",
        "peso": 3.0,
        "comparacao": "string",
        "metodo": "levenshtein",
        "threshold_apoio": THRESHOLD_APOIO_IDENTIFICADOR_DOCUMENTO,
    },
    {
        "nome": "cadastro_servico",
        "padrao_colunas": r"^(inscricao|instalacao|medidor|ligacao|idImovel|codFamiliar|prontuario)",
        "tipo": "codigo",
        "peso": 1.5,
        "comparacao": "string",
        "metodo": "levenshtein",
    },
]


def ler_final(caminho: str = ARQUIVO_ENTRADA) -> pd.DataFrame:
    return pd.read_csv(
        caminho_projeto(caminho),
        sep=";",
        encoding="utf-8-sig",
        dtype=str,
    )


def separar_validos_invalidos(df: pd.DataFrame):
    if "merge_key" not in df.columns:
        raise ValueError("Coluna merge_key nao encontrada no arquivo final.csv")

    merge_key = df["merge_key"].fillna("").astype(str).str.strip()
    mascara_validos = merge_key != ""

    df_validos = df[mascara_validos].copy()
    df_invalidos = df[~mascara_validos].copy()

    return df_validos, df_invalidos


def normalizar_texto(valor) -> str:
    if pd.isna(valor):
        return ""

    texto = str(valor).strip().lower()

    if texto in {"", "nan", "none", "null"}:
        return ""

    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    texto = re.sub(r"[^a-z0-9@._ -]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


def apenas_digitos(texto) -> str:
    return re.sub(r"\D", "", normalizar_texto(texto))


def normalizar_data(valor) -> str:
    texto = apenas_digitos(valor)

    if len(texto) >= 8:
        texto = texto[:8]

        if texto[:4] in {str(ano) for ano in range(1900, 2101)}:
            return texto

        return f"{texto[4:8]}{texto[2:4]}{texto[0:2]}"

    return texto


def normalizar_email(valor) -> str:
    texto = normalizar_texto(valor)
    emails = re.findall(r"[\w.+-]+@[\w.-]+\.\w+", texto)

    return " ".join(sorted(set(emails)))


def normalizar_telefone(valor) -> str:
    digitos = apenas_digitos(valor)

    if len(digitos) >= 8:
        return digitos[-9:]

    return digitos


def normalizar_cep(valor) -> str:
    digitos = apenas_digitos(valor)

    if len(digitos) >= 8:
        return digitos[:8]

    return digitos


def normalizar_codigo(valor) -> str:
    texto = normalizar_texto(valor)

    return re.sub(r"[^a-z0-9]", "", texto)


def selecionar_colunas(df: pd.DataFrame, parametro: dict) -> list[str]:
    regex = re.compile(parametro["padrao_colunas"], re.IGNORECASE)
    termos_excluidos = [
        "merge_key",
        "valido",
        "unnamed",
        "index",
        "indice",
    ]

    return [
        coluna
        for coluna in df.columns
        if regex.search(coluna) and not any(termo in coluna.lower() for termo in termos_excluidos)
    ]


def concatenar_linha(linha: pd.Series, tipo: str) -> str:
    valores = []
    vistos = set()

    for valor in linha:
        if tipo == "telefone":
            texto = normalizar_telefone(valor)
        elif tipo == "data":
            texto = normalizar_data(valor)
        elif tipo == "email":
            texto = normalizar_email(valor)
        elif tipo == "cep":
            texto = normalizar_cep(valor)
        elif tipo == "numero":
            texto = apenas_digitos(valor)
        elif tipo == "codigo":
            texto = normalizar_codigo(valor)
        else:
            texto = normalizar_texto(valor)

        if texto and texto not in vistos:
            vistos.add(texto)
            valores.append(texto)

    return " ".join(valores)


def primeiro_token(texto) -> str:
    partes = str(texto or "").split()

    return partes[0] if partes else ""


def ultimo_token(texto) -> str:
    partes = str(texto or "").split()

    return partes[-1] if partes else ""


def tokens_nome(texto) -> list[str]:
    ignorar = {
        "da",
        "de",
        "do",
        "das",
        "dos",
        "e",
    }
    tokens = []

    for token in str(texto or "").split():
        if len(token) < 3 or token in ignorar:
            continue

        tokens.append(token)

    return sorted(set(tokens))


def criar_perfis(df: pd.DataFrame):
    perfis = pd.DataFrame(index=df.index)
    colunas_por_parametro = {}

    for parametro in PARAMETROS_COMPARACAO:
        nome = parametro["nome"]
        colunas = selecionar_colunas(df, parametro)
        colunas_por_parametro[nome] = colunas

        if colunas:
            perfis[nome] = df[colunas].apply(concatenar_linha, axis=1, tipo=parametro["tipo"])
        else:
            perfis[nome] = ""

    perfis = perfis.fillna("")

    perfis["bloco_telefone"] = perfis["telefone"].apply(
        lambda x: apenas_digitos(x)[-8:] if len(apenas_digitos(x)) >= 8 else ""
    )
    perfis["bloco_email"] = perfis["email"].apply(lambda x: primeiro_token(x.split("@")[0]) if "@" in x else "")
    perfis["bloco_cep"] = perfis["cep"].apply(lambda x: x[:8] if len(x) >= 8 else "")
    perfis["bloco_identificador_documento"] = perfis["identificador_documento"].apply(
        lambda x: x[:20] if len(x) >= 5 else ""
    )
    perfis["bloco_cadastro_servico"] = perfis["cadastro_servico"].apply(
        lambda x: x[:20] if len(x) >= 4 else ""
    )
    perfis["bloco_nascimento"] = perfis["data_nascimento"].apply(lambda x: x[:8] if len(x) >= 8 else "")
    perfis["bloco_nome_nascimento"] = perfis.apply(
        lambda row: f"{row['nome'][:4]}|{row['data_nascimento'][:8]}"
        if len(row["nome"]) >= 4 and len(row["data_nascimento"]) >= 8
        else "",
        axis=1,
    )
    perfis["bloco_bairro_nome"] = perfis.apply(
        lambda row: f"{row['bairro'][:5]}|{row['nome'][:4]}"
        if len(row["bairro"]) >= 5 and len(row["nome"]) >= 4
        else "",
        axis=1,
    )

    return perfis, colunas_por_parametro


def adicionar_bloco(indexer, perfis_invalidos, perfis_validos, coluna: str):
    if perfis_invalidos[coluna].eq("").all() or perfis_validos[coluna].eq("").all():
        return False

    indexer.block(left_on=coluna, right_on=coluna)

    return True


def gerar_pares_por_token_nome(
    perfis_invalidos: pd.DataFrame,
    perfis_validos: pd.DataFrame,
) -> tuple[pd.MultiIndex, int]:
    indices_invalidos_por_token = {}
    indices_validos_por_token = {}

    for idx, nome in perfis_invalidos["nome"].items():
        for token in tokens_nome(nome):
            indices_invalidos_por_token.setdefault(token, []).append(idx)

    for idx, nome in perfis_validos["nome"].items():
        for token in tokens_nome(nome):
            indices_validos_por_token.setdefault(token, []).append(idx)

    pares = []
    tokens_ignorados = 0

    for token in sorted(set(indices_invalidos_por_token) & set(indices_validos_por_token)):
        indices_invalidos = indices_invalidos_por_token[token]
        indices_validos = indices_validos_por_token[token]
        total_pares_token = len(indices_invalidos) * len(indices_validos)

        if total_pares_token > MAX_PARES_POR_VALOR_BLOCO:
            tokens_ignorados += 1
            continue

        pares.extend(
            (idx_invalido, idx_valido)
            for idx_invalido in indices_invalidos
            for idx_valido in indices_validos
        )

    if not pares:
        return pd.MultiIndex.from_tuples([]), tokens_ignorados

    return pd.MultiIndex.from_tuples(pares).drop_duplicates(), tokens_ignorados


def gerar_pares_candidatos(perfis_invalidos: pd.DataFrame, perfis_validos: pd.DataFrame):
    indexer = recordlinkage.Index()
    blocos_usados = []
    colunas_bloco = [
        "bloco_telefone",
        "bloco_email",
        "bloco_identificador_documento",
        "bloco_cadastro_servico",
        "bloco_nome_nascimento",
        "bloco_cep",
        "bloco_bairro_nome",
    ]

    for coluna in colunas_bloco:
        if adicionar_bloco(indexer, perfis_invalidos, perfis_validos, coluna):
            blocos_usados.append(coluna)

    if blocos_usados:
        perfis_invalidos_index = perfis_invalidos.copy()
        perfis_validos_index = perfis_validos.copy()
        perfis_invalidos_index[colunas_bloco] = perfis_invalidos_index[colunas_bloco].replace("", pd.NA)
        perfis_validos_index[colunas_bloco] = perfis_validos_index[colunas_bloco].replace("", pd.NA)
        perfis_invalidos_index, perfis_validos_index, removidos_por_bloco = limitar_blocos_frequentes(
            perfis_invalidos_index,
            perfis_validos_index,
            blocos_usados,
        )

        blocos_limitados = {
            coluna: quantidade
            for coluna, quantidade in removidos_por_bloco.items()
            if quantidade > 0
        }

        if blocos_limitados:
            print("  Blocos limitados por excesso de combinacoes:")

            for coluna, quantidade in blocos_limitados.items():
                print(f"    {coluna}: {quantidade} valores ignorados")

        candidate_links = indexer.index(perfis_invalidos_index, perfis_validos_index)
    else:
        candidate_links = pd.MultiIndex.from_tuples([])

    pares_nome, tokens_nome_ignorados = gerar_pares_por_token_nome(perfis_invalidos, perfis_validos)

    if len(pares_nome) > 0:
        blocos_usados.append("bloco_nome_qualquer_parte")
        if len(candidate_links) == 0:
            candidate_links = pares_nome
        else:
            candidate_links = candidate_links.union(pares_nome)

    if tokens_nome_ignorados > 0:
        print(f"  Tokens de nome ignorados por excesso de combinacoes: {tokens_nome_ignorados}")

    return candidate_links.drop_duplicates(), blocos_usados


def iterar_lotes_pares(candidate_links: pd.MultiIndex, tamanho_lote: int):
    for inicio in range(0, len(candidate_links), tamanho_lote):
        yield candidate_links[inicio : inicio + tamanho_lote]


def limitar_blocos_frequentes(
    perfis_invalidos: pd.DataFrame,
    perfis_validos: pd.DataFrame,
    colunas_bloco: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    perfis_invalidos = perfis_invalidos.copy()
    perfis_validos = perfis_validos.copy()
    removidos_por_bloco = {}

    for coluna in colunas_bloco:
        contagem_invalidos = perfis_invalidos[coluna].value_counts(dropna=True)
        contagem_validos = perfis_validos[coluna].value_counts(dropna=True)
        valores_comuns = contagem_invalidos.index.intersection(contagem_validos.index)
        valores_excessivos = [
            valor
            for valor in valores_comuns
            if contagem_invalidos[valor] * contagem_validos[valor] > MAX_PARES_POR_VALOR_BLOCO
        ]

        if valores_excessivos:
            perfis_invalidos.loc[perfis_invalidos[coluna].isin(valores_excessivos), coluna] = pd.NA
            perfis_validos.loc[perfis_validos[coluna].isin(valores_excessivos), coluna] = pd.NA

        removidos_por_bloco[coluna] = len(valores_excessivos)

    return perfis_invalidos, perfis_validos, removidos_por_bloco


def calcular_score_total(
    features: pd.DataFrame,
    perfis_invalidos: pd.DataFrame,
    perfis_validos: pd.DataFrame,
) -> pd.DataFrame:
    score_ponderado = pd.Series(0.0, index=features.index)
    peso_disponivel = pd.Series(0.0, index=features.index)

    for parametro in PARAMETROS_COMPARACAO:
        nome = parametro["nome"]
        score_col = f"score_{nome}"

        if score_col not in features.columns:
            continue

        idx_invalidos = features.index.get_level_values(0)
        idx_validos = features.index.get_level_values(1)
        tem_valor_invalido = perfis_invalidos.loc[idx_invalidos, nome].notna().to_numpy()
        tem_valor_valido = perfis_validos.loc[idx_validos, nome].notna().to_numpy()
        tem_valor = tem_valor_invalido & tem_valor_valido
        peso = parametro["peso"]

        score_ponderado += features[score_col].fillna(0) * peso * tem_valor
        peso_disponivel += peso * tem_valor

    features["peso_disponivel"] = peso_disponivel
    features["score_total"] = (score_ponderado / peso_disponivel.mask(peso_disponivel == 0)).fillna(0) * 100

    return features


def score_coluna(nome: str) -> str:
    return f"score_{nome}"


def obter_parametro(nome: str) -> dict | None:
    for parametro in PARAMETROS_COMPARACAO:
        if parametro["nome"] == nome:
            return parametro

    return None


def configurar_comparador() -> recordlinkage.Compare:
    compare = recordlinkage.Compare()

    for parametro in PARAMETROS_COMPARACAO:
        nome = parametro["nome"]
        label = score_coluna(nome)
        comparacao = parametro.get("comparacao", "string")

        if comparacao == "exact":
            compare.exact(nome, nome, label=label, missing_value=0)
        elif comparacao == "string":
            compare.string(
                nome,
                nome,
                method=parametro.get("metodo", "jarowinkler"),
                label=label,
                missing_value=0,
            )
        else:
            raise ValueError(f"Comparacao invalida para {nome}: {comparacao}")

    return compare


def calcular_regra_apoio(features: pd.DataFrame, parametro: dict) -> pd.Series | None:
    threshold = parametro.get("threshold_apoio")

    if threshold is None:
        return None

    score_col = score_coluna(parametro["nome"])

    if score_col not in features.columns:
        return None

    regra = features[score_col] >= threshold / 100

    for nome_dependencia in parametro.get("apoio_com", []):
        parametro_dependencia = obter_parametro(nome_dependencia)
        threshold_dependencia = (
            parametro_dependencia.get("threshold_dependencia", parametro_dependencia.get("threshold_apoio"))
            if parametro_dependencia
            else None
        )

        if threshold_dependencia is None:
            raise ValueError(
                f"Parametro {parametro['nome']} depende de {nome_dependencia}, "
                "mas a dependencia nao tem threshold_apoio"
            )

        score_dependencia = score_coluna(nome_dependencia)

        if score_dependencia not in features.columns:
            regra = regra & False
        else:
            regra = regra & (features[score_dependencia] >= threshold_dependencia / 100)

    return regra


def marcar_regras_match_automatico(features: pd.DataFrame) -> pd.DataFrame:
    features = features.copy()
    score_total_ok = features["score_total"] >= THRESHOLD_SIMILARIDADE
    apoio_ok = pd.Series(False, index=features.index)

    features["regra_score_total_ok"] = score_total_ok

    for parametro in PARAMETROS_COMPARACAO:
        regra = calcular_regra_apoio(features, parametro)

        if regra is None:
            continue

        features[f"regra_{parametro['nome']}_ok"] = regra
        apoio_ok = apoio_ok | regra

    match_automatico = score_total_ok & apoio_ok
    features["regra_apoio_ok"] = apoio_ok
    features["match_automatico"] = match_automatico

    return features


def comparar_lote_pares(
    pares: pd.MultiIndex,
    perfis_invalidos_comparacao: pd.DataFrame,
    perfis_validos_comparacao: pd.DataFrame,
) -> pd.DataFrame:
    compare = configurar_comparador()
    features = compare.compute(pares, perfis_invalidos_comparacao, perfis_validos_comparacao)
    features = calcular_score_total(
        features,
        perfis_invalidos_comparacao,
        perfis_validos_comparacao,
    )
    return marcar_regras_match_automatico(features)


def inicializar_worker_comparacao(perfis_invalidos_comparacao: pd.DataFrame, perfis_validos_comparacao: pd.DataFrame):
    global _PERFIS_INVALIDOS_WORKER
    global _PERFIS_VALIDOS_WORKER

    _PERFIS_INVALIDOS_WORKER = perfis_invalidos_comparacao
    _PERFIS_VALIDOS_WORKER = perfis_validos_comparacao


def comparar_lote_pares_worker(pares: pd.MultiIndex) -> pd.DataFrame:
    if _PERFIS_INVALIDOS_WORKER is None or _PERFIS_VALIDOS_WORKER is None:
        raise RuntimeError("Worker de comparacao nao inicializado.")

    return comparar_lote_pares(pares, _PERFIS_INVALIDOS_WORKER, _PERFIS_VALIDOS_WORKER)


def definir_workers_comparacao(total_lotes: int) -> int:
    if total_lotes <= 1:
        return 1

    return max(1, min(total_lotes, MAX_WORKERS_COMPARACAO))


def limpar_acumuladores_comparacao(
    matches_list: list[pd.DataFrame],
    linhas_revisao: set,
    melhor_score_por_invalido: dict,
    pares_revisao: dict,
) -> None:
    matches_list.clear()
    linhas_revisao.clear()
    melhor_score_por_invalido.clear()
    pares_revisao.clear()


def comparar_lotes_em_modo_sequencial(
    lotes_pares: list[pd.MultiIndex],
    total_lotes: int,
    perfis_invalidos_comparacao: pd.DataFrame,
    perfis_validos_comparacao: pd.DataFrame,
    matches_list: list[pd.DataFrame],
    linhas_revisao: set,
    melhor_score_por_invalido: dict,
    pares_revisao: dict,
) -> None:
    for chunk in tqdm(
        lotes_pares,
        total=total_lotes,
        desc="Calculando similaridade",
        unit="lote",
        file=sys.stdout,
        dynamic_ncols=False,
        mininterval=1,
    ):
        features_chunk = comparar_lote_pares(
            chunk,
            perfis_invalidos_comparacao,
            perfis_validos_comparacao,
        )
        acumular_resultado_comparacao(
            features_chunk,
            matches_list,
            linhas_revisao,
            melhor_score_por_invalido,
            pares_revisao,
        )


def acumular_resultado_comparacao(
    features_chunk: pd.DataFrame,
    matches_list: list[pd.DataFrame],
    linhas_revisao: set,
    melhor_score_por_invalido: dict,
    pares_revisao: dict,
) -> None:
    indices_revisao = features_chunk.index[
        features_chunk["score_total"] >= THRESHOLD_REVISAR
    ].get_level_values(0)
    linhas_revisao.update(indices_revisao)

    candidatos_revisao = features_chunk[
        (features_chunk["score_total"] >= THRESHOLD_REVISAR)
        & (~features_chunk["match_automatico"])
    ]

    for (idx_invalido, idx_valido), row in candidatos_revisao.iterrows():
        score = row["score_total"]
        par_atual = pares_revisao.get(idx_invalido)

        if par_atual is None or score > par_atual["score_total"]:
            pares_revisao[idx_invalido] = {
                "idx_valido": idx_valido,
                "score_total": score,
            }

    melhores_do_lote = features_chunk["score_total"].groupby(level=0).max()

    for idx_invalido, score in melhores_do_lote.items():
        score_atual = melhor_score_por_invalido.get(idx_invalido, 0)

        if score > score_atual:
            melhor_score_por_invalido[idx_invalido] = score

    matches_chunk = features_chunk[features_chunk["match_automatico"]].copy()

    if not matches_chunk.empty:
        matches_list.append(matches_chunk)


def preparar_perfis_para_comparacao(perfis: pd.DataFrame) -> pd.DataFrame:
    perfis_comparacao = perfis.copy()
    colunas_comparacao = [parametro["nome"] for parametro in PARAMETROS_COMPARACAO]
    perfis_comparacao[colunas_comparacao] = perfis_comparacao[colunas_comparacao].replace("", pd.NA)

    return perfis_comparacao


def preencher_linha(destino: pd.Series, origem: pd.Series) -> pd.Series:
    resultado = destino.copy()
    origem_util = origem.reindex(resultado.index)
    vazios = resultado.isna() | resultado.astype(str).str.strip().str.lower().isin(["", "nan", "none", "null"])

    resultado.loc[vazios] = origem_util.loc[vazios]

    return resultado


def resumir_colunas(colunas: list[str]) -> str:
    if not colunas:
        return "-"

    return ", ".join(colunas)


def combinar_colunas_unicas(*listas_colunas: list[str]) -> list[str]:
    colunas_unicas = []
    vistas = set()

    for colunas in listas_colunas:
        for coluna in colunas:
            if coluna in vistas:
                continue

            vistas.add(coluna)
            colunas_unicas.append(coluna)

    return colunas_unicas


def imprimir_colunas_detectadas(colunas_validos: dict, colunas_invalidos: dict):
    print("\nColunas usadas na comparacao:")

    for parametro in PARAMETROS_COMPARACAO:
        nome = parametro["nome"]
        colunas = combinar_colunas_unicas(
            colunas_validos.get(nome, []),
            colunas_invalidos.get(nome, []),
        )

        if not colunas:
            continue

        print(f"  {nome}: {len(colunas)} colunas [{resumir_colunas(colunas)}]")


def imprimir_amostras_matches(matches: pd.DataFrame, perfis_invalidos: pd.DataFrame, perfis_validos: pd.DataFrame):
    if matches.empty:
        return

    print("\nMelhores matches:")

    for (idx_invalido, idx_valido), row in matches.head(10).iterrows():
        print(
            "  "
            f"invalido={idx_invalido} valido={idx_valido} "
            f"score={row['score_total']:.1f}% "
            f"nome=({perfis_invalidos.at[idx_invalido, 'nome']} <> {perfis_validos.at[idx_valido, 'nome']})"
        )


def listar_apoios_merge(row: pd.Series) -> str:
    apoios = []

    for parametro in PARAMETROS_COMPARACAO:
        if parametro.get("threshold_apoio") is None:
            continue

        nome = parametro["nome"]

        if row.get(f"regra_{nome}_ok", False):
            dependencias = parametro.get("apoio_com", [])
            sufixo = f"+{'+'.join(dependencias)}" if dependencias else ""
            apoios.append(f"{nome}{sufixo}")

    return ", ".join(apoios)


def montar_log_merge(
    idx_invalido,
    idx_valido,
    row: pd.Series,
    df_validos: pd.DataFrame,
    perfis_invalidos: pd.DataFrame,
    perfis_validos: pd.DataFrame,
) -> dict:
    log = {
        "idx_invalido": idx_invalido,
        "idx_valido": idx_valido,
        "merge_key_valido": df_validos.at[idx_valido, "merge_key"],
        "score_total": row["score_total"],
        "peso_disponivel": row["peso_disponivel"],
        "apoios": listar_apoios_merge(row),
    }

    for parametro in PARAMETROS_COMPARACAO:
        nome = parametro["nome"]
        score_col = f"score_{nome}"

        if score_col in row.index:
            log[score_col] = row[score_col]

        log[f"{nome}_invalido"] = perfis_invalidos.at[idx_invalido, nome]
        log[f"{nome}_valido"] = perfis_validos.at[idx_valido, nome]

    return log


def montar_resumo_thresholds() -> dict:
    resumo = {
        "threshold_similaridade": THRESHOLD_SIMILARIDADE,
        "threshold_revisar": THRESHOLD_REVISAR,
    }

    for parametro in PARAMETROS_COMPARACAO:
        threshold = parametro.get("threshold_apoio")

        if threshold is not None:
            resumo[f"threshold_apoio_{parametro['nome']}"] = threshold

        threshold_dependencia = parametro.get("threshold_dependencia")

        if threshold_dependencia is not None:
            resumo[f"threshold_dependencia_{parametro['nome']}"] = threshold_dependencia

    return resumo


def marcar_pares_revisao(
    df_resultado: pd.DataFrame,
    df_invalidos_restantes: pd.DataFrame,
    pares_revisao: dict,
) -> tuple[pd.DataFrame, pd.DataFrame, int, int]:
    df_resultado = df_resultado.copy()
    df_invalidos_restantes = df_invalidos_restantes.copy()
    df_resultado[COLUNA_REVISAO] = ""
    df_invalidos_restantes[COLUNA_REVISAO] = ""
    df_resultado[COLUNA_SCORE_REVISAO] = ""
    df_invalidos_restantes[COLUNA_SCORE_REVISAO] = ""

    pares_por_valido = {}

    for idx_invalido, par in pares_revisao.items():
        if idx_invalido not in df_invalidos_restantes.index:
            continue

        idx_valido = par["idx_valido"]

        if idx_valido not in df_resultado.index:
            continue

        pares_por_valido.setdefault(idx_valido, []).append(idx_invalido)

    for numero, idx_valido in enumerate(sorted(pares_por_valido), start=1):
        indices_invalidos = sorted(pares_por_valido[idx_valido])
        id_revisao = f"REV{numero:06d}"
        df_resultado.at[idx_valido, COLUNA_REVISAO] = id_revisao
        df_resultado.at[idx_valido, COLUNA_SCORE_REVISAO] = max(
            pares_revisao[idx_invalido]["score_total"]
            for idx_invalido in indices_invalidos
        )
        df_invalidos_restantes.loc[indices_invalidos, COLUNA_REVISAO] = id_revisao

        for idx_invalido in indices_invalidos:
            df_invalidos_restantes.at[idx_invalido, COLUNA_SCORE_REVISAO] = pares_revisao[idx_invalido]["score_total"]

    qtd_linhas_revisao_marcadas = sum(len(indices) for indices in pares_por_valido.values())

    return df_resultado, df_invalidos_restantes, len(pares_por_valido), qtd_linhas_revisao_marcadas


def comparar_e_juntar(df_validos: pd.DataFrame, df_invalidos: pd.DataFrame):
    perfis_validos, colunas_validos = criar_perfis(df_validos)
    perfis_invalidos, colunas_invalidos = criar_perfis(df_invalidos)
    perfis_validos_comparacao = preparar_perfis_para_comparacao(perfis_validos)
    perfis_invalidos_comparacao = preparar_perfis_para_comparacao(perfis_invalidos)

    imprimir_colunas_detectadas(colunas_validos, colunas_invalidos)

    print("\nGerando pares candidatos com blocagem ampliada...")
    candidate_links, blocos_usados = gerar_pares_candidatos(perfis_invalidos, perfis_validos)

    print(f"  Blocos usados: {', '.join(blocos_usados) or 'nenhum'}")
    print(f"  Total de pares candidatos: {len(candidate_links)}")

    if len(candidate_links) == 0:
        print("Nenhum par candidato encontrado.")
        df_final = pd.concat([df_validos, df_invalidos], ignore_index=True)
        df_final[COLUNA_REVISAO] = ""
        df_final[COLUNA_SCORE_REVISAO] = ""

        return df_final, pd.DataFrame(), pd.DataFrame()

    print("\nComparando os pares...")

    tamanho_lote = 50000
    total_lotes = (len(candidate_links) + tamanho_lote - 1) // tamanho_lote
    lotes_pares = list(iterar_lotes_pares(candidate_links, tamanho_lote))
    max_workers = definir_workers_comparacao(total_lotes)
    matches_list = []
    linhas_revisao = set()
    melhor_score_por_invalido = {}
    pares_revisao = {}

    if max_workers > 1:
        print(f"  Usando ProcessPoolExecutor com {max_workers} processo(s).")
        try:
            with ProcessPoolExecutor(
                max_workers=max_workers,
                initializer=inicializar_worker_comparacao,
                initargs=(perfis_invalidos_comparacao, perfis_validos_comparacao),
            ) as executor:
                barra_features = tqdm(
                    executor.map(comparar_lote_pares_worker, lotes_pares),
                    total=total_lotes,
                    desc="Calculando similaridade",
                    unit="lote",
                    file=sys.stdout,
                    dynamic_ncols=False,
                    mininterval=1,
                )

                for features_chunk in barra_features:
                    acumular_resultado_comparacao(
                        features_chunk,
                        matches_list,
                        linhas_revisao,
                        melhor_score_por_invalido,
                        pares_revisao,
                    )
        except Exception as erro:
            print(
                "  ProcessPoolExecutor falhou "
                f"({type(erro).__name__}: {erro}). Reprocessando em modo sequencial."
            )
            limpar_acumuladores_comparacao(
                matches_list,
                linhas_revisao,
                melhor_score_por_invalido,
                pares_revisao,
            )
            comparar_lotes_em_modo_sequencial(
                lotes_pares,
                total_lotes,
                perfis_invalidos_comparacao,
                perfis_validos_comparacao,
                matches_list,
                linhas_revisao,
                melhor_score_por_invalido,
                pares_revisao,
            )
    else:
        comparar_lotes_em_modo_sequencial(
            lotes_pares,
            total_lotes,
            perfis_invalidos_comparacao,
            perfis_validos_comparacao,
            matches_list,
            linhas_revisao,
            melhor_score_por_invalido,
            pares_revisao,
        )

    if matches_list:
        matches = pd.concat(matches_list).sort_values(by="score_total", ascending=False)
    else:
        matches = pd.DataFrame()

    qtd_linhas_com_match_automatico = (
        matches.index.get_level_values(0).nunique()
        if not matches.empty
        else 0
    )
    qtd_linhas_entre_thresholds = sum(
        1
        for score in melhor_score_por_invalido.values()
        if THRESHOLD_REVISAR <= score < THRESHOLD_SIMILARIDADE
    )
    qtd_linhas_avaliadas = len(melhor_score_por_invalido)
    qtd_linhas_revisao = len(linhas_revisao)

    print(f"\nLinhas invalidas avaliadas: {qtd_linhas_avaliadas}")
    print(f"Linhas invalidas acima de {THRESHOLD_REVISAR}% para revisao: {qtd_linhas_revisao}")
    print(
        f"Linhas invalidas entre {THRESHOLD_REVISAR}% e {THRESHOLD_SIMILARIDADE}%: "
        f"{qtd_linhas_entre_thresholds}"
    )
    print(f"Linhas invalidas com match automatico acima de {THRESHOLD_SIMILARIDADE}%: {qtd_linhas_com_match_automatico}")
    imprimir_amostras_matches(matches, perfis_invalidos, perfis_validos)

    df_resultado = df_validos.copy()
    invalidos_juntados = set()
    validos_com_merge = set()
    logs_merge = []

    print("\nAplicando merges automaticos...")

    merges_ignorados = 0

    with tqdm(
        matches.iterrows(),
        total=len(matches),
        desc="Juntando registros",
        unit="match",
        file=sys.stdout,
        dynamic_ncols=False,
        mininterval=1,
    ) as barra_juncao:
        for (idx_invalido, idx_valido), row in barra_juncao:
            if idx_invalido in invalidos_juntados:
                merges_ignorados += 1
                barra_juncao.set_postfix(
                    juntados=len(invalidos_juntados),
                    validos=len(validos_com_merge),
                    ignorados=merges_ignorados,
                    restantes=len(df_invalidos) - len(invalidos_juntados),
                )
                continue

            linha_invalida = df_invalidos.loc[idx_invalido]
            df_resultado.loc[idx_valido] = preencher_linha(df_resultado.loc[idx_valido], linha_invalida)

            invalidos_juntados.add(idx_invalido)
            validos_com_merge.add(idx_valido)

            logs_merge.append(
                montar_log_merge(
                    idx_invalido,
                    idx_valido,
                    row,
                    df_validos,
                    perfis_invalidos,
                    perfis_validos,
                )
            )
            barra_juncao.set_postfix(
                juntados=len(invalidos_juntados),
                validos=len(validos_com_merge),
                ignorados=merges_ignorados,
                restantes=len(df_invalidos) - len(invalidos_juntados),
            )

    df_invalidos_restantes = df_invalidos.drop(index=list(invalidos_juntados))
    (
        df_resultado,
        df_invalidos_restantes,
        qtd_grupos_revisao,
        qtd_linhas_revisao_marcadas,
    ) = marcar_pares_revisao(
        df_resultado,
        df_invalidos_restantes,
        pares_revisao,
    )
    df_final = pd.concat([df_resultado, df_invalidos_restantes], ignore_index=True)
    df_log_merges = pd.DataFrame(logs_merge)

    df_resumo = pd.DataFrame(
        [
            {
                **montar_resumo_thresholds(),
                "validos": len(df_validos),
                "invalidos": len(df_invalidos),
                "linhas_avaliadas": qtd_linhas_avaliadas,
                "linhas_revisao": qtd_linhas_revisao,
                "linhas_entre_thresholds": qtd_linhas_entre_thresholds,
                "grupos_revisao": qtd_grupos_revisao,
                "linhas_revisao_marcadas": qtd_linhas_revisao_marcadas,
                "linhas_com_match_automatico": qtd_linhas_com_match_automatico,
                "invalidos_juntados": len(invalidos_juntados),
                "validos_com_merge": len(validos_com_merge),
                "invalidos_nao_juntados": len(df_invalidos_restantes),
            }
        ]
    )

    return df_final, df_log_merges, df_resumo


def main():
    garantir_pasta(PASTA_GERADOS)
    garantir_pasta(PASTA_LOGS)

    print(f"Lendo {ARQUIVO_ENTRADA}")

    df = ler_final()
    df_validos, df_invalidos = separar_validos_invalidos(df)

    print("\nResumo do enriquecimento:")
    print(f"  Total de linhas: {len(df)}")
    print(f"  Registros validos: {len(df_validos)}")
    print(f"  Registros invalidos: {len(df_invalidos)}")
    print(f"  Colunas: {len(df.columns)}")

    df_final, df_log_merges, df_resumo = comparar_e_juntar(df_validos, df_invalidos)

    df_final.to_csv(caminho_projeto(ARQUIVO_SAIDA), sep=";", encoding="utf-8-sig", index=False)
    df_log_merges.to_csv(
        caminho_projeto(ARQUIVO_LOG_MERGES),
        sep=";",
        encoding="utf-8-sig",
        index=False,
        decimal=",",
        float_format="%.4f",
    )

    caminho_decisoes = caminho_projeto(ARQUIVO_DECISOES_REVISAO)
    if os.path.exists(caminho_decisoes):
        os.remove(caminho_decisoes)
        print(f"Arquivo de decisoes anterior removido: {ARQUIVO_DECISOES_REVISAO}")

    resumo = df_resumo.iloc[0].to_dict() if not df_resumo.empty else {}

    print("\nResultado do enriquecimento:")
    print(
        f"  Invalidos: {len(df_invalidos)} | "
        f"avaliados: {resumo.get('linhas_avaliadas', 0)} | "
        f"juntados: {len(df_log_merges)} | "
        f"restantes: {len(df_final) - len(df_validos)}"
    )
    print(
        f"  Revisao: {resumo.get('linhas_revisao_marcadas', 0)} linhas marcadas | "
        f"{resumo.get('grupos_revisao', 0)} grupos"
    )
    print(f"  Saidas: {ARQUIVO_SAIDA} | {ARQUIVO_LOG_MERGES}")

    return df_validos, df_invalidos, df_final


if __name__ == "__main__":
    with registrar_log_terminal(ARQUIVO_LOG_TXT):
        main()

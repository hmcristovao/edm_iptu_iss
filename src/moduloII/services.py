import asyncio
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from typing import Callable

import pandas as pd

from src.moduloII.app_config import (
    COLUNA_DATA_REVISAO,
    COLUNA_DECISAO_REVISAO,
    COLUNA_MERGE_KEY,
    COLUNA_OBSERVACAO_REVISAO,
    COLUNA_REVISAO,
    COLUNA_SCORE_REVISAO,
    COLUNA_USUARIO_REVISAO,
    AppPaths,
    AppSettings,
)


def valor_vazio(valor) -> bool:
    if pd.isna(valor):
        return True
    texto = str(valor).strip()
    return texto == "" or texto.lower() in {"nan", "none", "null"}


def texto_valor(valor) -> str:
    if valor_vazio(valor):
        return ""
    return str(valor)


def formatar_score(valor) -> str:
    texto = texto_valor(valor).replace(",", ".")
    if not texto:
        return "Não informado"
    try:
        return f"{float(texto):.2f}%"
    except ValueError:
        return texto_valor(valor)


def extrair_porcentagem(texto: str) -> int | None:
    percentuais = re.findall(r"(\d{1,3})%", texto)
    if not percentuais:
        return None
    return max(0, min(100, int(percentuais[-1])))


class IntegracaoConfigService:
    def __init__(self, paths: AppPaths, settings: AppSettings):
        self.paths = paths
        self.settings = settings

    def carregar(self) -> dict:
        caminho_config = self.paths.resolver_codigo(self.paths.arquivo_config_integracao)
        if not caminho_config.exists():
            return self.settings.integracao_config_padrao.copy()

        try:
            with caminho_config.open("r", encoding="utf-8") as arquivo:
                config = json.load(arquivo)
        except (json.JSONDecodeError, OSError):
            return self.settings.integracao_config_padrao.copy()

        config_final = self.settings.integracao_config_padrao.copy()
        config_final.update(config)
        return config_final

    def salvar(self, config: dict):
        caminho_config = self.paths.resolver_codigo(self.paths.arquivo_config_integracao)
        with caminho_config.open("w", encoding="utf-8") as arquivo:
            json.dump(config, arquivo, ensure_ascii=False, indent=2)


class EntradaService:
    def __init__(self, paths: AppPaths):
        self.paths = paths

    def listar_csvs(self) -> list[str]:
        if not self.paths.work_dir.is_dir():
            return []

        arquivos = []
        for pasta in [self.paths.work_dir, self.paths.resolver(self.paths.pasta_dados_processados)]:
            if not pasta.is_dir():
                continue
            for arquivo in pasta.iterdir():
                if arquivo.is_file() and arquivo.name.lower().endswith(".csv"):
                    arquivos.append(arquivo.relative_to(self.paths.work_dir).as_posix())

        return sorted(arquivos)

    def pasta_valida(self) -> bool:
        return self.paths.work_dir.is_dir()


class RevisaoService:
    def __init__(self, paths: AppPaths):
        self.paths = paths

    def carregar_dados(self) -> pd.DataFrame:
        return pd.read_csv(
            self.paths.resolver(self.paths.arquivo_enriquecimento),
            sep=";",
            encoding="utf-8-sig",
            dtype=str,
        ).fillna("")

    def carregar_decisoes(self) -> dict[str, dict]:
        if not self.paths.existe(self.paths.arquivo_decisoes):
            return {}

        df_decisoes = pd.read_csv(
            self.paths.resolver(self.paths.arquivo_decisoes),
            sep=";",
            encoding="utf-8-sig",
            dtype=str,
        ).fillna("")

        return {
            row["par_id"]: row.to_dict()
            for _, row in df_decisoes.iterrows()
            if row.get("par_id")
        }

    def salvar_decisoes(self, decisoes: dict[str, dict]):
        df_decisoes = pd.DataFrame(decisoes.values())
        self.paths.garantir_pasta_arquivo(self.paths.arquivo_decisoes)
        df_decisoes.to_csv(
            self.paths.resolver(self.paths.arquivo_decisoes),
            sep=";",
            encoding="utf-8-sig",
            index=False,
        )

    def _grupos_revisao_validos(self, df: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
        if COLUNA_REVISAO not in df.columns:
            return []

        filtro = df[COLUNA_REVISAO].astype(str).str.strip() != ""
        grupos = df[filtro].groupby(COLUNA_REVISAO, sort=True)
        grupos_validos = []

        for id_revisao, grupo in grupos:
            validos = grupo[grupo[COLUNA_MERGE_KEY].astype(str).str.strip() != ""]
            invalidos = grupo[grupo[COLUNA_MERGE_KEY].astype(str).str.strip() == ""]

            if validos.empty or invalidos.empty:
                continue

            grupos_validos.append((id_revisao, grupo))

        return grupos_validos

    def contar_grupos_revisao(self, df: pd.DataFrame) -> int:
        return len(self._grupos_revisao_validos(df))

    def criar_pares_candidatos(
        self,
        df: pd.DataFrame,
        limite_grupos: int | None = None,
        offset_grupos: int = 0,
    ) -> list[dict]:
        pares = []
        grupos = self._grupos_revisao_validos(df)

        if offset_grupos > 0 or limite_grupos is not None:
            fim = None if limite_grupos is None else offset_grupos + limite_grupos
            grupos = grupos[offset_grupos:fim]

        for id_revisao, grupo in grupos:
            validos = grupo[grupo[COLUNA_MERGE_KEY].astype(str).str.strip() != ""]
            invalidos = grupo[grupo[COLUNA_MERGE_KEY].astype(str).str.strip() == ""]
            idx_valido = validos.index[0]

            for idx_invalido in invalidos.index:
                pares.append(
                    {
                        "par_id": f"{id_revisao}:{idx_valido}:{idx_invalido}",
                        "id_revisao": id_revisao,
                        "idx_valido": idx_valido,
                        "idx_invalido": idx_invalido,
                        "score_revisao": texto_valor(df.at[idx_invalido, COLUNA_SCORE_REVISAO])
                        if COLUNA_SCORE_REVISAO in df.columns
                        else "",
                    }
                )

        return pares

    def carregar_lote_pendente(
        self,
        df: pd.DataFrame,
        decisoes: dict[str, dict],
        limite_grupos: int,
        offset_grupos: int = 0,
    ) -> tuple[list[dict], int]:
        grupos = self._grupos_revisao_validos(df)

        for offset in range(offset_grupos, len(grupos), limite_grupos):
            pares = self.criar_pares_candidatos(
                df,
                limite_grupos=limite_grupos,
                offset_grupos=offset,
            )
            pendentes = [par for par in pares if par["par_id"] not in decisoes]
            if pendentes:
                return pares, offset + limite_grupos

        return [], len(grupos)

    def primeiro_indice_pendente(self, pares: list[dict], decisoes: dict[str, dict]) -> int:
        for indice, par in enumerate(pares):
            if par["par_id"] not in decisoes:
                return indice
        return 0

    def montar_comparacao(self, linha_valida: pd.Series, linha_invalida: pd.Series) -> list[dict]:
        linhas = []
        for coluna in linha_valida.index:
            valor_valido = texto_valor(linha_valida[coluna])
            valor_invalido = texto_valor(linha_invalida.get(coluna, ""))

            if not valor_valido and not valor_invalido:
                continue

            if valor_valido == valor_invalido:
                situacao = "Igual"
            elif not valor_valido and valor_invalido:
                situacao = "Preenche vazio"
            elif valor_valido and not valor_invalido:
                situacao = "Só no válido"
            else:
                situacao = "Diferente"

            linhas.append(
                {
                    "coluna": coluna,
                    "valido": valor_valido,
                    "invalido": valor_invalido,
                    "situacao": situacao,
                }
            )
        return linhas

    def registrar_decisao(self, decisoes: dict[str, dict], par: dict, usuario: str, decisao: str, observacao: str = ""):
        decisoes[par["par_id"]] = {
            "par_id": par["par_id"],
            "id_revisao": par["id_revisao"],
            "idx_valido": par["idx_valido"],
            "idx_invalido": par["idx_invalido"],
            "score_revisao": par.get("score_revisao", ""),
            "decisao": decisao,
            "usuario_revisor": usuario,
            "observacao": texto_valor(observacao),
            "data_decisao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.salvar_decisoes(decisoes)

    def salvar_arquivo_revisado(self, df: pd.DataFrame, decisoes: dict[str, dict], caminho_saida: str):
        df_revisado = self.aplicar_decisoes(df, decisoes)
        self.paths.garantir_pasta_arquivo(caminho_saida)
        df_revisado.to_csv(
            self.paths.resolver(caminho_saida),
            sep=";",
            encoding="utf-8-sig",
            index=False,
        )

    def aplicar_decisoes(self, df: pd.DataFrame, decisoes: dict[str, dict]) -> pd.DataFrame:
        resultado = df.copy()
        self._garantir_colunas_revisao(resultado)
        indices_remover = []

        for decisao in decisoes.values():
            idx_valido = int(decisao["idx_valido"])
            idx_invalido = int(decisao["idx_invalido"])

            if idx_valido not in resultado.index or idx_invalido not in resultado.index:
                continue

            if decisao.get("decisao") == "aprovar":
                resultado.loc[idx_valido] = self._preencher_linha(
                    resultado.loc[idx_valido],
                    resultado.loc[idx_invalido],
                )
                self._registrar_metadados_revisao(resultado, idx_valido, decisao)
                indices_remover.append(idx_invalido)
            else:
                self._registrar_metadados_revisao(resultado, idx_invalido, decisao)

        resultado = resultado.drop(index=sorted(set(indices_remover)))
        return resultado.reset_index(drop=True)

    def _preencher_linha(self, destino: pd.Series, origem: pd.Series) -> pd.Series:
        resultado = destino.copy()
        origem_util = origem.reindex(resultado.index)
        vazios = resultado.apply(valor_vazio)
        resultado.loc[vazios] = origem_util.loc[vazios]
        return resultado

    def _garantir_colunas_revisao(self, df: pd.DataFrame):
        for coluna in [
            COLUNA_USUARIO_REVISAO,
            COLUNA_DECISAO_REVISAO,
            COLUNA_OBSERVACAO_REVISAO,
            COLUNA_DATA_REVISAO,
        ]:
            if coluna not in df.columns:
                df[coluna] = ""

    def _registrar_metadados_revisao(self, resultado: pd.DataFrame, indice: int, decisao: dict):
        resultado.at[indice, COLUNA_USUARIO_REVISAO] = self._juntar_metadado(
            resultado.at[indice, COLUNA_USUARIO_REVISAO],
            decisao.get("usuario_revisor", ""),
        )
        resultado.at[indice, COLUNA_DECISAO_REVISAO] = self._juntar_metadado(
            resultado.at[indice, COLUNA_DECISAO_REVISAO],
            decisao.get("decisao", ""),
        )
        resultado.at[indice, COLUNA_OBSERVACAO_REVISAO] = self._juntar_metadado(
            resultado.at[indice, COLUNA_OBSERVACAO_REVISAO],
            decisao.get("observacao", ""),
        )
        resultado.at[indice, COLUNA_DATA_REVISAO] = self._juntar_metadado(
            resultado.at[indice, COLUNA_DATA_REVISAO],
            decisao.get("data_decisao", ""),
        )

    def _juntar_metadado(self, valor_atual, novo_valor: str) -> str:
        atual = texto_valor(valor_atual)
        novo = texto_valor(novo_valor)

        if not novo:
            return atual
        if not atual:
            return novo

        partes = [parte.strip() for parte in atual.split(" | ") if parte.strip()]
        if novo in partes:
            return atual

        return f"{atual} | {novo}"


class PipelineRunner:
    def __init__(self, paths: AppPaths):
        self.paths = paths

    async def executar(
        self,
        script: str,
        ao_progredir: Callable[[str], None],
    ) -> int:
        script_path = self.paths.resolver_codigo(script)
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["AVALIADOR_WORKDIR"] = str(self.paths.work_dir)
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        processo = await asyncio.create_subprocess_exec(
            sys.executable,
            "-u",
            str(script_path),
            cwd=str(self.paths.code_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
            creationflags=creationflags,
        )

        assert processo.stdout is not None
        buffer = ""
        while True:
            bloco = await processo.stdout.read(4096)
            if not bloco:
                break

            texto = bloco.decode("utf-8", errors="replace")
            buffer += texto

            while "\n" in buffer:
                linha, buffer = buffer.split("\n", 1)
                ao_progredir(linha.rstrip())

            if len(buffer) > 4096:
                ao_progredir(buffer)
                buffer = ""

        if buffer:
            ao_progredir(buffer)

        return await processo.wait()

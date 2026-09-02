import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

import pandas as pd

from src.moduloI.handlers.adapters.anomizador.anonimizador_reversivel_adaptado import AnonimizadorReversivel
from src.moduloII.app_config import COLUNA_MERGE_KEY, AppPaths


@dataclass(frozen=True)
class ResultadoReidentificacao:
    entrada: str
    saida: str
    colunas_reidentificadas: list[str]
    valores_reidentificados: int
    base_imobiliaria_saida: str = ""
    base_imobiliaria_valores_reidentificados: int = 0


def resultado_reidentificacao_payload(resultado: ResultadoReidentificacao) -> dict:
    return {
        "entrada": resultado.entrada,
        "saida": resultado.saida,
        "total_colunas_reidentificadas": len(resultado.colunas_reidentificadas),
        "valores_reidentificados": resultado.valores_reidentificados,
        "base_imobiliaria_saida": resultado.base_imobiliaria_saida,
        "base_imobiliaria_valores_reidentificados": resultado.base_imobiliaria_valores_reidentificados,
    }


class ReidentificacaoService:
    def __init__(self, paths: AppPaths):
        self.paths = paths

    def reidentificar(
        self,
        chave: str,
        arquivo_entrada: str | None = None,
        arquivo_saida: str | None = None,
        registrar_progresso: Callable[[str], None] | None = None,
    ) -> ResultadoReidentificacao:
        if not chave:
            raise ValueError("Informe a chave usada na pseudonimização.")

        entrada = arquivo_entrada or self._arquivo_entrada_padrao()
        saida = arquivo_saida or self.paths.arquivo_integracao_reidentificada

        if not entrada:
            raise FileNotFoundError("Nenhuma base final ou parcial foi encontrada para reidentificação.")

        caminho_entrada = self.paths.resolver(entrada)
        if not caminho_entrada.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {entrada}.")

        self._registrar(registrar_progresso, f"Lendo {entrada}.")
        os.environ["key"] = chave
        anonimizador = AnonimizadorReversivel()

        df = pd.read_csv(caminho_entrada, sep=";", encoding="utf-8-sig", dtype=str).fillna("")
        self._registrar(registrar_progresso, f"Arquivo carregado: {len(df)} linha(s), {len(df.columns)} coluna(s).")
        colunas = self._colunas_cpf(df)
        total = 0

        for indice, coluna in enumerate(colunas, start=1):
            self._registrar(registrar_progresso, f"Reidentificando CPF {indice}/{len(colunas)}: {coluna}.")
            df[coluna], quantidade = self._decriptografar_serie(df[coluna], anonimizador)
            total += quantidade

        if COLUNA_MERGE_KEY in df.columns:
            self._registrar(registrar_progresso, f"Reidentificando {COLUNA_MERGE_KEY}.")
            df[COLUNA_MERGE_KEY], quantidade = self._decriptografar_merge_key(df[COLUNA_MERGE_KEY], anonimizador)
            total += quantidade

        self._registrar(registrar_progresso, f"Salvando {saida}.")
        self.paths.garantir_pasta_arquivo(saida)
        self._proteger_documentos_como_texto(df)
        df.to_csv(self.paths.resolver(saida), sep=";", encoding="utf-8-sig", index=False)
        base_saida, base_total = self._reidentificar_base_imobiliaria(
            anonimizador,
            registrar_progresso,
        )

        return ResultadoReidentificacao(
            entrada=entrada,
            saida=saida,
            colunas_reidentificadas=colunas,
            valores_reidentificados=total,
            base_imobiliaria_saida=base_saida,
            base_imobiliaria_valores_reidentificados=base_total,
        )

    def _registrar(self, registrar_progresso: Callable[[str], None] | None, mensagem: str) -> None:
        if registrar_progresso:
            registrar_progresso(mensagem)

    def _arquivo_entrada_padrao(self) -> str:
        if self.paths.existe(self.paths.arquivo_integracao_final):
            return self.paths.arquivo_integracao_final
        if self.paths.existe(self.paths.arquivo_integracao_parcial):
            return self.paths.arquivo_integracao_parcial
        return ""

    def _reidentificar_base_imobiliaria(
        self,
        anonimizador: AnonimizadorReversivel,
        registrar_progresso: Callable[[str], None] | None,
    ) -> tuple[str, int]:
        if not self.paths.existe(self.paths.arquivo_base_imobiliario_modulo_iv):
            return "", 0

        entrada = self.paths.arquivo_base_imobiliario_modulo_iv
        saida = self.paths.arquivo_base_imobiliario_reidentificada
        self._registrar(registrar_progresso, f"Reidentificando base imobiliaria {entrada}.")
        df = pd.read_csv(self.paths.resolver(entrada), sep=";", encoding="utf-8-sig", dtype=str).fillna("")
        total = 0

        for coluna in self._colunas_cpf(df):
            df[coluna], quantidade = self._decriptografar_serie(df[coluna], anonimizador)
            total += quantidade

        self.paths.garantir_pasta_arquivo(saida)
        self._proteger_documentos_como_texto(df)
        df.to_csv(self.paths.resolver(saida), sep=";", encoding="utf-8-sig", index=False)
        return saida, total

    def _colunas_cpf(self, df: pd.DataFrame) -> list[str]:
        return [
            coluna
            for coluna in df.columns
            if "cpf" in str(coluna).lower() and "valid" not in str(coluna).lower()
        ]

    def _proteger_documentos_como_texto(self, df: pd.DataFrame) -> None:
        for coluna in df.columns:
            nome = str(coluna).lower()
            if ("cpf" not in nome and "cnpj" not in nome) or "valid" in nome:
                continue
            df[coluna] = df[coluna].apply(self._formatar_como_texto)

    def _formatar_como_texto(self, valor) -> str:
        texto = str(valor).strip()
        if texto.lower() in {"", "nan", "none", "null"}:
            return ""
        if texto.startswith("\t"):
            return texto
        return f"\t{texto}"

    def _decriptografar_serie(
        self,
        serie: pd.Series,
        anonimizador: AnonimizadorReversivel,
    ) -> tuple[pd.Series, int]:
        total = 0

        def converter(valor):
            nonlocal total
            texto = str(valor).strip()
            if not texto:
                return valor

            decriptografado = anonimizador.decrypt(texto)
            if decriptografado.startswith("[ERRO"):
                return valor

            total += 1
            return decriptografado

        return serie.apply(converter), total

    def _decriptografar_merge_key(
        self,
        serie: pd.Series,
        anonimizador: AnonimizadorReversivel,
    ) -> tuple[pd.Series, int]:
        total = 0

        def converter(valor):
            nonlocal total
            texto = str(valor).strip()
            if not texto.startswith("CPF_"):
                return valor

            decriptografado = anonimizador.decrypt(texto[4:])
            if decriptografado.startswith("[ERRO"):
                return valor

            total += 1
            return f"CPF_{decriptografado}"

        return serie.apply(converter), total


def main():
    chave = os.environ.get("key") or os.environ.get("APP_CHAVE_PSEUDONIMIZACAO", "")
    resultado = ReidentificacaoService(AppPaths()).reidentificar(
        chave,
        registrar_progresso=lambda linha: print(linha, flush=True),
    )
    print(
        "Reidentificação concluída: "
        f"{resultado.valores_reidentificados} valor(es), saída {resultado.saida}."
    )
    print(
        f"RESULTADO_REIDENTIFICACAO_JSON={json.dumps(resultado_reidentificacao_payload(resultado), ensure_ascii=False)}",
        flush=True,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()

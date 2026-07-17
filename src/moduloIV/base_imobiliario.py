import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

import pandas as pd

from src.moduloI.handlers.adapters.anomizador.anonimizador_reversivel_adaptado import AnonimizadorReversivel
from src.moduloII.app_config import AppPaths
from src.moduloII.enriquecimento import PARAMETROS_COMPARACAO


COLUNA_DOCUMENTO = "cpfCnpjImobiliario"
COLUNA_CPF_VALIDO = "cpfValidoImobiliario"
COLUNA_CNPJ_VALIDO = "cnpjValidoImobiliario"
COLUNA_INSCRICAO = "inscricaoImobiliario"
COLUNA_ENDERECO = "enderecoImobiliario"
COLUNA_CELULAR = "celularImobiliario"
COLUNA_EMAIL = "emailImobiliario"
COLUNA_MERGE_KEY = "merge_key"
PREFIXO_TELEFONE_ENRIQUECIDO = "telefoneEnriquecido"
PREFIXO_EMAIL_ENRIQUECIDO = "emailEnriquecido"


@dataclass(frozen=True)
class ResultadoBaseImobiliarioModuloIV:
    entrada: str
    saida: str
    linhas_entrada: int
    linhas_saida: int
    linhas_removidas_duplicadas: int
    cpfs_reidentificados: int
    celulares_preenchidos: int
    emails_preenchidos: int
    telefones_enriquecidos: int
    emails_enriquecidos: int


class BaseImobiliarioModuloIVService:
    def __init__(self, paths: AppPaths):
        self.paths = paths

    def gerar(
        self,
        chave: str,
        arquivo_entrada: str | None = None,
        arquivo_saida: str | None = None,
        arquivo_integracao: str | None = None,
    ) -> ResultadoBaseImobiliarioModuloIV:
        if not chave:
            raise ValueError("Informe a chave usada na pseudonimizacao.")

        entrada = arquivo_entrada or self._arquivo_entrada_padrao()
        saida = arquivo_saida or self.paths.arquivo_base_imobiliario_modulo_iv
        integracao = arquivo_integracao or self.paths.arquivo_integracao_reidentificada

        caminho_entrada = self.paths.resolver(entrada)
        if not caminho_entrada.exists():
            raise FileNotFoundError(f"Arquivo do cadastro imobiliario nao encontrado: {entrada}.")
        caminho_integracao = self.paths.resolver(integracao)
        if not caminho_integracao.exists():
            raise FileNotFoundError(f"Arquivo de integracao reidentificada nao encontrado: {integracao}.")

        os.environ["key"] = chave
        anonimizador = AnonimizadorReversivel()

        df = pd.read_csv(caminho_entrada, sep=";", encoding="utf-8-sig", dtype=str).fillna("")
        df_saida, linhas_removidas = self._remover_duplicados_agregando_inscricoes(df)
        cpfs_reidentificados = self._reidentificar_cpfs(df_saida, anonimizador)
        df_integracao = pd.read_csv(caminho_integracao, sep=";", encoding="utf-8-sig", dtype=str).fillna("")
        telefones_enriquecidos, emails_enriquecidos = self._enriquecer_contatos(df_saida, df_integracao)
        celulares_preenchidos = self._contar_preenchidos(df_saida, COLUNA_CELULAR)
        emails_preenchidos = self._contar_preenchidos(df_saida, COLUNA_EMAIL)
        self._remover_colunas_saida(df_saida)
        self._proteger_documento_saida(df_saida)

        self.paths.garantir_pasta_arquivo(saida)
        df_saida.to_csv(self.paths.resolver(saida), sep=";", encoding="utf-8-sig", index=False)

        return ResultadoBaseImobiliarioModuloIV(
            entrada=entrada,
            saida=saida,
            linhas_entrada=len(df),
            linhas_saida=len(df_saida),
            linhas_removidas_duplicadas=linhas_removidas,
            cpfs_reidentificados=cpfs_reidentificados,
            celulares_preenchidos=celulares_preenchidos,
            emails_preenchidos=emails_preenchidos,
            telefones_enriquecidos=telefones_enriquecidos,
            emails_enriquecidos=emails_enriquecidos,
        )

    def _arquivo_entrada_padrao(self) -> str:
        return (Path(self.paths.pasta_dados_processados) / "imobiliario.csv").as_posix()

    def _enriquecer_contatos(self, df_imobiliario: pd.DataFrame, df_integracao: pd.DataFrame) -> tuple[int, int]:
        mapa = self._mapear_contatos_por_documento(df_integracao)
        telefones_por_linha = []
        emails_por_linha = []

        for _, linha in df_imobiliario.iterrows():
            chave = self._chave_documento_linha(linha)
            contatos = mapa.get(chave, {"telefone": [], "email": []})
            telefones = self._novos_valores(contatos["telefone"], [linha.get(COLUNA_CELULAR, "")])
            emails = self._novos_valores(contatos["email"], [linha.get(COLUNA_EMAIL, "")])
            telefones_por_linha.append(telefones)
            emails_por_linha.append(emails)

        self._criar_colunas_enriquecidas(df_imobiliario, PREFIXO_TELEFONE_ENRIQUECIDO, telefones_por_linha)
        self._criar_colunas_enriquecidas(df_imobiliario, PREFIXO_EMAIL_ENRIQUECIDO, emails_por_linha)

        return sum(len(valores) for valores in telefones_por_linha), sum(len(valores) for valores in emails_por_linha)

    def _mapear_contatos_por_documento(self, df: pd.DataFrame) -> dict[str, dict[str, list[str]]]:
        colunas_documento = self._colunas_documento_integracao(df)
        colunas_telefone = self._colunas_por_parametro(df, "telefone")
        colunas_email = self._colunas_por_parametro(df, "email")
        mapa: dict[str, dict[str, list[str]]] = {}

        for _, linha in df.iterrows():
            chaves = self._chaves_documento_integracao(linha, colunas_documento)
            if not chaves:
                continue

            telefones = self._valores_linha(linha, colunas_telefone)
            emails = self._valores_linha(linha, colunas_email)
            for chave in chaves:
                destino = mapa.setdefault(chave, {"telefone": [], "email": []})
                destino["telefone"] = self._novos_valores([*destino["telefone"], *telefones], [])
                destino["email"] = self._novos_valores([*destino["email"], *emails], [])

        return mapa

    def _colunas_documento_integracao(self, df: pd.DataFrame) -> list[str]:
        colunas = []
        for coluna in df.columns:
            nome = str(coluna).lower()
            if nome == COLUNA_MERGE_KEY or (("cpf" in nome or "cnpj" in nome) and "valid" not in nome):
                colunas.append(coluna)
        return colunas

    def _chaves_documento_integracao(self, linha: pd.Series, colunas_documento: list[str]) -> list[str]:
        chaves = []
        vistos = set()
        for coluna in colunas_documento:
            chave = self._chave_documento_integracao(coluna, linha.get(coluna, ""))
            if chave and chave not in vistos:
                chaves.append(chave)
                vistos.add(chave)
        return chaves

    def _chave_documento_integracao(self, coluna: str, valor) -> str:
        texto = self._limpar_texto_documento(valor)
        if not texto:
            return ""

        if str(coluna).lower() == COLUNA_MERGE_KEY:
            if texto.startswith("CPF_"):
                return f"CPF_{self._normalizar_documento(texto[4:])}"
            if texto.startswith("CNPJ_"):
                return f"CNPJ_{self._normalizar_documento(texto[5:])}"
            return ""

        nome = str(coluna).lower()
        documento = self._normalizar_documento(texto)
        if not documento:
            return ""
        if "cnpj" in nome and "cpf" not in nome:
            return f"CNPJ_{documento}"
        if "cpf" in nome and "cnpj" not in nome:
            return f"CPF_{documento}"
        if len(documento) == 14:
            return f"CNPJ_{documento}"
        if len(documento) == 11:
            return f"CPF_{documento}"
        return ""

    def _colunas_por_parametro(self, df: pd.DataFrame, nome_parametro: str) -> list[str]:
        parametro = next(item for item in PARAMETROS_COMPARACAO if item["nome"] == nome_parametro)
        regex = re.compile(parametro["padrao_colunas"], re.IGNORECASE)
        termos_excluidos = ("merge_key", "valido", "valid", "unnamed", "index", "indice")
        return [
            coluna
            for coluna in df.columns
            if regex.search(str(coluna)) and not any(termo in str(coluna).lower() for termo in termos_excluidos)
        ]

    def _valores_linha(self, linha: pd.Series, colunas: list[str]) -> list[str]:
        valores = []
        for coluna in colunas:
            for parte in str(linha.get(coluna, "")).split("|"):
                texto = self._texto(parte)
                if texto:
                    valores.append(texto)
        return self._novos_valores(valores, [])

    def _novos_valores(self, candidatos: list[str], existentes: list) -> list[str]:
        vistos = set()
        valores = []
        for valor in existentes:
            texto = self._texto(valor)
            if texto:
                vistos.add(self._chave_unicidade_contato(texto))
        for valor in candidatos:
            texto = self._texto(valor)
            chave = self._chave_unicidade_contato(texto)
            if texto and chave not in vistos:
                valores.append(texto)
                vistos.add(chave)
        return valores

    def _chave_unicidade_contato(self, valor: str) -> str:
        texto = self._texto(valor)
        if "@" in texto:
            return texto.lower()

        digitos = re.sub(r"\D", "", texto)
        if len(digitos) >= 8:
            if digitos.startswith("55") and len(digitos) in {12, 13}:
                digitos = digitos[2:]
            return digitos

        return texto.lower()

    def _criar_colunas_enriquecidas(self, df: pd.DataFrame, prefixo: str, valores_por_linha: list[list[str]]) -> None:
        maximo = max((len(valores) for valores in valores_por_linha), default=0)
        for posicao in range(maximo):
            df[f"{prefixo}{posicao + 1}"] = [
                valores[posicao] if posicao < len(valores) else ""
                for valores in valores_por_linha
            ]

    def _remover_duplicados_agregando_inscricoes(self, df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        self._validar_colunas_obrigatorias(df)

        resultado = []
        indice_por_chave = {}
        removidas = 0

        for _, linha in df.iterrows():
            chave = self._chave_documento_linha(linha)
            if not chave or chave not in indice_por_chave:
                resultado.append(linha.copy())
                if chave:
                    indice_por_chave[chave] = len(resultado) - 1
                continue

            destino = resultado[indice_por_chave[chave]]
            destino[COLUNA_INSCRICAO] = self._juntar_valores(
                destino.get(COLUNA_INSCRICAO, ""),
                linha.get(COLUNA_INSCRICAO, ""),
            )
            removidas += 1

        return pd.DataFrame(resultado, columns=df.columns).fillna(""), removidas

    def _validar_colunas_obrigatorias(self, df: pd.DataFrame) -> None:
        ausentes = [
            coluna
            for coluna in [COLUNA_DOCUMENTO, COLUNA_CPF_VALIDO, COLUNA_CNPJ_VALIDO, COLUNA_INSCRICAO]
            if coluna not in df.columns
        ]
        if ausentes:
            raise ValueError(f"Coluna(s) obrigatoria(s) ausente(s): {', '.join(ausentes)}.")

    def _chave_documento_linha(self, linha: pd.Series) -> str:
        documento = self._texto(linha.get(COLUNA_DOCUMENTO, ""))
        if not documento:
            return ""

        cpf_valido = self._status_valido(linha.get(COLUNA_CPF_VALIDO, ""))
        cnpj_valido = self._status_valido(linha.get(COLUNA_CNPJ_VALIDO, ""))
        if not cpf_valido and not cnpj_valido:
            return ""

        if cpf_valido:
            return f"CPF_{documento}"
        return f"CNPJ_{self._normalizar_cnpj(documento)}"

    def _reidentificar_cpfs(self, df: pd.DataFrame, anonimizador: AnonimizadorReversivel) -> int:
        total = 0

        for indice, linha in df.iterrows():
            if not self._status_valido(linha.get(COLUNA_CPF_VALIDO, "")):
                continue

            documento = self._texto(linha.get(COLUNA_DOCUMENTO, ""))
            if not documento:
                continue

            decriptografado = anonimizador.decrypt(documento)
            if decriptografado.startswith("[ERRO"):
                continue

            df.at[indice, COLUNA_DOCUMENTO] = re.sub(r"\D", "", decriptografado) or decriptografado
            total += 1

        return total

    def _juntar_valores(self, atual, novo) -> str:
        valores = []
        vistos = set()
        for valor in [atual, novo]:
            for parte in str(valor).split("|"):
                item = self._texto(parte)
                if item and item not in vistos:
                    valores.append(item)
                    vistos.add(item)
        return " | ".join(valores)

    def _texto(self, valor) -> str:
        texto = str(valor).strip()
        if texto.lower() in {"", "nan", "none", "null"}:
            return ""
        return texto

    def _status_valido(self, valor) -> bool:
        return self._texto(valor).upper() == "S"

    def _normalizar_cnpj(self, valor) -> str:
        return re.sub(r"\D", "", self._texto(valor))

    def _normalizar_documento(self, valor) -> str:
        return re.sub(r"\D", "", self._limpar_texto_documento(valor))

    def _limpar_texto_documento(self, valor) -> str:
        texto = self._texto(valor)
        if texto.startswith("\t"):
            texto = texto[1:].strip()
        if texto.startswith('="') and texto.endswith('"'):
            texto = texto[2:-1].strip()
        return texto

    def _contar_preenchidos(self, df: pd.DataFrame, coluna: str) -> int:
        if coluna not in df.columns:
            return 0

        valores = df[coluna].fillna("").astype(str).str.strip()
        return int((~valores.str.lower().isin(["", "-", "nan", "none", "null"])).sum())

    def _remover_colunas_saida(self, df: pd.DataFrame) -> None:
        if COLUNA_ENDERECO in df.columns:
            df.drop(columns=[COLUNA_ENDERECO], inplace=True)

    def _proteger_documento_saida(self, df: pd.DataFrame) -> None:
        if COLUNA_DOCUMENTO not in df.columns:
            return

        df[COLUNA_DOCUMENTO] = df[COLUNA_DOCUMENTO].apply(self._formatar_como_texto)

    def _formatar_como_texto(self, valor) -> str:
        texto = self._texto(valor)
        if not texto:
            return ""
        if texto.startswith("\t"):
            return texto
        return f"\t{texto}"


def main():
    chave = os.environ.get("key") or os.environ.get("APP_CHAVE_PSEUDONIMIZACAO", "")
    resultado = BaseImobiliarioModuloIVService(AppPaths()).gerar(chave)
    print(
        "Base imobiliaria do modulo IV gerada: "
        f"{resultado.linhas_saida} linha(s), "
        f"{resultado.linhas_removidas_duplicadas} duplicata(s) removida(s), "
        f"{resultado.cpfs_reidentificados} CPF(s) reidentificado(s), "
        f"{resultado.celulares_preenchidos} celular(es) preenchido(s), "
        f"{resultado.emails_preenchidos} email(s) preenchido(s), "
        f"{resultado.telefones_enriquecidos} telefone(s) enriquecido(s), "
        f"{resultado.emails_enriquecidos} email(s) enriquecido(s), "
        f"saida {resultado.saida}."
    )
    print(f"RESULTADO_MODULO_IV_JSON={json.dumps(asdict(resultado), ensure_ascii=False)}")


if __name__ in {"__main__", "__mp_main__"}:
    main()

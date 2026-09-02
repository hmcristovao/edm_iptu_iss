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
from src.moduloII.app_config import (
    COLUNA_DATA_REVISAO,
    COLUNA_REVISAO as COLUNA_ID_REVISAO,
    COLUNA_USUARIO_REVISAO,
    AppPaths,
)
from src.moduloII.enriquecimento import PARAMETROS_COMPARACAO


COLUNA_CPF = "cpfImobiliario"
COLUNA_CNPJ = "cnpjImobiliario"
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
class ContatoRastreado:
    valor: str
    origem: str
    id_revisao: str
    usuario_revisao: str
    data_revisao: str


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
    percentual_telefones_enriquecidos: float
    percentual_emails_enriquecidos: float


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
        entrada = arquivo_entrada or self._arquivo_entrada_padrao()
        saida = arquivo_saida or self.paths.arquivo_base_imobiliario_modulo_iv
        integracao = arquivo_integracao or self._arquivo_integracao_padrao()

        caminho_entrada = self.paths.resolver(entrada)
        if not caminho_entrada.exists():
            raise FileNotFoundError(f"Arquivo do cadastro imobiliario nao encontrado: {entrada}.")
        caminho_integracao = self.paths.resolver(integracao)
        if not caminho_integracao.exists():
            raise FileNotFoundError(f"Arquivo de integracao final ou parcial nao encontrado: {integracao}.")

        df = pd.read_csv(caminho_entrada, sep=";", encoding="utf-8-sig", dtype=str).fillna("")
        df_saida, linhas_removidas = self._remover_duplicados_agregando_inscricoes(df)
        cpfs_reidentificados = 0
        df_integracao = pd.read_csv(caminho_integracao, sep=";", encoding="utf-8-sig", dtype=str).fillna("")
        celulares_preenchidos = self._contar_preenchidos(df_saida, COLUNA_CELULAR)
        emails_preenchidos = self._contar_preenchidos(df_saida, COLUNA_EMAIL)
        telefones_enriquecidos, emails_enriquecidos = self._enriquecer_contatos(df_saida, df_integracao)
        percentual_telefones = self._calcular_percentual_enriquecimento(
            telefones_enriquecidos,
            celulares_preenchidos,
        )
        percentual_emails = self._calcular_percentual_enriquecimento(
            emails_enriquecidos,
            emails_preenchidos,
        )
        self._remover_colunas_saida(df_saida)
        self._proteger_documento_saida(df_saida)
        df_saida = self._ordenar_validos_primeiro(df_saida)
        df_saida = self._mover_colunas_rastreio_para_final(df_saida)

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
            percentual_telefones_enriquecidos=percentual_telefones,
            percentual_emails_enriquecidos=percentual_emails,
        )

    def _arquivo_entrada_padrao(self) -> str:
        return (Path(self.paths.pasta_dados_processados) / "imobiliario.csv").as_posix()

    def _arquivo_integracao_padrao(self) -> str:
        if self.paths.existe(self.paths.arquivo_integracao_final):
            return self.paths.arquivo_integracao_final
        if self.paths.existe(self.paths.arquivo_integracao_parcial):
            return self.paths.arquivo_integracao_parcial
        return self.paths.arquivo_integracao_final

    def _enriquecer_contatos(self, df_imobiliario: pd.DataFrame, df_integracao: pd.DataFrame) -> tuple[int, int]:
        mapa = self._mapear_contatos_por_documento(df_integracao)
        telefones_por_linha = []
        emails_por_linha = []

        for _, linha in df_imobiliario.iterrows():
            chave = self._chave_documento_linha(linha)
            contatos = mapa.get(chave, {"telefone": [], "email": []})
            telefones = self._novos_contatos(contatos["telefone"], [linha.get(COLUNA_CELULAR, "")])
            emails = self._novos_contatos(contatos["email"], [linha.get(COLUNA_EMAIL, "")])
            telefones_por_linha.append(telefones)
            emails_por_linha.append(emails)

        self._criar_colunas_enriquecidas_rastreadas(
            df_imobiliario,
            PREFIXO_TELEFONE_ENRIQUECIDO,
            telefones_por_linha,
        )
        self._criar_colunas_enriquecidas_rastreadas(
            df_imobiliario,
            PREFIXO_EMAIL_ENRIQUECIDO,
            emails_por_linha,
        )

        linhas_com_telefone = sum(1 for valores in telefones_por_linha if valores)
        linhas_com_email = sum(1 for valores in emails_por_linha if valores)
        return linhas_com_telefone, linhas_com_email

    def _mapear_contatos_por_documento(self, df: pd.DataFrame) -> dict[str, dict[str, list[ContatoRastreado]]]:
        colunas_documento = self._colunas_documento_integracao(df)
        colunas_telefone = self._colunas_por_parametro(df, "telefone")
        colunas_email = self._colunas_por_parametro(df, "email")
        mapa: dict[str, dict[str, list[ContatoRastreado]]] = {}

        for _, linha in df.iterrows():
            chaves = self._chaves_documento_integracao(linha, colunas_documento)
            if not chaves:
                continue
            if self._revisao_pendente(linha):
                continue

            telefones = self._contatos_linha(linha, colunas_telefone)
            emails = self._contatos_linha(linha, colunas_email)
            for chave in chaves:
                destino = mapa.setdefault(chave, {"telefone": [], "email": []})
                destino["telefone"] = self._novos_contatos([*destino["telefone"], *telefones], [])
                destino["email"] = self._novos_contatos([*destino["email"], *emails], [])

        return mapa

    def _revisao_pendente(self, linha: pd.Series) -> bool:
        if not self._texto(linha.get(COLUNA_ID_REVISAO, "")):
            return False

        return not (
            self._texto(linha.get(COLUNA_USUARIO_REVISAO, ""))
            and self._texto(linha.get(COLUNA_DATA_REVISAO, ""))
        )

    def _colunas_documento_integracao(self, df: pd.DataFrame) -> list[str]:
        if COLUNA_MERGE_KEY in df.columns:
            return [COLUNA_MERGE_KEY]
        return []

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
                cpf = self._limpar_texto_documento(texto[4:])
                return f"CPF_{cpf}" if cpf else ""
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

    def _contatos_linha(self, linha: pd.Series, colunas: list[str]) -> list[ContatoRastreado]:
        contatos = []
        for coluna in colunas:
            for parte in str(linha.get(coluna, "")).split("|"):
                texto = self._texto(parte)
                if self._coluna_telefone(coluna) and not self._telefone_valido(texto):
                    continue
                if texto:
                    contatos.append(
                        ContatoRastreado(
                            valor=texto,
                            origem=str(coluna),
                            id_revisao=self._texto(linha.get(COLUNA_ID_REVISAO, "")),
                            usuario_revisao=self._texto(linha.get(COLUNA_USUARIO_REVISAO, "")),
                            data_revisao=self._texto(linha.get(COLUNA_DATA_REVISAO, "")),
                        )
                    )
        return self._novos_contatos(contatos, [])

    def _coluna_telefone(self, coluna: str) -> bool:
        parametro = next(item for item in PARAMETROS_COMPARACAO if item["nome"] == "telefone")
        return bool(re.search(parametro["padrao_colunas"], str(coluna), re.IGNORECASE))

    def _telefone_valido(self, valor) -> bool:
        texto = self._texto(valor)
        if not texto:
            return False

        digitos = re.sub(r"\D", "", texto)
        if digitos.startswith("55") and len(digitos) in {12, 13}:
            digitos = digitos[2:]

        return len(digitos) >= 8

    def _novos_contatos(
        self,
        candidatos: list[ContatoRastreado],
        existentes: list,
    ) -> list[ContatoRastreado]:
        vistos = set()
        contatos = []
        for valor in existentes:
            texto = self._texto(valor)
            if texto:
                vistos.add(self._chave_unicidade_contato(texto))
        for contato in candidatos:
            texto = self._texto(contato.valor)
            chave = self._chave_unicidade_contato(texto)
            if texto and chave not in vistos:
                contatos.append(contato)
                vistos.add(chave)
        return contatos

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

    def _criar_colunas_enriquecidas_rastreadas(
        self,
        df: pd.DataFrame,
        prefixo: str,
        contatos_por_linha: list[list[ContatoRastreado]],
    ) -> None:
        maximo = max((len(contatos) for contatos in contatos_por_linha), default=0)
        for posicao in range(maximo):
            coluna_base = f"{prefixo}{posicao + 1}"
            df[coluna_base] = [self._atributo_contato(contatos, posicao, "valor") for contatos in contatos_por_linha]
            df[f"{coluna_base}_origem"] = [
                self._atributo_contato(contatos, posicao, "origem")
                for contatos in contatos_por_linha
            ]
            df[f"{coluna_base}_id_revisao"] = [
                self._atributo_contato(contatos, posicao, "id_revisao")
                for contatos in contatos_por_linha
            ]
            df[f"{coluna_base}_usuario_revisao"] = [
                self._atributo_contato(contatos, posicao, "usuario_revisao")
                for contatos in contatos_por_linha
            ]
            df[f"{coluna_base}_data_revisao"] = [
                self._atributo_contato(contatos, posicao, "data_revisao")
                for contatos in contatos_por_linha
            ]

    def _atributo_contato(self, contatos: list[ContatoRastreado], posicao: int, atributo: str) -> str:
        if posicao >= len(contatos):
            return ""
        return self._texto(getattr(contatos[posicao], atributo))

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
            for coluna in [COLUNA_CPF, COLUNA_CNPJ, COLUNA_CPF_VALIDO, COLUNA_CNPJ_VALIDO, COLUNA_INSCRICAO]
            if coluna not in df.columns
        ]
        if ausentes:
            raise ValueError(f"Coluna(s) obrigatoria(s) ausente(s): {', '.join(ausentes)}.")

    def _chave_documento_linha(self, linha: pd.Series) -> str:
        cpf_valido = self._status_valido(linha.get(COLUNA_CPF_VALIDO, ""))
        cnpj_valido = self._status_valido(linha.get(COLUNA_CNPJ_VALIDO, ""))

        if cpf_valido:
            cpf = self._texto(linha.get(COLUNA_CPF, ""))
            if cpf:
                return f"CPF_{cpf}"

        if cnpj_valido:
            cnpj = self._normalizar_cnpj(linha.get(COLUNA_CNPJ, ""))
            if cnpj:
                return f"CNPJ_{cnpj}"

        return ""

    def _reidentificar_cpfs(self, df: pd.DataFrame, anonimizador: AnonimizadorReversivel) -> int:
        total = 0

        for indice, linha in df.iterrows():
            if not self._status_valido(linha.get(COLUNA_CPF_VALIDO, "")):
                continue

            documento = self._texto(linha.get(COLUNA_CPF, ""))
            if not documento:
                continue

            decriptografado = anonimizador.decrypt(documento)
            if decriptografado.startswith("[ERRO"):
                continue

            df.at[indice, COLUNA_CPF] = re.sub(r"\D", "", decriptografado) or decriptografado
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

    def _calcular_percentual_enriquecimento(self, adicionados: int, preenchidos_antes: int) -> float:
        if preenchidos_antes <= 0:
            return 0.0
        return round((adicionados / preenchidos_antes) * 100, 2)

    def _remover_colunas_saida(self, df: pd.DataFrame) -> None:
        if COLUNA_ENDERECO in df.columns:
            df.drop(columns=[COLUNA_ENDERECO], inplace=True)

    def _ordenar_validos_primeiro(self, df: pd.DataFrame) -> pd.DataFrame:
        if COLUNA_CPF_VALIDO not in df.columns or COLUNA_CNPJ_VALIDO not in df.columns:
            return df

        resultado = df.copy()
        resultado["_documento_valido_ordem"] = resultado.apply(
            lambda linha: 0
            if self._status_valido(linha.get(COLUNA_CPF_VALIDO, "")) or self._status_valido(linha.get(COLUNA_CNPJ_VALIDO, ""))
            else 1,
            axis=1,
        )
        resultado = resultado.sort_values("_documento_valido_ordem", kind="stable")
        return resultado.drop(columns=["_documento_valido_ordem"]).reset_index(drop=True)

    def _proteger_documento_saida(self, df: pd.DataFrame) -> None:
        for coluna in [COLUNA_CPF, COLUNA_CNPJ]:
            if coluna in df.columns:
                df[coluna] = df[coluna].apply(self._formatar_como_texto)

    def _mover_colunas_rastreio_para_final(self, df: pd.DataFrame) -> pd.DataFrame:
        sufixos_rastreio = (
            "_origem",
            "_id_revisao",
            "_usuario_revisao",
            "_data_revisao",
        )
        colunas_rastreio = [
            coluna
            for coluna in df.columns
            if (
                str(coluna).startswith(PREFIXO_TELEFONE_ENRIQUECIDO)
                or str(coluna).startswith(PREFIXO_EMAIL_ENRIQUECIDO)
            )
            and str(coluna).endswith(sufixos_rastreio)
        ]
        if not colunas_rastreio:
            return df

        colunas_base = [coluna for coluna in df.columns if coluna not in colunas_rastreio]
        return df[colunas_base + colunas_rastreio]

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
        f"{resultado.celulares_preenchidos} telefone(s) preenchido(s), "
        f"{resultado.emails_preenchidos} email(s) preenchido(s), "
        f"{resultado.telefones_enriquecidos} linha(s) com telefone enriquecido, "
        f"{resultado.percentual_telefones_enriquecidos:.2f}% de aumento por telefone, "
        f"{resultado.emails_enriquecidos} linha(s) com email enriquecido, "
        f"{resultado.percentual_emails_enriquecidos:.2f}% de aumento por email, "
        f"saida {resultado.saida}."
    )
    print(f"RESULTADO_MODULO_IV_JSON={json.dumps(asdict(resultado), ensure_ascii=False)}")


if __name__ in {"__main__", "__mp_main__"}:
    main()

import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

import pandas as pd

from src.moduloI.handlers.adapters.anomizador.anonimizador_reversivel_adaptado import AnonimizadorReversivel
from src.moduloI.usecase.leitor import ParameterReader
from src.moduloII.app_config import AppPaths


GRUPOS_COLUNAS = [
    ("cpf", ("cpf",)),
    ("cnpj", ("cnpj",)),
    ("nome", ("nome", "parceiro", "cliente", "individuo", "responsavel", "parceironegocios")),
    ("data_nascimento", ("datanascimento", "nascimento")),
    (
        "telefone",
        (
            "telefone",
            "telefones",
            "celular",
            "fone",
            "tel",
            "whatsapp",
            "zap",
            "contato",
            "contatotelefonico",
            "numerotelefone",
            "ddd",
        ),
    ),
    (
        "email",
        (
            "email",
            "mail",
            "correioeletronico",
            "enderecoeletronico",
            "contatoeletronico",
        ),
    ),
    ("cep", ("cep",)),
    ("numero", ("numero", "endereconumero")),
    ("endereco", ("endereco", "logradouro", "rua", "tipologradouro", "complemento")),
    ("bairro", ("bairro",)),
    ("cidade", ("cidade", "municipio", "localidade", "descricaolocalidade", "uf", "pais", "estado")),
    ("identificador_documento", ("rg", "cns", "nis", "pis", "tituloeleitor", "ctpsnumero", "ctpsserie")),
    ("cadastro_servico", ("inscricao", "instalacao", "medidor", "ligacao", "idimovel", "codfamiliar", "prontuario")),
]

GRUPOS_AGREGADOS = {"telefone", "email"}


@dataclass(frozen=True)
class ResultadoPreenchimentoImobiliario:
    cadastro_original: str
    base_integrada: str
    saida: str
    linhas_cadastro: int
    linhas_cruzadas: int
    celulas_preenchidas: int
    telefones_antes: int
    telefones_agora: int
    emails_antes: int
    emails_agora: int


class PreenchimentoImobiliarioService:
    def __init__(self, paths: AppPaths):
        self.paths = paths

    def preencher(
        self,
        chave: str,
        arquivo_cadastro: str | None = None,
        arquivo_integrado: str | None = None,
        arquivo_saida: str | None = None,
    ) -> ResultadoPreenchimentoImobiliario:
        if not chave:
            raise ValueError("Informe a chave usada na pseudonimização.")

        cadastro = arquivo_cadastro or self._arquivo_cadastro_padrao()
        integrado = arquivo_integrado or self._arquivo_integrado_padrao()
        saida = arquivo_saida or self.paths.arquivo_cadastro_imobiliario_preenchido

        if not cadastro:
            raise FileNotFoundError("Arquivo dados_processados/imobiliario.csv não encontrado.")
        if not integrado:
            raise FileNotFoundError("Nenhuma base final ou parcial foi encontrada para preenchimento.")

        caminho_cadastro = self.paths.resolver(cadastro)
        caminho_integrado = self.paths.resolver(integrado)
        if not caminho_cadastro.exists():
            raise FileNotFoundError(f"Arquivo do cadastro imobiliário não encontrado: {cadastro}.")
        if not caminho_integrado.exists():
            raise FileNotFoundError(f"Base integrada não encontrada: {integrado}.")

        os.environ["key"] = chave
        anonimizador = AnonimizadorReversivel()
        df_cadastro = pd.read_csv(caminho_cadastro, sep=";", encoding="utf-8-sig", dtype=str).fillna("")
        df_integrado = pd.read_csv(caminho_integrado, sep=";", encoding="utf-8-sig", dtype=str).fillna("")
        colunas_documento_cadastro = self._colunas_documento_cadastro(df_cadastro)

        chaves_cadastro = self._montar_chaves(
            df_cadastro,
            colunas_documento_cadastro,
            anonimizador,
        )
        chaves_integrado = self._montar_chaves(
            df_integrado,
            self._colunas_documento_integrado(df_integrado),
            anonimizador,
        )

        if not chaves_cadastro:
            raise ValueError("O TXT do imobiliário não indicou colunas de CPF/CNPJ com dados válidos.")
        if not chaves_integrado:
            raise ValueError("A base integrada não possui CPF/CNPJ pseudonimizado identificável.")

        mapa_destinos = self._mapear_colunas_existentes(df_cadastro.columns)
        telefones_antes = self._contar_linhas_preenchidas(df_cadastro, mapa_destinos.get("telefone", ""))
        emails_antes = self._contar_linhas_preenchidas(df_cadastro, mapa_destinos.get("email", ""))

        mapa_integrado = self._mapear_integrados(df_integrado, chaves_integrado)
        df_saida, linhas_cruzadas, celulas = self._preencher_apenas_colunas_existentes(
            df_cadastro,
            chaves_cadastro,
            mapa_integrado,
        )
        telefones_agora = self._contar_linhas_preenchidas(df_saida, mapa_destinos.get("telefone", ""))
        emails_agora = self._contar_linhas_preenchidas(df_saida, mapa_destinos.get("email", ""))
        self._reidentificar_documentos_imobiliario(df_saida, colunas_documento_cadastro, anonimizador)

        self.paths.garantir_pasta_arquivo(saida)
        df_saida.to_csv(self.paths.resolver(saida), sep=";", encoding="utf-8-sig", index=False)

        return ResultadoPreenchimentoImobiliario(
            cadastro_original=cadastro,
            base_integrada=integrado,
            saida=saida,
            linhas_cadastro=len(df_saida),
            linhas_cruzadas=linhas_cruzadas,
            celulas_preenchidas=celulas,
            telefones_antes=telefones_antes,
            telefones_agora=telefones_agora,
            emails_antes=emails_antes,
            emails_agora=emails_agora,
        )

    def _arquivo_cadastro_padrao(self) -> str:
        caminho = self.paths.resolver(self.paths.pasta_dados_processados) / "imobiliario.csv"
        if not caminho.exists():
            return ""
        return caminho.relative_to(self.paths.work_dir).as_posix()

    def _arquivo_integrado_padrao(self) -> str:
        if self.paths.existe(self.paths.arquivo_integracao_final):
            return self.paths.arquivo_integracao_final
        if self.paths.existe(self.paths.arquivo_integracao_parcial):
            return self.paths.arquivo_integracao_parcial
        return ""

    def _arquivo_parametros_imobiliario(self) -> Path:
        pasta = self.paths.resolver(self.paths.pasta_cadastro_imobiliario)
        if not pasta.is_dir():
            raise FileNotFoundError("Pasta imobiliario não encontrada na pasta de trabalho.")

        arquivos = sorted(arquivo for arquivo in pasta.iterdir() if arquivo.is_file() and arquivo.suffix.lower() == ".txt")
        if not arquivos:
            raise FileNotFoundError("Nenhum TXT de parâmetros foi encontrado na pasta imobiliario.")
        return arquivos[0]

    def _colunas_documento_cadastro(self, df: pd.DataFrame) -> list[tuple[str, str]]:
        parametros = ParameterReader(self._arquivo_parametros_imobiliario()).ler_arquivo()
        sufixo = parametros.sufixo[0] if parametros.sufixo else ""
        colunas = []

        for variavel in parametros.variaveis:
            for nome_amigavel, originais in variavel.items():
                texto = " ".join([str(nome_amigavel), *[str(original) for original in originais]]).lower()
                tipo = self._tipo_documento(texto)
                if not tipo:
                    continue

                candidatos = [str(nome_amigavel)]
                for coluna in originais:
                    candidatos.append(str(coluna))
                    if sufixo:
                        candidatos.append(f"{coluna}{sufixo}")

                for coluna in candidatos:
                    if coluna in df.columns and (coluna, tipo) not in colunas:
                        colunas.append((coluna, tipo))
        return colunas

    def _colunas_documento_integrado(self, df: pd.DataFrame) -> list[tuple[str, str]]:
        colunas = []
        for coluna in df.columns:
            nome = str(coluna).lower()
            if "valid" in nome:
                continue
            tipo = self._tipo_documento(nome)
            if tipo:
                colunas.append((coluna, tipo))
            elif nome == "merge_key":
                colunas.append((coluna, "MERGE"))
        return colunas

    def _tipo_documento(self, nome: str) -> str:
        if "cpf" in nome and "cnpj" in nome:
            return "DOC"
        if "cpf" in nome:
            return "CPF"
        if "cnpj" in nome:
            return "CNPJ"
        return ""

    def _montar_chaves(
        self,
        df: pd.DataFrame,
        colunas_documento: list[tuple[str, str]],
        anonimizador: AnonimizadorReversivel | None = None,
    ) -> dict[int, set[str]]:
        chaves = {}
        for indice, linha in df.iterrows():
            documentos = set()
            for coluna, tipo in colunas_documento:
                chave = self._normalizar_valor_documento(str(linha.get(coluna, "")).strip(), tipo, anonimizador)
                if chave:
                    documentos.add(chave)
            if documentos:
                chaves[indice] = documentos
        return chaves

    def _normalizar_valor_documento(
        self,
        valor: str,
        tipo: str,
        anonimizador: AnonimizadorReversivel | None = None,
    ) -> str:
        if tipo == "MERGE":
            return self._normalizar_chave_documento(valor, anonimizador)

        documento = self._normalizar_documento(valor, anonimizador)
        if not documento:
            return ""
        if tipo == "CPF" or (tipo == "DOC" and len(documento) == 11):
            return f"CPF_{documento}"
        if tipo == "CNPJ" or (tipo == "DOC" and len(documento) == 14):
            return f"CNPJ_{documento}"
        return ""

    def _normalizar_documento(self, valor: str, anonimizador: AnonimizadorReversivel | None = None) -> str:
        texto = str(valor).strip()
        if not texto or texto.lower() in {"nan", "none", "null"}:
            return ""
        if texto.startswith(("CPF_", "CNPJ_")):
            texto = texto.split("_", 1)[1]
        if anonimizador is not None:
            decriptografado = anonimizador.decrypt(texto)
            if not decriptografado.startswith("[ERRO"):
                texto = decriptografado
        return re.sub(r"\D", "", texto)

    def _reidentificar_documentos_imobiliario(
        self,
        df: pd.DataFrame,
        colunas_documento: list[tuple[str, str]],
        anonimizador: AnonimizadorReversivel,
    ) -> None:
        for coluna, tipo in colunas_documento:
            if coluna not in df.columns or tipo not in {"CPF", "CNPJ", "DOC"}:
                continue

            df[coluna] = df[coluna].apply(lambda valor: self._reidentificar_valor_documento(valor, anonimizador))

    def _reidentificar_valor_documento(self, valor: str, anonimizador: AnonimizadorReversivel) -> str:
        texto = str(valor).strip()
        if not texto or texto.lower() in {"nan", "none", "null"}:
            return ""

        partes = [parte.strip() for parte in texto.split(" | ") if parte.strip()]
        valores = []
        vistos = set()
        for parte in partes:
            reidentificado = self._reidentificar_parte_documento(parte, anonimizador)
            chave = re.sub(r"\D", "", reidentificado) or reidentificado
            if chave and chave not in vistos:
                valores.append(reidentificado)
                vistos.add(chave)
        return " | ".join(valores)

    def _reidentificar_parte_documento(self, valor: str, anonimizador: AnonimizadorReversivel) -> str:
        texto = str(valor).strip()
        candidato = texto
        if texto.startswith(("CPF_", "CNPJ_", "DOC_")):
            candidato = texto.split("_", 1)[1]

        decriptografado = anonimizador.decrypt(candidato)
        if not decriptografado.startswith("[ERRO"):
            documento = re.sub(r"\D", "", decriptografado)
            return documento or decriptografado.strip()

        if texto.startswith(("CPF_", "CNPJ_", "DOC_")):
            documento = re.sub(r"\D", "", candidato)
            return documento or candidato
        return texto

    def _normalizar_chave_documento(
        self,
        documento: str,
        anonimizador: AnonimizadorReversivel | None = None,
    ) -> str:
        texto = str(documento).strip()
        if not texto:
            return ""
        if texto.startswith("CPF_"):
            return f"CPF_{self._normalizar_documento(texto, anonimizador)}"
        if texto.startswith("CNPJ_"):
            return f"CNPJ_{self._normalizar_documento(texto, anonimizador)}"
        if texto.startswith("DOC_"):
            digitos = self._normalizar_documento(texto, anonimizador)
            if len(digitos) == 11:
                return f"CPF_{digitos}"
            if len(digitos) == 14:
                return f"CNPJ_{digitos}"
        if texto.startswith("MERGE_"):
            return self._normalizar_chave_documento(texto.split("_", 1)[1], anonimizador)
        return ""

    def _mapear_integrados(self, df: pd.DataFrame, chaves: dict[int, set[str]]) -> dict[str, dict[str, str]]:
        mapa = {}
        for indice, documentos in chaves.items():
            dados = {
                coluna: str(valor).strip()
                for coluna, valor in df.loc[indice].items()
                if str(valor).strip()
            }
            for documento in documentos:
                if documento and documento not in mapa:
                    mapa[documento] = dados
        return mapa

    def _preencher_apenas_colunas_existentes(
        self,
        df_cadastro: pd.DataFrame,
        chaves_cadastro: dict[int, set[str]],
        mapa_integrado: dict[str, dict[str, str]],
    ) -> tuple[pd.DataFrame, int, int]:
        df_saida = df_cadastro.copy()
        mapa_destinos = self._mapear_colunas_existentes(df_saida.columns)
        linhas_cruzadas = 0
        celulas_preenchidas = 0

        for indice, documentos in chaves_cadastro.items():
            enriquecido = self._primeiro_match(documentos, mapa_integrado)
            if not enriquecido:
                continue

            linhas_cruzadas += 1
            celulas_preenchidas += self._preencher_grupos_agregados(df_saida, indice, enriquecido, mapa_destinos)

            for coluna_origem, valor in enriquecido.items():
                if self._mapear_coluna(coluna_origem) in GRUPOS_AGREGADOS:
                    continue

                coluna_destino = self._coluna_existente_destino(coluna_origem, mapa_destinos)
                if not coluna_destino:
                    continue

                atual = str(df_saida.at[indice, coluna_destino]).strip()
                combinado = self._juntar_valores(atual, valor)
                if combinado != atual:
                    df_saida.at[indice, coluna_destino] = combinado
                    celulas_preenchidas += 1

        return df_saida, linhas_cruzadas, celulas_preenchidas

    def _preencher_grupos_agregados(
        self,
        df_saida: pd.DataFrame,
        indice: int,
        enriquecido: dict[str, str],
        mapa_destinos: dict[str, str],
    ) -> int:
        celulas_preenchidas = 0
        for grupo in GRUPOS_AGREGADOS:
            coluna_destino = mapa_destinos.get(grupo, "")
            if not coluna_destino:
                continue

            atual = str(df_saida.at[indice, coluna_destino]).strip()
            combinado = atual
            for coluna_origem, valor in enriquecido.items():
                if self._mapear_coluna(coluna_origem) == grupo:
                    combinado = self._juntar_valores(combinado, valor)

            if combinado != atual:
                df_saida.at[indice, coluna_destino] = combinado
                celulas_preenchidas += 1
        return celulas_preenchidas

    def _mapear_coluna(self, coluna: str) -> str:
        nome = self._normalizar_nome_coluna(coluna)
        for grupo, termos in GRUPOS_COLUNAS:
            if any(termo in nome for termo in termos):
                return grupo
        return ""

    def _mapear_colunas_existentes(self, colunas) -> dict[str, str]:
        destinos = {}
        for coluna in colunas:
            grupo = self._mapear_coluna(str(coluna))
            if grupo and grupo not in destinos:
                destinos[grupo] = coluna
        return destinos

    def _contar_linhas_preenchidas(self, df: pd.DataFrame, coluna: str) -> int:
        if not coluna or coluna not in df.columns:
            return 0

        valores = df[coluna].fillna("").astype(str).str.strip()
        return int((valores != "").sum())

    def _coluna_existente_destino(self, coluna_origem: str, destinos: dict[str, str]) -> str:
        grupo = self._mapear_coluna(coluna_origem)
        return destinos.get(grupo, "")

    def _normalizar_nome_coluna(self, coluna: str) -> str:
        texto = unicodedata.normalize("NFKD", str(coluna))
        texto = "".join(char for char in texto if not unicodedata.combining(char))
        texto = re.sub(r"([a-z])([A-Z])", r"\1 \2", texto)
        return re.sub(r"[^a-zA-Z0-9]+", " ", texto).replace(" ", "").lower()

    def _juntar_valores(self, atual: str, novo: str) -> str:
        novo = str(novo).strip()
        if not novo or novo.lower() in {"nan", "none", "null"}:
            return atual
        if not atual:
            return novo

        valores = [valor.strip() for valor in atual.split(" | ") if valor.strip()]
        if novo not in valores:
            valores.append(novo)
        return " | ".join(valores)

    def _primeiro_match(self, documentos: set[str], mapa_integrado: dict[str, dict[str, str]]) -> dict[str, str] | None:
        for documento in documentos:
            if documento in mapa_integrado:
                return mapa_integrado[documento]
        return None


def main():
    chave = os.environ.get("key") or os.environ.get("APP_CHAVE_PSEUDONIMIZACAO", "")
    resultado = PreenchimentoImobiliarioService(AppPaths()).preencher(chave)
    print(
        "Preenchimento imobiliário concluído: "
        f"{resultado.linhas_cruzadas} linha(s) cruzada(s), "
        f"{resultado.celulas_preenchidas} célula(s) preenchida(s), "
        f"saída {resultado.saida}."
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()

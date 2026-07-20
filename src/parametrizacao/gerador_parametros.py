import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.moduloII.app_config import AppPaths
from src.parametrizacao.regras_variaveis import sugerir_variavel


@dataclass
class ModeloParametros:
    sufixo: str = ""
    header: int = 0
    footer: int = 0
    formato: str = "csv"
    separador_csv: str = ""
    variaveis: list[tuple[str, list[str]]] = field(default_factory=list)


@dataclass(frozen=True)
class ResultadoGeracaoParametros:
    entrada: str
    saida: str
    gerados: int
    erros: list[str]
    arquivos: list[str]


class GeradorParametrosService:
    def __init__(self, paths: AppPaths):
        self.paths = paths

    def gerar(self) -> ResultadoGeracaoParametros:
        pasta_entrada = self.paths.resolver("parametros")
        pasta_saida = self.paths.resolver(Path(self.paths.pasta_gerados) / "parametros")
        arquivos_gerados = []
        fontes_geradas = 0
        erros = []

        if not pasta_entrada.is_dir():
            raise FileNotFoundError("Pasta parametros não encontrada na pasta de trabalho.")

        for pasta_fonte in sorted(pasta for pasta in pasta_entrada.iterdir() if pasta.is_dir()):
            try:
                arquivos_saida = self._gerar_para_fonte(pasta_fonte, pasta_saida)
                arquivos_gerados.extend(
                    arquivo.relative_to(self.paths.work_dir).as_posix()
                    for arquivo in arquivos_saida
                )
                fontes_geradas += 1
            except Exception as erro:
                erros.append(f"{pasta_fonte.name}: {erro}")

        if not arquivos_gerados and not erros:
            raise FileNotFoundError("Nenhuma subpasta foi encontrada dentro da pasta parametros.")

        return ResultadoGeracaoParametros(
            entrada=pasta_entrada.relative_to(self.paths.work_dir).as_posix(),
            saida=pasta_saida.relative_to(self.paths.work_dir).as_posix(),
            gerados=fontes_geradas,
            erros=erros,
            arquivos=arquivos_gerados,
        )

    def _gerar_para_fonte(self, pasta_fonte: Path, pasta_saida_raiz: Path) -> list[Path]:
        arquivo_modelo = self._encontrar_modelo(pasta_fonte)
        modelo = self._ler_modelo(arquivo_modelo)
        tabela = self._encontrar_tabela(pasta_fonte, modelo.formato)
        colunas = self._ler_colunas_tabela(tabela, modelo)
        prefixo = modelo.sufixo or pasta_fonte.name

        pasta_saida = pasta_saida_raiz / prefixo
        pasta_saida.mkdir(parents=True, exist_ok=True)
        arquivo_saida = pasta_saida / f"parametros_{self._nome_arquivo(prefixo)}.txt"
        tabela_saida = pasta_saida / tabela.name
        shutil.copy2(tabela, tabela_saida)
        arquivo_saida.write_text(self._renderizar(modelo, prefixo, colunas), encoding="utf-8")
        return [arquivo_saida, tabela_saida]

    def _encontrar_modelo(self, pasta_fonte: Path) -> Path:
        candidatos = sorted(pasta_fonte.glob("parametros_*.txt")) or sorted(pasta_fonte.glob("*.txt"))
        if not candidatos:
            raise FileNotFoundError("Nenhum TXT de parametros encontrado.")
        return candidatos[0]

    def _encontrar_tabela(self, pasta_fonte: Path, formato: str) -> Path:
        extensoes = [formato.lower()] if formato else ["csv", "xlsx", "xls"]
        if extensoes == ["xlsx"] or extensoes == ["xls"]:
            extensoes = ["xlsx", "xls"]

        for extensao in extensoes:
            candidatos = sorted(
                arquivo
                for arquivo in pasta_fonte.iterdir()
                if arquivo.is_file()
                and arquivo.suffix.lower() == f".{extensao}"
                and not arquivo.name.startswith("~")
            )
            if candidatos:
                return candidatos[0]

        raise FileNotFoundError("Nenhuma tabela correspondente ao formato do TXT foi encontrada.")

    def _ler_modelo(self, arquivo: Path) -> ModeloParametros:
        modelo = ModeloParametros()
        lendo_variaveis = False

        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            texto = linha.strip()
            if not texto:
                continue

            lower = texto.lower()
            if lower.startswith("variables:"):
                lendo_variaveis = True
                continue
            if lendo_variaveis and ":" in texto:
                chave, valor = texto.split(":", 1)
                campos = [item.strip() for item in valor.split(",") if item.strip()]
                modelo.variaveis.append((chave.strip(), campos))
                continue
            if lower.startswith("sufix:"):
                modelo.sufixo = texto.split(":", 1)[1].strip()
            elif lower.startswith("header#:"):
                modelo.header = int(texto.split(":", 1)[1].strip() or 0)
            elif lower.startswith("footer#:"):
                modelo.footer = int(texto.split(":", 1)[1].strip() or 0)
            elif lower.startswith("format:"):
                modelo.formato = texto.split(":", 1)[1].strip() or "csv"
            elif lower.startswith("csv separator:"):
                modelo.separador_csv = texto.split(":", 1)[1].strip()

        return modelo

    def _ler_colunas_tabela(self, tabela: Path, modelo: ModeloParametros) -> list[str]:
        if tabela.suffix.lower() == ".csv":
            sep = modelo.separador_csv or None
            df = pd.read_csv(tabela, sep=sep, header=modelo.header, encoding="utf-8-sig", nrows=0, engine="python")
        elif tabela.suffix.lower() == ".xlsx":
            df = pd.read_excel(tabela, header=modelo.header, nrows=0, engine="openpyxl")
        else:
            df = pd.read_excel(tabela, header=modelo.header, nrows=0)

        return [
            str(coluna).strip()
            for coluna in df.columns
            if self._coluna_valida(str(coluna))
        ]

    def _renderizar(self, modelo: ModeloParametros, prefixo: str, colunas: list[str]) -> str:
        linhas = [
            f"Sufix: {prefixo}",
            f"Header#: {modelo.header}",
            f"Footer#: {modelo.footer}",
            f"Format: {modelo.formato}",
            f"CSV separator: {modelo.separador_csv}",
            "Variables:",
        ]
        linhas.extend(self._renderizar_variavel(coluna) for coluna in colunas)
        return "\n".join(linhas) + "\n"

    def _renderizar_variavel(self, coluna: str) -> str:
        variavel = sugerir_variavel(coluna)
        if variavel:
            return f"{coluna}: {variavel}"
        return f"{coluna}:"

    def _nome_arquivo(self, prefixo: str) -> str:
        texto = unicodedata.normalize("NFKD", str(prefixo))
        texto = "".join(char for char in texto if not unicodedata.combining(char))
        texto = re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_").lower()
        return texto or "parametros"

    def _coluna_valida(self, coluna: str) -> bool:
        texto = coluna.strip().lower()
        return bool(texto) and not texto.startswith("unnamed") and texto not in {"nan", "none", "null"}

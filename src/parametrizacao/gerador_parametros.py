import re
import unicodedata
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from src.moduloII.app_config import AppPaths
from src.parametrizacao.detector_tabela import EstruturaTabela, detectar_estrutura_tabela
from src.parametrizacao.regras_variaveis import sugerir_variavel


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
        pasta_entrada = self.paths.work_dir
        arquivos_gerados = []
        fontes_geradas = 0
        erros = []

        if not pasta_entrada.is_dir():
            raise FileNotFoundError("Pasta de trabalho nao encontrada.")

        for pasta_fonte in sorted(pasta for pasta in pasta_entrada.iterdir() if pasta.is_dir()):
            if self._pasta_deve_ser_ignorada(pasta_fonte):
                continue

            try:
                arquivo_saida = self._gerar_para_fonte(pasta_fonte)
            except Exception as erro:
                erros.append(f"{pasta_fonte.name}: {erro}")
                continue

            if arquivo_saida is None:
                continue

            arquivos_gerados.append(arquivo_saida.relative_to(self.paths.work_dir).as_posix())
            fontes_geradas += 1

        return ResultadoGeracaoParametros(
            entrada=".",
            saida=".",
            gerados=fontes_geradas,
            erros=erros,
            arquivos=arquivos_gerados,
        )

    def _pasta_deve_ser_ignorada(self, pasta_fonte: Path) -> bool:
        pastas_sistema = {
            self.paths.pasta_gerados,
            self.paths.pasta_logs,
            self.paths.pasta_dados_processados,
            "parametros",
        }
        if pasta_fonte.name in pastas_sistema:
            return True
        return any(arquivo.is_file() and arquivo.suffix.lower() == ".txt" for arquivo in pasta_fonte.iterdir())

    def _gerar_para_fonte(self, pasta_fonte: Path) -> Path | None:
        tabela = self._encontrar_tabela(pasta_fonte)
        if tabela is None:
            return None

        estrutura = detectar_estrutura_tabela(tabela)
        prefixo = pasta_fonte.name
        arquivo_saida = pasta_fonte / f"parametros_{self._nome_arquivo(prefixo)}.txt"
        arquivo_saida.write_text(self._renderizar(prefixo, estrutura), encoding="utf-8")
        return arquivo_saida

    def _encontrar_tabela(self, pasta_fonte: Path) -> Path | None:
        for extensao in ["csv", "xlsx", "xls"]:
            candidatos = sorted(
                arquivo
                for arquivo in pasta_fonte.iterdir()
                if arquivo.is_file()
                and arquivo.suffix.lower() == f".{extensao}"
                and not arquivo.name.startswith("~")
            )
            if candidatos:
                return candidatos[0]
        return None

    def _renderizar(self, prefixo: str, estrutura: EstruturaTabela) -> str:
        linhas = []
        for linha in self._conteudo_template().splitlines():
            lower = linha.strip().lower()
            if lower.startswith("sufix:"):
                linhas.append(f"Sufix: {self._sufixo(prefixo)}")
            elif lower.startswith("header#:"):
                linhas.append(f"Header#: {estrutura.header}")
            elif lower.startswith("footer#:"):
                linhas.append(f"Footer#: {estrutura.footer}")
            elif lower.startswith("format:"):
                linhas.append(f"Format: {estrutura.formato}")
            elif lower.startswith("csv separator:"):
                linhas.append(f"CSV separator: {estrutura.separador_csv}")
            elif lower.startswith("variables:"):
                linhas.append("Variables:")
                linhas.extend(self._renderizar_variavel(coluna) for coluna in estrutura.colunas)
                break
            else:
                linhas.append(linha)
        return "\n".join(linhas) + "\n"

    def _conteudo_template(self) -> str:
        return resources.files("src.parametrizacao").joinpath("parametros.txt").read_text(encoding="utf-8")

    def _renderizar_variavel(self, coluna: str) -> str:
        variavel = sugerir_variavel(coluna)
        if variavel:
            return f"{coluna} : {variavel}"
        return f"{coluna} :"

    def _nome_arquivo(self, prefixo: str) -> str:
        texto = unicodedata.normalize("NFKD", str(prefixo))
        texto = "".join(char for char in texto if not unicodedata.combining(char))
        texto = re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_").lower()
        return texto or "parametros"

    def _sufixo(self, prefixo: str) -> str:
        texto = str(prefixo).strip()
        if not texto:
            return ""
        return texto[:1].upper() + texto[1:]

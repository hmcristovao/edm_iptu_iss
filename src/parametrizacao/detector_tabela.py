import csv
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


SEPARADORES_CSV = [";", ",", "\t", "|"]
TERMOS_CABECALHO = ("cpf", "cnpj", "nome", "email", "telefone", "celular", "inscricao")


@dataclass(frozen=True)
class EstruturaTabela:
    formato: str
    separador_csv: str
    header: int
    footer: int
    colunas: list[str]


def detectar_estrutura_tabela(tabela: Path) -> EstruturaTabela:
    formato = tabela.suffix.lower().lstrip(".")
    if formato == "csv":
        return _detectar_csv(tabela)
    if formato in {"xlsx", "xls"}:
        return _detectar_excel(tabela, formato)
    raise ValueError(f"Formato de tabela nao suportado: {tabela.suffix}.")


def _detectar_csv(tabela: Path) -> EstruturaTabela:
    linhas = tabela.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    separador = _detectar_separador(linhas)
    registros = list(csv.reader(linhas, delimiter=separador))
    header = _detectar_header(registros)
    footer = _detectar_footer(registros, header)
    colunas = _limpar_colunas(registros[header] if header < len(registros) else [])
    return EstruturaTabela("csv", separador, header, footer, colunas)


def _detectar_excel(tabela: Path, formato: str) -> EstruturaTabela:
    engine = "openpyxl" if formato == "xlsx" else None
    df = pd.read_excel(tabela, header=None, dtype=str, engine=engine).fillna("")
    registros = df.astype(str).values.tolist()
    header = _detectar_header(registros)
    footer = _detectar_footer(registros, header)
    colunas = _limpar_colunas(registros[header] if header < len(registros) else [])
    return EstruturaTabela(formato, "", header, footer, colunas)


def _detectar_separador(linhas: list[str]) -> str:
    amostra = [linha for linha in linhas[:30] if linha.strip()]
    melhor = ","
    melhor_pontuacao = -1
    for separador in SEPARADORES_CSV:
        pontuacao = 0
        for linha in amostra:
            colunas = next(csv.reader([linha], delimiter=separador))
            preenchidas = sum(1 for coluna in colunas if coluna.strip())
            if preenchidas > 1:
                pontuacao += preenchidas
        if pontuacao > melhor_pontuacao:
            melhor = separador
            melhor_pontuacao = pontuacao
    return melhor


def _detectar_header(registros: list[list[str]]) -> int:
    melhor_indice = 0
    melhor_pontuacao = -1
    for indice, registro in enumerate(registros[:50]):
        colunas = _limpar_colunas(registro)
        if not colunas:
            continue

        termos = " ".join(colunas).lower()
        pontuacao = len(colunas) * 3
        pontuacao += sum(4 for termo in TERMOS_CABECALHO if termo in termos)
        pontuacao -= sum(2 for coluna in colunas if coluna.replace(".", "", 1).isdigit())

        if pontuacao > melhor_pontuacao:
            melhor_indice = indice
            melhor_pontuacao = pontuacao
    return melhor_indice


def _detectar_footer(registros: list[list[str]], header: int) -> int:
    ultima_linha_dados = header
    largura_header = len(_limpar_colunas(registros[header] if header < len(registros) else []))

    for indice in range(header + 1, len(registros)):
        colunas = _limpar_colunas(registros[indice])
        if _linha_dados(colunas, largura_header):
            ultima_linha_dados = indice

    return max(0, len(registros) - ultima_linha_dados - 1)


def _linha_dados(colunas: list[str], largura_header: int) -> bool:
    if not colunas:
        return False
    if largura_header > 1 and len(colunas) < max(2, largura_header // 2):
        return False
    texto = " ".join(colunas).strip().lower()
    if texto.startswith(("fonte:", "total", "observacao", "observacao:", "relatorio")):
        return False
    return True


def _limpar_colunas(registro) -> list[str]:
    return [
        str(coluna).strip()
        for coluna in registro
        if str(coluna).strip() and str(coluna).strip().lower() not in {"nan", "none", "null"}
    ]

import re
import unicodedata


def sugerir_variavel(coluna: str) -> str:
    nome = str(coluna).strip()
    nome_normalizado = _normalizar_para_busca(nome)

    tem_cpf = "cpf" in nome_normalizado
    tem_cnpj = "cnpj" in nome_normalizado
    if tem_cpf and tem_cnpj:
        return "cpf, cpfValido, cnpj, cnpjValido"
    if tem_cpf:
        return "cpf, cpfValido"
    if tem_cnpj:
        return "cnpj, cnpjValido"
    if "email" in nome_normalizado:
        return "email"

    partes = _partes_coluna(nome)
    if "_" in nome and len(partes) >= 2:
        return _camel_case(partes)
    if len(partes) == 2:
        return _camel_case(partes)
    if len(partes) == 1:
        return partes[0].lower()
    return ""


def _normalizar_para_busca(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    return re.sub(r"[^a-zA-Z0-9]+", "", texto).lower()


def _partes_coluna(valor: str) -> list[str]:
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    return re.findall(r"[A-Za-z0-9]+", texto)


def _camel_case(partes: list[str]) -> str:
    primeira, *restantes = [parte.lower() for parte in partes]
    return primeira + "".join(parte[:1].upper() + parte[1:] for parte in restantes)

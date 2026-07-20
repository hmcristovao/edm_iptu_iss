import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.moduloII.app_config import AppPaths
from src.parametrizacao import GeradorParametrosService
from src.parametrizacao.regras_variaveis import sugerir_variavel


class GeradorParametrosServiceTest(unittest.TestCase):
    def test_regras_de_preenchimento_das_variaveis(self):
        casos = {
            "CPF/CNPJ": "cpf, cpfValido, cnpj, cnpjValido",
            "numero cpf": "cpf, cpfValido",
            "CNPJ Empresa": "cnpj, cnpjValido",
            "E-mail Principal": "email",
            "Nome Contribuinte": "nomeContribuinte",
            "inscricao_municipal": "inscricaoMunicipal",
            "endereço": "endereco",
            "Data de Nascimento": "",
        }

        for coluna, esperado in casos.items():
            with self.subTest(coluna=coluna):
                self.assertEqual(sugerir_variavel(coluna), esperado)

    def test_gera_txt_com_variaveis_sugeridas_apos_variables(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            entrada = raiz / "parametros" / "imobiliario"
            entrada.mkdir(parents=True)
            (entrada / "parametros_imobiliario.txt").write_text(
                "\n".join(
                    [
                        "Sufix: Imobiliario",
                        "Header#: 0",
                        "Footer#: 0",
                        "Format: csv",
                        "CSV separator: ;",
                        "Variables:",
                    ]
                ),
                encoding="utf-8",
            )
            pd.DataFrame(
                columns=[
                    "Nome Contribuinte",
                    "CPF/CNPJ",
                    "Inscricao Municipal",
                    "Data de Nascimento",
                ]
            ).to_csv(entrada / "cadastro.csv", sep=";", index=False, encoding="utf-8-sig")

            paths = AppPaths(work_dir=raiz)
            resultado = GeradorParametrosService(paths).gerar()

            saida = raiz / "arquivos_gerados" / "parametros" / "Imobiliario" / "parametros_imobiliario.txt"
            tabela_saida = raiz / "arquivos_gerados" / "parametros" / "Imobiliario" / "cadastro.csv"
            conteudo = saida.read_text(encoding="utf-8")
            tabela_copiada = tabela_saida.exists()

        self.assertEqual(resultado.gerados, 1)
        self.assertIn(
            (
                "Variables:\n"
                "Nome Contribuinte: nomeContribuinte\n"
                "CPF/CNPJ: cpf, cpfValido, cnpj, cnpjValido\n"
                "Inscricao Municipal: inscricaoMunicipal\n"
                "Data de Nascimento:"
            ),
            conteudo,
        )
        self.assertTrue(tabela_copiada)
        self.assertIn("arquivos_gerados/parametros/Imobiliario/cadastro.csv", resultado.arquivos)

    def test_usa_nome_da_pasta_quando_txt_nao_tem_sufixo(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            entrada = raiz / "parametros" / "saae"
            entrada.mkdir(parents=True)
            (entrada / "modelo.txt").write_text(
                "\n".join(
                    [
                        "Header#: 0",
                        "Footer#: 0",
                        "Format: csv",
                        "CSV separator: ;",
                        "Variables:",
                        "cliente: Cliente",
                    ]
                ),
                encoding="utf-8",
            )
            pd.DataFrame(columns=["Cliente"]).to_csv(entrada / "saae.csv", sep=";", index=False)

            paths = AppPaths(work_dir=raiz)
            GeradorParametrosService(paths).gerar()

            saida = raiz / "arquivos_gerados" / "parametros" / "saae" / "parametros_saae.txt"
            self.assertTrue(saida.exists())


if __name__ == "__main__":
    unittest.main()

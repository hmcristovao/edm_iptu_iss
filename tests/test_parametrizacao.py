import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.moduloII.app_config import AppPaths
from src.parametrizacao import GeradorParametrosService
from src.parametrizacao.detector_tabela import detectar_estrutura_tabela
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
            "endereco": "endereco",
            "Data de Nascimento": "",
        }

        for coluna, esperado in casos.items():
            with self.subTest(coluna=coluna):
                self.assertEqual(sugerir_variavel(coluna), esperado)

    def test_detecta_estrutura_de_csv_com_titulo_cabecalho_separador_e_rodape(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            tabela = raiz / "cadastro.csv"
            tabela.write_text(
                "\n".join(
                    [
                        "Relatorio de cadastro",
                        "Nome Contribuinte;CPF/CNPJ;Inscricao Municipal",
                        "Ana;52998224725;100",
                        "Bruno;04252011000110;200",
                        "",
                        "Fonte: sistema legado",
                    ]
                ),
                encoding="utf-8",
            )

            estrutura = detectar_estrutura_tabela(tabela)

        self.assertEqual(estrutura.formato, "csv")
        self.assertEqual(estrutura.separador_csv, ";")
        self.assertEqual(estrutura.header, 1)
        self.assertEqual(estrutura.footer, 2)
        self.assertEqual(estrutura.colunas, ["Nome Contribuinte", "CPF/CNPJ", "Inscricao Municipal"])

    def test_gera_txt_na_mesma_pasta_usando_template_e_ignora_pastas_com_txt(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            entrada = raiz / "imobiliario"
            entrada.mkdir()
            pd.DataFrame(
                columns=[
                    "Nome Contribuinte",
                    "CPF/CNPJ",
                    "Inscricao Municipal",
                    "Data de Nascimento",
                ]
            ).to_csv(entrada / "cadastro.csv", index=False, encoding="utf-8-sig")

            ignorada = raiz / "ja_parametrizada"
            ignorada.mkdir()
            (ignorada / "parametros_existente.txt").write_text("Variables:\n", encoding="utf-8")
            pd.DataFrame(columns=["Cliente"]).to_csv(ignorada / "clientes.csv", sep=";", index=False)

            paths = AppPaths(work_dir=raiz)
            resultado = GeradorParametrosService(paths).gerar()

            saida = entrada / "parametros_imobiliario.txt"
            conteudo = saida.read_text(encoding="utf-8")

        self.assertEqual(resultado.gerados, 1)
        self.assertEqual(resultado.entrada, ".")
        self.assertEqual(resultado.saida, ".")
        self.assertIn(
            (
                "Sufix: Imobiliario\n"
                "Header#: 0\n"
                "Footer#: 0\n"
                "Format: csv\n"
                "CSV separator: ,\n"
                "Variables:\n"
                "Nome Contribuinte : nomeContribuinte\n"
                "CPF/CNPJ : cpf, cpfValido, cnpj, cnpjValido\n"
                "Inscricao Municipal : inscricaoMunicipal\n"
                "Data de Nascimento :"
            ),
            conteudo,
        )
        self.assertIn("imobiliario/parametros_imobiliario.txt", resultado.arquivos)
        self.assertFalse((raiz / "ja_parametrizada" / "parametros_ja_parametrizada.txt").exists())


if __name__ == "__main__":
    unittest.main()

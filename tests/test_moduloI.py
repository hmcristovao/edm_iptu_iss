import os
import tempfile
import unittest
from pathlib import Path

from src.moduloI.handlers.adapters.anomizador.anonimizador_reversivel_adaptado import AnonimizadorReversivel
from src.moduloI.usecase.leitor import ParameterReader


class ParameterReaderTest(unittest.TestCase):
    def test_le_arquivo_de_parametros_com_variaveis_e_metadados(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            pasta_fonte = raiz / "fonte"
            pasta_fonte.mkdir()
            arquivo = pasta_fonte / "parametros.txt"
            arquivo.write_text(
                "\n".join(
                    [
                        "CSV separator: ;",
                        "Format: csv",
                        "Header#: 2",
                        "Footer#: 1",
                        "Sufix: Imobiliario",
                        "Variables:",
                        "nomeContribuinte: nome, nome_social",
                        "cpfCnpj: cpf, cnpj",
                    ]
                ),
                encoding="utf-8",
            )

            antigo_data_path = os.environ.get("DATA_PATH")
            os.environ["DATA_PATH"] = str(raiz / "trabalho")
            try:
                parametros = ParameterReader(arquivo).ler_arquivo()
            finally:
                if antigo_data_path is None:
                    os.environ.pop("DATA_PATH", None)
                else:
                    os.environ["DATA_PATH"] = antigo_data_path

        self.assertEqual(parametros.pasta, str(pasta_fonte.resolve()))
        self.assertEqual(parametros.saida, str((raiz / "dados_processados").resolve()))
        self.assertEqual(parametros.sep, ";")
        self.assertEqual(parametros.formato, "csv")
        self.assertEqual(parametros.header, 2)
        self.assertEqual(parametros.footer, 1)
        self.assertEqual(parametros.sufixo, ["Imobiliario"])
        self.assertEqual(
            parametros.variaveis,
            [
                {"nomeContribuinte": ["nome", "nome_social"]},
                {"cpfCnpj": ["cpf", "cnpj"]},
            ],
        )


class AnonimizadorReversivelTest(unittest.TestCase):
    def test_mesmo_texto_gera_mesmo_pseudonimo_com_mesma_chave(self):
        chave_antiga = os.environ.get("key")
        os.environ["key"] = "chave-de-teste"
        try:
            anonimizador = AnonimizadorReversivel()
            primeiro = anonimizador.encrypt("12345678901")
            segundo = anonimizador.encrypt("12345678901")
            outro = anonimizador.encrypt("98765432100")
        finally:
            if chave_antiga is None:
                os.environ.pop("key", None)
            else:
                os.environ["key"] = chave_antiga

        self.assertEqual(primeiro, segundo)
        self.assertNotEqual(primeiro, outro)
        self.assertEqual(anonimizador.decrypt(primeiro), "12345678901")


if __name__ == "__main__":
    unittest.main()

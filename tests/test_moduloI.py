import os
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.moduloI.Domain.Package import Package
from src.moduloI.Domain.Parameters import Parameters
from src.moduloI.handlers.adapters.anomizador.anonimizador_reversivel_adaptado import AnonimizadorReversivel
from src.moduloI.handlers.export_handler import ExportHandler
from src.moduloI.handlers.standardization_handler import StandardizationHandler
from src.moduloI.handlers.ultis.MultivariablesHander import MultivariablesHanderBuilder
from src.moduloI.services import ProcessamentoLegadoService
from src.moduloI.usecase.leitor import ParameterReader
from src.moduloII.app_config import AppPaths


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
                        "observacao :",
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
                {"observacao": []},
            ],
        )


class ProcessamentoLegadoServiceTest(unittest.TestCase):
    def test_lista_parametros_ignora_pastas_do_parametrizador(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            entrada = raiz / "fonte"
            entrada.mkdir()
            parametros_entrada = entrada / "parametros_fonte.txt"
            parametros_entrada.write_text("Variables:\n", encoding="utf-8")

            parametros_modelo = raiz / "parametros" / "Fonte"
            parametros_modelo.mkdir(parents=True)
            (parametros_modelo / "parametros_fonte.txt").write_text("Variables:\n", encoding="utf-8")

            parametros_gerados = raiz / "arquivos_gerados" / "parametros" / "Fonte"
            parametros_gerados.mkdir(parents=True)
            (parametros_gerados / "parametros_fonte.txt").write_text("Variables:\n", encoding="utf-8")

            arquivos = ProcessamentoLegadoService(AppPaths(work_dir=raiz)).listar_parametros()

        self.assertEqual(arquivos, [parametros_entrada])


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


class MultivariablesHanderBuilderTest(unittest.TestCase):
    def test_campo_cpfcnpj_preserva_cnpj_valido(self):
        df = pd.DataFrame({"documento": ["04.252.011/0001-10", "529.982.247-25", "111"]})
        builder = MultivariablesHanderBuilder()

        builder.build(df, "documento", "cpfCnpjFonte")
        builder.build(df, "documento", "cpfCnpjValidoFonte")

        self.assertEqual(df["cpfCnpjFonte"].tolist(), ["04252011000110", "52998224725", ""])
        self.assertEqual(df["cpfCnpjValidoFonte"].tolist(), ["S", "S", "N"])


class StandardizationHandlerTest(unittest.TestCase):
    def test_remove_colunas_que_nao_estao_no_txt_de_parametros(self):
        parametros = Parameters(
            pasta=".",
            sep=";",
            footer=0,
            header=0,
            formato="csv",
            saida=".",
            sufixo=["Fonte"],
            variaveis=[
                {"Nome": ["nome"]},
                {"CPF/CNPJ": ["cpf", "cpfValido", "cnpj", "cnpjValido"]},
            ],
        )
        dados = pd.DataFrame(
            {
                "Nome": ["Ana"],
                "CPF/CNPJ": ["529.982.247-25"],
                "Coluna Apagada Do TXT": ["nao deve sair"],
            }
        )

        resultado = StandardizationHandler()._renomear_colunas_mapeadas(
            dados,
            parametros.variaveis,
            parametros.sufixo,
        )

        self.assertEqual(
            resultado.columns.tolist(),
            ["nomeFonte", "cpfFonte", "cpfValidoFonte", "cnpjFonte", "cnpjValidoFonte"],
        )
        self.assertNotIn("Coluna Apagada Do TXT", resultado.columns)


class ExportHandlerTest(unittest.TestCase):
    def test_exporta_cpf_e_cnpj_como_texto_no_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            parametros = Parameters(
                pasta=tmp,
                sep=";",
                footer=0,
                header=0,
                formato="csv",
                saida=tmp,
                sufixo=["Fonte"],
                variaveis=[],
            )
            dados = pd.DataFrame(
                {
                    "cpfFonte": ["00147611733"],
                    "cnpjFonte": ["04252011000110"],
                    "cpfCnpjFonte": ["52998224725"],
                    "cpfValidoFonte": ["S"],
                    "cnpjValidoFonte": ["S"],
                    "nomeFonte": ["Empresa"],
                }
            )

            ExportHandler().handle(Package(parametros, dados))

            conteudo = (Path(tmp) / "Fonte.csv").read_text(encoding="utf-8-sig")

        self.assertIn("\t00147611733", conteudo)
        self.assertIn("\t04252011000110", conteudo)
        self.assertIn("\t52998224725", conteudo)
        self.assertIn(";S;", conteudo)


if __name__ == "__main__":
    unittest.main()

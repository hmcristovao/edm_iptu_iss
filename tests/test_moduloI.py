import os
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.moduloI.Domain.Package import Package
from src.moduloI.Domain.Parameters import Parameters
from src.moduloI.handlers.adapters.anomizador.anonimizador_reversivel_adaptado import AnonimizadorReversivel
from src.moduloI.handlers.extractor_handler import ExtractorHandler
from src.moduloI.handlers.export_handler import ExportHandler
from src.moduloI.handlers.Pseudonymization_handler import PseudonymizationHandler
from src.moduloI.handlers.standardization_handler import StandardizationHandler
from src.moduloI.handlers.ultis.MultivariablesHander import MultivariablesHanderBuilder
from src.moduloI.services import ProcessamentoLegadoService
from src.moduloI.usecase.leitor import ParameterReader
from src.moduloII.app_config import AppPaths


class FakeAnonimizador:
    def encrypt(self, text: str) -> str:
        return f"enc({text})"


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


class ExtractorHandlerTest(unittest.TestCase):
    def test_extrai_csv_com_header_footer_e_tudo_como_texto(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            (pasta / "entrada.csv").write_text(
                "\n".join(
                    [
                        "linha ignorada",
                        "Nome;CPF;Observacao",
                        "Ana;00147611733;",
                        "Rodape;999;fim",
                    ]
                ),
                encoding="utf-8",
            )
            parametros = Parameters(
                pasta=str(pasta),
                sep=";",
                footer=1,
                header=1,
                formato="csv",
                saida=str(pasta),
                sufixo=["Fonte"],
            )

            resultado = ExtractorHandler()._carregarUnirXlsx(parametros)

        self.assertEqual(resultado.to_dict("records"), [{"Nome": "Ana", "CPF": "00147611733", "Observacao": ""}])
        self.assertEqual(resultado["CPF"].iloc[0], "00147611733")

    def test_handle_rejeita_formato_nao_tratado(self):
        parametros = Parameters(
            pasta=".",
            sep=";",
            footer=0,
            header=0,
            formato="json",
            saida=".",
            sufixo=["Fonte"],
        )

        with self.assertRaises(Exception) as contexto:
            ExtractorHandler().handle(Package(parametros))

        self.assertIn("Formato", str(contexto.exception))


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

    def test_processamento_ignora_colunas_removidas_do_txt_no_csv_final(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            fonte = raiz / "fonte"
            fonte.mkdir()
            (fonte / "parametros_fonte.txt").write_text(
                "\n".join(
                    [
                        "CSV separator: ;",
                        "Format: csv",
                        "Header#: 0",
                        "Footer#: 0",
                        "Sufix: Fonte",
                        "Variables:",
                        "Nome : nome",
                        "CPF/CNPJ : cpf, cpfValido, cnpj, cnpjValido",
                        "Telefone Removido :",
                    ]
                ),
                encoding="utf-8",
            )
            pd.DataFrame(
                {
                    "Nome": ["Ana"],
                    "CPF/CNPJ": ["529.982.247-25"],
                    "Telefone Removido": ["81999990000"],
                    "Email Removido": ["ana@exemplo.com"],
                }
            ).to_csv(fonte / "dados.csv", sep=";", index=False, encoding="utf-8-sig")

            resultado = ProcessamentoLegadoService(AppPaths(work_dir=raiz)).executar(
                "chave-de-teste",
                lambda _: None,
            )
            saida = pd.read_csv(raiz / "dados_processados" / "Fonte.csv", sep=";", dtype=str).fillna("")

        self.assertEqual(resultado["csvs_exportados"], 1)
        self.assertEqual(
            saida.columns.tolist(),
            ["nomeFonte", "cpfFonte", "cpfValidoFonte", "cnpjFonte", "cnpjValidoFonte"],
        )
        self.assertNotIn("Telefone Removido", saida.columns)
        self.assertNotIn("Email Removido", saida.columns)

    def test_processamento_nao_carrega_parametros_de_subpastas_geradas(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            fonte = raiz / "fonte"
            fonte.mkdir()
            (fonte / "parametros_fonte.txt").write_text(
                "\n".join(
                    [
                        "CSV separator: ;",
                        "Format: csv",
                        "Header#: 0",
                        "Footer#: 0",
                        "Sufix: Fonte",
                        "Variables:",
                        "Nome : nome",
                    ]
                ),
                encoding="utf-8",
            )
            pd.DataFrame({"Nome": ["Ana"]}).to_csv(fonte / "dados.csv", sep=";", index=False, encoding="utf-8-sig")

            pasta_ignorada = raiz / "arquivos_gerados" / "parametros" / "Outra"
            pasta_ignorada.mkdir(parents=True)
            (pasta_ignorada / "parametros_outra.txt").write_text(
                "CSV separator: ;\nFormat: csv\nHeader#: 0\nFooter#: 0\nSufix: Outra\nVariables:\nCampo : campo\n",
                encoding="utf-8",
            )
            pd.DataFrame({"Campo": ["Nao deve processar"]}).to_csv(
                pasta_ignorada / "dados.csv",
                sep=";",
                index=False,
                encoding="utf-8-sig",
            )

            resultado = ProcessamentoLegadoService(AppPaths(work_dir=raiz)).executar("chave-de-teste", lambda _: None)

            self.assertEqual(resultado["csvs_exportados"], 1)
            self.assertTrue((raiz / "dados_processados" / "Fonte.csv").exists())
            self.assertFalse((raiz / "dados_processados" / "Outra.csv").exists())


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

    def test_separa_cpf_e_cnpj_sem_perder_zeros_a_esquerda(self):
        df = pd.DataFrame({"documento": ["001.476.117-33", "04.252.011/0001-10", "147611733"]})
        builder = MultivariablesHanderBuilder()

        builder.build(df, "documento", "cpfFonte")
        builder.build(df, "documento", "cpfValidoFonte")
        builder.build(df, "documento", "cnpjFonte")
        builder.build(df, "documento", "cnpjValidoFonte")

        self.assertEqual(df["cpfFonte"].tolist(), ["00147611733", "", ""])
        self.assertEqual(df["cpfValidoFonte"].tolist(), ["S", "N", "N"])
        self.assertEqual(df["cnpjFonte"].tolist(), ["", "04252011000110", ""])
        self.assertEqual(df["cnpjValidoFonte"].tolist(), ["N", "S", "N"])


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
                {"Coluna Apagada Do TXT": []},
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

    def test_nao_mantem_colunas_originais_apos_renomear(self):
        parametros = Parameters(
            pasta=".",
            sep=";",
            footer=0,
            header=0,
            formato="csv",
            saida=".",
            sufixo=["Fonte"],
            variaveis=[{"Telefone": ["telefone"]}, {"Email": ["email"]}],
        )
        dados = pd.DataFrame({"Telefone": ["81999990000"], "Email": ["ana@exemplo.com"]})

        resultado = StandardizationHandler()._renomear_colunas_mapeadas(
            dados,
            parametros.variaveis,
            parametros.sufixo,
        )

        self.assertEqual(resultado.columns.tolist(), ["telefoneFonte", "emailFonte"])
        self.assertNotIn("Telefone", resultado.columns)
        self.assertNotIn("Email", resultado.columns)


class PseudonymizationHandlerTest(unittest.TestCase):
    def test_anonimiza_apenas_cpf_valido_e_preserva_cnpj(self):
        parametros = Parameters(
            pasta=".",
            sep=";",
            footer=0,
            header=0,
            formato="csv",
            saida=".",
            sufixo=["Fonte"],
        )
        dados = pd.DataFrame(
            {
                "cpfFonte": ["00147611733", "147611733"],
                "cpfValidoFonte": ["S", "N"],
                "cnpjFonte": ["04252011000110", ""],
                "cnpjValidoFonte": ["S", "N"],
            }
        )

        pacote = Package(parametros, dados)
        PseudonymizationHandler(FakeAnonimizador()).handle(pacote)

        self.assertEqual(pacote.datas["cpfFonte"].tolist(), ["enc(00147611733)", "147611733"])
        self.assertEqual(pacote.datas["cnpjFonte"].tolist(), ["04252011000110", ""])


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

    def test_nao_exporta_dataframe_vazio(self):
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
            pacote = Package(parametros, pd.DataFrame())

            ExportHandler().handle(pacote)

            self.assertFalse(pacote.exported)
            self.assertFalse((Path(tmp) / "Fonte.csv").exists())


if __name__ == "__main__":
    unittest.main()

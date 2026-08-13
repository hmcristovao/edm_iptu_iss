import unittest
import os
from contextlib import redirect_stderr
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from src.views.app_nicegui import IntegracaoEnriquecimentoApp


class IntegracaoEnriquecimentoAppTest(unittest.TestCase):
    def test_parametrizacao_exige_pasta_de_trabalho_selecionada(self):
        app = IntegracaoEnriquecimentoApp()
        app.state.autenticado = True
        app.state.rodando = False

        self.assertFalse(app._pode_gerar_parametros())

        app.state.pasta_trabalho_selecionada = True

        self.assertTrue(app._pode_gerar_parametros())

    def test_executar_ui_ignora_slot_deletado_do_nicegui(self):
        app = IntegracaoEnriquecimentoApp()

        resultado = app._executar_ui(
            lambda: (_ for _ in ()).throw(RuntimeError("The parent element this slot belongs to has been deleted."))
        )

        self.assertFalse(resultado)

    def test_executar_ui_ignora_slot_vazio_de_background_task(self):
        app = IntegracaoEnriquecimentoApp()

        resultado = app._executar_ui(
            lambda: (_ for _ in ()).throw(
                RuntimeError("The current slot cannot be determined because the slot stack for this task is empty.")
            )
        )

        self.assertFalse(resultado)

    def test_executar_ui_propaga_erros_runtime_diferentes(self):
        app = IntegracaoEnriquecimentoApp()

        with self.assertRaisesRegex(RuntimeError, "erro real"):
            app._executar_ui(lambda: (_ for _ in ()).throw(RuntimeError("erro real")))

    def test_tabela_revisao_usa_paginacao_real(self):
        app = IntegracaoEnriquecimentoApp()

        self.assertEqual(app._paginacao_tabela_revisao(), {"rowsPerPage": 20})

    def test_conta_pendentes_considera_grupos_ainda_nao_carregados(self):
        app = IntegracaoEnriquecimentoApp()
        app.state.total_grupos_revisao = 3
        app.state.pares = [
            {"par_id": "G1:0:1", "id_revisao": "G1"},
            {"par_id": "G2:2:3", "id_revisao": "G2"},
        ]
        app.state.decisoes = {
            "G1:0:1": {"decisao": "aprovar"},
            "G2:2:3": {"decisao": "rejeitar"},
        }

        self.assertEqual(app._contar_pares_pendentes(), 1)

    def test_estende_pares_sem_duplicar(self):
        app = IntegracaoEnriquecimentoApp()
        app.state.pares = [{"par_id": "G1:0:1", "id_revisao": "G1"}]

        app._adicionar_pares_revisao(
            [
                {"par_id": "G1:0:1", "id_revisao": "G1"},
                {"par_id": "G2:2:3", "id_revisao": "G2"},
            ]
        )

        self.assertEqual([par["par_id"] for par in app.state.pares], ["G1:0:1", "G2:2:3"])

    def test_imprime_erro_modulo_iv_no_terminal(self):
        app = IntegracaoEnriquecimentoApp()
        saida = StringIO()

        with redirect_stderr(saida):
            app._imprimir_erro_modulo_iv("traceback do modulo iv")

        self.assertIn("Erro ao gerar a base imobiliaria", saida.getvalue())
        self.assertIn("traceback do modulo iv", saida.getvalue())

    def test_mensagem_erro_modulo_iv_exibe_value_error(self):
        app = IntegracaoEnriquecimentoApp()
        erro = (
            "ValueError: Coluna(s) obrigatoria(s) ausente(s): "
            "cpfImobiliario, cnpjImobiliario."
        )

        mensagem = app._mensagem_erro_modulo_iv(erro)

        self.assertEqual(
            mensagem,
            "ERRO: Coluna(s) obrigatoria(s) ausente(s): cpfImobiliario, cnpjImobiliario.",
        )


class IntegracaoEnriquecimentoAppAsyncTest(unittest.IsolatedAsyncioTestCase):
    async def test_arquivo_revisado_roda_em_subprocesso_pelo_pipeline_runner(self):
        app = IntegracaoEnriquecimentoApp()
        chamadas = {}

        class FakePipelineRunner:
            async def executar(self, script, ao_progredir):
                chamadas["script"] = script
                ao_progredir(
                    'RESULTADO_ARQUIVO_REVISADO_JSON={"saida": "arquivos_gerados/integracao_parcial.csv"}'
                )
                return 0

        app.state.df = object()
        app.state.decisoes = {"G1:0:1": {"decisao": "aprovar"}}
        app.pipeline_runner = FakePipelineRunner()
        app.revisao_service.carregar_dados = lambda: (_ for _ in ()).throw(
            AssertionError("nao deve carregar o CSV completo no processo da interface")
        )
        app._definir_arquivo_etapa3_saida = lambda: "arquivos_gerados/integracao_parcial.csv"
        app._remover_arquivo_se_existir = lambda arquivo: chamadas.setdefault("removido", arquivo)
        app._abrir_loading = lambda *args: None
        app._atualizar_loading = lambda *args: None
        app._fechar_bloqueio = lambda: None
        app._atualizar_botoes = lambda: None
        app.download_revisado_label = SimpleNamespace(set_text=lambda texto: chamadas.setdefault("label", texto))
        app.dialog_download_revisado = SimpleNamespace(open=lambda: chamadas.setdefault("dialog", True))

        with patch("src.views.app_nicegui.ui.notify"):
            await app.gerar_arquivo_revisado()

        self.assertEqual(chamadas["script"], os.path.join("..", "moduloII", "gerar_revisado.py"))
        self.assertEqual(app.state.arquivo_revisao_atual, "arquivos_gerados/integracao_parcial.csv")

    async def test_reidentificacao_roda_em_subprocesso_pelo_pipeline_runner(self):
        app = IntegracaoEnriquecimentoApp()
        chamadas = {}

        class FakePipelineRunner:
            async def executar(self, script, ao_progredir):
                chamadas["script"] = script
                ao_progredir(
                    'RESULTADO_REIDENTIFICACAO_JSON={"valores_reidentificados": 7, "saida": "arquivos_gerados/integracao_reidentificada.csv"}'
                )
                return 0

        app.chave_legado_input = SimpleNamespace(value="12345678")
        app.pipeline_runner = FakePipelineRunner()
        app.reidentificacao_service.reidentificar = lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("nao deve rodar no processo da interface")
        )
        app._arquivo_revisao_existente = lambda: "arquivos_gerados/integracao_parcial.csv"
        app._abrir_loading = lambda *args: None
        app._atualizar_loading = lambda *args: None
        app._fechar_bloqueio = lambda: None
        app._atualizar_botoes = lambda: None

        with patch("src.views.app_nicegui.ui.notify"), patch("src.views.app_nicegui.ui.download") as download:
            await app.reidentificar_base()

        self.assertEqual(chamadas["script"], os.path.join("..", "moduloIII", "reassociacao.py"))
        download.assert_called_once()


if __name__ == "__main__":
    unittest.main()

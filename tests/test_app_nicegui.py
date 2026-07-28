import unittest

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


if __name__ == "__main__":
    unittest.main()

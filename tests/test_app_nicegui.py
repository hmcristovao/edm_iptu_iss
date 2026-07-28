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


if __name__ == "__main__":
    unittest.main()

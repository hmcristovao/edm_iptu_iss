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


if __name__ == "__main__":
    unittest.main()

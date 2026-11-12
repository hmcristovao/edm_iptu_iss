import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pandas as pd
from nicegui import ui

from src.views.app_nicegui import IntegracaoEnriquecimentoApp


class ExecutionPopupsTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = IntegracaoEnriquecimentoApp()
        self.app.paths.definir_pasta_trabalho(self.temp.name)
        self.app.state.autenticado = True
        self.app.state.pasta_trabalho_selecionada = True
        self.root = ui.column()
        self.addCleanup(self.root.delete)
        with self.root:
            self.app._montar_dialogos()
            self.app._montar_layout()
        for target in ["src.views.app_nicegui.ui.notify", "src.views.app_nicegui.ui.download",
                       "src.views.workflow.ui.run_javascript", "src.views.workflow.ui.timer"]:
            mock = patch(target)
            mock.start()
            self.addCleanup(mock.stop)

    def criar(self, arquivo):
        caminho = self.app.paths.resolver(arquivo)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.touch()

    async def executar_preparacao(self, codigo=0, erro=None):
        self.app.workflow.exibir("preparacao")

        async def executar(script, progresso):
            self.assertFalse(self.app.botao_fechar_loading.enabled)
            self.app._fechar_popup(self.app.bloqueio)
            self.assertTrue(self.app.bloqueio.value)
            progresso("Mensagem da etapa")
            if erro:
                raise erro
            self.criar(self.app.paths.arquivo_preparacao)
            return codigo

        self.app.pipeline_runner.executar = executar
        with self.root:
            await self.app.executar_script_com_progresso(1, "preparacao.py")

    async def test_preparacao_aguarda_fechar_para_avancar(self):
        await self.executar_preparacao()
        self.assertTrue(self.app.bloqueio.value)
        self.assertTrue(self.app.botao_fechar_loading.enabled)
        self.assertEqual(self.app.workflow.pagina_atual, "preparacao")
        self.app._fechar_popup(self.app.bloqueio)
        self.assertFalse(self.app.bloqueio.value)
        self.assertEqual(self.app.workflow.pagina_atual, "enriquecimento")

    async def test_erro_nao_avanca_mesmo_com_arquivo_antigo(self):
        for erro in [None, ValueError("Falha de teste")]:
            with self.subTest(erro=erro):
                await self.executar_preparacao(codigo=1, erro=erro)
                self.assertTrue(self.app.bloqueio.value)
                self.assertTrue(self.app.botao_fechar_loading.enabled)
                self.assertFalse(self.app.state.rodando)
                self.app._fechar_popup(self.app.bloqueio)
                self.assertEqual(self.app.workflow.pagina_atual, "preparacao")

    async def test_enriquecimento_mostra_um_resultado_e_avanca_ao_fechar(self):
        self.criar(self.app.paths.arquivo_preparacao)
        self.app.workflow.exibir("enriquecimento")

        async def executar(script, progresso):
            self.criar(self.app.paths.arquivo_enriquecimento)
            return 0

        self.app.pipeline_runner.executar = executar
        with self.root:
            await self.app.executar_script_com_progresso(2, "enriquecimento.py")
        self.assertFalse(self.app.bloqueio.value)
        self.assertTrue(self.app.dialog_resultado_enriquecimento.value)
        self.assertEqual(self.app.workflow.pagina_atual, "enriquecimento")
        self.app._fechar_popup(self.app.dialog_resultado_enriquecimento)
        self.assertEqual(self.app.workflow.pagina_atual, "revisao")

    async def test_carregar_revisao_fecha_espera_sem_notificacao_nem_avanco(self):
        self.criar(self.app.paths.arquivo_enriquecimento)
        self.app.workflow.exibir("revisao")
        self.app.preparar_revisao = lambda: (pd.DataFrame(), [], {}, 0, 0, 0, pd.DataFrame())
        self.app._agendar_desenho_revisao = lambda: None
        with self.root, patch("src.views.app_nicegui.ui.notify") as notificar:
            await self.app.iniciar_revisao()
        notificar.assert_not_called()
        self.assertFalse(self.app.bloqueio.value)
        self.assertTrue(self.app.state.etapa3_ativa)
        self.assertEqual(self.app.workflow.pagina_atual, "revisao")

    async def test_reidentificacao_mantem_resultado_aberto_sem_proxima_pagina(self):
        self.criar(self.app.paths.arquivo_integracao_final)
        self.app.workflow.exibir("imobiliario")
        self.app.chave_legado_input.value = "chave-sintetica"
        async def executar(script, progresso):
            self.criar(self.app.paths.arquivo_integracao_reidentificada)
            progresso("RESULTADO_REIDENTIFICACAO_JSON=" + json.dumps({"saida": self.app.paths.arquivo_integracao_reidentificada}))
            return 0

        self.app.pipeline_runner.executar = executar
        with self.root:
            await self.app.reidentificar_base()
        self.assertTrue(self.app.bloqueio.value)
        self.assertTrue(self.app.botao_fechar_loading.enabled)
        self.app._fechar_popup(self.app.bloqueio)
        self.assertEqual(self.app.workflow.pagina_atual, "imobiliario")

    async def test_cada_download_reidentifica_antes_e_baixa_somente_a_base_escolhida(self):
        self.criar(self.app.paths.arquivo_integracao_final)
        self.criar("dados_processados/imobiliario.csv")
        self.app.chave_legado_input.value = "chave-sintetica"
        for acao, arquivo in [
            (self.app.baixar_base_imobiliaria_reidentificada, self.app.paths.arquivo_base_imobiliario_reidentificada),
            (self.app.baixar_base_integrada_reidentificada, self.app.paths.arquivo_integracao_reidentificada),
        ]:
            with self.subTest(arquivo=arquivo), patch("src.views.app_nicegui.ui.download") as download:
                async def executar(script, progresso):
                    download.assert_not_called()
                    self.assertFalse(self.app.botao_download_base_integrada.enabled)
                    self.assertFalse(self.app.botao_download_base_imobiliaria.enabled)
                    await self.app.baixar_base_integrada_reidentificada()
                    if script.endswith("base_imobiliario.py"):
                        self.criar(self.app.paths.arquivo_base_imobiliario_modulo_iv)
                        progresso("RESULTADO_MODULO_IV_JSON=" + json.dumps({"saida": self.app.paths.arquivo_base_imobiliario_modulo_iv, "celulares_preenchidos": 5}))
                        return 0
                    self.criar(arquivo)
                    progresso("RESULTADO_REIDENTIFICACAO_JSON=" + json.dumps({
                        "saida": self.app.paths.arquivo_integracao_reidentificada,
                        "base_imobiliaria_saida": self.app.paths.arquivo_base_imobiliario_reidentificada,
                    }))
                    return 0

                self.app.pipeline_runner.executar = AsyncMock(side_effect=executar)
                with self.root:
                    await acao()
                scripts = [c.args[0] for c in self.app.pipeline_runner.executar.await_args_list]
                esperados = ["base_imobiliario.py", "reassociacao.py"] if arquivo == self.app.paths.arquivo_base_imobiliario_reidentificada else ["reassociacao.py"]
                self.assertEqual([s.replace("\\", "/").split("/")[-1] for s in scripts], esperados)
                caminho = self.app.paths.resolver(arquivo)
                download.assert_called_once_with(str(caminho), filename=caminho.name)
                self.assertTrue(self.app.bloqueio.value)
                if len(esperados) == 2:
                    self.assertIn("Telefones preenchidos: 5", self.app.progresso_linha.text)
                self.app._fechar_popup(self.app.bloqueio)

    async def test_falha_ou_resultado_ausente_nao_baixa_arquivo_antigo(self):
        self.criar(self.app.paths.arquivo_integracao_final)
        self.criar("dados_processados/imobiliario.csv")
        self.criar(self.app.paths.arquivo_integracao_reidentificada)
        self.criar(self.app.paths.arquivo_base_imobiliario_modulo_iv)
        self.criar(self.app.paths.arquivo_base_imobiliario_reidentificada)
        self.app.chave_legado_input.value = "chave-sintetica"
        for codigo in [0, 1]:
            for acao in [self.app.baixar_base_imobiliaria_reidentificada, self.app.baixar_base_integrada_reidentificada]:
                with self.subTest(codigo=codigo, acao=acao.__name__), self.root, patch("src.views.app_nicegui.ui.download") as download, patch("sys.stderr"):
                    self.app.pipeline_runner.executar = AsyncMock(return_value=codigo)
                    await acao()
                    self.app.pipeline_runner.executar.assert_awaited_once()
                    download.assert_not_called()
                    popup = self.app.dialog_resultado_base_imobiliaria if self.app.dialog_resultado_base_imobiliaria.value else self.app.bloqueio
                    self.assertTrue(popup.value)
                    self.assertIn("Erro", self.app.progresso_texto.text)
                    self.app._fechar_popup(popup)

    async def test_download_nao_executa_com_chave_curta_ou_sem_base_imobiliaria(self):
        self.criar(self.app.paths.arquivo_integracao_final)
        self.app.pipeline_runner.executar = AsyncMock()
        with self.root, patch("src.views.app_nicegui.ui.download") as download:
            self.app.chave_legado_input.value = "curta"
            await self.app.baixar_base_integrada_reidentificada()
            await self.app.baixar_base_imobiliaria_reidentificada()
            self.app.chave_legado_input.value = "chave-sintetica"
            await self.app.baixar_base_imobiliaria_reidentificada()
        self.app.pipeline_runner.executar.assert_not_awaited()
        download.assert_not_called()

    async def test_resultado_da_geracao_permanece_na_tela_final(self):
        self.criar(self.app.paths.arquivo_integracao_final)
        self.criar("dados_processados/imobiliario.csv")
        for codigo in [1, 0]:
            with self.subTest(codigo=codigo):
                self.app.workflow.exibir("imobiliario")

                async def executar(script, progresso):
                    if codigo == 0:
                        self.criar(self.app.paths.arquivo_base_imobiliario_modulo_iv)
                        progresso("RESULTADO_MODULO_IV_JSON=" + json.dumps({"saida": self.app.paths.arquivo_base_imobiliario_modulo_iv}))
                    else:
                        progresso("ValueError: Falta coluna de teste.")
                    return codigo

                self.app.pipeline_runner.executar = executar
                with self.root, patch("sys.stderr"):
                    await self.app.gerar_base_imobiliario_modulo_iv()
                self.assertFalse(self.app.bloqueio.value)
                self.assertTrue(self.app.dialog_resultado_base_imobiliaria.value)
                self.assertEqual(self.app.workflow.pagina_atual, "imobiliario")
                self.app._fechar_popup(self.app.dialog_resultado_base_imobiliaria)
                self.assertEqual(self.app.workflow.pagina_atual, "imobiliario")

    async def test_arquivo_revisado_avanca_somente_depois_de_fechar_resultado(self):
        self.criar(self.app.paths.arquivo_enriquecimento)
        self.criar("dados_processados/imobiliario.csv")
        self.app.workflow.exibir("revisao")
        self.app.state.df = pd.DataFrame()

        async def executar(script, progresso):
            self.criar(self.app.paths.arquivo_integracao_final)
            return 0

        self.app.pipeline_runner.executar = executar
        with self.root:
            await self.app.gerar_arquivo_revisado()
        self.assertFalse(self.app.bloqueio.value)
        self.assertTrue(self.app.dialog_download_revisado.value)
        self.assertEqual(self.app.workflow.pagina_atual, "revisao")
        self.app._fechar_popup(self.app.dialog_download_revisado)
        self.assertEqual(self.app.workflow.pagina_atual, "imobiliario")

    async def test_falhas_de_carregamento_parametrizacao_e_reidentificacao_ficam_visiveis(self):
        self.criar(self.app.paths.arquivo_integracao_final)
        self.app.chave_legado_input.value = "chave-sintetica"

        def falhar():
            raise ValueError("Mensagem de teste")

        self.app.preparar_revisao = falhar
        self.app.gerador_parametros_service.gerar = falhar
        self.app.pipeline_runner.executar = AsyncMock(return_value=1)
        for executar in [self.app.iniciar_revisao, self.app.gerar_parametros, self.app.reidentificar_base]:
            with self.subTest(tarefa=executar.__name__), self.root:
                await executar()
                self.assertTrue(self.app.bloqueio.value)
                self.assertTrue(self.app.botao_fechar_loading.enabled)
                self.assertFalse(self.app.state.rodando)
                self.assertIsNone(self.app._pagina_apos_popup)
                self.app._fechar_popup(self.app.bloqueio)

    async def test_script_ausente_mantem_erro_aberto(self):
        self.app.pipeline_runner.script_disponivel = lambda script: False
        with self.root:
            await self.app.executar_script_com_progresso(1, "ausente.py")
        self.assertTrue(self.app.bloqueio.value)
        self.assertTrue(self.app.botao_fechar_loading.enabled)
        self.assertIn("Script não encontrado", self.app.progresso_linha.text)

    def test_mensagem_final_completa_e_fechamento_reiniciado_na_proxima_execucao(self):
        mensagem = "Detalhe de teste. " * 40
        with self.root:
            self.app._abrir_loading("Teste", "Aguardando")
            self.app._atualizar_loading("Erro", mensagem, 0)
            self.app._pagina_apos_popup = "enriquecimento"
            self.app._finalizar_loading()
            self.assertEqual(self.app.progresso_linha.text, mensagem)
            self.app._abrir_loading("Nova execução", "Aguardando novamente")
        self.assertFalse(self.app.botao_fechar_loading.enabled)
        self.assertIsNone(self.app._pagina_apos_popup)

    async def test_parametrizacao_e_processamento_nao_pulam_preparacao(self):
        self.app.workflow.exibir("preparacao")
        self.app.gerador_parametros_service.gerar = lambda: SimpleNamespace(
            arquivos=[], erros=[], gerados=0, entrada=".", saida=".")
        with self.root:
            await self.app.gerar_parametros()
        self.assertFalse(self.app.bloqueio.value)
        self.assertTrue(self.app.dialog_resultado_parametros.value)
        self.app._fechar_popup(self.app.dialog_resultado_parametros)
        self.assertEqual(self.app.workflow.pagina_atual, "preparacao")
        self.app.processamento_legado_service.executar = lambda *args: {
            "parametros": 1, "csvs_exportados": 1, "erros": [], "saida": "."}
        with self.root:
            await self.app.executar_processamento_legado()
        self.assertTrue(self.app.dialog_logs_processamento.value)
        self.app._fechar_popup(self.app.dialog_logs_processamento)
        self.assertEqual(self.app.workflow.pagina_atual, "preparacao")

    def test_resultados_so_fecham_pelo_botao(self):
        for dialog in [self.app.bloqueio, self.app.dialog_logs_processamento,
                       self.app.dialog_download_revisado, self.app.dialog_resultado_enriquecimento,
                       self.app.dialog_resultado_base_imobiliaria, self.app.dialog_resultado_parametros]:
            self.assertTrue(dialog._props.get("persistent"))

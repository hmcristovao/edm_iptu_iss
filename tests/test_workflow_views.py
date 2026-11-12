import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pandas as pd
from nicegui import ui

from src.views.app_nicegui import IntegracaoEnriquecimentoApp


class WorkflowViewsTest(unittest.TestCase):
    def setUp(self):
        navegador = patch("src.views.workflow.ui.run_javascript")
        navegador.start()
        self.addCleanup(navegador.stop)
        timer = patch("src.views.workflow.ui.timer")
        self.timer = timer.start()
        self.addCleanup(timer.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = IntegracaoEnriquecimentoApp()
        self.app.paths.definir_pasta_trabalho(self.temp.name)
        self.app.state.autenticado = True
        self.app.state.pasta_trabalho_selecionada = True
        self.root = ui.column()
        self.addCleanup(self.root.delete)
        with self.root:
            self.app._montar_layout()

    def criar(self, arquivo):
        caminho = self.app.paths.resolver(arquivo)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.touch()

    def test_navegacao_preserva_chave_configuracao_e_pasta(self):
        self.assertIsNotNone(getattr(self.app, "workflow", None))
        self.criar(self.app.paths.arquivo_preparacao)
        chave = self.app.chave_legado_input
        campo = self.app.campos_config["threshold_similaridade"]
        chave.value = "chave-de-teste"
        campo.value = 93
        self.app.workflow.exibir("preparacao")
        self.app.workflow.exibir("enriquecimento")
        self.app.workflow.exibir("preparacao")
        self.assertIs(self.app.chave_legado_input, chave)
        self.assertEqual(chave.value, "chave-de-teste")
        self.assertIs(self.app.campos_config["threshold_similaridade"], campo)
        self.assertEqual(campo.value, 93)
        self.assertEqual(self.app.paths.work_dir, Path(self.temp.name).resolve())
        self.assertEqual([p for p, view in self.app.workflow.paginas.items() if view.visible], ["preparacao"])

    def test_avanco_so_e_liberado_quando_existe_saida_da_etapa(self):
        self.assertIsNotNone(getattr(self.app, "workflow", None))
        self.app.workflow.exibir("preparacao")
        self.app.workflow.avancar()
        self.assertEqual(self.app.workflow.pagina_atual, "preparacao")
        self.criar(self.app.paths.arquivo_preparacao)
        self.app.workflow.avancar()
        self.assertEqual(self.app.workflow.pagina_atual, "enriquecimento")
        self.app.workflow.avancar()
        self.assertEqual(self.app.workflow.pagina_atual, "enriquecimento")
        self.criar(self.app.paths.arquivo_enriquecimento)
        self.app.workflow.avancar()
        self.assertEqual(self.app.workflow.pagina_atual, "revisao")
        self.app.workflow.avancar()
        self.assertEqual(self.app.workflow.pagina_atual, "revisao")
        self.criar(self.app.paths.arquivo_integracao_final)
        self.criar("dados_processados/imobiliario.csv")
        self.app.workflow.avancar()
        self.assertEqual(self.app.workflow.pagina_atual, "imobiliario")
        self.criar(self.app.paths.arquivo_base_imobiliario_modulo_iv)
        self.app._atualizar_botoes()
        self.assertFalse(self.app.workflow.avancar_button.visible)
        self.app.workflow.avancar()
        self.assertEqual(self.app.workflow.pagina_atual, "imobiliario")

    def test_navegacao_bloqueada_durante_execucao(self):
        self.assertIsNotNone(getattr(self.app, "workflow", None))
        self.app.workflow.exibir("preparacao")
        self.app.state.rodando = True
        self.app.workflow.exibir("pasta")
        self.assertEqual(self.app.workflow.pagina_atual, "preparacao")

    def test_retomada_respeita_arquivos_disponiveis_sem_escrever_neles(self):
        self.assertIsNotNone(getattr(self.app, "workflow", None))
        casos = [
            (None, "preparacao"),
            (self.app.paths.arquivo_preparacao, "enriquecimento"),
            (self.app.paths.arquivo_enriquecimento, "revisao"),
            (self.app.paths.arquivo_integracao_parcial, "imobiliario"),
            ("dados_processados/imobiliario.csv", "imobiliario"),
            (self.app.paths.arquivo_base_imobiliario_modulo_iv, "imobiliario"),
            (self.app.paths.arquivo_base_imobiliario_reidentificada, "imobiliario"),
        ]
        for arquivo, pagina in casos:
            with self.subTest(pagina=pagina, arquivo=arquivo):
                if arquivo:
                    self.criar(arquivo)
                antes = sorted(str(p) for p in Path(self.temp.name).rglob("*"))
                self.app.workflow.retomar()
                self.assertEqual(self.app.workflow.pagina_atual, pagina)
                self.assertEqual(sorted(str(p) for p in Path(self.temp.name).rglob("*")), antes)

    def test_barra_reconhece_revisao_salva_final_ou_parcial(self):
        for arquivo in [self.app.paths.arquivo_integracao_final, self.app.paths.arquivo_integracao_parcial]:
            with self.subTest(arquivo=arquivo):
                self.criar(arquivo)
                self.app._atualizar_status()
                self.app._atualizar_botoes()
                self.app.workflow.retomar()
                self.assertEqual(self.app.workflow.pagina_atual, "imobiliario")
                self.assertEqual(self.app.card_revisao.text, "Realizada")
                self.assertIn("complete", self.app.workflow.passos["revisao"][0]._classes)
                self.app.paths.resolver(arquivo).unlink()
        self.app.workflow.atualizar()
        self.assertEqual(self.app.card_revisao.text, "Pendente")

    def test_trocar_pasta_nao_libera_geracao_com_revisao_da_pasta_anterior(self):
        self.app.state.df = pd.DataFrame({"merge_key": ["CPF_documento-teste"]})
        self.app.state.etapa3_ativa = True
        self.app.workflow.pasta_revisao = self.app.paths.work_dir
        self.app.workflow.atualizar()
        self.assertTrue(self.app.workflow.salvar_sair_button.enabled)
        outra_pasta = Path(self.temp.name) / "outra-pasta"
        outra_pasta.mkdir()
        self.app.paths.definir_pasta_trabalho(outra_pasta)
        self.criar(self.app.paths.arquivo_enriquecimento)
        self.app.workflow.retomar()
        self.assertEqual(self.app.workflow.pagina_atual, "revisao")
        self.assertFalse(self.app.workflow.salvar_sair_button.enabled)
        self.assertFalse(self.app.area_revisao.visible)
        self.assertTrue(self.app.workflow.revisao_placeholder.visible)
        self.assertEqual(self.app.card_revisao.text, "Pendente")

    def test_downloads_exigem_bases_pseudonimizadas_para_reidentificar(self):
        self.criar(self.app.paths.arquivo_base_imobiliario_reidentificada)
        self.app._atualizar_botoes()
        self.app.workflow.retomar()
        self.assertFalse(self.app.botao_download_base_imobiliaria.enabled)
        self.assertEqual(self.app.workflow.pagina_atual, "imobiliario")
        self.assertTrue(self.app.workflow.paginas["imobiliario"].visible)
        self.assertFalse(self.app.botao_download_base_integrada.enabled)
        self.criar(self.app.paths.arquivo_integracao_final)
        self.app._atualizar_botoes()
        self.assertTrue(self.app.botao_download_base_integrada.enabled)
        self.assertFalse(self.app.botao_download_base_imobiliaria.enabled)
        self.criar("dados_processados/imobiliario.csv")
        self.app._atualizar_botoes()
        self.assertTrue(self.app.botao_download_base_imobiliaria.enabled)

    def test_ultima_pagina_tem_dois_cards_de_download(self):
        self.assertEqual(tuple(self.app.workflow.paginas), ("pasta", "preparacao", "enriquecimento", "revisao", "imobiliario"))
        pagina = self.app.workflow.paginas["imobiliario"]
        cards = [e for e in pagina.descendants() if isinstance(e, ui.card)]
        self.assertEqual(len(cards), 2)
        botoes = [e.text for e in pagina.descendants() if isinstance(e, ui.button) and e.text]
        self.assertEqual(botoes, ["Baixar base imobiliária", "Baixar base integrada"])

    def test_revisao_tem_apenas_um_comando_para_salvar_e_sair(self):
        botoes = [elemento for elemento in self.app.workflow.paginas["revisao"].descendants()
                  if isinstance(elemento, ui.button)]
        self.assertEqual([botao.text for botao in botoes], ["Salvar e sair da revisão"])

    def test_configuracao_usa_termo_revisao_manual(self):
        self.assertEqual(self.app.campos_config["threshold_revisar"]._props["label"], "Revisão manual (%)")

    def test_resumo_tem_cinco_cards_sem_carregados_e_preserva_contagens(self):
        pares = [{"id_revisao": "R1", "par_id": "P1"}, {"id_revisao": "R2", "par_id": "P2"}]
        self.app.state.total_grupos_revisao = 5
        self.app.state.decisoes = {"P1": {"decisao": "aprovar"}}
        with self.root, ui.column() as resumo:
            self.app._montar_resumo_revisao(pares, self.app._agrupar_pares(pares))
        textos = [e.text for e in resumo.descendants() if isinstance(e, ui.label)]
        self.assertEqual(textos, ["Pares", "5", "Pares pendentes", "4", "Pares decididos", "1", "Aprovados", "1", "Rejeitados", "0"])

    def test_entrada_na_revisao_agenda_carregamento_sem_clique_adicional(self):
        self.criar(self.app.paths.arquivo_enriquecimento)
        self.app.iniciar_revisao = AsyncMock()
        self.app.workflow.exibir("revisao")
        self.app.workflow.exibir("revisao")
        self.timer.assert_called_once()
        asyncio.run(self.timer.call_args.args[1]())
        self.app.iniciar_revisao.assert_awaited_once()

    def test_retomada_na_revisao_tambem_inicia_carregamento(self):
        self.criar(self.app.paths.arquivo_enriquecimento)
        self.app.iniciar_revisao = AsyncMock()
        self.app.workflow.retomar()
        self.assertEqual(self.app.workflow.pagina_atual, "revisao")
        self.timer.assert_called_once()
        asyncio.run(self.timer.call_args.args[1]())
        self.app.iniciar_revisao.assert_awaited_once()

    def test_nao_carrega_revisao_se_usuario_sair_antes_do_inicio(self):
        self.criar(self.app.paths.arquivo_enriquecimento)
        self.app.iniciar_revisao = AsyncMock()
        self.app.workflow.exibir("revisao")
        iniciar = self.timer.call_args.args[1]
        self.app.workflow.exibir("preparacao")
        asyncio.run(iniciar())
        self.app.iniciar_revisao.assert_not_awaited()

    def test_salvar_e_sair_dispara_geracao_do_arquivo(self):
        self.app.gerar_arquivo_revisado = AsyncMock()
        self.app.solicitar_geracao_arquivo_revisado()
        asyncio.run(self.timer.call_args.args[1]())
        self.app.gerar_arquivo_revisado.assert_awaited_once()

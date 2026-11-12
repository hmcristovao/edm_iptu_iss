from nicegui import ui


class WorkflowView:
    PAGINAS = ("pasta", "preparacao", "enriquecimento", "revisao", "imobiliario")

    def __init__(self, application):
        self.app = application
        self.pagina_atual = "pasta"
        self.paginas = {}
        self.passos = {}
        self.comandos_etapa = {}
        self.pasta_revisao = None
        self._revisao_agendada = False

    def montar(self):
        with ui.element("div").classes("workflow-root"):
            self._cabecalho()
            self._progresso()
            with ui.element("main").classes("workflow-main"):
                for nome, construir in [
                    ("pasta", self._pasta),
                    ("preparacao", self._preparacao),
                    ("enriquecimento", self._enriquecimento),
                    ("revisao", self._revisao),
                    ("imobiliario", self._imobiliario),
                ]:
                    with ui.element("section").classes("workflow-page").props(f'data-etapa="{nome}"') as pagina:
                        construir()
                    self.paginas[nome] = pagina
                with ui.element("div").classes("workflow-footer"):
                    self.voltar_button = ui.button("Voltar", icon="arrow_back", on_click=self.voltar).props("flat no-caps").classes("workflow-back")
                    with ui.element("div").classes("workflow-footer-actions"):
                        self.app.botao_preparacao = self._comando("Executar preparação", self.app.abrir_confirmacao_preparacao)
                        self.app.botao_enriquecimento = self._comando("Executar enriquecimento", self.app.abrir_confirmacao_enriquecimento)
                        self.comandos_etapa = {
                            "preparacao": self.app.botao_preparacao,
                            "enriquecimento": self.app.botao_enriquecimento,
                        }
                        self.avancar_button = ui.button("Avançar", on_click=self.avancar).props("unelevated no-caps").classes("workflow-next")
        self.atualizar()

    def _cabecalho(self):
        with ui.element("header").classes("workflow-header"):
            with ui.element("div").classes("workflow-header-inner"):
                with ui.element("div").classes("workflow-wordmark"):
                    ui.label("integra FISCAL").classes("workflow-wordmark-name")
                    ui.html("Inteligência cadastral<br>para a gestão fiscal").classes("workflow-wordmark-description")
                with ui.element("div").classes("workflow-user"):
                    ui.icon("person").classes("workflow-avatar")
                    self.app.usuario_logado_label = ui.label("Usuário: não autenticado")
                    self.pasta_header_button = ui.button(icon="folder_open", color=None, on_click=self._abrir_pasta).props('flat round aria-label="Alterar pasta de trabalho"').classes("workflow-folder-button")
                    self.pasta_header_button.tooltip("Alterar pasta de trabalho")

    def _abrir_pasta(self):
        self.exibir("pasta")

    def _progresso(self):
        with ui.element("nav").classes("workflow-progress").props('aria-label="Etapas do processamento"'):
            with ui.element("div").classes("workflow-steps"):
                for nome, titulo, atributo in [
                    ("preparacao", "PREPARAÇÃO", "card_preparacao"),
                    ("enriquecimento", "ENRIQUECIMENTO", "card_enriquecimento"),
                    ("revisao", "REVISÃO MANUAL", "card_revisao"),
                ]:
                    with ui.element("div").classes("workflow-step") as passo:
                        with ui.button(on_click=lambda etapa=nome: self.exibir(etapa), color=None).props(f'flat no-caps aria-label="Ir para {titulo}"').classes("workflow-step-status") as botao:
                            label = ui.label("Pendente")
                        ui.label(titulo).classes("workflow-step-title")
                    setattr(self.app, atributo, label)
                    self.passos[nome] = (passo, botao, label)

    def _titulo(self, titulo, descricao=None):
        ui.label(titulo).classes("workflow-heading").props("role=heading aria-level=1")
        if descricao:
            ui.label(descricao).classes("workflow-description")
        else:
            ui.element("div").classes("workflow-description-gap").props("aria-hidden=true")

    def _comando(self, titulo, callback):
        return ui.button(titulo, on_click=callback).props("unelevated no-caps").classes("workflow-command")

    def _pasta(self):
        self._titulo("Localização da pasta de trabalho", "Para começar, localize abaixo a pasta de trabalho.")
        with ui.card().classes("workflow-panel workflow-workdir"):
            self.app.botao_pasta_trabalho = self._comando("Localizar pasta de trabalho", self.app.abrir_selecao_pasta_trabalho)
            self.app.pasta_trabalho_label = ui.label("").classes("workflow-workdir-path")
            self.app.arquivos_entrada_label = ui.label("").classes("workflow-panel-footer")

    def _preparacao(self):
        self._titulo("Preparação de arquivos")
        with ui.card().classes("workflow-panel workflow-parameters"):
            with ui.element("div").classes("workflow-tool-row"):
                with ui.element("div").classes("workflow-tool-copy"):
                    ui.label("Gerar parâmetros").classes("workflow-panel-title")
                    ui.label("Etapa opcional").classes("workflow-panel-description")
                self.app.botao_gerar_parametros = self._comando("Gerar parâmetros", self.app.gerar_parametros)
            resumo = ui.label("").classes("workflow-panel-footer")
            if hasattr(self.app, "resultado_parametros_label"):
                resumo.bind_text_from(self.app.resultado_parametros_label, "text", backward=lambda texto: texto.splitlines()[0] if texto else "")
        with ui.card().classes("workflow-panel workflow-processing"):
            ui.label("Processar arquivos originais").classes("workflow-panel-title")
            ui.label("Leitura dos parâmetros, extração, padronização, pseudonimização e exportação.").classes("workflow-panel-description")
            with ui.element("div").classes("workflow-processing-controls"):
                self.app.chave_legado_input = ui.input(
                    placeholder="Insira aqui a chave de pseudonimização",
                    password=True,
                    password_toggle_button=True,
                ).props('outlined dense aria-label="Chave de pseudonimização"').classes("workflow-field")
                self.app.botao_processamento_legado = self._comando("Processar arquivos", self.app.abrir_confirmacao_processamento_legado)
            self.app.processamento_legado_status = ui.label("").classes("workflow-panel-footer")

    def _enriquecimento(self):
        self._titulo("Enriquecimento de dados")
        with ui.card().classes("workflow-panel workflow-config"):
            ui.label("Configurações do Enriquecimento").classes("workflow-panel-title")
            config = self.app.config_service.carregar()
            with ui.element("div").classes("workflow-config-fields"):
                for chave, titulo in [
                    ("threshold_similaridade", "Merge automático (%)"),
                    ("threshold_revisar", "Revisão manual (%)"),
                    ("threshold_apoio_nome", "Nome (%)"),
                    ("threshold_apoio_telefone", "Telefone (%)"),
                    ("threshold_apoio_email", "E-mail (%)"),
                    ("threshold_apoio_nascimento", "Nascimento (%)"),
                    ("threshold_apoio_endereco", "Endereço (%)"),
                    ("threshold_apoio_numero", "Número (%)"),
                    ("threshold_apoio_identificador_documento", "Identificador (%)"),
                    ("max_pares_por_valor_bloco", "Máx. pares por bloco"),
                ]:
                    self.app.campos_config[chave] = ui.number(titulo, value=int(config[chave]), min=0).props("outlined stack-label").classes("workflow-field")
            with ui.element("div").classes("workflow-config-save"):
                self.app.botao_salvar_config = self._comando("Salvar configurações", self.app.salvar_config_ui)

    def _revisao(self):
        self._titulo("Revisão manual")
        with ui.element("div").classes("workflow-review-toolbar"):
            self.salvar_sair_button = ui.button("Salvar e sair da revisão", on_click=self.app.solicitar_geracao_arquivo_revisado).props("unelevated no-caps")
        self.revisao_placeholder = ui.label("Revisão não iniciada.").classes("workflow-review-placeholder")
        self.app.area_revisao = ui.column().classes("workflow-review-area gap-0")

    def _imobiliario(self):
        self._titulo("Download das bases")
        self.chave_reidentificacao_input = ui.input(
            "Chave de pseudonimização", password=True, password_toggle_button=True,
        ).props("outlined").classes("workflow-field workflow-download-key")
        self.chave_reidentificacao_input.bind_value(self.app.chave_legado_input)
        with ui.element("div").classes("workflow-downloads"):
            with ui.card().classes("workflow-download-card"):
                ui.label("Base imobiliária").classes("workflow-panel-title")
                self.app.botao_download_base_imobiliaria = ui.button(
                    "Baixar base imobiliária", icon="download", on_click=self.app.baixar_base_imobiliaria_reidentificada,
                ).props("unelevated no-caps").classes("workflow-command")
            with ui.card().classes("workflow-download-card"):
                ui.label("Base integrada").classes("workflow-panel-title")
                self.app.botao_download_base_integrada = ui.button(
                    "Baixar base integrada", icon="download", on_click=self.app.baixar_base_integrada_reidentificada,
                ).props("unelevated no-caps").classes("workflow-command")

    def _disponiveis(self):
        paths = self.app.paths
        pasta = self.app.state.pasta_trabalho_selecionada
        revisado = bool(self.app._arquivo_revisao_existente())
        return {
            "pasta": True,
            "preparacao": pasta,
            "enriquecimento": paths.existe(paths.arquivo_preparacao),
            "revisao": paths.existe(paths.arquivo_enriquecimento),
            "imobiliario": revisado or paths.existe(paths.arquivo_base_imobiliario_reidentificada),
        }

    def _proxima_pagina(self):
        disponiveis = self._disponiveis()
        if self.pagina_atual == "pasta":
            return self._pagina_retomada() if self.app.state.pasta_trabalho_selecionada else None
        if self.pagina_atual == "preparacao":
            return "enriquecimento" if disponiveis["enriquecimento"] else None
        if self.pagina_atual == "enriquecimento":
            return "revisao" if disponiveis["revisao"] else None
        if self.pagina_atual == "revisao":
            return "imobiliario" if disponiveis["imobiliario"] else None
        return None

    def _pagina_retomada(self):
        disponiveis = self._disponiveis()
        for nome in ("imobiliario", "revisao", "enriquecimento"):
            if disponiveis[nome]:
                return nome
        return "preparacao"

    def retomar(self):
        self.exibir(self._pagina_retomada())

    def revisao_da_pasta_atual(self):
        return self.pasta_revisao == self.app.paths.work_dir and self.app.state.df is not None

    def exibir(self, pagina):
        if self.app.state.rodando or not self.app.state.autenticado:
            return
        if pagina not in self.paginas or not self._disponiveis()[pagina]:
            return
        carregar_revisao = pagina == "revisao" and (
            pagina != self.pagina_atual or not self.revisao_da_pasta_atual() or not self.app.state.etapa3_ativa
        )
        self.pagina_atual = pagina
        if carregar_revisao and not self._revisao_agendada:
            self._revisao_agendada = True
            with self.paginas["revisao"]:
                ui.timer(0.05, self._iniciar_revisao_automaticamente, once=True)
        self.atualizar()
        ui.run_javascript("window.scrollTo(0, 0)")

    async def _iniciar_revisao_automaticamente(self):
        try:
            if (
                self.pagina_atual == "revisao"
                and self.app.state.autenticado
                and self.app.state.pasta_trabalho_selecionada
                and not self.app.state.rodando
            ):
                await self.app.iniciar_revisao()
        finally:
            self._revisao_agendada = False
            self.atualizar()

    def avancar(self):
        proxima = self._proxima_pagina()
        if proxima:
            self.exibir(proxima)

    def voltar(self):
        indice = self.PAGINAS.index(self.pagina_atual)
        for pagina in reversed(self.PAGINAS[:indice]):
            if self._disponiveis()[pagina]:
                self.exibir(pagina)
                return

    def atualizar(self):
        disponiveis = self._disponiveis()
        state = self.app.state
        paths = self.app.paths
        pode_navegar = state.autenticado and not state.rodando
        for nome, pagina in self.paginas.items():
            pagina.set_visibility(nome == self.pagina_atual)
        for nome, comando in self.comandos_etapa.items():
            comando.set_visibility(nome == self.pagina_atual)
        self.voltar_button.set_visibility(self.pagina_atual != "pasta")
        self.voltar_button.set_enabled(pode_navegar)
        self.avancar_button.set_visibility(self.pagina_atual == "pasta" or self._proxima_pagina() is not None)
        self.avancar_button.set_enabled(pode_navegar and self._proxima_pagina() is not None)
        self.pasta_header_button.set_enabled(pode_navegar)
        for nome, (elemento, botao, label) in self.passos.items():
            concluida = {
                "preparacao": paths.existe(paths.arquivo_preparacao),
                "enriquecimento": paths.existe(paths.arquivo_enriquecimento),
                "revisao": bool(self.app._arquivo_revisao_existente()),
            }[nome]
            andamento = nome == self.pagina_atual and (
                nome != "revisao" or (state.etapa3_ativa and self.revisao_da_pasta_atual())
            )
            label.set_text("Realizada" if concluida else "Em andamento" if andamento else "Pendente")
            elemento.classes(add="complete" if concluida else "", remove="" if concluida else "complete")
            botao.props(
                'aria-current="step"' if nome == self.pagina_atual else "",
                remove="" if nome == self.pagina_atual else "aria-current",
            )
            botao.set_enabled(pode_navegar and disponiveis[nome])
        revisao_atual = self.revisao_da_pasta_atual()
        revisao_visivel = state.etapa3_ativa and revisao_atual
        self.revisao_placeholder.set_visibility(not revisao_visivel)
        self.revisao_placeholder.set_text("Carregando revisão..." if self._revisao_agendada else "Revisão não iniciada.")
        self.app.area_revisao.set_visibility(revisao_visivel)
        self.salvar_sair_button.set_enabled(pode_navegar and revisao_atual and not self._revisao_agendada)

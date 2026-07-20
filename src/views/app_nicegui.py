import asyncio
import json
import os
import queue
import socket

from nicegui import ui

from src.moduloI.services import ProcessamentoLegadoService
from src.moduloII.app_config import COLUNA_MERGE_KEY, AppPaths, AppSettings
from src.moduloII.services import (
    EntradaService,
    IntegracaoConfigService,
    PipelineRunner,
    RevisaoService,
    extrair_porcentagem,
    formatar_score,
    texto_valor,
)
from src.moduloIII.reassociacao import ReidentificacaoService
from src.parametrizacao import GeradorParametrosService
from src.views.app_state import AppState


class IntegracaoEnriquecimentoApp:
    def __init__(self):
        self.paths = AppPaths()
        self.settings = AppSettings()
        self.state = AppState()
        self.config_service = IntegracaoConfigService(self.paths, self.settings)
        self.entrada_service = EntradaService(self.paths)
        self.processamento_legado_service = ProcessamentoLegadoService(self.paths)
        self.gerador_parametros_service = GeradorParametrosService(self.paths)
        self.revisao_service = RevisaoService(self.paths)
        self.reidentificacao_service = ReidentificacaoService(self.paths)
        self.pipeline_runner = PipelineRunner(self.paths)
        self.campos_config = {}
        self.progresso_estimado = 0
        self.saida_execucao_atual = []

    def run(self):
        self._configurar_tema()
        self._montar_dialogos()
        self._montar_layout()
        self._desenhar_revisao()
        self._atualizar_status_entrada()
        self._atualizar_status()
        self._atualizar_botoes()
        ui.timer(0.1, self.abrir_login, once=True)
        porta = self._encontrar_porta_livre()
        ui.run(title="Integração e Enriquecimento", reload=False, port=porta)

    def _encontrar_porta_livre(self, inicial: int = 8080) -> int:
        for porta in range(inicial, inicial + 20):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                try:
                    sock.bind(("0.0.0.0", porta))
                except OSError:
                    continue
                return porta

        return inicial

    def _configurar_tema(self):
        ui.page_title("Integração e Enriquecimento")
        ui.colors(
            primary="#2563eb",
            secondary="#475569",
            accent="#0f766e",
            positive="#16a34a",
            negative="#dc2626",
            warning="#d97706",
        )
        ui.add_head_html(
            """
            <style>
              body {
                background: #f8fafc;
                color: #0f172a;
                font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
              }
              .nicegui-content {
                max-width: 1380px;
                margin: 0 auto;
              }
              .q-card {
                border-radius: 10px;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
              }
              .q-field__label,
              .q-table th {
                font-weight: 600;
                color: #475569;
              }
              .q-table tbody td {
                color: #1e293b;
              }
            </style>
            """
        )

    def _montar_dialogos(self):
        self.login_dialog = ui.dialog().props("persistent")
        with self.login_dialog, ui.card().classes("w-[420px] gap-4 rounded-lg"):
            ui.label("Acesso ao Sistema").classes("text-xl font-semibold text-slate-900")
            ui.label("Informe seu nome e a senha padrão para continuar.").classes("text-sm text-slate-600")
            self.nome_usuario_input = ui.input("Nome do usuário").props("outlined dense").classes("w-full")
            self.senha_input = ui.input("Senha", password=True, password_toggle_button=True).props(
                "outlined dense"
            ).classes("w-full")
            ui.button("Entrar", on_click=self.autenticar_usuario).props("color=primary unelevated").classes("w-full")

        self.dialog_pasta_trabalho = ui.dialog()
        with self.dialog_pasta_trabalho, ui.card().classes("w-[680px] gap-4 rounded-lg"):
            ui.label("Selecionar Pasta de Trabalho").classes("text-xl font-semibold text-slate-900")
            ui.label(
                "Cole o caminho da pasta onde estão os CSVs de entrada. As pastas arquivos_gerados e logs serão criadas dentro dela."
            ).classes("text-sm text-slate-600")
            self.pasta_trabalho_input = ui.input("Caminho da pasta de trabalho").props("outlined dense").classes(
                "w-full"
            )
            self.pasta_trabalho_status_label = ui.label("").classes("text-sm text-slate-600")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancelar", on_click=self.dialog_pasta_trabalho.close).props("flat")
                ui.button("Usar Pasta", on_click=self.confirmar_pasta_trabalho).props("color=primary unelevated")

        self.dialog_download_revisado = ui.dialog()
        with self.dialog_download_revisado, ui.card().classes("w-[460px] gap-4 rounded-lg"):
            ui.label("Arquivo Revisado Gerado").classes("text-xl font-semibold text-slate-900")
            self.download_revisado_label = ui.label("").classes("text-sm text-slate-600")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Fechar", on_click=self.dialog_download_revisado.close).props("flat")
                ui.button("Baixar Arquivo", on_click=self.baixar_arquivo_revisado).props("color=primary unelevated")

        self.dialog_resultado_enriquecimento = ui.dialog()
        with self.dialog_resultado_enriquecimento, ui.card().classes("w-[560px] gap-4 rounded-lg"):
            ui.label("Resultado do Enriquecimento").classes("text-xl font-semibold text-slate-900")
            self.resultado_enriquecimento_area = ui.column().classes("w-full gap-2")
            with ui.row().classes("w-full justify-end"):
                ui.button("Fechar", on_click=self.dialog_resultado_enriquecimento.close).props("flat")

        self.dialog_resultado_base_imobiliaria = ui.dialog()
        with self.dialog_resultado_base_imobiliaria, ui.card().classes("w-[560px] gap-4 rounded-lg"):
            ui.label("Resultado da Base Imobiliaria").classes("text-xl font-semibold text-slate-900")
            self.resultado_base_imobiliaria_label = ui.label("").classes("whitespace-pre-wrap text-sm text-slate-700")
            with ui.row().classes("w-full justify-end"):
                ui.button("Fechar", on_click=self.dialog_resultado_base_imobiliaria.close).props("flat")

        self.dialog_resultado_parametros = ui.dialog()
        with self.dialog_resultado_parametros, ui.card().classes("w-[560px] gap-4 rounded-lg"):
            ui.label("Resultado da Parametrização").classes("text-xl font-semibold text-slate-900")
            self.resultado_parametros_label = ui.label("").classes("whitespace-pre-wrap text-sm text-slate-700")
            with ui.row().classes("w-full justify-end"):
                ui.button("Fechar", on_click=self.dialog_resultado_parametros.close).props("flat")

        self.bloqueio = ui.dialog().props("persistent")
        with self.bloqueio, ui.card().classes("w-[520px] gap-4 rounded-lg"):
            ui.label("Execução em Andamento").classes("text-lg font-semibold text-slate-900")
            self.progresso_texto = ui.label("Aguardando...")
            self.progresso_barra = ui.linear_progress(value=0).props("instant-feedback").classes("w-full")
            self.progresso_linha = ui.label("").classes("text-sm text-slate-600")

        self.dialog_logs_processamento = ui.dialog().props("persistent")
        with self.dialog_logs_processamento, ui.card().classes("w-[760px] max-w-[92vw] gap-4 rounded-lg"):
            self.logs_processamento_titulo = ui.label("Processamento dos Arquivos Originais").classes(
                "text-lg font-semibold text-slate-900"
            )
            self.logs_processamento_status = ui.label("Aguardando...").classes("text-sm text-slate-600")
            with ui.scroll_area().classes(
                "h-[420px] w-full rounded border border-slate-200 bg-slate-950 p-3"
            ):
                self.logs_processamento_texto = ui.label("").classes(
                    "whitespace-pre-wrap font-mono text-xs leading-relaxed text-slate-100"
                )
            with ui.row().classes("w-full justify-end"):
                self.botao_fechar_logs_processamento = ui.button(
                    "Fechar",
                    on_click=self.dialog_logs_processamento.close,
                ).props("flat")

    def _montar_layout(self):
        with ui.column().classes("w-full gap-5 p-6"):
            with ui.column().classes("gap-1"):
                ui.label("Integração e Enriquecimento").classes("text-3xl font-bold text-slate-950")
                ui.label("Execute a preparação, o enriquecimento e a revisão dos dados integrados.").classes(
                    "text-sm text-slate-600"
                )

            self.usuario_logado_label = ui.label("Usuário: não autenticado").classes(
                "rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700"
            )

            self._montar_cards_status()
            self._montar_card_entrada()
            self._montar_card_processamento_legado()
            self._montar_card_configuracoes()
            self._montar_card_execucao()
            self.area_revisao = ui.column().classes("w-full gap-4")

    def _montar_cards_status(self):
        with ui.row().classes("w-full gap-3"):
            with ui.card().classes("flex-1 gap-1 border border-slate-200 bg-white"):
                ui.label("Preparação").classes("text-xs font-medium uppercase tracking-wide text-slate-500")
                self.card_preparacao = ui.label("").classes("text-xl font-semibold text-slate-900")
            with ui.card().classes("flex-1 gap-1 border border-slate-200 bg-white"):
                ui.label("Enriquecimento").classes("text-xs font-medium uppercase tracking-wide text-slate-500")
                self.card_enriquecimento = ui.label("").classes("text-xl font-semibold text-slate-900")
            with ui.card().classes("flex-1 gap-1 border border-slate-200 bg-white"):
                ui.label("Revisão Humana").classes("text-xs font-medium uppercase tracking-wide text-slate-500")
                self.card_revisao = ui.label("").classes("text-xl font-semibold text-slate-900")

    def _montar_card_entrada(self):
        with ui.card().classes("w-full gap-3 border border-slate-200 bg-white"):
            ui.label("Pasta de Trabalho").classes("text-xl font-semibold text-slate-900")
            self.pasta_trabalho_label = ui.label("").classes("text-sm font-medium text-slate-700")
            self.arquivos_entrada_label = ui.label("Nenhum CSV carregado.").classes("text-sm text-slate-600")
            self.botao_pasta_trabalho = ui.button(
                "Selecionar Pasta de Trabalho",
                on_click=self.abrir_selecao_pasta_trabalho,
            ).props("color=primary unelevated")

    def _montar_card_processamento_legado(self):
        with ui.card().classes("w-full gap-4 border border-slate-200 bg-white"):
            ui.label("Processamento dos Arquivos Originais").classes("text-xl font-semibold text-slate-900")
            ui.label(
                "Executa os algoritmos antigos: leitura dos parâmetros, extração, padronização, pseudonimização e exportação."
            ).classes("text-sm text-slate-600")
            with ui.row().classes("w-full gap-3 items-end"):
                self.chave_legado_input = ui.input(
                    "Chave de pseudonimização",
                    password=True,
                    password_toggle_button=True,
                ).props("outlined dense").classes("flex-1")
                self.botao_processamento_legado = ui.button(
                    "Processar Arquivos Originais",
                    on_click=self.abrir_confirmacao_processamento_legado,
                ).props("color=primary unelevated")
                self.botao_gerar_parametros = ui.button(
                    "Gerar Parâmetros",
                    on_click=self.gerar_parametros,
                ).props("color=secondary unelevated")
            self.processamento_legado_status = ui.label("").classes("text-sm text-slate-600")

    def _montar_card_configuracoes(self):
        with ui.card().classes("w-full gap-4 border border-slate-200 bg-white"):
            ui.label("Configurações do Enriquecimento").classes("text-xl font-semibold text-slate-900")
            config = self.config_service.carregar()
            with ui.grid(columns=5).classes("w-full gap-3"):
                for chave, rotulo in [
                    ("threshold_similaridade", "Merge Automático (%)"),
                    ("threshold_revisar", "Revisão Humana (%)"),
                    ("threshold_apoio_nome", "Nome (%)"),
                    ("threshold_apoio_telefone", "Telefone (%)"),
                    ("threshold_apoio_email", "E-mail (%)"),
                    ("threshold_apoio_nascimento", "Nascimento (%)"),
                    ("threshold_apoio_endereco", "Endereço (%)"),
                    ("threshold_apoio_numero", "Número (%)"),
                    ("threshold_apoio_identificador_documento", "Identificador (%)"),
                    ("max_pares_por_valor_bloco", "Máx. Pares por Bloco"),
                ]:
                    self.campos_config[chave] = ui.number(rotulo, value=int(config[chave]), min=0).props(
                        "outlined dense"
                    )
            self.botao_salvar_config = ui.button("Salvar Configuração", on_click=self.salvar_config_ui).props(
                "color=primary unelevated"
            )

    def _montar_card_execucao(self):
        with ui.card().classes("w-full gap-4 border border-slate-200 bg-white"):
            ui.label("Executar Integração").classes("text-xl font-semibold text-slate-900")
            with ui.row().classes("w-full gap-3"):
                self.botao_preparacao = ui.button(
                    "Iniciar Preparação",
                    on_click=self.abrir_confirmacao_preparacao,
                ).props("color=primary unelevated")
                self.botao_enriquecimento = ui.button(
                    "Iniciar Enriquecimento",
                    on_click=self.abrir_confirmacao_enriquecimento,
                ).props("color=primary unelevated")
                self.botao_revisao = ui.button("Iniciar Revisão", on_click=self.iniciar_revisao).props(
                    "color=primary unelevated"
                )
                self.botao_reidentificacao = ui.button(
                    "Reidentificar Base",
                    on_click=self.reidentificar_base,
                ).props("color=primary unelevated")
                self.botao_base_imobiliario_modulo_iv = ui.button(
                    "Gerar Base Imobiliária",
                    on_click=self.gerar_base_imobiliario_modulo_iv,
                ).props("color=primary unelevated")
    def autenticar_usuario(self):
        usuario = texto_valor(self.nome_usuario_input.value)
        senha = texto_valor(self.senha_input.value)

        if not usuario:
            ui.notify("Informe o nome do usuário.")
            return

        if senha != self.settings.senha_padrao:
            ui.notify("Senha inválida.")
            return

        self.state.autenticado = True
        self.state.usuario = usuario
        self.usuario_logado_label.set_text(f"Usuário: {usuario}")
        self.login_dialog.close()
        self._atualizar_botoes()
        ui.notify(f"Bem-vindo, {usuario}.")

    def abrir_login(self):
        self.login_dialog.open()

    def abrir_selecao_pasta_trabalho(self):
        if self.state.rodando:
            return
        if not self.state.autenticado:
            ui.notify("Faça login antes de selecionar a pasta de trabalho.")
            self.abrir_login()
            return

        self.pasta_trabalho_input.value = str(self.paths.work_dir)
        self.pasta_trabalho_status_label.set_text("")
        self.dialog_pasta_trabalho.open()

    def confirmar_pasta_trabalho(self):
        caminho = texto_valor(self.pasta_trabalho_input.value)
        if not caminho:
            self.pasta_trabalho_status_label.set_text("Informe o caminho da pasta.")
            return

        if not os.path.isdir(caminho):
            self.pasta_trabalho_status_label.set_text("Pasta não encontrada.")
            return

        self.paths.definir_pasta_trabalho(caminho)
        self.paths.garantir_pasta(self.paths.pasta_gerados)
        self.paths.garantir_pasta(self.paths.pasta_logs)
        self.dialog_pasta_trabalho.close()
        self._atualizar_status_entrada()
        self._atualizar_status()
        self._atualizar_botoes()
        ui.notify(f"Pasta de trabalho definida: {self.paths.work_dir}")

    def salvar_config_ui(self):
        self.config_service.salvar(self._config_atual())
        ui.notify(f"Configuração salva em {self.paths.arquivo_config_integracao}.")

    def _config_atual(self) -> dict:
        return {chave: int(campo.value) for chave, campo in self.campos_config.items()}

    async def abrir_confirmacao_processamento_legado(self):
        chave = texto_valor(self.chave_legado_input.value)
        if len(chave) < 8:
            ui.notify("Informe uma chave de pseudonimização com pelo menos 8 caracteres.")
            return

        await self._confirmar_processamento_legado()

    async def _confirmar_processamento_legado(self):
        with ui.dialog() as dialog, ui.card().classes("w-[500px] gap-4 rounded-lg"):
            ui.label("Confirmar Processamento dos Arquivos Originais").classes(
                "text-lg font-semibold text-slate-900"
            )
            ui.label("Os CSVs serão gerados na pasta dados_processados da pasta de trabalho.").classes(
                "text-sm text-slate-600"
            )
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancelar", on_click=dialog.close).props("flat")

                async def confirmar():
                    dialog.close()
                    await self.executar_processamento_legado()

                ui.button("Confirmar e Executar", on_click=confirmar).props("color=primary unelevated")

        dialog.open()

    async def executar_processamento_legado(self):
        chave = texto_valor(self.chave_legado_input.value)
        self.state.rodando = True
        self._atualizar_botoes()
        self._abrir_logs_processamento()

        def ao_progredir(linha: str):
            self._adicionar_log_processamento(linha)

        fila_progresso = queue.Queue()

        def registrar_progresso(linha: str):
            fila_progresso.put(linha)

        tarefa = asyncio.create_task(
            asyncio.to_thread(
                self.processamento_legado_service.executar,
                chave,
                registrar_progresso,
            )
        )

        try:
            while not tarefa.done():
                self._drenar_progresso(fila_progresso, ao_progredir)
                await asyncio.sleep(0.1)

            resumo = await tarefa
            self._drenar_progresso(fila_progresso, ao_progredir)
        except Exception as erro:
            self._adicionar_log_processamento(f"Erro: {erro}")
            self._finalizar_logs_processamento("Processamento dos Arquivos Originais: Erro")
            ui.notify(f"Erro no processamento dos arquivos originais: {erro}")
        else:
            texto = (
                f"{resumo['parametros']} parâmetro(s), {resumo['csvs_exportados']} CSV(s) exportado(s), "
                f"{len(resumo['erros'])} erro(s). Saída: {resumo['saida']}."
            )
            self.processamento_legado_status.set_text(texto)
            self._adicionar_log_processamento(texto)
            self._finalizar_logs_processamento("Processamento dos Arquivos Originais: Concluido")
            ui.notify("Processamento dos arquivos originais concluído.")
        finally:
            self.state.rodando = False
            self._atualizar_status_entrada()
            self._atualizar_status()
            self._atualizar_botoes()

    async def gerar_parametros(self):
        if self.state.rodando:
            return
        if not self.state.autenticado:
            ui.notify("Faça login antes de gerar os parâmetros.")
            self.abrir_login()
            return
        if not self.paths.existe("parametros"):
            ui.notify("Selecione uma pasta de trabalho que contenha a pasta parametros.")
            return

        self.state.rodando = True
        self._atualizar_botoes()
        self._abrir_loading("Gerando Parâmetros...", "Lendo a pasta parametros da pasta de trabalho.")

        try:
            resultado = await asyncio.to_thread(self.gerador_parametros_service.gerar)
        except Exception as erro:
            self._atualizar_loading("Parametrização: Erro", str(erro), 0)
            ui.notify(f"Erro ao gerar parâmetros: {erro}")
        else:
            arquivos = "\n".join(f"- {arquivo}" for arquivo in resultado.arquivos[:12])
            if len(resultado.arquivos) > 12:
                arquivos += f"\n- e mais {len(resultado.arquivos) - 12} arquivo(s)"
            erros = "\n".join(f"- {erro}" for erro in resultado.erros[:8])
            mensagem = (
                f"{resultado.gerados} arquivo(s) de parâmetros gerado(s).\n"
                f"Entrada: {resultado.entrada}\n"
                f"Saída: {resultado.saida}"
            )
            if arquivos:
                mensagem += f"\n\nArquivos:\n{arquivos}"
            if erros:
                mensagem += f"\n\nErros:\n{erros}"

            self._atualizar_loading("Parametrização: 100%", mensagem, 100)
            self.resultado_parametros_label.set_text(mensagem)
            self.dialog_resultado_parametros.open()
            ui.notify("Parâmetros gerados.")
        finally:
            self.state.rodando = False
            self._fechar_bloqueio()
            self._atualizar_status_entrada()
            self._atualizar_botoes()

    def _drenar_progresso(self, fila_progresso: queue.Queue, ao_progredir):
        while True:
            try:
                linha = fila_progresso.get_nowait()
            except queue.Empty:
                break
            ao_progredir(linha)

    async def abrir_confirmacao_preparacao(self):
        await self._confirmar_execucao(1, [self.paths.arquivo_preparacao])

    async def abrir_confirmacao_enriquecimento(self):
        await self._confirmar_execucao(2, [self.paths.arquivo_enriquecimento, self.paths.arquivo_log_merges])

    async def _confirmar_execucao(self, numero_execucao: int, arquivos: list[str]):
        with ui.dialog() as dialog, ui.card().classes("w-[460px] gap-4 rounded-lg"):
            ui.label(f"Confirmar {self._nome_execucao(numero_execucao)}").classes("text-lg font-semibold text-slate-900")
            ui.label("Arquivos que serão sobrescritos:").classes("text-sm text-slate-600")
            for arquivo in arquivos:
                ui.label(f"- {arquivo}").classes("font-mono text-sm text-slate-700")

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancelar", on_click=dialog.close).props("flat")

                async def confirmar():
                    dialog.close()
                    script = "preparacao.py" if numero_execucao == 1 else "enriquecimento.py"
                    await self.executar_script_com_progresso(numero_execucao, script)

                ui.button("Confirmar e Executar", on_click=confirmar).props("color=primary unelevated")

        dialog.open()

    async def executar_script_com_progresso(self, numero_execucao: int, script: str):
        if numero_execucao == 2:
            self.config_service.salvar(self._config_atual())

        self.paths.garantir_pasta(self.paths.pasta_gerados)
        self.paths.garantir_pasta(self.paths.pasta_logs)
        self.state.rodando = True
        self._atualizar_status()
        self._atualizar_botoes()
        self._abrir_loading(f"{self._nome_execucao(numero_execucao)}: Iniciando...", "")

        if not self.paths.resolver_codigo(script).exists():
            self._atualizar_loading(f"{self._nome_execucao(numero_execucao)}: Erro", f"Script não encontrado: {script}.", 0)
            ui.notify(f"Script não encontrado: {script}.")
            self.state.rodando = False
            self._fechar_bloqueio()
            self._atualizar_status()
            self._atualizar_botoes()
            return

        self.progresso_estimado = 0
        self.saida_execucao_atual = []

        def ao_progredir(linha: str):
            self.saida_execucao_atual.append(linha)
            self.progresso_estimado = self._calcular_progresso(linha, self.progresso_estimado)
            self._atualizar_loading(f"{self._nome_execucao(numero_execucao)}: {self.progresso_estimado}%", linha, self.progresso_estimado)

        codigo = await self.pipeline_runner.executar(script, ao_progredir)
        mostrar_resultado_enriquecimento = codigo == 0 and numero_execucao == 2

        if codigo == 0:
            self._atualizar_loading(f"{self._nome_execucao(numero_execucao)}: Concluída", "Processo finalizado.", 100)
        else:
            self._atualizar_loading(f"{self._nome_execucao(numero_execucao)}: Erro", "Processo finalizado com erro.", self.progresso_estimado)

        ui.notify(f"{self._nome_execucao(numero_execucao)} {'concluída' if codigo == 0 else 'terminou com erro'}.")
        self.state.rodando = False
        self._fechar_bloqueio()
        self._atualizar_status()
        self._atualizar_botoes()
        if mostrar_resultado_enriquecimento:
            self._mostrar_resultado_enriquecimento()

    def _calcular_progresso(self, texto: str, progresso_atual: int) -> int:
        percentual = extrair_porcentagem(texto)
        if percentual is None:
            return min(95, progresso_atual + 1)
        return max(progresso_atual, percentual)

    def _mostrar_resultado_enriquecimento(self):
        resumo = self._extrair_resumo_enriquecimento()
        self.resultado_enriquecimento_area.clear()

        with self.resultado_enriquecimento_area:
            if resumo:
                with ui.grid(columns=2).classes("w-full gap-3"):
                    for titulo, valor in resumo:
                        with ui.card().classes("gap-1 rounded-lg border border-slate-200 bg-white shadow-none"):
                            ui.label(titulo).classes("text-xs font-medium uppercase tracking-wide text-slate-500")
                            ui.label(valor).classes("text-xl font-semibold text-slate-900")
            else:
                ui.label("Não foi possível extrair o resumo estruturado. Últimas mensagens:").classes(
                    "text-sm text-slate-600"
                )
                for linha in self.saida_execucao_atual[-8:]:
                    if linha.strip():
                        ui.label(linha).classes("font-mono text-xs text-slate-700")

        self.dialog_resultado_enriquecimento.open()

    def _extrair_resumo_enriquecimento(self) -> list[tuple[str, str]]:
        linhas = [linha.strip() for linha in self.saida_execucao_atual if linha.strip()]
        resumo = []

        for linha in reversed(linhas):
            if "Invalidos:" in linha and "avaliados:" in linha and "juntados:" in linha:
                resumo.extend(self._extrair_pares_chave_valor(linha))
                break

        for linha in reversed(linhas):
            if "Revisao:" in linha or "Revisão:" in linha:
                resumo.extend(self._extrair_linha_revisao(linha))
                break

        titulos = {
            "Invalidos": "Registros inválidos",
            "avaliados": "Registros avaliados",
            "juntados": "Mesclagens automáticas",
            "restantes": "Registros restantes",
        }

        return [(titulos.get(titulo, titulo), valor) for titulo, valor in resumo]

    def _extrair_pares_chave_valor(self, linha: str) -> list[tuple[str, str]]:
        partes = [parte.strip() for parte in linha.split("|")]
        resultado = []
        for parte in partes:
            if ":" not in parte:
                continue
            chave, valor = parte.split(":", 1)
            resultado.append((chave.strip(), valor.strip()))
        return resultado

    def _extrair_linha_revisao(self, linha: str) -> list[tuple[str, str]]:
        texto = linha.split(":", 1)[-1].strip()
        partes = [parte.strip() for parte in texto.split("|")]
        resultado = []

        if partes:
            resultado.append(("Linhas marcadas para revisão", partes[0].replace("linhas marcadas", "").strip()))
        if len(partes) > 1:
            resultado.append(("Grupos de revisão", partes[1].replace("grupos", "").strip()))

        return resultado

    def _abrir_loading(self, titulo: str, linha: str):
        if not self._executar_ui(lambda: setattr(self.progresso_barra, "value", 0)):
            return False
        if not self._executar_ui(lambda: self.progresso_texto.set_text(titulo)):
            return False
        if not self._executar_ui(lambda: self.progresso_linha.set_text(linha)):
            return False
        return self._executar_ui(self.bloqueio.open)

    def _atualizar_loading(self, titulo: str, linha: str, percentual: int):
        if not self._executar_ui(lambda: setattr(self.progresso_barra, "value", max(0, min(100, percentual)))):
            return False
        if not self._executar_ui(lambda: self.progresso_texto.set_text(titulo)):
            return False
        return self._executar_ui(lambda: self.progresso_linha.set_text(linha[-220:] if linha else "Processando..."))

    def _fechar_bloqueio(self):
        return self._executar_ui(self.bloqueio.close)

    def _executar_ui(self, acao):
        try:
            acao()
            return True
        except RuntimeError as erro:
            texto = str(erro).lower()
            if "client" in texto and "deleted" in texto:
                return False
            if "parent element" in texto and "deleted" in texto:
                return False
            raise

    def _abrir_logs_processamento(self):
        self.saida_execucao_atual = []
        self.logs_processamento_titulo.set_text("Processamento dos Arquivos Originais")
        self.logs_processamento_status.set_text("Executando...")
        self.logs_processamento_texto.set_text("Iniciando processamento...")
        self.botao_fechar_logs_processamento.disable()
        self.dialog_logs_processamento.open()

    def _adicionar_log_processamento(self, linha: str):
        texto = linha.strip()
        if not texto:
            return

        self.saida_execucao_atual.append(texto)
        self.logs_processamento_texto.set_text("\n".join(self.saida_execucao_atual[-400:]))
        self.logs_processamento_status.set_text(texto[-180:])

    def _finalizar_logs_processamento(self, titulo: str):
        self.logs_processamento_titulo.set_text(titulo)
        self.logs_processamento_status.set_text("Execucao finalizada.")
        self.botao_fechar_logs_processamento.enable()

    def preparar_revisao(self):
        if not self.state.autenticado:
            raise PermissionError("Faça login antes de iniciar a revisão.")

        if not self.paths.existe(self.paths.arquivo_enriquecimento):
            raise FileNotFoundError(f"Arquivo não encontrado: {self.paths.arquivo_enriquecimento}.")

        df = self.revisao_service.carregar_dados()
        if "id_revisao" not in df.columns or COLUNA_MERGE_KEY not in df.columns:
            raise ValueError("O arquivo da Etapa 2 não contém as colunas obrigatórias.")

        pares = self.revisao_service.criar_pares_candidatos(df)
        decisoes = self.revisao_service.carregar_decisoes()
        indice_atual = self.revisao_service.primeiro_indice_pendente(pares, decisoes)
        return df, pares, decisoes, indice_atual

    async def iniciar_revisao(self):
        if self.state.rodando:
            return

        self.state.rodando = True
        self._atualizar_botoes()
        self._abrir_loading("Carregando Revisão Humana...", f"Lendo {self.paths.arquivo_enriquecimento}.")

        try:
            df, pares, decisoes, indice_atual = await asyncio.to_thread(self.preparar_revisao)
        except (FileNotFoundError, PermissionError, ValueError) as erro:
            ui.notify(str(erro))
        except Exception as erro:
            ui.notify(f"Erro ao carregar revisão: {erro}")
        else:
            self.state.df = df
            self.state.pares = pares
            self.state.decisoes = decisoes
            self.state.indice_atual = indice_atual
            self.state.etapa3_ativa = True
            ui.notify(f"Revisão carregada com {len(pares)} pares.")
        finally:
            self.state.rodando = False
            self._fechar_bloqueio()
            self._atualizar_status()
            self._atualizar_botoes()
            if self.state.etapa3_ativa:
                self._agendar_desenho_revisao()

    def mudar_indice(self, delta: int):
        total = len(self.state.pares)
        if total == 0:
            return
        self.state.indice_atual = max(0, min(total - 1, self.state.indice_atual + delta))
        self._agendar_desenho_revisao()

    def decidir(self, decisao: str, observacao: str = ""):
        if not self.state.pares:
            return
        if not self.state.autenticado:
            ui.notify("Faça login antes de registrar decisões.")
            self.abrir_login()
            return

        par = self.state.pares[self.state.indice_atual]
        self.revisao_service.registrar_decisao(
            self.state.decisoes,
            par,
            self.state.usuario,
            decisao,
            observacao,
        )
        self._proximo_pendente()
        self._agendar_desenho_revisao()

    def _proximo_pendente(self):
        inicio = self.state.indice_atual + 1
        for indice in range(inicio, len(self.state.pares)):
            if self.state.pares[indice]["par_id"] not in self.state.decisoes:
                self.state.indice_atual = indice
                return
        self.state.indice_atual = self.revisao_service.primeiro_indice_pendente(
            self.state.pares,
            self.state.decisoes,
        )

    def solicitar_geracao_arquivo_revisado(self):
        ui.timer(0.05, self.gerar_arquivo_revisado, once=True)

    async def gerar_arquivo_revisado(self):
        if self.state.df is None or self.state.rodando:
            return

        arquivo_saida = self._definir_arquivo_etapa3_saida()
        arquivo_remover = (
            self.paths.arquivo_integracao_parcial
            if arquivo_saida == self.paths.arquivo_integracao_final
            else self.paths.arquivo_integracao_final
        )

        self.state.rodando = True
        self._atualizar_botoes()
        self._abrir_loading("Gerando Arquivo Revisado...", "Aplicando decisões da revisão humana.")

        try:
            await asyncio.to_thread(
                self.revisao_service.salvar_arquivo_revisado,
                self.state.df,
                self.state.decisoes,
                arquivo_saida,
            )
            await asyncio.to_thread(self._remover_arquivo_se_existir, arquivo_remover)
        except Exception as erro:
            ui.notify(f"Erro ao gerar arquivo revisado: {erro}")
            self._atualizar_loading("Geração do Arquivo Revisado: Erro", str(erro), 0)
        else:
            self.state.arquivo_revisao_atual = arquivo_saida
            self._atualizar_loading("Geração do Arquivo Revisado: 100%", "Arquivo revisado gerado com sucesso.", 100)
            self._fechar_bloqueio()
            self.download_revisado_label.set_text(f"O arquivo foi salvo em {arquivo_saida}.")
            ui.notify(f"Arquivo salvo: {arquivo_saida}.")
            self.dialog_download_revisado.open()
        finally:
            self.state.rodando = False
            self._atualizar_botoes()
            self._fechar_bloqueio()

    def baixar_arquivo_revisado(self):
        arquivo = self.state.arquivo_revisao_atual or self._arquivo_revisao_existente()
        if not arquivo:
            ui.notify("Gere o arquivo revisado antes de baixar.")
            return

        caminho = self.paths.resolver(arquivo)
        if not caminho.exists():
            ui.notify("Gere o arquivo revisado antes de baixar.")
            return
        ui.download(str(caminho), filename=caminho.name)

    async def reidentificar_base(self):
        if self.state.rodando:
            return

        chave = texto_valor(self.chave_legado_input.value)
        if len(chave) < 8:
            ui.notify("Informe a chave de pseudonimização usada no processamento original.")
            return

        arquivo_entrada = self._arquivo_revisao_existente()
        if not arquivo_entrada:
            ui.notify("Gere o arquivo final ou parcial antes de reidentificar a base.")
            return

        self.state.rodando = True
        self._atualizar_botoes()
        self._abrir_loading("Reidentificando Base...", f"Lendo {arquivo_entrada}.")

        try:
            resultado = await asyncio.to_thread(
                self.reidentificacao_service.reidentificar,
                chave,
                arquivo_entrada,
            )
        except Exception as erro:
            ui.notify(f"Erro ao reidentificar a base: {erro}")
            self._atualizar_loading("Reidentificação: Erro", str(erro), 0)
        else:
            mensagem = (
                f"{resultado.valores_reidentificados} valor(es) reidentificado(s). "
                f"Arquivo salvo em {resultado.saida}."
            )
            self._atualizar_loading("Reidentificação: 100%", mensagem, 100)
            ui.notify(mensagem)
            caminho = self.paths.resolver(resultado.saida)
            ui.download(str(caminho), filename=caminho.name)
        finally:
            self.state.rodando = False
            self._fechar_bloqueio()
            self._atualizar_botoes()

    async def gerar_base_imobiliario_modulo_iv(self):
        if self.state.rodando:
            return

        chave = texto_valor(self.chave_legado_input.value)
        if len(chave) < 8:
            ui.notify("Informe a chave de pseudonimização usada no processamento original.")
            return

        arquivo_entrada = os.path.join(self.paths.pasta_dados_processados, "imobiliario.csv")
        if not self.paths.existe(arquivo_entrada):
            ui.notify("Arquivo dados_processados/imobiliario.csv não encontrado na pasta de trabalho.")
            return
        if not self.paths.existe(self.paths.arquivo_integracao_reidentificada):
            ui.notify("Gere a integração reidentificada antes de gerar a base imobiliária.")
            return

        self.state.rodando = True
        self._atualizar_botoes()
        self._abrir_loading("Gerando Base Imobiliária...", f"Lendo {arquivo_entrada}.")

        self.saida_execucao_atual = []
        chave_anterior = os.environ.get("key")
        os.environ["key"] = chave

        try:
            def ao_progredir(linha: str):
                if not linha.strip():
                    return
                self.saida_execucao_atual.append(linha)
                self._atualizar_loading("Base Imobiliária: Executando...", linha, 50)

            codigo = await self.pipeline_runner.executar(
                os.path.join("..", "moduloIV", "base_imobiliario.py"),
                ao_progredir,
            )

            if codigo != 0:
                ultimas_linhas = "\n".join(self.saida_execucao_atual[-8:]) or "Processo finalizado com erro."
                self._executar_ui(lambda: ui.notify("Erro ao gerar a base imobiliária."))
                self._atualizar_loading("Base Imobiliária: Erro", ultimas_linhas, 0)
                return

            resultado = self._extrair_resultado_modulo_iv()
            mensagem = (
                f"Telefones preenchidos: {resultado.get('celulares_preenchidos', 0)}\n"
                f"E-mails preenchidos: {resultado.get('emails_preenchidos', 0)}\n"
                f"Linhas com telefone adicionado pela integração: {resultado.get('telefones_enriquecidos', 0)}\n"
                f"Aumento por telefone: {self._formatar_percentual(resultado.get('percentual_telefones_enriquecidos', 0))}\n"
                f"Linhas com e-mail adicionado pela integração: {resultado.get('emails_enriquecidos', 0)}\n"
                f"Aumento por e-mail: {self._formatar_percentual(resultado.get('percentual_emails_enriquecidos', 0))}"
            )
            self._atualizar_loading("Base Imobiliária: 100%", mensagem, 100)
            if self._executar_ui(lambda: self.resultado_base_imobiliaria_label.set_text(mensagem)):
                self._executar_ui(self.dialog_resultado_base_imobiliaria.open)
            caminho = self.paths.resolver(resultado.get("saida", self.paths.arquivo_base_imobiliario_modulo_iv))
            self._executar_ui(lambda: ui.download(str(caminho), filename=caminho.name))
        except Exception as erro:
            self._executar_ui(lambda: ui.notify(f"Erro ao gerar a base imobiliária: {erro}"))
            self._atualizar_loading("Base Imobiliária: Erro", str(erro), 0)
        finally:
            if chave_anterior is None:
                os.environ.pop("key", None)
            else:
                os.environ["key"] = chave_anterior
            self.state.rodando = False
            self._fechar_bloqueio()
            self._executar_ui(self._atualizar_botoes)

    def _extrair_resultado_modulo_iv(self) -> dict:
        prefixo = "RESULTADO_MODULO_IV_JSON="
        for linha in reversed(self.saida_execucao_atual):
            if linha.startswith(prefixo):
                return json.loads(linha[len(prefixo):])
        return {}

    def _formatar_percentual(self, valor) -> str:
        try:
            return f"{float(valor):.2f}%".replace(".", ",")
        except (TypeError, ValueError):
            return "0,00%"

    def _definir_arquivo_etapa3_saida(self) -> str:
        return (
            self.paths.arquivo_integracao_final
            if self._contar_pares_pendentes() == 0
            else self.paths.arquivo_integracao_parcial
        )

    def _contar_pares_pendentes(self) -> int:
        grupos = self._agrupar_pares(self.state.pares)
        total_pares = len(grupos)
        pares_decididos = sum(
            1
            for itens in grupos.values()
            if all(par["par_id"] in self.state.decisoes for par in itens)
        )
        return max(total_pares - pares_decididos, 0)

    def _remover_arquivo_se_existir(self, arquivo: str):
        caminho = self.paths.resolver(arquivo)
        if caminho.exists():
            caminho.unlink()

    def _arquivo_revisao_existente(self) -> str:
        if self.paths.existe(self.paths.arquivo_integracao_final):
            return self.paths.arquivo_integracao_final
        if self.paths.existe(self.paths.arquivo_integracao_parcial):
            return self.paths.arquivo_integracao_parcial
        return ""

    def _agendar_desenho_revisao(self):
        ui.timer(0.05, self._desenhar_revisao, once=True)

    def _desenhar_revisao(self):
        self.area_revisao.clear()

        with self.area_revisao:
            if not self.state.etapa3_ativa:
                self.area_revisao.update()
                return

            ui.separator()
            ui.label("Revisão Humana").classes("text-2xl font-bold text-slate-900")

            pares = self.state.pares
            if not pares:
                ui.label("Nenhum candidato de revisão encontrado.").classes("text-slate-600")
                self.area_revisao.update()
                return

            grupos = self._agrupar_pares(pares)
            self._montar_resumo_revisao(pares, grupos)
            self._montar_par_atual(pares, grupos)

        self.area_revisao.update()

    def _agrupar_pares(self, pares: list[dict]) -> dict:
        grupos = {}
        for par in pares:
            grupos.setdefault(par["id_revisao"], []).append(par)
        return grupos

    def _montar_resumo_revisao(self, pares: list[dict], grupos: dict):
        total_pares = len(grupos)
        pares_decididos = sum(
            1
            for itens in grupos.values()
            if all(par["par_id"] in self.state.decisoes for par in itens)
        )
        pares_pendentes = max(total_pares - pares_decididos, 0)
        aprovados = sum(1 for item in self.state.decisoes.values() if item.get("decisao") == "aprovar")
        rejeitados = sum(1 for item in self.state.decisoes.values() if item.get("decisao") == "rejeitar")

        with ui.row().classes("w-full gap-3"):
            for titulo, valor in [
                ("Pares", total_pares),
                ("Pares pendentes", pares_pendentes),
                ("Pares decididos", pares_decididos),
                ("Aprovados", aprovados),
                ("Rejeitados", rejeitados),
            ]:
                with ui.card().classes("min-w-[150px] gap-1 rounded-lg shadow-sm border border-slate-200 bg-white"):
                    ui.label(titulo).classes("text-xs font-medium uppercase tracking-wide text-slate-500")
                    ui.label(str(valor)).classes("text-2xl font-semibold text-slate-900")

    def _montar_par_atual(self, pares: list[dict], grupos: dict):
        indice = min(self.state.indice_atual, len(pares) - 1)
        self.state.indice_atual = indice
        par = pares[indice]
        ids_ordenados = list(grupos)
        numero_par = ids_ordenados.index(par["id_revisao"]) + 1
        total_pares = len(grupos)
        linha_valida = self.state.df.loc[par["idx_valido"]]
        linha_invalida = self.state.df.loc[par["idx_invalido"]]
        decisao_atual = self.state.decisoes.get(par["par_id"], {}).get("decisao", "pendente")
        observacao_atual = self.state.decisoes.get(par["par_id"], {}).get("observacao", "")

        with ui.card().classes("w-full gap-3"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.button("Anterior", on_click=lambda: self.mudar_indice(-1)).props("outline color=primary")
                ui.label(
                    f"Par {numero_par} de {total_pares} | Linha {indice + 1} de {len(pares)} | "
                    f"Grupo {par['id_revisao']} | Status {decisao_atual.capitalize()}"
                ).classes("font-semibold text-slate-900")
                ui.button("Próximo", on_click=lambda: self.mudar_indice(1)).props("outline color=primary")

            ui.label(
                f"Índice válido: {par['idx_valido']} | "
                f"Índice inválido: {par['idx_invalido']} | "
                f"Score: {formatar_score(par.get('score_revisao', ''))} | "
                f"Merge key: {texto_valor(linha_valida[COLUNA_MERGE_KEY])}"
            ).classes("text-sm text-slate-600")

            self._montar_registros_lado_a_lado(linha_valida, linha_invalida)

            colunas = [
                {"name": "coluna", "label": "Coluna", "field": "coluna", "align": "left"},
                {"name": "valido", "label": "Válido", "field": "valido", "align": "left"},
                {"name": "invalido", "label": "Inválido", "field": "invalido", "align": "left"},
                {"name": "situacao", "label": "Situação", "field": "situacao", "align": "left"},
            ]

            campo_observacao = ui.textarea("Observações da decisão", value=observacao_atual).props(
                "outlined autogrow"
            ).classes("w-full")

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button(
                    "Gerar Arquivo Revisado",
                    on_click=self.solicitar_geracao_arquivo_revisado,
                ).props("outline color=primary")
                ui.button("Baixar Arquivo Revisado", on_click=self.baixar_arquivo_revisado).props(
                    "outline color=primary"
                )
                ui.button("Pausar Revisão", on_click=self.pausar_revisao).props("outline color=secondary")
                ui.button(
                    "Rejeitar Merge",
                    on_click=lambda: self.decidir("rejeitar", campo_observacao.value),
                ).props("color=negative unelevated")
                ui.button(
                    "Aprovar Merge",
                    on_click=lambda: self.decidir("aprovar", campo_observacao.value),
                ).props("color=primary unelevated")

    def _montar_registros_lado_a_lado(self, linha_valida, linha_invalida):
        colunas = [
            {"name": "campo", "label": "Campo", "field": "campo", "align": "left"},
            {"name": "valor", "label": "Valor", "field": "valor", "align": "left"},
        ]

        with ui.row().classes("w-full gap-3 items-start"):
            with ui.card().classes("flex-1 min-w-0 gap-2 border border-slate-200 bg-white shadow-none"):
                ui.label("Registro válido").classes("text-sm font-semibold text-slate-900")
                with ui.element("div").classes("w-full max-h-[420px] overflow-y-auto rounded-lg border border-slate-200"):
                    ui.table(
                        columns=colunas,
                        rows=self._linhas_registro(linha_valida),
                        pagination={"rowsPerPage": 0},
                    ).props("hide-pagination").classes("w-full")

            with ui.card().classes("flex-1 min-w-0 gap-2 border border-slate-200 bg-white shadow-none"):
                ui.label("Registro inválido").classes("text-sm font-semibold text-slate-900")
                with ui.element("div").classes("w-full max-h-[420px] overflow-y-auto rounded-lg border border-slate-200"):
                    ui.table(
                        columns=colunas,
                        rows=self._linhas_registro(linha_invalida),
                        pagination={"rowsPerPage": 0},
                    ).props("hide-pagination").classes("w-full")

    def _linhas_registro(self, linha) -> list[dict]:
        linhas = []
        for campo, valor in linha.items():
            texto = texto_valor(valor)
            if not texto:
                continue
            linhas.append({"campo": campo, "valor": texto})
        return linhas

    def pausar_revisao(self):
        self.state.etapa3_ativa = False
        self._agendar_desenho_revisao()
        ui.notify("Revisão pausada. As decisões já registradas ficam salvas.")

    def _atualizar_status_entrada(self):
        self.pasta_trabalho_label.set_text(f"Pasta atual: {self.paths.work_dir}")
        arquivos = self.entrada_service.listar_csvs()
        parametros = self.processamento_legado_service.listar_parametros()
        self.processamento_legado_status.set_text(
            f"{len(parametros)} arquivo(s) parametros_*.txt encontrado(s)."
        )
        if not arquivos:
            self.arquivos_entrada_label.set_text("Nenhum CSV encontrado na pasta de trabalho.")
            return

        texto = ", ".join(arquivos[:6])
        if len(arquivos) > 6:
            texto += f" e mais {len(arquivos) - 6}"
        self.arquivos_entrada_label.set_text(f"{len(arquivos)} CSV(s): {texto}")

    def _nome_execucao(self, numero: int) -> str:
        return "Preparação" if numero == 1 else "Enriquecimento"

    def _atualizar_status(self):
        preparacao_existe = self.paths.existe(self.paths.arquivo_preparacao)
        enriquecimento_existe = self.paths.existe(self.paths.arquivo_enriquecimento)
        self.card_preparacao.set_text("Pronta" if preparacao_existe else "Pendente")
        self.card_enriquecimento.set_text("Pronta" if enriquecimento_existe else "Pendente")
        self.card_revisao.set_text("Disponível" if enriquecimento_existe else "Aguardando")

    def _atualizar_botoes(self):
        preparacao_existe = self.paths.existe(self.paths.arquivo_preparacao)
        enriquecimento_existe = self.paths.existe(self.paths.arquivo_enriquecimento)
        imobiliario_existe = self.paths.existe(os.path.join(self.paths.pasta_dados_processados, "imobiliario.csv"))
        integracao_reidentificada_existe = self.paths.existe(self.paths.arquivo_integracao_reidentificada)
        parametros_existe = self.paths.existe("parametros")
        entrada_existe = bool(self.entrada_service.listar_csvs())
        rodando = self.state.rodando
        autenticado = self.state.autenticado

        self._definir_habilitado(self.botao_pasta_trabalho, autenticado and not rodando)
        self._definir_habilitado(self.botao_processamento_legado, autenticado and not rodando)
        self._definir_habilitado(self.botao_gerar_parametros, autenticado and not rodando and parametros_existe)
        self._definir_habilitado(self.botao_preparacao, autenticado and not rodando and entrada_existe)
        self._definir_habilitado(self.botao_enriquecimento, autenticado and not rodando and preparacao_existe)
        self._definir_habilitado(self.botao_revisao, autenticado and not rodando and enriquecimento_existe)
        self._definir_habilitado(
            self.botao_reidentificacao,
            autenticado and not rodando and bool(self._arquivo_revisao_existente()),
        )
        self._definir_habilitado(
            self.botao_base_imobiliario_modulo_iv,
            autenticado and not rodando and imobiliario_existe and integracao_reidentificada_existe,
        )
        self._definir_habilitado(self.botao_salvar_config, autenticado and not rodando)

    def _definir_habilitado(self, elemento, habilitado: bool):
        if habilitado:
            elemento.enable()
        else:
            elemento.disable()



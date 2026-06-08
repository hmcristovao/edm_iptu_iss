import asyncio
import os
from pathlib import Path

from nicegui import ui

from app_config import COLUNA_MERGE_KEY, AppPaths, AppSettings
from app_services import (
    EntradaService,
    IntegracaoConfigService,
    PipelineRunner,
    RevisaoService,
    extrair_porcentagem,
    formatar_score,
    texto_valor,
)
from app_state import AppState


class IntegracaoEnriquecimentoApp:
    def __init__(self):
        self.paths = AppPaths()
        self.settings = AppSettings()
        self.state = AppState()
        self.config_service = IntegracaoConfigService(self.paths, self.settings)
        self.entrada_service = EntradaService(self.paths)
        self.revisao_service = RevisaoService(self.paths)
        self.pipeline_runner = PipelineRunner(self.paths)
        self.campos_config = {}
        self.progresso_estimado = 0
        self.navegador_pasta_atual = self.paths.work_dir

    def run(self):
        self._configurar_tema()
        self._montar_dialogos()
        self._montar_layout()
        self._desenhar_revisao()
        self._atualizar_status_entrada()
        self._atualizar_status()
        self._atualizar_botoes()
        ui.timer(0.1, self.abrir_login, once=True)
        ui.run(title="Integração e Enriquecimento", reload=False)

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
        with self.dialog_pasta_trabalho, ui.card().classes("w-[760px] gap-4 rounded-lg"):
            ui.label("Selecionar Pasta de Trabalho").classes("text-xl font-semibold text-slate-900")
            ui.label(
                "Navegue até a pasta onde estão os CSVs de entrada. As pastas arquivos_gerados e logs serão criadas dentro dela."
            ).classes("text-sm text-slate-600")
            self.navegador_path_label = ui.label("").classes(
                "w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 font-mono text-xs text-slate-700"
            )
            self.pasta_trabalho_status_label = ui.label("").classes("text-sm text-slate-600")
            with ui.row().classes("w-full gap-2"):
                ui.button("Discos", on_click=self.ir_para_lista_de_discos).props("outline color=secondary")
                ui.button("Voltar", on_click=self.ir_para_pasta_pai).props("outline color=secondary")
                ui.button("Atualizar", on_click=self.atualizar_navegador_pastas).props("outline color=secondary")
            self.navegador_area = ui.column().classes(
                "w-full max-h-[430px] gap-1 overflow-y-auto rounded-lg border border-slate-200 p-2"
            )
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

        self.bloqueio = ui.dialog().props("persistent")
        with self.bloqueio, ui.card().classes("w-[520px] gap-4 rounded-lg"):
            ui.label("Execução em Andamento").classes("text-lg font-semibold text-slate-900")
            self.progresso_texto = ui.label("Aguardando...")
            self.progresso_barra = ui.linear_progress(value=0).props("instant-feedback").classes("w-full")
            self.progresso_linha = ui.label("").classes("text-sm text-slate-600")

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

        self.navegador_pasta_atual = self.paths.work_dir if self.paths.work_dir.exists() else Path.home()
        self.pasta_trabalho_status_label.set_text("")
        self.atualizar_navegador_pastas()
        self.dialog_pasta_trabalho.open()

    def confirmar_pasta_trabalho(self):
        caminho = self.navegador_pasta_atual
        if not caminho.is_dir():
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

    def atualizar_navegador_pastas(self):
        self.navegador_area.clear()
        atual = self.navegador_pasta_atual
        self.navegador_path_label.set_text(str(atual))
        self.pasta_trabalho_status_label.set_text(self._resumo_pasta(atual))

        with self.navegador_area:
            pastas = self._listar_pastas_navegador(atual)
            if not pastas:
                ui.label("Nenhuma subpasta disponível.").classes("text-sm text-slate-500")
                return

            for pasta in pastas:
                ui.button(
                    pasta.name,
                    on_click=lambda p=pasta: self.ir_para_pasta(p),
                ).props("flat align=left").classes("w-full justify-start text-left")

    def ir_para_pasta(self, pasta: Path):
        if pasta.is_dir():
            self.navegador_pasta_atual = pasta
            self.atualizar_navegador_pastas()

    def ir_para_pasta_pai(self):
        atual = self.navegador_pasta_atual
        pai = atual.parent
        if pai != atual and pai.exists():
            self.navegador_pasta_atual = pai
            self.atualizar_navegador_pastas()

    def ir_para_lista_de_discos(self):
        self.navegador_area.clear()
        self.navegador_path_label.set_text("Discos disponíveis")
        self.pasta_trabalho_status_label.set_text("Selecione um disco para navegar.")

        with self.navegador_area:
            for disco in self._listar_discos():
                ui.button(
                    str(disco),
                    on_click=lambda p=disco: self.ir_para_pasta(p),
                ).props("flat align=left").classes("w-full justify-start text-left")

    def _listar_discos(self) -> list[Path]:
        if os.name != "nt":
            return [Path("/")]

        discos = []
        for letra in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            disco = Path(f"{letra}:\\")
            if disco.exists():
                discos.append(disco)
        return discos

    def _listar_pastas_navegador(self, pasta: Path) -> list[Path]:
        try:
            return sorted(
                [item for item in pasta.iterdir() if item.is_dir()],
                key=lambda item: item.name.lower(),
            )
        except (OSError, PermissionError):
            self.pasta_trabalho_status_label.set_text("Não foi possível acessar esta pasta.")
            return []

    def _resumo_pasta(self, pasta: Path) -> str:
        try:
            qtd_csv = sum(1 for item in pasta.iterdir() if item.is_file() and item.name.lower().endswith(".csv"))
        except (OSError, PermissionError):
            return "Não foi possível contar os CSVs desta pasta."

        return f"CSVs encontrados nesta pasta: {qtd_csv}"

    def salvar_config_ui(self):
        self.config_service.salvar(self._config_atual())
        ui.notify(f"Configuração salva em {self.paths.arquivo_config_integracao}.")

    def _config_atual(self) -> dict:
        return {chave: int(campo.value) for chave, campo in self.campos_config.items()}

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
            self.bloqueio.close()
            self._atualizar_status()
            self._atualizar_botoes()
            return

        self.progresso_estimado = 0

        def ao_progredir(linha: str):
            self.progresso_estimado = self._calcular_progresso(linha, self.progresso_estimado)
            self._atualizar_loading(f"{self._nome_execucao(numero_execucao)}: {self.progresso_estimado}%", linha, self.progresso_estimado)

        codigo = await self.pipeline_runner.executar(script, ao_progredir)

        if codigo == 0:
            self._atualizar_loading(f"{self._nome_execucao(numero_execucao)}: Concluída", "Processo finalizado.", 100)
        else:
            self._atualizar_loading(f"{self._nome_execucao(numero_execucao)}: Erro", "Processo finalizado com erro.", self.progresso_estimado)

        ui.notify(f"{self._nome_execucao(numero_execucao)} {'concluída' if codigo == 0 else 'terminou com erro'}.")
        self.state.rodando = False
        self.bloqueio.close()
        self._atualizar_status()
        self._atualizar_botoes()

    def _calcular_progresso(self, texto: str, progresso_atual: int) -> int:
        percentual = extrair_porcentagem(texto)
        if percentual is None:
            return min(95, progresso_atual + 1)
        return max(progresso_atual, percentual)

    def _abrir_loading(self, titulo: str, linha: str):
        self.progresso_barra.value = 0
        self.progresso_texto.set_text(titulo)
        self.progresso_linha.set_text(linha)
        self.bloqueio.open()

    def _atualizar_loading(self, titulo: str, linha: str, percentual: int):
        self.progresso_barra.value = max(0, min(100, percentual))
        self.progresso_texto.set_text(titulo)
        self.progresso_linha.set_text(linha[-220:] if linha else "Processando...")

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
            self.bloqueio.close()
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
            self.bloqueio.close()
            self.download_revisado_label.set_text(f"O arquivo foi salvo em {arquivo_saida}.")
            ui.notify(f"Arquivo salvo: {arquivo_saida}.")
            self.dialog_download_revisado.open()
        finally:
            self.state.rodando = False
            self._atualizar_botoes()
            self.bloqueio.close()

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
        entrada_existe = bool(self.entrada_service.listar_csvs())
        rodando = self.state.rodando
        autenticado = self.state.autenticado

        self._definir_habilitado(self.botao_pasta_trabalho, autenticado and not rodando)
        self._definir_habilitado(self.botao_preparacao, autenticado and not rodando and entrada_existe)
        self._definir_habilitado(self.botao_enriquecimento, autenticado and not rodando and preparacao_existe)
        self._definir_habilitado(self.botao_revisao, autenticado and not rodando and enriquecimento_existe)
        self._definir_habilitado(self.botao_salvar_config, autenticado and not rodando)

    def _definir_habilitado(self, elemento, habilitado: bool):
        if habilitado:
            elemento.enable()
        else:
            elemento.disable()


if __name__ in {"__main__", "__mp_main__"}:
    IntegracaoEnriquecimentoApp().run()

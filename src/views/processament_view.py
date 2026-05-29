import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import logging
import os
from pathlib import Path
from dotenv import load_dotenv, set_key

from src.Domain.Package import Package
from src.handlers.Pseudonymization_handler import PseudonymizationHandler
from src.handlers.adapters.anomizador.anonimizador_reversivel_adaptado import AnonimizadorReversivel
from src.handlers.export_handler import ExportHandler
from src.handlers.extractor_handler import ExtractorHandler
from src.handlers.standardization_handler import StandardizationHandler
from src.usecase.leitor import ParameterReader
from src.views.components.Text_component import TextHandler


class ProcessamentoFrame(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master)
        self.controller = controller

        # Setup de Paths (herdado do seu original)
        self.ROOT_DIR = Path(__file__).resolve().parent.parent.parent
        self.dotenv_path = self.ROOT_DIR / 'config' / '.env'
        load_dotenv(dotenv_path=self.dotenv_path)

        self.is_password_visible = False
        self._build_ui()
        self.setup_logging()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        # Botão Voltar
        ctk.CTkButton(self, text="← Voltar ao Menu", width=100, fg_color="transparent", border_width=1,
                      command=lambda: self.controller.show_frame("Menu")).grid(row=0, column=0, padx=20, pady=10,
                                                                               sticky="w")

        ctk.CTkLabel(self, text="Painel de Processamento", font=("Arial", 22, "bold")).grid(row=1, pady=10)

        # Frame de Configurações
        self.config_frame = ctk.CTkFrame(self)
        self.config_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.config_frame.grid_columnconfigure(1, weight=1)

        # Pasta
        ctk.CTkLabel(self.config_frame, text="Pasta de Origem:", font=("Arial", 12, "bold")).grid(row=0, column=0,
                                                                                                  padx=10, pady=10,
                                                                                                  sticky="w")
        self.path_entry = ctk.CTkEntry(self.config_frame)
        self.path_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.path_entry.insert(0, os.getenv("DATA_PATH", ""))
        ctk.CTkButton(self.config_frame, text="Buscar", width=100, command=self.browse_directory).grid(row=0, column=2,
                                                                                                       padx=10)

        # Chave
        ctk.CTkLabel(self.config_frame, text="Chave Mestra:", font=("Arial", 12, "bold")).grid(row=1, column=0, padx=10,
                                                                                               pady=10, sticky="w")
        self.key_frame = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        self.key_frame.grid(row=1, column=1, columnspan=2, padx=10, pady=10, sticky="ew")
        self.key_frame.grid_columnconfigure(0, weight=1)

        self.key_entry = ctk.CTkEntry(self.key_frame, show="*")
        self.key_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.key_entry.insert(0, os.getenv("key", ""))
        ctk.CTkButton(self.key_frame, text="👁️", width=40, command=self.toggle_password_visibility).grid(row=0,
                                                                                                         column=1,
                                                                                                         padx=2)
        ctk.CTkButton(self.key_frame, text="Ajuda", width=60, command=self.show_key_help).grid(row=0, column=2, padx=2)

        # Barra de Progresso
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        self.progress_bar.set(0)

        # Botão Iniciar
        self.run_btn = ctk.CTkButton(self, text="INICIAR PIPELINE", height=50, fg_color="#28a745",
                                     font=("Arial", 16, "bold"), command=self.execute_async)
        self.run_btn.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

        # Console
        self.log_box = ctk.CTkTextbox(self, font=("Consolas", 12))
        self.log_box.grid(row=5, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.log_box.configure(state="disabled")

    # --- Lógica do seu código original (Métodos permanecem os mesmos) ---
    def setup_logging(self):
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        handler = TextHandler(self.log_box)
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | [%(name)s] | %(message)s', '%H:%M:%S')
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        self.logger = logging.getLogger("SAAEApp")

    def toggle_password_visibility(self):
        self.is_password_visible = not self.is_password_visible
        self.key_entry.configure(show="" if self.is_password_visible else "*")

    def show_key_help(self):
        messagebox.showinfo("Segurança", "Use uma chave com pelo menos 16 caracteres.")

    def browse_directory(self):
        path = filedialog.askdirectory()
        if path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, path)

    def validate_inputs(self):
        key = self.key_entry.get().strip()
        path = Path(self.path_entry.get())
        if not key or len(key) < 8:
            return False, "Chave inválida (mínimo 8 caracteres)."
        if not path.exists():
            return False, "O caminho selecionado não existe."
        return True, (path, key)

    def execute_async(self):
        valid, result = self.validate_inputs()
        if not valid:
            messagebox.showwarning("Erro", result)
            return
        self.run_btn.configure(state="disabled", text="PROCESSANDO...")
        threading.Thread(target=self.run_pipeline, args=result, daemon=True).start()

    def run_pipeline(self, data_path, key_value):
        try:
            # 1. Persistência
            os.environ["key"] = key_value
            os.environ["DATA_PATH"] = str(data_path)
            app_dotenv_path = self.ROOT_DIR / "config" / ".env"
            app_dotenv_path.parent.mkdir(parents=True, exist_ok=True)
            set_key(str(app_dotenv_path), "key", key_value)
            set_key(str(app_dotenv_path), "DATA_PATH", str(data_path))

            # 2. Setup do Pipeline
            extractor = ExtractorHandler()
            standardizer = StandardizationHandler()
            anon_adapter = AnonimizadorReversivel()
            pseudo = PseudonymizationHandler(anon_adapter)
            exporter = ExportHandler()

            extractor.set_next(standardizer)
            standardizer.set_next(pseudo)
            pseudo.set_next(exporter)

            arquivos = list(data_path.rglob("parametros_*.txt"))
            total_arquivos = len(arquivos)

            if total_arquivos == 0:
                self.logger.warning("Nenhum arquivo .txt encontrado.")
                return

            self.logger.info(f"Iniciando lote: {total_arquivos} arquivos.")

            for i, arquivo in enumerate(arquivos):
                try:
                    self.logger.info(f"[{i + 1}/{total_arquivos}] Processando: {arquivo.name}")
                    param = ParameterReader(arquivo).ler_arquivo()
                    package = Package(param)
                    extractor.handle(request=package)
                except Exception as file_error:
                    self.logger.error(f"Erro no arquivo {arquivo.name}: {file_error}")

                progress = (i + 1) / total_arquivos
                self.after(0, lambda p=progress: self.progress_bar.set(p))

            resumo = f"PROCESSAMENTO CONCLUÍDO.\n\n📁 Total: {total_arquivos}\n📄 CSVs: {exporter.iteracao}"
            self.logger.info(resumo)
            messagebox.showinfo("Fim do Processo", resumo)

        except Exception as e:
            self.logger.error(f"Erro Crítico: {e}")
            messagebox.showerror("Erro Crítico", str(e))
        finally:
            self.run_btn.after(0, lambda: self.run_btn.configure(state="normal", text="INICIAR PIPELINE"))


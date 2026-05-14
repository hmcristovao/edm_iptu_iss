import pathlib

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import logging
import os
from pathlib import Path
from dotenv import load_dotenv, set_key

# Importações internas do projeto
try:
    from src.Domain.Package import Package
    from src.handlers.Pseudonymization_handler import PseudonymizationHandler
    from src.handlers.adapters.anomizador.anonimizador_reversivel_adaptado import AnonimizadorReversivel
    from src.handlers.export_handler import ExportHandler
    from src.handlers.extractor_handler import ExtractorHandler
    from src.handlers.standardization_handler import StandardizationHandler
    from src.usecase.leitor import ParameterReader
except ImportError as e:
    print(f"❌ Erro de Dependência: {e}")


class TextHandler(logging.Handler):
    """Direciona logs do Python diretamente para o widget CTkTextbox."""

    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)

        def append():
            self.text_widget.configure(state="normal")
            self.text_widget.insert("end", msg + "\n")
            self.text_widget.see("end")
            self.text_widget.configure(state="disabled")

        self.text_widget.after(0, append)


class SAAEApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Inicialização de Paths ---
        self.ROOT_DIR = Path(__file__).resolve().parent.parent.parent
        self.dotenv_path = self.ROOT_DIR / 'config' / '.env'
        load_dotenv(dotenv_path=self.dotenv_path)

        # --- Configuração de Janela ---
        self.title("SAAE - Sistema de Pseudonimização")
        self.geometry("900x800")
        ctk.set_appearance_mode("Dark")

        self.is_password_visible = False
        self._build_ui()
        self.setup_logging()

    def _build_ui(self):
        """Constrói a interface gráfica completa."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)  # Ajustado para acomodar barra de progresso

        # Header
        ctk.CTkLabel(self, text="Painel de Processamento SAAE", font=("Arial", 24, "bold")).grid(row=0, pady=20)

        # Frame de Configurações
        self.config_frame = ctk.CTkFrame(self)
        self.config_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.config_frame.grid_columnconfigure(1, weight=1)

        # Input: Pasta
        ctk.CTkLabel(self.config_frame, text="Pasta de Origem:", font=("Arial", 12, "bold")).grid(row=0, column=0,
                                                                                                  padx=10, pady=10,
                                                                                                  sticky="w")
        self.path_entry = ctk.CTkEntry(self.config_frame)
        self.path_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.path_entry.insert(0, os.getenv("DATA_PATH", ""))
        ctk.CTkButton(self.config_frame, text="Buscar", width=100, command=self.browse_directory).grid(row=0, column=2,
                                                                                                       padx=10)

        # Input: Chave
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
        self.progress_bar.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.progress_bar.set(0)

        # Botão de Execução
        self.run_btn = ctk.CTkButton(self, text="INICIAR PIPELINE", height=50, fg_color="#28a745",
                                     font=("Arial", 16, "bold"), command=self.execute_async)
        self.run_btn.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        # Console
        self.log_box = ctk.CTkTextbox(self, font=("Consolas", 12))
        self.log_box.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.log_box.configure(state="disabled")

    def setup_logging(self):
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        handler = TextHandler(self.log_box)

        # Adicionamos [%(name)s] ao formato para mostrar a origem
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | [%(name)s] | %(message)s',
            '%H:%M:%S'
        )

        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        self.logger = logging.getLogger("SAAEApp")

    def toggle_password_visibility(self):
        self.is_password_visible = not self.is_password_visible
        self.key_entry.configure(show="" if self.is_password_visible else "*")

    def show_key_help(self):
        messagebox.showinfo("Segurança", "Use uma chave com pelo menos 16 caracteres. Guarde em local seguro.")

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
        self.progress_bar.set(0)
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

            self.logger.info(f"Iniciando lote: {total_arquivos} arquivos encontrados.")

            success_count = 0
            error_count = 0
            pastas_processadas = set()
            # 3. Processamento
            for i, arquivo in enumerate(arquivos):
                try:
                    self.logger.info(f"[{i + 1}/{total_arquivos}] Processando: {arquivo.name}")
                    param = ParameterReader(arquivo).ler_arquivo()
                    package = Package(param)

                    extractor.handle(request=package)


                except Exception as file_error:
                    self.logger.error(f"Erro no arquivo {arquivo.name}: {file_error}")

                # Atualização visual da barra
                progress = (i + 1) / total_arquivos
                self.after(0, lambda p=progress: self.progress_bar.set(p))
            pasta_saida = pathlib.Path(package.parameters.saida)

            # Conta quantas subpastas existem dentro do caminho informado
            quantidade_csv = sum(1 for item in pasta_saida.rglob("*.csv") if item.is_file())
            relatorio_pastas = "\n".join([f"📁 {p}" for p in sorted(pastas_processadas)])
            resumo = (
                f"PROCESSAMENTO CONCLUÍDO.\n\n"
                f"📁 Quantidade de arquivos de saida: {total_arquivos}\n\n"
                f"📄 Quantidade de arquivos CSV gerados: {exporter.iteracao}\n\n"
                f"⚠️ Quantidade de pastas não processadas: {total_arquivos - exporter.iteracao}\n"
                f"🔎 Consulte os logs para mais detalhes.\n\n"
            )

            self.logger.info(resumo)
            messagebox.showinfo("Fim do Processo", resumo)

        except Exception as e:
            self.logger.error(f"Erro Crítico: {e}")
            messagebox.showerror("Erro Crítico", str(e))
        finally:
            self.run_btn.after(0, lambda: self.run_btn.configure(state="normal", text="INICIAR PIPELINE"))


if __name__ == "__main__":
    app = SAAEApp()
    app.mainloop()
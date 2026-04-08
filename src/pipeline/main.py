import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import hashlib
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv, set_key

# --- Configuração de Path para o seu projeto SAAE ---
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))

try:
    from src.Domain.Package import Package
    from src.handlers.Pseudonymization_handler import PseudonymizationHandler
    from src.handlers.adapters.anomizador.anonimizador_reversivel_adaptado import AnonimizadorReversivel
    from src.handlers.export_handler import ExportHandler
    from src.handlers.extractor_handler import ExtractorHandler
    from src.handlers.standardization_handler import StandardizationHandler
    from src.usecase.leitor import ParameterReader
except ImportError as e:
    print(f"⚠️ Erro de Importação: {e}. Verifique a estrutura de pastas 'src'.")


class TextHandler(logging.Handler):
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
    def toggle_password(self):
        """Alterna a visibilidade da chave entre asteriscos e texto plano."""
        if self.is_password_visible:
            self.key_entry.configure(show="*")
            self.btn_view_key.configure(text="👁️")
            self.is_password_visible = False
        else:
            self.key_entry.configure(show="")
            self.btn_view_key.configure(text="🔒")  # Ícone de cadeado quando visível
            self.is_password_visible = True
    def __init__(self):
        super().__init__()

        # Configurações de Path
        self.dotenv_path = ROOT_DIR / 'dados' / '.env'
        load_dotenv(dotenv_path=self.dotenv_path)

        self.title("Data Pipeline & Pseudonymization")
        self.geometry("800x650")
        ctk.set_appearance_mode("Dark")

        # --- UI LAYOUT ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # 1. Título
        self.header = ctk.CTkLabel(self, text="Pipeline de Processamento", font=("Arial", 20, "bold"))
        self.header.grid(row=0, column=0, pady=20)

        # 2. Frame de Configurações
        self.config_frame = ctk.CTkFrame(self)
        self.config_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.config_frame.grid_columnconfigure(1, weight=1)

        # Campo Caminho
        ctk.CTkLabel(self.config_frame, text="Pasta de Dados:", font=("Arial", 12, "bold")).grid(row=0, column=0,
                                                                                                 padx=10, pady=10,
                                                                                                 sticky="w")
        self.path_entry = ctk.CTkEntry(self.config_frame)
        self.path_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.path_entry.insert(0, os.getenv("DATA_PATH", str(ROOT_DIR / 'dados')))

        self.btn_browse = ctk.CTkButton(self.config_frame, text="📁", width=40, command=self.browse)
        self.btn_browse.grid(row=0, column=2, padx=10)

        # --- Campo Chave com Botão de Visualização ---
        ctk.CTkLabel(self.config_frame, text="Chave (key):", font=("Arial", 12, "bold")).grid(row=1, column=0, padx=10,
                                                                                              pady=10, sticky="w")

        # Frame interno para agrupar Entry + Botão Olho
        self.key_container = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        self.key_container.grid(row=1, column=1, columnspan=2, padx=10, pady=10, sticky="ew")
        self.key_container.grid_columnconfigure(0, weight=1)

        self.key_entry = ctk.CTkEntry(self.key_container, show="*")
        self.key_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.key_entry.insert(0, os.getenv("key", ""))

        # Botão de Olho (Toggle)
        self.is_password_visible = False
        self.btn_view_key = ctk.CTkButton(self.key_container, text="👁️", width=40,
                                          fg_color="transparent", text_color="white",
                                          hover_color="#333333", command=self.toggle_password)
        self.btn_view_key.grid(row=0, column=1)
        # 3. Botão de Ação
        self.run_btn = ctk.CTkButton(self, text="EXECUTAR PIPELINE", height=50,
                                     fg_color="#1f6aa5", font=("Arial", 16, "bold"),
                                     command=self.start_thread)
        self.run_btn.grid(row=2, column=0, padx=20, pady=20, sticky="ew")

        # 4. Console de Logs
        self.log_box = ctk.CTkTextbox(self, font=("Consolas", 12))
        self.log_box.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.log_box.configure(state="disabled")

        self.setup_logging()

    def setup_logging(self):
        self.logger = logging.getLogger("SAAE_INTEGRATED")
        self.logger.setLevel(logging.INFO)

        handler = TextHandler(self.log_box)

        # CORREÇÃO AQUI:
        # O primeiro argumento é o formato da MENSAGEM.
        # O segundo argumento (datefmt) é onde você usa %H:%M:%S.
        formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )

        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def browse(self):
        path = filedialog.askdirectory()
        if path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, path)

    def start_thread(self):
        self.run_btn.configure(state="disabled", text="PROCESSANDO...")
        threading.Thread(target=self.run_pipeline, daemon=True).start()

    def run_pipeline(self):
        data_path = Path(self.path_entry.get())
        key_value = self.key_entry.get()

        if not key_value:
            self.logger.error("ERRO: A chave 'key' não pode estar vazia!")
            self.run_btn.after(0, lambda: self.run_btn.configure(state="normal", text="EXECUTAR PIPELINE"))
            return

        # --- INTEGRAÇÃO CRÍTICA ---
        # 1. Seta a variável de ambiente em tempo de execução para o processo atual
        os.environ['key'] = key_value
        # 2. Persiste no arquivo .env para o próximo boot
        if not self.dotenv_path.parent.exists(): self.dotenv_path.parent.mkdir(parents=True)
        set_key(str(self.dotenv_path), "key", key_value)
        set_key(str(self.dotenv_path), "DATA_PATH", str(data_path))

        self.logger.info("Configurações validadas e injetadas no ambiente.")

        try:
            arquivos = list(data_path.rglob("*.txt"))
            if not arquivos:
                self.logger.warning(f"Nenhum arquivo .txt em {data_path}")

            for arquivo in arquivos:
                self.logger.info(f"######################################################################")
                self.logger.info(f"Iniciando: {arquivo.name}")

                # Seu fluxo original
                parameter = ParameterReader(arquivo).ler_arquivo()
                self.logger.warning(f"Iniciando: {parameter.pasta}")
                package = Package(parameter)

                extractor = ExtractorHandler()
                standardizer = StandardizationHandler()
                anon = AnonimizadorReversivel()  # Este cara vai ler o os.environ['key']
                pseudo = PseudonymizationHandler(anon)
                exporthandler = ExportHandler()

                extractor.set_next(standardizer)
                standardizer.set_next(pseudo)
                pseudo.set_next(exporthandler)

                package = extractor.handle(request=package)
                self.logger.info(f"Sucesso no arquivo: {arquivo.name}")

            self.logger.info("Pipeline finalizado com sucesso!")
            messagebox.showinfo("SAAE", "Processamento Concluído!")

        except Exception as e:
            self.logger.error(f"Falha crítica no pipeline: {str(e)}")

        finally:
            self.run_btn.after(0, lambda: self.run_btn.configure(state="normal", text="EXECUTAR PIPELINE"))


if __name__ == "__main__":
    app = SAAEApp()
    app.mainloop()
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv, set_key

# --- Configuração de Path para o projeto SAAE ---
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
    def __init__(self):
        super().__init__()

        # Configurações de Path e Ambiente
        self.dotenv_path = ROOT_DIR / 'dados' / '.env'
        load_dotenv(dotenv_path=self.dotenv_path)

        self.title("SAAE - Sistema de Pseudonimização")
        self.geometry("900x750")
        ctk.set_appearance_mode("Dark")
        self.is_password_visible = False

        # --- UI LAYOUT ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # 1. Cabeçalho
        self.header = ctk.CTkLabel(self, text="Painel de Processamento de Dados", font=("Arial", 24, "bold"))
        self.header.grid(row=0, column=0, pady=(20, 10))

        # 2. Frame de Configurações
        self.config_frame = ctk.CTkFrame(self)
        self.config_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.config_frame.grid_columnconfigure(1, weight=1)

        # Seleção de Pasta
        ctk.CTkLabel(self.config_frame, text="Pasta de Arquivos:", font=("Arial", 12, "bold")).grid(row=0, column=0,
                                                                                                    padx=10, pady=10,
                                                                                                    sticky="w")
        self.path_entry = ctk.CTkEntry(self.config_frame, placeholder_text="Caminho dos arquivos .txt")
        self.path_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.path_entry.insert(0, os.getenv("DATA_PATH", str(ROOT_DIR / 'dados')))

        self.btn_browse = ctk.CTkButton(self.config_frame, text="Selecionar", width=100, command=self.browse)
        self.btn_browse.grid(row=0, column=2, padx=10)

        # Campo Chave (Key)
        ctk.CTkLabel(self.config_frame, text="Chave Mestra (Key):", font=("Arial", 12, "bold")).grid(row=1, column=0,
                                                                                                     padx=10, pady=10,
                                                                                                     sticky="w")

        self.key_container = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        self.key_container.grid(row=1, column=1, columnspan=2, padx=10, pady=10, sticky="ew")
        self.key_container.grid_columnconfigure(0, weight=1)

        self.key_entry = ctk.CTkEntry(self.key_container, show="*", placeholder_text="Chave para criptografia")
        self.key_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.key_entry.insert(0, os.getenv("key", ""))

        self.btn_view_key = ctk.CTkButton(self.key_container, text="👁️", width=40, fg_color="#444",
                                          command=self.toggle_password)
        self.btn_view_key.grid(row=0, column=1, padx=2)

        self.btn_help_key = ctk.CTkButton(self.key_container, text="❓ Ajuda", width=80, fg_color="#1f6aa5",
                                          command=self.mostrar_dicas_chave)
        self.btn_help_key.grid(row=0, column=2, padx=2)

        # 3. Botão de Execução Principal
        self.run_btn = ctk.CTkButton(self, text="EXECUTAR PIPELINE", height=60, fg_color="#28a745",
                                     hover_color="#218838", font=("Arial", 18, "bold"), command=self.start_thread)
        self.run_btn.grid(row=2, column=0, padx=20, pady=20, sticky="ew")

        # 4. Console de Logs
        self.log_box = ctk.CTkTextbox(self, font=("Consolas", 12), border_width=2)
        self.log_box.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.log_box.configure(state="disabled")

        self.setup_logging()

    def setup_logging(self):
        """Configura o logger global para que todas as classes internas enviem logs para a UI."""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)

        for h in root_logger.handlers[:]:
            root_logger.removeHandler(h)

        handler = TextHandler(self.log_box)
        formatter = logging.Formatter(fmt='%(asctime)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S')
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        self.logger = root_logger

    def toggle_password(self):
        if self.is_password_visible:
            self.key_entry.configure(show="*")
            self.btn_view_key.configure(text="👁️")
            self.is_password_visible = False
        else:
            self.key_entry.configure(show="")
            self.btn_view_key.configure(text="🔒")
            self.is_password_visible = True

    def mostrar_dicas_chave(self):
        dicas = (
            "Dicas para uma Chave Segura:\n\n"
            "• Recomendado: 12 a 16 caracteres.\n"
            "• Use letras maiúsculas, minúsculas, números e símbolos.\n"
            "• Exemplo: Projet0_SAAE_#2026\n\n"
            "⚠️ IMPORTANTE: Esta chave é necessária para ler os dados futuramente. "
            "Se você alterá-la, os novos arquivos usarão a nova chave."
        )
        messagebox.showinfo("Dicas de Segurança", dicas)

    def validar_chave(self, chave):
        if not chave:
            return False, "O campo da chave não pode estar vazio."
        if len(chave) < 8:
            return False, "A chave deve ter no mínimo 8 caracteres."
        if chave.isnumeric() or chave.isalpha():
            return False, "Chave muito fraca! Misture letras e números."
        return True, ""

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
        key_value = self.key_entry.get().strip()

        # 1. Validação de Segurança
        ok, msg = self.validar_chave(key_value)
        if not ok:
            self.logger.error(f"Erro: {msg}")
            messagebox.showwarning("Atenção", msg)
            self.run_btn.after(0, lambda: self.run_btn.configure(state="normal", text="EXECUTAR PIPELINE"))
            return

        # 2. Configuração de Ambiente
        os.environ['key'] = key_value
        if not self.dotenv_path.parent.exists(): self.dotenv_path.parent.mkdir(parents=True)
        set_key(str(self.dotenv_path), "key", key_value)
        set_key(str(self.dotenv_path), "DATA_PATH", str(data_path))

        self.logger.info("Configuração salva. Iniciando varredura de arquivos...")

        try:
            arquivos = list(data_path.rglob("*.txt"))

            # 3. Verificação de Arquivos Alvo (Correção do falso positivo)
            if not arquivos:
                self.logger.warning(f"Nenhum arquivo encontrado em: {data_path}")
                messagebox.showwarning("Pasta Vazia", f"Não foram encontrados arquivos .txt na pasta selecionada.")
                self.run_btn.after(0, lambda: self.run_btn.configure(state="normal", text="EXECUTAR PIPELINE"))
                return

            sucessos = 0
            for arquivo in arquivos:
                self.logger.info("-" * 40)
                self.logger.info(f"Processando: {arquivo.name}")

                parameter = ParameterReader(arquivo).ler_arquivo()
                package = Package(parameter)

                extractor = ExtractorHandler()
                standardizer = StandardizationHandler()
                anon_adapter = AnonimizadorReversivel()
                pseudo = PseudonymizationHandler(anon_adapter)
                exporter = ExportHandler()

                extractor.set_next(standardizer)
                standardizer.set_next(pseudo)
                pseudo.set_next(exporter)

                extractor.handle(request=package)
                sucessos += 1
                self.logger.info(f"Arquivo concluído: {arquivo.name}")

            # 4. Feedback Final
            if sucessos > 0:
                self.logger.info("=" * 40)
                self.logger.info(f"Pipeline finalizado. Total: {sucessos} arquivos.")
                messagebox.showinfo("Sucesso",
                                    f"Processamento concluído com sucesso!\n{sucessos} arquivos processados.")

        except Exception as e:
            self.logger.error(f"ERRO NO PROCESSO: {str(e)}")
            messagebox.showerror("Erro Crítico", f"Ocorreu uma falha inesperada:\n{str(e)}")

        finally:
            self.run_btn.after(0, lambda: self.run_btn.configure(state="normal", text="EXECUTAR PIPELINE"))


if __name__ == "__main__":
    app = SAAEApp()
    app.mainloop()
import pathlib
import customtkinter as ctk
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import logging
import os
from pathlib import Path
from dotenv import load_dotenv, set_key
import pandas as pd

from src.handlers.adapters.anomizador.anonimizador_reversivel_adaptado import AnonimizadorReversivel
from src.views.components.Text_component import TextHandler

class DescriptFrame(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master)
        self.controller = controller

        # Variáveis de controle
        self.is_password_visible = False

        # --- Configuração de Grid ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(6, weight=1)  # Faz o log_box expandir

        # --- 1. Cabeçalho ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")

        ctk.CTkButton(self.header_frame, text="← Voltar", width=80, fg_color="transparent",
                      border_width=1, command=lambda: self.controller.show_frame("Menu")).pack(side="left")

        ctk.CTkLabel(self, text="Módulo de Descriptografia",
                     font=("Arial", 22, "bold")).grid(row=1, column=0, pady=5)

        # --- 2. Frame de Configurações ---
        self.config_frame = ctk.CTkFrame(self)
        self.config_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.config_frame.grid_columnconfigure(1, weight=1)

        # Pasta
        ctk.CTkLabel(self.config_frame, text="Pasta de Arquivos:", font=("Arial", 12, "bold")).grid(row=0, column=0,
                                                                                                    padx=10, pady=10,
                                                                                                    sticky="w")
        self.path_entry = ctk.CTkEntry(self.config_frame)
        self.path_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
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
        ctk.CTkButton(self.key_frame, text="👁️", width=40, command=self.toggle_password_visibility).grid(row=0,
                                                                                                         column=1)

        # --- 3. Barra de Progresso ---
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        self.progress_bar.set(0)

        # --- 4. Botão de Ação ---
        self.run_btn = ctk.CTkButton(self, text="DESCRIPTOGRAFAR CPFS", height=50,
                                     fg_color="#c0392b", hover_color="#a93226",  # Vermelho para diferenciar
                                     font=("Arial", 16, "bold"),
                                     command=self.execute_decryption)
        self.run_btn.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

        # --- 5. Tela de Log (Console) ---
        ctk.CTkLabel(self, text="Logs do Sistema:", font=("Arial", 12, "bold")).grid(row=5, column=0, padx=20,
                                                                                     sticky="w")
        self.log_box = ctk.CTkTextbox(self, font=("Consolas", 12))
        self.log_box.grid(row=6, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.log_box.configure(state="disabled")

        # Inicializa o Logger para esta tela
        self.setup_logging()

    # --- Lógica e Handlers ---
    def setup_logging(self):
        # Usamos o mesmo TextHandler definido no início do seu código
        self.logger = logging.getLogger("VargemAlta_Reversao")
        handler = TextHandler(self.log_box)
        formatter = logging.Formatter('%(asctime)s | %(message)s', '%H:%M:%S')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def browse_directory(self):
        path = filedialog.askdirectory()
        if path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, path)

    def toggle_password_visibility(self):
        self.is_password_visible = not self.is_password_visible
        self.key_entry.configure(show="" if self.is_password_visible else "*")

    def execute_decryption(self):
        caminho = self.path_entry.get().strip()
        chave = self.key_entry.get().strip()

        if not caminho or not chave:
            messagebox.showwarning("Erro", "Preencha a pasta e a chave mestra.")
            return

        self.run_btn.configure(state="disabled", text="DESCRIPTOGRAFANDO...")
        self.logger.info("Iniciando varredura de arquivos...")

        # Inicia a busca e processamento em uma thread separada
        threading.Thread(target=self.processar_arquivos_csv, args=(caminho, chave), daemon=True).start()

    def processar_arquivos_csv(self, caminho_pasta, chave):
        try:
            # Configura a variável de ambiente para que a classe AnonimizadorReversivel a encontre
            os.environ['key'] = chave

            # Inicializa o motor de descriptografia
            deserializador = AnonimizadorReversivel()

            pasta = Path(caminho_pasta)
            arquivos = list(pasta.rglob("*.csv"))
            total = len(arquivos)

            if total == 0:
                self.logger.warning("Nenhum arquivo CSV encontrado.")
                return

            for i, arquivo in enumerate(arquivos):
                self.logger.info(f"📂 Lendo: {arquivo.name}")

                # 1. Carregar o arquivo
                # Usamos low_memory=False para evitar avisos de tipos de dados mistos
                df = pd.read_csv(arquivo,
                                  sep=None,
                                  engine='python',
                                  dtype=str,
                                  on_bad_lines='warn',
                                  encoding='utf-8'
                                 )

                # 2. Identificar colunas que contêm "cpf" (Case Insensitive)
                colunas_cpf = [col for col in df.columns if 'cpf' in col.lower()]

                if not colunas_cpf:
                    self.logger.info(f"⚠️ Nenhuma coluna de CPF encontrada em {arquivo.name}. Pulando...")
                    continue

                # 3. Aplicar a descriptografia em cada coluna identificada
                for col in colunas_cpf:
                    self.logger.info(f"   🔓 Descriptografando coluna: {col}")

                    # Aplicamos a função decrypt da sua classe AnonimizadorReversivel
                    # O .apply garante que processamos linha por linha
                    df[col] = df[col].apply(lambda x: deserializador.decrypt(x) if pd.notnull(x) else x)

                # 4. Salvar o arquivo (Sobrescrevendo ou criando um novo)
                # Aqui salvamos como _DESCRIPTOGRAFADO para segurança, ou você pode manter o original
                novo_nome = arquivo.parent / f"REVERSO_{arquivo.name}"
                df.to_csv(novo_nome, index=False, encoding='utf-8')

                self.logger.info(f"✅ Arquivo salvo: {novo_nome.name}")

                # Atualiza barra de progresso
                progresso = (i + 1) / total
                self.after(0, lambda p=progresso: self.progress_bar.set(p))

            self.logger.info("🎉 Processo de Lapidação (Vargem Alta) finalizado!")
            messagebox.showinfo("Sucesso", "Os CPFs foram restaurados com sucesso!")

        except Exception as e:
            self.logger.error(f"Erro crítico no Pandas: {str(e)}")
            messagebox.showerror("Erro", f"Falha ao processar CSV: {str(e)}")
        finally:
            self.after(0, lambda: self.run_btn.configure(state="normal", text="DESCRIPTOGRAFAR CPFS"))
    def _finalizar_exemplo(self):
        self.progress_bar.set(1.0)
        self.logger.info("Processo concluído com sucesso!")
        self.run_btn.configure(state="normal")
        messagebox.showinfo("Sucesso", "CPFs descriptografados na pasta de destino.")

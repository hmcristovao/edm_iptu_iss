import customtkinter as ctk
from tkinter import filedialog, messagebox
import hashlib
import os
from dotenv import load_dotenv, set_key

ENV_FILE = ".env"
load_dotenv(ENV_FILE)


class AppHash(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Hash Vault Professional")
        self.geometry("650x500")
        ctk.set_appearance_mode("Dark")

        # Grid layout 1x2
        self.grid_columnconfigure(0, weight=1)

        # --- Estilização ---
        self.font_bold = ctk.CTkFont(size=13, weight="bold")
        self.accent_color = "#1f6aa5"

        # --- Seção de Entrada (Input Section) ---
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.label_path = ctk.CTkLabel(self.input_frame, text="Alvo (Arquivo ou Diretório):", font=self.font_bold)
        self.label_path.grid(row=0, column=0, padx=15, pady=(15, 0), sticky="w")

        # Container para Entry + Botões de busca
        self.path_container = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        self.path_container.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        self.path_container.grid_columnconfigure(0, weight=1)

        self.entry_path = ctk.CTkEntry(self.path_container, placeholder_text="Selecione ou cole o caminho...")
        self.entry_path.grid(row=0, column=0, padx=(5, 10), sticky="ew")
        self.entry_path.insert(0, os.getenv("LAST_PATH", ""))
        self.entry_path.bind("<KeyRelease>", self.validate_path)

        self.btn_file = ctk.CTkButton(self.path_container, text="📄 Arquivo", width=90,
                                      command=lambda: self.browse("file"))
        self.btn_file.grid(row=0, column=1, padx=2)

        self.btn_folder = ctk.CTkButton(self.path_container, text="📁 Pasta", width=90,
                                        command=lambda: self.browse("folder"), fg_color="#4a4a4a")
        self.btn_folder.grid(row=0, column=2, padx=2)

        # --- Seção de Chave ---
        self.label_key = ctk.CTkLabel(self.input_frame, text="Chave de Criptografia:", font=self.font_bold)
        self.label_key.grid(row=2, column=0, padx=15, sticky="w")

        self.entry_key = ctk.CTkEntry(self.input_frame, show="*", placeholder_text="Sua chave secreta...")
        self.entry_key.grid(row=3, column=0, padx=15, pady=(5, 20), sticky="ew")
        self.entry_key.insert(0, os.getenv("SECRET_KEY", ""))

        # --- Botão de Ação ---
        self.btn_run = ctk.CTkButton(self, text="GERAR HASH E SALVAR CONFIG", height=45,
                                     font=ctk.CTkFont(size=14, weight="bold"),
                                     fg_color="#28a745", hover_color="#218838",
                                     command=self.process_hash)
        self.btn_run.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")

        # --- Output/Log ---
        self.output_box = ctk.CTkTextbox(self, height=120, font=("Consolas", 12))
        self.output_box.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")

        self.validate_path()  # Validação inicial

    def validate_path(self, event=None):
        """Muda a borda da entrada para dar feedback visual de caminho válido."""
        path = self.entry_path.get()
        if os.path.exists(path):
            self.entry_path.configure(border_color="green")
        else:
            self.entry_path.configure(border_color="#942626")

    def browse(self, mode):
        # Tenta abrir no diretório atual do .env ou no diretório base
        initial_dir = os.path.dirname(self.entry_path.get()) if self.entry_path.get() else "/"

        if mode == "file":
            path = filedialog.askopenfilename(initialdir=initial_dir, title="Selecionar Arquivo")
        else:
            path = filedialog.askdirectory(initialdir=initial_dir, title="Selecionar Pasta")

        if path:
            self.entry_path.delete(0, ctk.END)
            self.entry_path.insert(0, path)
            self.validate_path()

    def calculate_hash(self, path, key):
        sha256 = hashlib.sha256(key.encode())

        if os.path.isfile(path):
            with open(path, "rb") as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
        else:
            # Se for pasta, faz o hash da lista de arquivos (exemplo simples)
            files = sorted(os.listdir(path))
            sha256.update("".join(files).encode())

        return sha256.hexdigest()

    def process_hash(self):
        path = self.entry_path.get()
        key = self.entry_key.get()

        if not os.path.exists(path) or not key:
            messagebox.showwarning("Erro", "Caminho ou Chave inválidos!")
            return

        # Salva no .env
        if not os.path.exists(ENV_FILE): open(ENV_FILE, 'w').close()
        set_key(ENV_FILE, "LAST_PATH", path)
        set_key(ENV_FILE, "SECRET_KEY", key)

        try:
            result = self.calculate_hash(path, key)
            self.output_box.delete("1.0", ctk.END)
            self.output_box.insert("1.0", f"✅ CONFIG SALVA NO .ENV\n\n🎯 ALVO: {path}\n🔑 HASH: {result}")
            self.clipboard_clear()
            self.clipboard_append(result)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha no processamento: {e}")


if __name__ == "__main__":
    app = AppHash()
    app.mainloop()
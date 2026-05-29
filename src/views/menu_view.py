
import customtkinter as ctk

class MenuFrame(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master)
        self.controller = controller

        # Design do Menu
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="Gestão de Dados", font=("Arial", 28, "bold")).grid(row=0, pady=(100, 40))

        btn_proc = ctk.CTkButton(self, text="Pipeline de Extração", width=350, height=60,
                                 font=("Arial", 16, "bold"),
                                 command=lambda: controller.show_frame("Processamento"))
        btn_proc.grid(row=1, pady=15)

        btn_outra = ctk.CTkButton(self, text="Descriptografar Base de Dados", width=350, height=60,
                                  font=("Arial", 16, "bold"), fg_color="#555",
                                  command=lambda: controller.show_frame("Descript"))
        btn_outra.grid(row=2, pady=15)
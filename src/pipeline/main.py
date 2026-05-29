import customtkinter as ctk

from src.views.descript_view import DescriptFrame
from src.views.menu_view import MenuFrame
from src.views.processament_view import ProcessamentoFrame


class SAAEApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Sistema Unifica Dados - Labcidades ")
        self.geometry("900x800")
        ctk.set_appearance_mode("Dark")

        # Container onde as telas são empilhadas
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {}

        for F in (MenuFrame, ProcessamentoFrame, DescriptFrame):
            page_name = F.__name__.replace("Frame", "")
            frame = F(master=self.container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("Menu")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()


if __name__ == "__main__":
    app = SAAEApp()
    app.mainloop()
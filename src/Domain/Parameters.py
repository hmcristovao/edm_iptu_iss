class Parameters():
    def __init__(self, pasta: str,footer:int, header:int, saida: str, sufixo: list[str], variaveis: list = None):
        self.pasta = pasta
        self.saida = saida
        self.header =  header
        self.footer = footer
        self.sufixo = sufixo
        self.variaveis = variaveis or []

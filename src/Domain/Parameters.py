class Parameters():
    def __init__(self, pasta: str, saida: str, sufixo: list[str], variaveis: list = None):
        self.pasta = pasta
        self.saida = saida
        self.sufixo = sufixo
        self.variaveis = variaveis or []

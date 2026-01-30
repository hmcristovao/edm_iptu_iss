class Parameters():
    def __init__(self, pasta: str,seq:str,footer:int, header:int, formato:str,saida: str, sufixo: list[str], variaveis: list = None):
        self.pasta = pasta
        self.saida = saida
        self.header =  header
        self.footer = footer
        self.sufixo = sufixo
        self.formato = formato
        self.seq = seq
        self.variaveis = variaveis or []

    def _get_differences(self, other):
        if not isinstance(other, Parameters):
            return "Os objetos não são da mesma classe."

        diffs = {}
        for key, value in self.__dict__.items():
            other_value = other.__dict__.get(key)
            if value != other_value:
                diffs[key] = {'self': value, 'other': other_value}

        return diffs

    def __eq__(self, other):
        if not isinstance(other, Parameters):
            return False
        if(self.__dict__ != other.__dict__):
            print(self._get_differences(other))
            return False
        else:
            return True


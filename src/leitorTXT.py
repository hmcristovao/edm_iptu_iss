import re
import pandas as pd

class LeitorParametros:
    """
    get_dados_gerais - Retorna o dicionário ("Chave: Valor") do cabeçalho do arquivo. 

    get_dataframe_variaveis - Retorna um DataFrame contendo as variáveis ordenadas.
    """
     
    def __init__(self, caminho_arquivo):
        self.caminho = caminho_arquivo
        self.dados_gerais = {}
        self.variaveis = []
        self.df_variaveis = None

        self.padrao_kv = re.compile(r"^(\w+):\s*(.*)$")
        self.padrao_var = re.compile(r"^(\d+)\s+(.*?)\:\s*(.*)$")
        self.ler_arquivo()


    def ler_arquivo(self):
        """Lê o arquivo e separa em dados gerais e variáveis."""
        with open(self.caminho, "r", encoding="utf-8") as f:
            linhas = f.readlines()

        lendo_variaveis = False

        for linha in linhas:
            linha = linha.strip()
            if not linha:
                continue

            if linha.lower().startswith("variáveis"):
                lendo_variaveis = True
                continue

            if not lendo_variaveis:
                self._processar_dado_geral(linha)
            else:
                self._processar_variavel(linha)

        self._criar_dataframe()

    def _processar_dado_geral(self, linha):
        """Processa linhas do tipo chave: valor."""
        match = self.padrao_kv.match(linha)
        if match:
            chave = match.group(1).lower()
            valor = match.group(2)
            self.dados_gerais[chave] = valor

    def _processar_variavel(self, linha):
        """Processa linhas de variáveis."""
        match = self.padrao_var.match(linha)
        if match:
            id_var = int(match.group(1))
            nome = match.group(2)
            colunas = [c.strip() for c in match.group(3).split(",")]
            self.variaveis.append([id_var, nome, colunas])

    def _criar_dataframe(self):
        """Cria o DataFrame final das variáveis."""
        self.df_variaveis = pd.DataFrame(
            self.variaveis,
            columns=["ordem", "nome", "colunas"]
        )

        self.df_variaveis = self.df_variaveis.sort_values(
            by="ordem", ascending=True
        ).reset_index(drop=True)

    def get_dados_gerais(self):
        return self.dados_gerais

    def get_dataframe_variaveis(self):
        return self.df_variaveis

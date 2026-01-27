from ProcesssadorDados import ProcessadorDados
from leitorTXT import LeitorParametros


if __name__ == "__main__":
    parametros = ["../dados/Saae/parametros_Saae.txt",
                  "../dados/Saude_bairros/parametros_Saude_bairros.txt"
                  ]

    for parametro in parametros:
        leitor = LeitorParametros(parametro)

        print("Dados Gerais:")
        print(leitor.get_dados_gerais())

        print("\nVariáveis:")
        print(leitor.get_dataframe_variaveis())

        proc = ProcessadorDados(leitor.get_dataframe_variaveis(), leitor.get_dados_gerais())
        df_final = proc.executarPipeline()
        print("Total de linhas:", len(df_final))
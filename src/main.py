from Saae import ProcessadorSaae

if __name__ == "__main__":
    proc = ProcessadorSaae("../dados/Saae")
    df_final = proc.processar()
    print("Total de linhas:", len(df_final))
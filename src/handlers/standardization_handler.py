from src.Domain.Package import Package
from src.handlers.Handler import AbstractHandler


class StandardizationHandler(AbstractHandler):
    def _renomear_colunas_mapeadas(self, df, lista_mapeamento):
        for item in lista_mapeamento:
            for nome_amigavel, colunas_tecnicas in item.items():

                # 1. Caso Simples: Um único item na lista (Renomeação Direta)
                if len(colunas_tecnicas) == 1:
                    col_destino = colunas_tecnicas[0]
                    if nome_amigavel in df.columns:
                        df.rename(columns={nome_amigavel: col_destino}, inplace=True)
                        print(f"Sucesso: {nome_amigavel} renomeado para {col_destino}")
                    else:
                        print(f"Alerta: Coluna original '{nome_amigavel}' não encontrada.")

                # 2. Caso Complexo: Múltiplos itens (Regras de Negócio: CPF, CNPJ, etc.)
                elif len(colunas_tecnicas) > 1:
                    if nome_amigavel not in df.columns:
                        print(f"Pulo: Coluna '{nome_amigavel}' ausente. Não foi possível criar {colunas_tecnicas}.")
                        continue


                    # Limpeza base: remove caracteres não numéricos uma única vez
                    serie_limpa = df[nome_amigavel].astype(str).str.replace(r"\D", "", regex=True)

                    for col_alvo in colunas_tecnicas:
                        if col_alvo == 'cpf':
                            df[col_alvo] = serie_limpa.where(serie_limpa.str.len() == 11, "")
                            print(f"Sucesso: Criada coluna CPF a partir de {nome_amigavel}")

                        elif col_alvo == 'cnpj':
                            df[col_alvo] = serie_limpa.where(serie_limpa.str.len() == 14, "")
                            print(f"Sucesso: Criada coluna CNPJ a partir de {nome_amigavel}")

                        elif col_alvo == 'cpfValido':
                            df[col_alvo] = serie_limpa.where(serie_limpa.str.len() == 11, "").apply(lambda x: "S" if self.validarCpf(x) else "N")
                            print(f"Sucesso: Criada coluna cpf valido a partir de {nome_amigavel}")
                        elif col_alvo == 'cnpjValido':
                            df[col_alvo] = serie_limpa.where(serie_limpa.str.len() == 14, "").apply(lambda x: "S" if self.validarCnpj(x) else "N")
                            print(f"Sucesso: Criada coluna cnpj valido a partir de {nome_amigavel}")
                        else :
                            print(f"Atenção: Nenhuma regra específica aplicada para a coluna '{nome_amigavel}' (Alvos: {col_alvo})")




                    # Remove a coluna original após processar as regras de documentos
                    if nome_amigavel == "Documento" and nome_amigavel in df.columns:
                        df.drop(columns=[nome_amigavel], inplace=True)

                else:
                    print(f"Erro: A chave '{nome_amigavel}' está vazia no mapeamento.")

        return df
    @staticmethod
    def validarCpf(cpf: str) -> bool:
        cpf = ''.join(filter(str.isdigit, str(cpf)))

        if len(cpf) != 11:
            return False
        if cpf == cpf[0] * 11:
            return False

        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        d1 = (soma * 10) % 11
        d1 = 0 if d1 == 10 else d1

        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        d2 = (soma * 10) % 11
        d2 = 0 if d2 == 10 else d2

        return cpf[-2:] == f"{d1}{d2}"

    @staticmethod
    def validarCnpj(cnpj: str) -> bool:
        cnpj = ''.join(filter(str.isdigit, str(cnpj)))

        if len(cnpj) != 14:
            return False
        if cnpj == cnpj[0] * 14:
            return False

        pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        pesos2 = [6] + pesos1

        soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
        d1 = 11 - (soma % 11)
        d1 = 0 if d1 >= 10 else d1

        soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
        d2 = 11 - (soma % 11)
        d2 = 0 if d2 >= 10 else d2

        return cnpj[-2:] == f"{d1}{d2}"

    def handle(self, request: Package) -> Package:
        request =Package(request.parameters, self._renomear_colunas_mapeadas(request.datas,request.parameters.variaveis))

        return super().handle(request)

from src.Domain.Parameters import Parameters


class ParameterReader:
    def __init__(self, caminho_arquivo):
        self.caminho = caminho_arquivo

    def ler_arquivo(self) -> Parameters:
        config = {
            'Pasta': '',
            'Saída': '',
            'Footer' :int,
            'Header' :int,
            'Sufixo': [],
            'Variáveis': []
        }

        with open(self.caminho, 'r', encoding='utf-8') as f:
            linhas = f.readlines()

        for linha in linhas:
            linha = linha.strip()
            if not linha: continue

            if linha.startswith('Pasta:'):
                config['Pasta'] = linha.split(':', 1)[1].strip()
            elif linha.startswith('Saída :'):
                config['Saída'] = linha.split(':', 1)[1].strip()
            elif linha.startswith('Footer :'):
                config['Footer'] = int(linha.split(':', 1)[1].strip())
            elif linha.startswith('Header :'):
                config['Header'] = int(linha.split(':', 1)[1].strip())
            elif linha.startswith('Sufixo:'):
                config['Sufixo'] = [linha.split(':', 1)[1].strip()]
            # Captura as linhas que começam com números (as variáveis)
            elif linha[0].isdigit() and ':' in linha:
                partes = linha.split(':', 1)
                info_base = partes[0].strip()  # Ex: "4 Ligação"
                campos = [c.strip() for c in partes[1].split(',')]  # Ex: ["cpf", "cpfValido"]

                config['Variáveis'].append({
                     " ".join(info_base.split()[1:]) : campos
                })

        return Parameters(
            pasta=config['Pasta'],
            saida=config['Saída'],
            footer=config['Footer'],
            header=config['Header'],
            sufixo=config['Sufixo'],
            variaveis=config['Variáveis']
        )
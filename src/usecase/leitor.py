from src.Domain.Parameters import Parameters


class ParameterReader:
    def __init__(self, caminho_arquivo):
        self.caminho = caminho_arquivo

    def ler_arquivo(self) -> Parameters:
        config = {
            'Input folder': '',
            'Output folder': '',
            'CSV separator':None,
            'Footer' :None,
            'Header#' :None,
            'Footer#':None,
            'Sufix': [],
            'Variables': []
        }

        with open(self.caminho, 'r', encoding='utf-8') as f:
            linhas = f.readlines()

        lendo_variaveis = False

        for linha in linhas:
            linha = linha.strip()
            if not linha:
                continue

            if linha.startswith('Input folder:'):
                config['Input folder'] = linha.split(':', 1)[1].strip()

            elif linha.startswith('Output folder:'):
                config['Output folder'] = linha.split(':', 1)[1].strip()

            elif linha.startswith('Footer#:'):
                config['Footer#'] = int(linha.split(':', 1)[1].strip())

            elif linha.startswith('Header#:'):
                config['Header#'] = int(linha.split(':', 1)[1].strip())

            elif linha.startswith('CSV separator:'):
                config['CSV separator'] = linha.split(':', 1)[1].strip()

            elif linha.startswith('Format:'):
                config['Format'] = linha.split(':', 1)[1].strip()

            elif linha.startswith('Sufix:'):
                config['Sufix'] = [linha.split(':', 1)[1].strip()]

            elif linha.startswith('Variables:'):
                lendo_variaveis = True
                continue

            elif lendo_variaveis and ':' in linha:
                partes = linha.split(':', 1)
                chave = partes[0].strip()
                campos = [c.strip() for c in partes[1].split(',')]

                config['Variables'].append({
                    chave: campos
                })

        return Parameters(
            pasta=config['Input folder'],
            saida=config['Output folder'],
            footer=config['Footer#'],
            header=config['Header#'],
            sep=config['CSV separator'],
            sufixo=config['Sufix'],
            formato=config['Format'],
            variaveis=config['Variables']
        )
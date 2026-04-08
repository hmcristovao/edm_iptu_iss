from src.Domain.Parameters import Parameters

class ParameterReader:
    def __init__(self, caminho_arquivo):
        self.caminho = caminho_arquivo

    def ler_arquivo(self) -> Parameters:
        # Inicialize todas as chaves esperadas para evitar KeyError
        config = {
            'Input folder': '',
            'Output folder': '',
            'CSV separator': None,
            'Format': '',
            'Header#': 0,
            'Footer#': 0,
            'Sufix': [],
            'Variables': []
        }

        with open(self.caminho, 'r', encoding='utf-8') as f:
            linhas = f.readlines()

        lendo_variaveis = False

        for linha in linhas:
            linha_limpa = linha.strip()
            if not linha_limpa:
                continue

            # Convertemos para minúsculas para comparar sem erro de digitação
            linha_lower = linha_limpa.lower()

            if linha_lower.startswith('input folder:'):
                config['Input folder'] = linha_limpa.split(':', 1)[1].strip()

            elif linha_lower.startswith('output folder:'):
                config['Output folder'] = linha_limpa.split(':', 1)[1].strip()

            elif linha_lower.startswith('footer#:'):
                config['Footer#'] = int(linha_limpa.split(':', 1)[1].strip())

            elif linha_lower.startswith('header#:'):
                config['Header#'] = int(linha_limpa.split(':', 1)[1].strip())

            elif linha_lower.startswith('csv separator:'):
                config['CSV separator'] = linha_limpa.split(':', 1)[1].strip()

            elif linha_lower.startswith('format:'):
                config['Format'] = linha_limpa.split(':', 1)[1].strip()

            elif linha_lower.startswith('sufix:'):
                config['Sufix'] = [linha_limpa.split(':', 1)[1].strip()]

            elif linha_lower.startswith('variables:'):
                lendo_variaveis = True
                continue

            elif lendo_variaveis and ':' in linha_limpa:
                partes = linha_limpa.split(':', 1)
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
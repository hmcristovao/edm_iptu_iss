import os
from dotenv import load_dotenv
from src.Domain.Parameters import Parameters

# Carrega as variáveis do arquivo .env
load_dotenv()


class ParameterReader:
    def __init__(self, caminho_arquivo):
        self.caminho = caminho_arquivo
        # DATA_PATH será a nossa raiz absoluta
        self.base_path = os.getenv('DATA_PATH', os.getcwd())

    def ler_arquivo(self) -> Parameters:
        # Valores padrão
        config = {
            'Subpasta': '',  # Virá do 'Input folder' do TXT
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
            if not linha_limpa: continue
            linha_lower = linha_limpa.lower()

            # Aqui pegamos apenas o NOME da subpasta (ex: 'economico')
            if linha_lower.startswith('input folder:'):
                config['Subpasta'] = linha_limpa.split(':', 1)[1].strip()

            elif linha_lower.startswith('footer#:'):
                config['Footer#'] = int(linha_limpa.split(':', 1)[1].strip())

            elif linha_lower.startswith('header#:'):
                config['Header#'] = int(linha_limpa.split(':', 1)[1].strip())

            elif linha_lower.startswith('csv separator:'):
                sep = linha_limpa.split(':', 1)[1].strip()
                config['CSV separator'] = None if sep.lower() == 'none' or not sep else sep

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
                config['Variables'].append({chave: campos})

        # --- Lógica de Montagem dos Caminhos via ENV ---

        # Entrada: DATA_PATH + subpasta lida no TXT
        caminho_entrada = os.path.join(self.base_path, config['Subpasta'])

        # Saída: DATA_PATH + pasta fixa 'data_processed'
        caminho_saida = os.path.join(self.base_path, 'data_processed')

        return Parameters(
            pasta=caminho_entrada,
            saida=caminho_saida,
            footer=config['Footer#'],
            header=config['Header#'],
            sep=config['CSV separator'],
            sufixo=config['Sufix'],
            formato=config['Format'],
            variaveis=config['Variables']
        )
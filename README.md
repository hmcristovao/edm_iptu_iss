# Pipeline de Enriquecimento

Aplicação local para executar um pipeline de enriquecimento de dados em três etapas:

1. **Etapa 1**: lê arquivos CSV de entrada, separa registros válidos/inválidos e gera a base consolidada inicial.
2. **Etapa 2**: compara registros, aplica regras de similaridade, realiza merges automáticos e marca candidatos para revisão humana.
3. **Etapa 3**: abre a revisão humana dos pares pendentes, registra aprovação/recusa, observações e usuário revisor, e gera o arquivo final revisado.

A interface gráfica é feita com **NiceGUI** e roda localmente no navegador.

## Estrutura do Projeto

```text
avaliador/
  app_nicegui.py          # Interface web NiceGUI
  app_config.py           # Caminhos, constantes e configurações padrão
  app_services.py         # Serviços de entrada, pipeline, configuração e revisão
  app_state.py            # Estado da aplicação
  etapa1.py               # Processamento da etapa 1
  etapa2.py               # Processamento da etapa 2
  etapa2_config.json      # Configuração editável da etapa 2
  requirements.txt        # Dependências Python

  dados_entrada/          # CSVs enviados para a etapa 1
  arquivos_gerados/       # Saídas geradas pelas etapas
  logs/                   # Logs de execução em TXT
```

## Requisitos

- Python 3.11 ou superior
- Windows PowerShell ou terminal equivalente

Dependências Python:

```text
nicegui
pandas
recordlinkage
tqdm
```

## Instalação

No terminal, entre na pasta do projeto:

```powershell
cd C:\Users\dalva\Documents\EDM\edppe\avaliador
```

Crie um ambiente virtual:

```powershell
python -m venv .venv
```

Ative o ambiente virtual:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instale as dependências:

```powershell
pip install -r requirements.txt
```

## Execução da Interface

Com o ambiente virtual ativo, rode:

```powershell
python app_nicegui.py
```

O NiceGUI exibirá um endereço parecido com:

```text
http://localhost:8080
```

Abra esse endereço no navegador.

## Login

Ao entrar no sistema, será solicitado:

- Nome do usuário
- Senha padrão

A senha padrão é:

```text
1234
```

Para alterar a senha sem editar o código, defina a variável de ambiente antes de iniciar o app:

```powershell
$env:APP_SENHA_PADRAO = "minha_senha"
python app_nicegui.py
```

O nome informado no login é usado para registrar quem aprovou ou recusou merges na etapa 3.

## Como Usar

### 1. Carregar Dados da Etapa 1

Na interface, use o botão:

```text
Carregar CSVs
```

Regras do carregamento:

- Apenas arquivos `.csv` são aceitos.
- Ao selecionar novos arquivos, a pasta `dados_entrada/` é limpa.
- Os novos CSVs enviados são salvos em `dados_entrada/`.
- Abrir e fechar a janela de upload não apaga arquivos; a limpeza só acontece quando um novo upload realmente começa.

### 2. Iniciar Etapa 1

Clique em:

```text
Iniciar Etapa 1
```

A etapa 1 lê os arquivos de:

```text
dados_entrada/
```

E gera:

```text
arquivos_gerados/etapa1_final.csv
logs/etapa1_log.txt
```

### 3. Configurar Etapa 2

Na área **Configurações da Etapa 2**, ajuste os thresholds pela interface.

Essas configurações são salvas em:

```text
etapa2_config.json
```

Principais campos:

- **Merge Automático (%)**: score mínimo para merge automático.
- **Revisão Humana (%)**: score mínimo para encaminhar à revisão.
- **Nome, Telefone, E-mail, Nascimento, Endereço, Número, Identificador**: thresholds de apoio.
- **Máx. Pares por Bloco**: limite para evitar blocos muito grandes na comparação.

### 4. Iniciar Etapa 2

Clique em:

```text
Iniciar Etapa 2
```

A etapa 2 lê:

```text
arquivos_gerados/etapa1_final.csv
```

E gera:

```text
arquivos_gerados/etapa2_final.csv
arquivos_gerados/etapa2_log_merges.csv
logs/etapa2_log.txt
```

Ao rodar a etapa 2, decisões antigas da revisão humana são removidas para evitar reaproveitar decisões de uma base anterior.

### 5. Iniciar Etapa 3

Clique em:

```text
Iniciar Etapa 3
```

A etapa 3 carrega os pares marcados para revisão humana em:

```text
arquivos_gerados/etapa2_final.csv
```

Durante a revisão, é possível:

- Aprovar merge
- Rejeitar merge
- Escrever observações
- Pausar e continuar depois
- Gerar arquivo revisado
- Baixar arquivo revisado

As decisões são salvas em:

```text
arquivos_gerados/revisao_merges_decisoes.csv
```

O arquivo final revisado é salvo em:

```text
arquivos_gerados/etapa2_final_revisado.csv
```

## Auditoria da Revisão Humana

Cada decisão da etapa 3 registra:

- `usuario_revisor`
- `decisao`
- `observacao`
- `data_decisao`
- `score_revisao`

No arquivo final revisado, as informações de auditoria entram nas colunas:

- `usuario_revisao`
- `decisao_revisao`
- `observacao_revisao`
- `data_revisao`

Para merges aprovados, a auditoria fica na linha válida enriquecida.

Para merges rejeitados, a auditoria fica na linha inválida que permanece no arquivo.

## Arquivos Gerados

Principais saídas:

```text
arquivos_gerados/etapa1_final.csv
arquivos_gerados/etapa2_final.csv
arquivos_gerados/etapa2_log_merges.csv
arquivos_gerados/revisao_merges_decisoes.csv
arquivos_gerados/etapa2_final_revisado.csv
```

Logs:

```text
logs/etapa1_log.txt
logs/etapa2_log.txt
```

## Executar Etapas Pelo Terminal

Embora o fluxo recomendado seja pela interface, também é possível rodar as etapas manualmente:

```powershell
python etapa1.py
python etapa2.py
```

Atenção: para a etapa 1 funcionar, os CSVs precisam estar em:

```text
dados_entrada/
```

## Solução de Problemas

### Etapa 1 não encontra arquivos

Confira se os CSVs foram carregados em:

```text
dados_entrada/
```

O botão **Iniciar Etapa 1** só é liberado quando há pelo menos um CSV nessa pasta.

### Etapa 2 não inicia

Confirme se a etapa 1 gerou:

```text
arquivos_gerados/etapa1_final.csv
```

### Etapa 3 não inicia

Confirme se a etapa 2 gerou:

```text
arquivos_gerados/etapa2_final.csv
```

### Upload apagou arquivos antigos

Esse é o comportamento esperado somente quando um novo upload começa. Ao selecionar novos CSVs, a pasta `dados_entrada/` é limpa para evitar mistura entre execuções.

### Quero trocar a senha padrão

Use:

```powershell
$env:APP_SENHA_PADRAO = "nova_senha"
python app_nicegui.py
```

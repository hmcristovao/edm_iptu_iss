# Pipeline de Enriquecimento

Aplicação local para executar um pipeline de enriquecimento de dados em três etapas, com interface web em **NiceGUI**.

## Visão Geral

1. **Etapa 1**: lê os CSVs da pasta de trabalho, separa registros válidos/inválidos e gera a base consolidada inicial.
2. **Etapa 2**: compara registros, aplica regras de similaridade, realiza merges automáticos e marca candidatos para revisão humana.
3. **Etapa 3**: permite revisar pares manualmente, registrar aprovação/recusa, observações e usuário responsável, e gerar o arquivo final ou parcial.

## Estrutura do Código

Na pasta do projeto ficam apenas os scripts e arquivos de configuração:

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
  README.md
```

## Pasta de Trabalho

A pasta de trabalho é escolhida na interface. Os CSVs de entrada devem estar diretamente na raiz dessa pasta:

```text
minha_pasta_de_trabalho/
  Economico.csv
  EdpArrecadado.csv
  EdpFaturado.csv
  EducacaoResponsaveis.csv
  ...
```

Durante a execução, o sistema cria dentro dela:

```text
minha_pasta_de_trabalho/
  arquivos_gerados/
  logs/
```

Todo o fluxo de dados acontece nessa pasta de trabalho. A pasta do código não muda.

## Requisitos

- Python 3.11 ou superior
- Windows PowerShell ou terminal equivalente

Dependências:

```text
nicegui
pandas
recordlinkage
tqdm
```

## Instalação

Entre na pasta do projeto:

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

## Executar a Interface

Com o ambiente virtual ativo:

```powershell
python app_nicegui.py
```

Abra no navegador o endereço mostrado pelo NiceGUI, normalmente:

```text
http://localhost:8080
```

## Login

Ao abrir o app, informe:

- Nome do usuário
- Senha padrão

A senha padrão é:

```text
1234
```

Para alterar a senha sem editar o código:

```powershell
$env:APP_SENHA_PADRAO = "minha_senha"
python app_nicegui.py
```

O nome informado no login é usado na auditoria da etapa 3.

## Como Usar

### 1. Selecionar Pasta de Trabalho

Clique em:

```text
Selecionar Pasta de Trabalho
```

O modal permite:

- listar os discos disponíveis;
- entrar em subpastas;
- voltar para a pasta anterior;
- atualizar a pasta atual;
- ver quantos CSVs existem na pasta atual;
- confirmar a pasta aberta com **Usar Pasta**.

Ao confirmar, o sistema:

- usa essa pasta como raiz de dados;
- lê os CSVs diretamente dela;
- cria `arquivos_gerados/`, se necessário;
- cria `logs/`, se necessário.

### 2. Iniciar Etapa 1

Clique em:

```text
Iniciar Etapa 1
```

A etapa 1 lê os CSVs da pasta de trabalho.

Saídas:

```text
arquivos_gerados/etapa1_final.csv
logs/etapa1_log.txt
```

### 3. Configurar Etapa 2

Na área **Configurações da Etapa 2**, ajuste os thresholds.

Essas configurações são salvas na pasta do código:

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

Ao rodar a etapa 2, decisões antigas da revisão humana são removidas para evitar reaproveitar decisões de outra base.

### 5. Iniciar Etapa 3

Clique em:

```text
Iniciar Etapa 3
```

A etapa 3 carrega:

```text
arquivos_gerados/etapa2_final.csv
```

Durante a revisão, é possível:

- aprovar merge;
- rejeitar merge;
- escrever observações;
- pausar e continuar depois;
- gerar arquivo revisado;
- baixar o arquivo gerado.

As decisões são salvas em:

```text
arquivos_gerados/revisao_merges_decisoes.csv
```

## Saídas da Etapa 3

O nome do arquivo depende da situação da revisão:

```text
arquivos_gerados/etapa3_final.csv
arquivos_gerados/etapa3_parcial.csv
```

Se não houver pares pendentes, o sistema gera:

```text
etapa3_final.csv
```

Se ainda houver pares pendentes, o sistema gera:

```text
etapa3_parcial.csv
```

Apenas um desses dois arquivos fica disponível por vez. Ao gerar um, o outro é removido automaticamente.

## Auditoria da Revisão Humana

Cada decisão registra:

- `usuario_revisor`
- `decisao`
- `observacao`
- `data_decisao`
- `score_revisao`

No arquivo revisado, a auditoria entra nas colunas:

- `usuario_revisao`
- `decisao_revisao`
- `observacao_revisao`
- `data_revisao`

Para merges aprovados, a auditoria fica na linha válida enriquecida.

Para merges rejeitados, a auditoria fica na linha inválida que permanece no arquivo.

## Executar Etapas Pelo Terminal

O fluxo recomendado é pela interface, porque ela define a pasta de trabalho automaticamente para os subprocessos.

Para executar manualmente, defina `AVALIADOR_WORKDIR` antes:

```powershell
$env:AVALIADOR_WORKDIR = "C:\Users\********\Documents\**********"
python etapa1.py
python etapa2.py
```

Sem `AVALIADOR_WORKDIR`, as etapas usam a própria pasta do código como pasta de trabalho.

## Solução de Problemas

### Etapa 1 não encontra arquivos

Confira se os CSVs estão diretamente na raiz da pasta de trabalho escolhida.

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

### Os arquivos foram gerados na pasta errada

Confira a pasta exibida em **Pasta de Trabalho** na interface.

### Quero trocar a senha padrão

Use:

```powershell
$env:APP_SENHA_PADRAO = "nova_senha"
python app_nicegui.py
```

# Integração e Enriquecimento
## Visão Geral

O processo é composto por três atividades operacionais:

1. **Preparação**: lê os CSVs da pasta de trabalho, identifica registros válidos/inválidos e gera a base inicial consolidada.
2. **Enriquecimento**: compara registros, aplica regras de similaridade, realiza uniões automáticas e marca candidatos para revisão humana.
3. **Revisão Humana**: permite aprovar ou rejeitar candidatos, registrar observações, identificar o usuário responsável e gerar o arquivo final ou parcial.

## Estrutura do Código

Na pasta do projeto ficam os scripts e arquivos de configuração:

```text
avaliador/
  app_nicegui.py          # Interface web NiceGUI
  app_config.py           # Caminhos, constantes e configurações padrão
  app_services.py         # Serviços de entrada, execução, configuração e revisão
  app_state.py            # Estado da aplicação
  preparacao.py           # Script de preparação
  enriquecimento.py       # Script de enriquecimento
  integracao_config.json  # Configuração editável do enriquecimento
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

Todo o fluxo de dados acontece nessa pasta de trabalho. A pasta do código permanece onde o sistema foi iniciado.

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

O nome informado no login é usado na auditoria da revisão humana.

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

### 2. Iniciar Preparação

Clique em:

```text
Iniciar Preparação
```

A preparação lê os CSVs da pasta de trabalho.

Saídas:

```text
arquivos_gerados/integracao_base.csv
logs/integracao_preparacao_log.txt
```

### 3. Configurar Enriquecimento

Na área **Configurações do Enriquecimento**, ajuste os thresholds.

As configurações são salvas na pasta do código:

```text
integracao_config.json
```

Principais campos:

- **Merge Automático (%)**: score mínimo para união automática.
- **Revisão Humana (%)**: score mínimo para encaminhar à revisão.
- **Nome, Telefone, E-mail, Nascimento, Endereço, Número, Identificador**: thresholds de apoio.
- **Máx. Pares por Bloco**: limite para evitar blocos muito grandes na comparação.

### 4. Iniciar Enriquecimento

Clique em:

```text
Iniciar Enriquecimento
```

O enriquecimento lê:

```text
arquivos_gerados/integracao_base.csv
```

E gera:

```text
arquivos_gerados/integracao_enriquecida.csv
arquivos_gerados/integracao_log_merges.csv
logs/integracao_enriquecimento_log.txt
```

Ao rodar o enriquecimento, decisões antigas da revisão humana são removidas para evitar reaproveitar decisões de outra base.

### 5. Iniciar Revisão

Clique em:

```text
Iniciar Revisão
```

A revisão carrega:

```text
arquivos_gerados/integracao_enriquecida.csv
```

Durante a revisão, é possível:

- aprovar união;
- rejeitar união;
- escrever observações;
- pausar e continuar depois;
- gerar arquivo revisado;
- baixar o arquivo gerado.

As decisões são salvas em:

```text
arquivos_gerados/revisao_merges_decisoes.csv
```

## Saídas da Revisão

O nome do arquivo depende da situação da revisão:

```text
arquivos_gerados/integracao_final.csv
arquivos_gerados/integracao_parcial.csv
```

Se não houver pares pendentes, o sistema gera:

```text
integracao_final.csv
```

Se ainda houver pares pendentes, o sistema gera:

```text
integracao_parcial.csv
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

Para uniões aprovadas, a auditoria fica na linha válida enriquecida.

Para uniões rejeitadas, a auditoria fica na linha inválida que permanece no arquivo.

## Executar Pelo Terminal

O fluxo recomendado é pela interface, porque ela define a pasta de trabalho automaticamente para os subprocessos.

Para executar manualmente, defina `AVALIADOR_WORKDIR` antes:

```powershell
$env:AVALIADOR_WORKDIR = "C:\Users\dalva\Documents\EDM\trabalho_vargem_alta"
python preparacao.py
python enriquecimento.py
```

Sem `AVALIADOR_WORKDIR`, os scripts usam a própria pasta do código como pasta de trabalho.

## Solução de Problemas

### A preparação não encontra arquivos

Confira se os CSVs estão diretamente na raiz da pasta de trabalho escolhida.

### O enriquecimento não inicia

Confirme se a preparação gerou:

```text
arquivos_gerados/integracao_base.csv
```

### A revisão não inicia

Confirme se o enriquecimento gerou:

```text
arquivos_gerados/integracao_enriquecida.csv
```

### Os arquivos foram gerados na pasta errada

Confira a pasta exibida em **Pasta de Trabalho** na interface.

### Quero trocar a senha padrão

Use:

```powershell
$env:APP_SENHA_PADRAO = "nova_senha"
python app_nicegui.py
```

# Integração e Enriquecimento

## Visão Geral

Este projeto organiza um fluxo de preparação, padronização, pseudonimização, enriquecimento, revisão humana, reidentificação e geração de uma base imobiliária enriquecida.

O uso recomendado é pela interface NiceGUI. Ela centraliza a escolha da pasta de trabalho, executa as etapas em sequência e registra os principais arquivos gerados.

## Estrutura do Projeto

```text
avaliador/
  app_nicegui.py          # Inicializador da interface
  requirements.txt        # Dependências Python
  README.md
  src/
    moduloI/              # Leitura, padronização e pseudonimização das bases originais
    moduloII/             # Preparação, enriquecimento, revisão e configuração
    moduloIII/            # Reidentificação dos CPFs pseudonimizados
    moduloIV/             # Geração da base imobiliária enriquecida
    parametrizacao/       # Geração automática de arquivos de parâmetros
    views/                # Interface gráfica e estado da aplicação
```

## Pasta de Trabalho

A pasta de trabalho é selecionada na interface. Ela concentra os arquivos de entrada e as saídas do processamento.

Durante a execução, o sistema pode criar ou utilizar pastas como:

```text
arquivos_gerados/
dados_processados/
logs/
```

Os arquivos gerados pelo fluxo principal ficam, em geral, em `arquivos_gerados/`. Os arquivos padronizados por fonte ficam em `dados_processados/`.

## Requisitos

- Python 3.11 ou superior
- Windows PowerShell ou terminal equivalente

Instale as dependências com:

```powershell
pip install -r requirements.txt
```

As principais dependências são:

```text
nicegui
pandas
recordlinkage
tqdm
beautifulsoup4
html5lib
lxml
openpyxl
pycryptodome
pyparsing
python-dotenv
xlrd
```

## Instalação

Entre na pasta do projeto, crie e ative um ambiente virtual:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
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

Abra no navegador o endereço exibido pelo NiceGUI, normalmente:

```text
http://localhost:8080
```

Por segurança, a interface escuta apenas em `127.0.0.1`, ficando acessível somente na máquina local.

Se a porta já estiver em uso, encerre o processo anterior ou configure outra porta pela variável de ambiente usada pela aplicação.

## Login

Ao abrir o app, informe:

- nome do usuário;
- senha padrão.

A senha padrão é:

```text
1234
```

Para alterar a senha sem editar o código:

```powershell
$env:APP_SENHA_PADRAO = "nova_senha"
python app_nicegui.py
```

O nome informado no login é usado na auditoria da revisão humana.

## Fluxo Pela Interface

### 1. Selecionar Pasta de Trabalho

Clique em `Selecionar Pasta de Trabalho` e informe a pasta que contém os dados do processamento.

A partir desse momento, as etapas passam a ler e gravar arquivos dentro dessa pasta.

### 2. Gerar Parâmetros

Clique em `Gerar Parâmetros` quando houver fontes ainda sem arquivo de parâmetros.

Essa etapa usa o modelo base em `src/parametrizacao/parametros.txt` e gera arquivos `parametros_*.txt` nas pastas das fontes.

A parametrização:

- percorre as subpastas da pasta de trabalho;
- ignora pastas de sistema do fluxo, como `arquivos_gerados`, `dados_processados`, `logs` e `parametros`;
- não altera pastas que já possuem arquivo `.txt`;
- identifica formato da tabela;
- tenta detectar cabeçalho e última linha de dados;
- preenche `Sufix`, `Header#`, `Footer#`, `Format`, `CSV separator` e `Variables`;
- sugere nomes padronizados para variáveis com base nos nomes das colunas.

### 3. Processar Arquivos Originais

Clique em `Processar Arquivos Originais` para ler os arquivos brutos das fontes e gerar bases padronizadas por fonte.

Essa etapa utiliza os arquivos de parâmetros disponíveis nas pastas das fontes e grava os resultados em `dados_processados/`.

O objetivo é transformar as diferentes entradas em tabelas padronizadas, com campos em camelCase e CPFs pseudonimizados quando aplicável.

### 4. Iniciar Preparação

Clique em `Iniciar Preparação`.

A preparação consolida os dados processados em uma base única para enriquecimento.

Saída principal:

```text
arquivos_gerados/integracao_base.csv
```

Log principal:

```text
logs/integracao_preparacao_log.txt
```

### 5. Configurar Enriquecimento

Na área de configuração do enriquecimento, ajuste os thresholds.

As configurações são salvas na pasta de trabalho em:

```text
arquivos_gerados/integracao_config.json
```

Campos principais:

- `threshold_similaridade`: score mínimo para merge automático.
- `threshold_revisar`: score mínimo para enviar à revisão humana.
- `threshold_apoio_nome`: apoio por nome.
- `threshold_apoio_telefone`: apoio por telefone.
- `threshold_apoio_email`: apoio por e-mail.
- `threshold_apoio_nascimento`: apoio por nascimento.
- `threshold_apoio_endereco`: apoio por endereço.
- `threshold_apoio_numero`: apoio por número.
- `threshold_apoio_identificador_documento`: apoio por documentos auxiliares.
- `max_pares_por_valor_bloco`: limite de pares gerados por bloco frequente.

Quando um threshold de apoio é configurado como `101`, esse apoio fica desabilitado, porque os scores vão de 0 a 100.

### 6. Iniciar Enriquecimento

Clique em `Iniciar Enriquecimento`.

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

Nessa etapa, o sistema compara registros, calcula scores, aplica merges automáticos e marca pares que precisam de revisão humana.

### 7. Iniciar Revisão

Clique em `Iniciar Revisão`.

A revisão carrega:

```text
arquivos_gerados/integracao_enriquecida.csv
```

Durante a revisão, é possível:

- aprovar merge;
- rejeitar merge;
- registrar observações;
- pausar e continuar depois;
- gerar arquivo revisado;
- baixar o arquivo revisado.

As decisões são salvas em:

```text
arquivos_gerados/revisao_merges_decisoes.csv
```

Ao gerar o arquivo revisado, o sistema cria:

```text
arquivos_gerados/integracao_final.csv
```

ou:

```text
arquivos_gerados/integracao_parcial.csv
```

Se ainda houver revisões pendentes, a saída é parcial. Se não houver pendências, a saída é final.

### 8. Reidentificar Base

Clique em `Reidentificar Base` após gerar a base final ou parcial.

Essa etapa usa a chave de pseudonimização para reidentificar CPFs em uma cópia da base, sem modificar o arquivo anterior.

Entrada:

```text
arquivos_gerados/integracao_final.csv
```

ou:

```text
arquivos_gerados/integracao_parcial.csv
```

Saída:

```text
arquivos_gerados/integracao_reidentificada.csv
```

### 9. Gerar Base Imobiliária

Clique em `Gerar Base Imobiliária` após gerar a integração reidentificada.

Essa etapa combina o cadastro imobiliário processado com dados disponíveis na integração reidentificada.

Entradas principais:

```text
dados_processados/imobiliario.csv
arquivos_gerados/integracao_reidentificada.csv
```

Saída:

```text
arquivos_gerados/base_imobiliario_modulo_iv.csv
```

O módulo IV:

- usa CPF/CNPJ válidos do imobiliário como chave;
- remove duplicidades por documento;
- agrega inscrições imobiliárias duplicadas com ` | `;
- reidentifica CPFs do imobiliário quando necessário;
- enriquece telefone e e-mail com dados da integração reidentificada;
- cria colunas rastreadas para contatos enriquecidos;
- mantém informações de origem, `id_revisao`, usuário e data de revisão quando disponíveis;
- ordena registros com CPF/CNPJ válido antes dos inválidos.

## Regra Geral do Enriquecimento

O enriquecimento separa a base em dois grupos:

- registros com `merge_key`: considerados válidos;
- registros sem `merge_key`: candidatos a serem juntados a registros válidos.

Depois, cria pares candidatos usando blocos de comparação, como telefone, e-mail, documentos auxiliares, cadastro de serviço, nome com nascimento, CEP, bairro com nome e tokens do nome.

Cada par recebe scores por campo. O score total é uma média ponderada apenas dos campos que existem nos dois lados.

Um merge automático exige:

```text
score_total >= threshold_similaridade
e
pelo menos uma regra de apoio válida
```

Pares que passam de `threshold_revisar`, mas não cumprem merge automático, são encaminhados para revisão humana.

## Auditoria da Revisão Humana

Cada decisão registra:

- `usuario_revisor`
- `decisao`
- `observacao`
- `data_decisao`
- `score_revisao`

No arquivo revisado, a auditoria pode aparecer em colunas como:

- `usuario_revisao`
- `decisao_revisao`
- `observacao_revisao`
- `data_revisao`

Quando uma junção aprovada contribui com telefone ou e-mail para a base imobiliária, o módulo IV também preserva rastros como:

- origem do dado;
- `id_revisao`;
- usuário da revisão;
- data da revisão.

## Empacotamento

Ao gerar um executável, inclua explicitamente o template da parametrização:

```text
src/parametrizacao/parametros.txt
```

Esse arquivo é usado em runtime pelo botão `Gerar Parâmetros`.

No PyInstaller, um exemplo de inclusão é:

```powershell
pyinstaller PIEC.spec
```

O executável também precisa preservar os módulos usados pelo modo interno `--run-pipeline`, pois a interface chama o próprio executável para executar etapas pesadas em subprocesso.

## Executar Pelo Terminal

O fluxo recomendado é pela interface, porque ela define a pasta de trabalho automaticamente para os subprocessos.

Para executar manualmente, defina a pasta de trabalho antes:

```powershell
$env:AVALIADOR_WORKDIR = "caminho_da_pasta_de_trabalho"
```

Depois execute os módulos desejados:

```powershell
python src\moduloII\preparacao.py
python src\moduloII\enriquecimento.py
python src\moduloII\gerar_revisado.py
python src\moduloIII\reassociacao.py
python src\moduloIV\base_imobiliario.py
```

Para etapas que usam a chave de pseudonimização:

```powershell
$env:APP_CHAVE_PSEUDONIMIZACAO = "minha_chave"
```

Sem `AVALIADOR_WORKDIR`, os scripts usam a pasta em que o sistema foi iniciado como pasta de trabalho.

## Solução de Problemas

### A interface não abre

Confira se o ambiente virtual está ativo e se as dependências foram instaladas.

Se a porta estiver em uso, encerre a execução anterior ou configure outra porta.

### A parametrização não gerou arquivo para uma fonte

Confira se a pasta da fonte contém uma tabela compatível e se ainda não existe arquivo `.txt` nela.

Pastas de sistema do fluxo são ignoradas automaticamente.

### A preparação não encontra dados

Confira se os arquivos processados foram gerados em `dados_processados/` ou se existem entradas válidas para a preparação.

### O enriquecimento não inicia

Confira se existe:

```text
arquivos_gerados/integracao_base.csv
```

### A revisão não inicia

Confira se existe:

```text
arquivos_gerados/integracao_enriquecida.csv
```

### A reidentificação não inicia

Gere primeiro o arquivo final ou parcial da revisão.

### A base imobiliária não inicia

Confira se existem:

```text
dados_processados/imobiliario.csv
arquivos_gerados/integracao_reidentificada.csv
```

### Arquivos foram gerados no lugar errado

Confira a pasta exibida em `Pasta de Trabalho` na interface.

### Quero trocar a senha padrão

Use:

```powershell
$env:APP_SENHA_PADRAO = "nova_senha"
python app_nicegui.py
```

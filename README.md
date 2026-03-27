Aqui está o ajuste no seu **README.md**, incorporando as exigências da imagem (versões específicas do Python e o sufixo `.bat`) e organizando melhor a parte de configuração das pastas que discutimos anteriormente.

---

# edm_iptu_iss
Soluções no contexto do enriquecimento de dados para IPTU e ISS

------------------------------------------------------------------------

## ⚙️ Pré-requisitos

* **Python:** Versões **3.10, 3.11 ou 3.12**.
* **Git:** (Opcional) para clonagem do repositório.
* **Ambiente virtual:** venv.

------------------------------------------------------------------------

## 📁 Estrutura do projeto

```text
edm_iptu_iss/
 ├── dados/              ← Contém as bases de dados e o arquivo .env
 │     ├── .env          <-- OBRIGATÓRIO (Chave de criptografia)
 │     ├── Imoveis/
 │     ├── Saae/
 │     └── ...
 ├── venv/               ← Ambiente virtual
 ├── src/                ← Código-fonte (Handlers, Pipeline, etc)
 │     ├── pipeline/
 │     │     └── main.py
 │     └── ...
 ├── requirements.txt
 └── README.md
```

------------------------------------------------------------------------

## 🚀 Como rodar o projeto

### 1️⃣ Clonar o repositório

```bash
git clone https://github.com/hmcristovao/edm_iptu_iss.git
cd edm_iptu_iss
```

### 2️⃣ Configurar Variáveis de Ambiente
Crie um arquivo chamado **`.env`** dentro da pasta `dados/` com a seguinte variável:
```text
key=sua_chave_de_criptografia_aqui
```

### 3️⃣ Criar o ambiente virtual

```bash
python -m venv venv
```

### 4️⃣ Ativar o ambiente virtual

#### **Windows (Prompt de Comando / CMD)**
```bash
venv\Scripts\activate.bat
```

#### **Windows (PowerShell)**
```powershell
.\venv\Scripts\Activate.ps1
```

#### **Linux/macOS**
```bash
source venv/bin/activate
```

### 5️⃣ Instalar as dependências

```bash
pip install -r requirements.txt
```

### 6️⃣ Executar o programa
Este projeto utiliza caminhos relativos. Certifique-se de estar na raiz do projeto ou ajuste o `PYTHONPATH`. Para rodar o pipeline principal:

```bash
python -m src.pipeline.main
```

------------------------------------------------------------------------

## 📌 Notas importantes

* **Versão do Python:** O projeto foi validado estritamente para as versões **3.10, 3.11 e 3.12**.
* **Segurança:** Nunca versione o arquivo `.env` da pasta `dados/`. Ele contém as chaves de reversão da pseudonimização.
* **Logs:** O sistema gera logs detalhados no console informando o sucesso ou falha de cada etapa da Chain of Responsibility (Limpeza, Validação e Pseudonimização).

---

**Deseja que eu crie um arquivo `.gitignore` padrão para garantir que a sua pasta `venv/` e o seu arquivo `.env` não sejam enviados por engano para o GitHub?**
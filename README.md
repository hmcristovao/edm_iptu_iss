# edm_iptu_iss
Soluções no contexto do enriquecimento de dados para IPTU e ISS

------------------------------------------------------------------------

## ⚙️ Pré-requisitos

-   Python **3.10+**
-   Git (opcional)
-   Ambiente virtual **venv**

------------------------------------------------------------------------

## 📁 Estrutura do projeto

    edm_iptu_iss/
     ├──dados/
           ├── Imoveis
           ├── Saae
           ├── Semades
           └── ...
     ├── venv/               ← ambiente virtual
     ├── src/
     │     ├── main.py
     │     ├── Saae.py
     │     ├── Anonimizador.py
     │     └── ...
     ├── requirements.txt
     └── README.md

------------------------------------------------------------------------

## 🚀 Como rodar o projeto

### 1️⃣ Clonar o repositório

``` bash
git clone https://github.com/hmcristovao/edm_iptu_iss.git
cd edm_iptu_iss
```

------------------------------------------------------------------------

### 2️⃣ Criar o ambiente virtual

``` bash
python -m venv venv
```

------------------------------------------------------------------------

### 3️⃣ Ativar o ambiente virtual

#### **Windows**

``` bash
venv\Scripts\activate
```

#### **Linux/macOS**

``` bash
source venv/bin/activate
```

------------------------------------------------------------------------

### 4️⃣ Instalar as dependências

``` bash
pip install -r requirements.txt
```
------------------------------------------------------------------------

### 5️⃣ Navegar até a pasta `src`

Este projeto usa caminhos relativos e importa módulos com base na pasta
`src`.\
Por isso, **é obrigatório rodar o sistema dentro da pasta `src`**:

``` bash
cd src
```

------------------------------------------------------------------------

### 6️⃣ Executar o programa

``` bash
python main.py
```


## 🧹 Desativar o ambiente virtual

``` bash
deactivate
```

------------------------------------------------------------------------

## 📌 Notas importantes

-   Sempre **ative o venv** antes de executar o projeto.
-   Sempre **navegue até a pasta `src/`** antes de rodar o `main.py`.

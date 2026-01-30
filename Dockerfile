# 1. Imagem base leve e oficial do Python
FROM python:3.11-slim

# 2. Define o diretório de trabalho dentro do container
WORKDIR /app

# 3. Instala dependências do sistema necessárias (opcional, dependendo do seu projeto)
# O pandas às vezes precisa de bibliotecas C extras
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. Copia o arquivo de dependências primeiro (aproveita o cache do Docker)
COPY requirements.txt .

# 5. Instala as bibliotecas (pandas, pytest, cryptography para sua anonimização, etc)
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copia o restante do código do projeto
COPY . .

ENV PYTHONPATH="${PYTHONPATH}:/app"

CMD ["python", "src/pipeline/pipeline.py"]
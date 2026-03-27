# 1. Imagem base estável
FROM python:3.12-slim

# 2. Diretório de trabalho
WORKDIR /app

# 3. Dependências do sistema (Mantemos as que adicionamos para lxml e geopandas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    libgdal-dev \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 4. Dependências do Python
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 5. Código
COPY . .

ENV PYTHONPATH="/app"

CMD ["python", "src/pipeline/pipeline.py"]
FROM apache/airflow:2.7.1

# Muda para o usuário root para instalar pacotes de sistema se necessário
USER root
RUN apt-get update && apt-get install -y git

# Volta para o usuário airflow
USER airflow

# Copia e instala as dependências da sua aplicação
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Copia sua aplicação para dentro do diretório de trabalho do Airflow
# Ou você pode usar volumes no docker-compose para desenvolvimento
COPY ./my_app /opt/airflow/plugins/my_app
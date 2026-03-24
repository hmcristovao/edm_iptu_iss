from airflow import DAG
# Import atualizado conforme o Warning que você recebeu
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime, timedelta

def extrair_dados():
    print("Extraindo dados...")
    return 100

with DAG(
    dag_id='meu_primeiro_pipeline',
    start_date=datetime(2024, 1, 1),
    # AJUSTE AQUI: Mudou de schedule_interval para schedule
    schedule='@daily',
    catchup=False
) as dag:

    task_extracao = PythonOperator(
        task_id='extrair_preco',
        python_callable=extrair_dados
    )
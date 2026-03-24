from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator

def minha_tarefa():
    print("Executando tarefa no Airflow!")

with DAG(
    dag_id="dag_exemplo_simples",
    start_date=datetime(2024,1,1),
    schedule_interval="@daily",
    catchup=False
) as dag:

    tarefa1 = PythonOperator(
        task_id="print_mensagem",
        python_callable=minha_tarefa
    )

    tarefa1
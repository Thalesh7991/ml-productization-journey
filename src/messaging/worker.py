import json
import logging
import os
import time
import pika
import pandas as pd

from src.config import QUEUE_NAME, CICLO
from src.models.train import load_artifacts
from src.models.predict import predict_proba
from src.db.connection import get_connection
from src.db.schema import create_tables

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")

model, scaler = load_artifacts()

# Conexão persistente com o banco — reutilizada entre jobs
db_conn = None

def get_db_conn():
    """Retorna conexão ativa, reconectando se necessário."""
    global db_conn
    if db_conn is None or db_conn.closed:
        db_conn = get_connection()
    return db_conn

def process_job(ch, method, properties, body):
    try:
        data = json.loads(body)
        job_id = data["job_id"]
        customer_data = data["customer_data"]

        df_raw = pd.DataFrame([customer_data])
        churn_proba = predict_proba(df_raw, model=model, scaler=scaler).iloc[0]

        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO predictions (job_id, churn_probability, churn_label, model_version, input_data)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (job_id, float(churn_proba), int(churn_proba >= 0.5), CICLO, json.dumps(customer_data))
            )
        conn.commit()

        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info("Job %s processado e persistido no banco.", job_id)
    except Exception as e:
        logger.error("Erro ao processar job: %s", e)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def start_worker():
    # Aguarda PostgreSQL estar pronto e cria tabela se necessário
    while True:
        try:
            conn = get_db_conn()
            create_tables(conn)
            logger.info("Worker conectado ao PostgreSQL.")
            break
        except Exception as e:
            logger.warning("Aguardando PostgreSQL... %s", e)
            time.sleep(5)

    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=process_job)
            logger.info("Worker iniciado. Aguardando mensagens...")
            channel.start_consuming()
        except Exception as e:
            logger.warning("Conexão RabbitMQ falhou: %s. Tentando novamente em 5s...", e)
            time.sleep(5)

if __name__ == "__main__":
    start_worker()
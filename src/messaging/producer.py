import pika
import uuid
import json
import os

from src.api.schemas import CustomerInput
from src.config import QUEUE_NAME

# buscar variaveis de ambiente em .env
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")

def get_channel():
    connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    return channel

def publish_prediction_job(customer: CustomerInput, channel)-> str:
    customer_data = customer.model_dump()
    # gerar um job_id unico (ex: UUID)
    job_id = str(uuid.uuid4())
    
    channel.basic_publish(exchange='', 
                          routing_key=QUEUE_NAME,
                          body=json.dumps({"job_id": job_id, "customer_data": customer_data})
                          )
    print(f"Job {job_id} publicado para previsão de churn!")
    return job_id



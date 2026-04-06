import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from src.api.schemas import CustomerInput, JobResponse
from src.messaging.producer import get_channel, publish_prediction_job
from src.db.connection import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

channel = None
db_conn = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global channel, db_conn
    while True:
        try:
            channel = get_channel()
            logger.info("API conectada ao RabbitMQ.")
            break
        except Exception as e:
            logger.warning("API: aguardando RabbitMQ... %s", e)
            time.sleep(5)
    while True:
        try:
            db_conn = get_connection()
            logger.info("API conectada ao PostgreSQL.")
            break
        except Exception as e:
            logger.warning("API: aguardando PostgreSQL... %s", e)
            time.sleep(5)
    yield

app = FastAPI(title="Churn Prediction API", version="2.0", lifespan=lifespan)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/predict", response_model=JobResponse)
def predict_churn(customer: CustomerInput):
    job_id = publish_prediction_job(customer, channel)
    logger.info("Job enfileirado: %s", job_id)
    return JobResponse(job_id=job_id, status="queued")

@app.get("/result/{job_id}")
def get_result(job_id: str):
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT job_id, churn_probability, churn_label, model_version, created_at FROM predictions WHERE job_id = %s",
            (job_id,)
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Result not ready yet")
    return {
        "job_id":            str(row[0]),
        "churn_probability": row[1],
        "churn_label":       row[2],
        "model_version":     row[3],
        "created_at":        row[4].isoformat(),
    }
import os
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/churn")


def get_connection():
    return psycopg2.connect(DATABASE_URL)

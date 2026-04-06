import psycopg2


def create_tables(conn: psycopg2.extensions.connection) -> None:
    """Create the predictions table if it does not already exist."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                job_id            UUID         PRIMARY KEY,
                created_at        TIMESTAMPTZ  DEFAULT NOW(),
                churn_probability FLOAT        NOT NULL,
                churn_label       SMALLINT     NOT NULL,
                model_version     VARCHAR(50)  NOT NULL,
                input_data        JSONB
            )
        """)
    conn.commit()

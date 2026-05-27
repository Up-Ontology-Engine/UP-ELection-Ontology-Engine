"""Prefect flow: recompute booth_metrics every 6 hours."""

import os

import sqlalchemy as sa
from dotenv import load_dotenv
from prefect import flow

load_dotenv()


@flow(name="booth-metrics", log_prints=True)
def metrics_flow(window_days: int = 7):
    from analytics.booth_metrics import compute_booth_metrics

    engine = sa.create_engine(os.environ["POSTGRES_URL"])
    compute_booth_metrics(engine, window_days=window_days)
    print(f"booth_metrics recomputed for {window_days}-day window.")


if __name__ == "__main__":
    metrics_flow()

""" ETL Pipeline DAG Script."""

import logging
import os
from datetime import datetime
from typing import Any

import pandas as pd
from airflow import DAG
from airflow.operators.python import PythonOperator
from etl_utils import clean_data

# Setup logging
logger = logging.getLogger("airflow.task")

# Paths loaded from environment variables with defaults
INPUT_PATH = os.getenv('AIRFLOW_INPUT_PATH', '/opt/airflow/data/listing_raw_technical_test.parquet')
OUTPUT_PATH = os.getenv('AIRFLOW_OUTPUT_PATH', '/opt/airflow/data/processed.parquet')


def extract(**kwargs: Any) -> str:
    """
    Extract function to return the input file path.

    :param kwargs: Airflow context (unused)
    :return: Path to the input parquet file.
    """
    logger.info("Extract task started, returning file path: %s", INPUT_PATH)
    return INPUT_PATH


def transform(ti, **kwargs: Any) -> str:
    """
    Transform function to clean and save the dataset.

    :param ti: Airflow TaskInstance to access XCom.
    :param kwargs: Airflow context (unused)
    :return: Path to the cleaned parquet file.
    """
    file_path = ti.xcom_pull(task_ids='extract_task')

    logger.info("Transform task started, received file path from XCom: %s", file_path)

    if not file_path:
        logger.error("No file path received from extract_task")
        raise ValueError("No file path received from extract_task")

    df = pd.read_parquet(file_path)
    logger.info("Start transform on dataframe with shape: %s", df.shape)

    try:
        cleaned_df = clean_data(df)
    except Exception as e:
        logger.error("Transform failed: %s", e)
        raise

    # Avoid big data transfer by XCOM
    cleaned_df.to_parquet(OUTPUT_PATH)
    logger.info("Transformed data saved to: %s", OUTPUT_PATH)

    return OUTPUT_PATH


def load(ti, **kwargs: Any) -> None:
    """
    Load function to confirm the presence of the cleaned dataset.

    :param ti: Airflow TaskInstance to access XCom.
    :param kwargs: Airflow context (unused)
    """
    cleaned_path = ti.xcom_pull(task_ids='transform_task')

    if not cleaned_path or not os.path.exists(cleaned_path):
        logger.error("No valid parquet file path received from transform_task: %s", cleaned_path)
        raise ValueError("No valid parquet file path received from transform_task: %s" % cleaned_path)

    df = pd.read_parquet(cleaned_path)
    logger.info("Load completed, data shape: %s", df.shape)


# Default DAG arguments
default_args = {
    'start_date': datetime(2025, 7, 1),
}

# Define the DAG
doc_md = """
# ETL Parquet Pipeline
This DAG extracts, transforms, and loads parquet files with basic data cleaning and logging.
"""

with DAG('etl_parquet_dag', default_args=default_args, schedule_interval='@daily', catchup=False, doc_md=doc_md) as dag:
    # [!]catchup=False means without backfilling the DAG for the time periods between the start_date and now.

    extract_task = PythonOperator(
        task_id='extract_task',
        python_callable=extract,
        do_xcom_push=True,
    )

    transform_task = PythonOperator(
        task_id='transform_task',
        python_callable=transform,
        do_xcom_push=True,
    )

    load_task = PythonOperator(
        task_id='load_task',
        python_callable=load,
    )

    extract_task >> transform_task >> load_task

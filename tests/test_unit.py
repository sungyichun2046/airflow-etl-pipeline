"""
Test suite for the Airflow ETL DAG "etl_parquet_dag".

This module tests:
- DAG existence and task presence
- Successful execution of extract, transform, and load tasks
- Proper mocking of XCom pull to simulate file inputs

Each test runs with a fixed execution date for reproducibility.
"""

from datetime import datetime
from typing import Generator

import pandas as pd
import pytest
from airflow.models import DagBag, TaskInstance
from airflow.utils.state import State

DAG_ID = "etl_parquet_dag"
EXECUTION_DATE = datetime(2025, 7, 3)


@pytest.fixture(scope="module")
def dag() -> Generator:
    """
    Load the DAG from Airflow DagBag and ensure it exists.

    :return: DAG object
    """
    dagbag = DagBag()
    dag = dagbag.get_dag(DAG_ID)
    assert dag is not None, "DAG %s not found" % DAG_ID
    return dag


def test_dag_tasks(dag):
    """
    Verify the DAG contains the expected task IDs.

    :param dag: DAG object from fixture
    """
    task_ids = [task.task_id for task in dag.tasks]
    assert "extract_task" in task_ids
    assert "transform_task" in task_ids
    assert "load_task" in task_ids


def test_extract_task_run(dag):
    """
    Run the extract_task and assert it completes successfully.

    :param dag: DAG object from fixture
    """
    task = dag.get_task("extract_task")
    ti = TaskInstance(task=task, execution_date=EXECUTION_DATE)
    ti.run(ignore_ti_state=True)
    assert ti.state == State.SUCCESS


def test_transform_task_run(dag, tmp_path):
    """
    Prepare a parquet input file and run transform_task,
    mocking the XCom pull to return the input file path.

    :param dag: DAG object from fixture
    :param tmp_path: pytest fixture for temporary directory
    """
    input_file = tmp_path / "listing_raw_technical_test.parquet"
    df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
    df.to_parquet(input_file)

    task = dag.get_task("transform_task")
    ti = TaskInstance(task=task, execution_date=EXECUTION_DATE)

    # Mock xcom_pull to accept any arguments and return input_file path
    ti.xcom_pull = lambda *args, **kwargs: str(input_file)

    ti.run(ignore_ti_state=True)
    assert ti.state == State.SUCCESS


def test_load_task_run(dag, tmp_path):
    """
    Prepare a parquet output file and run load_task,
    mocking the XCom pull to return the output file path.

    :param dag: DAG object from fixture
    :param tmp_path: pytest fixture for temporary directory
    """
    output_file = tmp_path / "processed.parquet"
    df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
    df.to_parquet(output_file)

    task = dag.get_task("load_task")
    ti = TaskInstance(task=task, execution_date=EXECUTION_DATE)

    # Mock xcom_pull to accept any arguments and return output_file path
    # To simulate retrieving files produced by previous tasks without depending on a full real run
    ti.xcom_pull = lambda *args, **kwargs: str(output_file)

    # Overrides this behavior and forces the task to execute again even if it previously succeeded or failed.
    ti.run(ignore_ti_state=True)
    assert ti.state == State.SUCCESS

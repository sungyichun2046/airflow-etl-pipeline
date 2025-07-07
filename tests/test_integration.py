"""
Test suite for Airflow ETL DAG tasks.

Includes:
- DAG existence and task presence checks
- Individual task runs with mocked inputs where needed
- Uses pytest fixtures for setup and teardown
"""

import logging
from typing import Generator

import pandas as pd
import pytest
from airflow.models import DagBag, DagRun, TaskInstance
from airflow.utils import timezone
from airflow.utils.session import create_session
from airflow.utils.state import State
from airflow.utils.types import DagRunType

DAG_ID = "etl_parquet_dag"
EXECUTION_DATE = timezone.datetime(2025, 7, 3, 0, 0, 0)  # timezone-aware datetime required
POLL_INTERVAL = 5  # seconds


@pytest.fixture(scope="module")
def dag() -> Generator:
    """
    Load the DAG from DagBag and ensure it exists.

    :return: DAG object
    """
    dagbag = DagBag()
    dag = dagbag.get_dag(DAG_ID)
    assert dag is not None, "DAG %s not found in DagBag." % DAG_ID
    yield dag


@pytest.fixture(scope="module", autouse=True)
def create_dag_run(dag) -> DagRun:
    """
    Ensure a DagRun exists for the specified execution date, creating one if necessary.

    Retries to find or create the DAG run once per call.

    :param dag: DAG object to create run for
    :return: DagRun object
    """
    with create_session() as session:
        dag_run = session.query(DagRun).filter(
            DagRun.dag_id == DAG_ID,
            DagRun.execution_date == EXECUTION_DATE
        ).first()

        if not dag_run:
            dag_run = dag.create_dagrun(
                run_id="manual__%s" % EXECUTION_DATE.isoformat(),
                execution_date=EXECUTION_DATE,
                start_date=timezone.utcnow(),
                state=State.RUNNING,
                run_type=DagRunType.MANUAL,
            )
            session.add(dag_run)
            session.commit()
            logging.info("Created new DAG run %s for DAG %s", dag_run.run_id, DAG_ID)
        else:
            logging.info("Found existing DAG run %s for DAG %s", dag_run.run_id, DAG_ID)
    return dag_run


def test_dag_tasks(dag) -> None:
    """
    Verify that the expected task IDs exist in the DAG.

    :param dag: DAG object
    """
    task_ids = [task.task_id for task in dag.tasks]
    assert "extract_task" in task_ids
    assert "transform_task" in task_ids
    assert "load_task" in task_ids


def test_extract_task_run(dag) -> None:
    """
    Run the extract task and assert it succeeds.

    :param dag: DAG object
    """
    task = dag.get_task("extract_task")
    ti = TaskInstance(task=task, execution_date=EXECUTION_DATE)
    ti.run(ignore_ti_state=True)
    assert ti.state == State.SUCCESS


def test_transform_task_run(dag, tmp_path) -> None:
    """
    Run the transform task with mocked XCom input (parquet file path) and assert success.

    :param dag: DAG object
    :param tmp_path: pytest tmp_path fixture for temp directory
    """
    input_file = tmp_path / "listing_raw_technical_test.parquet"
    df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
    df.to_parquet(input_file)

    task = dag.get_task("transform_task")
    ti = TaskInstance(task=task, execution_date=EXECUTION_DATE)
    # Mock xcom_pull to return the input file path
    ti.xcom_pull = lambda task_ids: str(input_file)

    ti.run(ignore_ti_state=True)
    assert ti.state == State.SUCCESS


def test_load_task_run(dag, tmp_path) -> None:
    """
    Run the load task with mocked XCom input (parquet file path) and assert success.

    :param dag: DAG object
    :param tmp_path: pytest tmp_path fixture for temp directory
    """
    output_file = tmp_path / "processed.parquet"
    df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
    df.to_parquet(output_file)

    task = dag.get_task("load_task")
    ti = TaskInstance(task=task, execution_date=EXECUTION_DATE)
    # Mock xcom_pull to return the output file path
    ti.xcom_pull = lambda task_ids: str(output_file)

    ti.run(ignore_ti_state=True)
    assert ti.state == State.SUCCESS

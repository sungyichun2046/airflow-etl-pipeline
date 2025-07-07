"""
End-to-End Test for Airflow DAG: etl_parquet_dag

The test workflow:
1) The test waits briefly to let the Airflow scheduler load the DAGs via DagBag.
2) It loads the DAG to be tested from DagBag and checks it exists in the database.
3) It triggers a DAG run.
4) First retry: it checks every 5 seconds, up to 1 minute, that the DAG run has started.
5) Second retry: it checks every 5 seconds, up to 5 minutes, that the DAG run has completed (success or failure).
6) It verifies that the expected output file has been generated.

This test helps ensure the DAG's end-to-end pipeline works as expected from triggering to output generation.
"""
import logging
import os
import time

import pytest
from airflow.api.common.experimental.trigger_dag import trigger_dag
from airflow.models import DagBag, DagModel, DagRun, TaskInstance
from airflow.utils.session import create_session
from airflow.utils.state import State

DAG_ID = "etl_parquet_dag"


@pytest.mark.skipif(
    os.getenv("SKIP_END2END_TRIGGER") == "true",
    reason="Skipping end-to-end test in CI due to the instability of Airflow scheduling and triggering."
)
def test_dag_run():
    """End-to-end Airflow DAG run test.

    Due to instability of Airflow scheduling in CI, this test is better run locally or in dedicated environments.
    The test triggers the DAG, waits for completion, checks task states, and validates output file creation.
    """
    # Wait briefly to let Airflow scheduler parse DAGs
    time.sleep(10)

    # Load DAG from DagBag
    dagbag = DagBag()
    dag = dagbag.get_dag(DAG_ID)
    assert dag is not None, "DAG '%s' not found in DagBag." % DAG_ID

    # Check DAG is not paused
    with create_session() as session:
        dag_model = session.query(DagModel).filter(DagModel.dag_id == DAG_ID).first()
        if dag_model.is_paused:
            dag_model.is_paused = False
            session.commit()

    # Trigger DAG run
    execution_date = trigger_dag(dag_id=DAG_ID)
    assert execution_date is not None, "Failed to trigger DAG run."

    poll_interval = 5
    dag_run = None

    # Wait and check every 5 seconds if the DAG run is created, up to 60 seconds timeout
    with create_session() as session:
        # Request the Airflow metadata database every 5 seconds to check for the DAG run creation,
        # retrying until a DAG run is found or the 60-second timeout is reached
        timeout = 60
        waited = 0
        while waited < timeout:
            dag_run = (
                session.query(DagRun)
                .filter(DagRun.dag_id == DAG_ID)
                .order_by(DagRun.execution_date.desc())
                .first()
            )
            if dag_run:
                break
            logging.info("Waiting for DAG run to be created...")
            time.sleep(poll_interval)
            waited += poll_interval

        assert dag_run is not None, "DAG Run was not created within timeout."

        # Print task instance states for debugging
        tis = (
            session.query(TaskInstance)
            .filter(
                TaskInstance.dag_id == DAG_ID,
                TaskInstance.execution_date == dag_run.execution_date,
            )
            .all()
        )
        for ti in tis:
            logging.info("Task %s: state=%s", ti.task_id, ti.state)

        # Request the Airflow metadata database every 5 seconds to check if the DAG run has finished,
        # retrying until it succeeds, fails, or the 300-second timeout is reached
        timeout = 300
        waited = 0
        while dag_run.get_state() not in {State.SUCCESS, State.FAILED} and waited < timeout:
            logging.info("DAG Run status: %s, waiting...", dag_run.get_state())
            time.sleep(poll_interval)
            waited += poll_interval
            session.refresh(dag_run)  # Reloads DAG run state from the database to get the latest execution status.

        assert (
            dag_run.get_state() == State.SUCCESS
        ), "DAG run failed or timed out with state %s." % dag_run.get_state()

    # Check if output file exists
    output_file = "/opt/airflow/data/processed.parquet"
    assert os.path.exists(output_file), "Output file '%s' not found." % output_file

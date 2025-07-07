FROM apache/airflow:2.8.1

USER root

# Install system-level dependencies if needed (example: for pandas, psycopg2)
# Use apt-get clean and rm -rf /var/lib/apt/lists/*: Minimizes final image size
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    --no-install-recommends && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

USER airflow

# Cache pip install step to avoid re-installing on every DAG change
COPY requirements.txt /opt/airflow/requirements.txt

RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /opt/airflow/requirements.txt


COPY ./dags /opt/airflow/dags
COPY ./data  /opt/airflow/data
COPY ./tests /opt/airflow/tests
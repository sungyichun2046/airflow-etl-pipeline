#!/bin/bash
set -e

echo "Step 1: Fix permissions on ./data folder"
sudo chmod -R 777 ./data

echo "Step 2: Start Postgres database container"
docker-compose up -d postgres

echo "Step 3: Initialize Airflow metadata database"
docker-compose run --rm airflow-webserver airflow db init

echo "Step 4: Create Airflow admin user"
docker-compose run --rm airflow-webserver airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com \
  --password admin

echo "Airflow setup completed! You can now run docker-compose up -d to start Airflow webserver and scheduler."

# 📦 airflow-etl-pipeline
![CI](https://github.com/sungyichun2046/airflow-etl-pipeline/actions/workflows/ci.yml/badge.svg?branch=main)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/github/license/sungyichun2046/airflow-etl-pipeline)

### 📚 Overview
This project builds a scalable, production-like ETL pipeline with:

- **Apache Airflow (with web UI)** for orchestration of extract-transform-load steps, including data clean and deduplication

- **Docker** & Docker Compose for containerized setup

- **Terraform** for local infrastructure simulation

- **Pytest** for unit, integration and end2end testing

- **GitHub Actions** for CI workflows running Pytest and automated tests

### 📚 Demo
![Demo](images/airflow_etl.gif)

### 📚 Project Structure
```text
airflow-etl-pipeline/
├── dags/                          # Airflow DAGs
│   ├── __init__.py
│   ├── etl_pipeline.py            # ETL pipeline DAG
│   └── etl_utils.py               # Utility functions (e.g. data cleaning)
├── data/                          # Raw and processed data
│   ├── input.parquet              # Input data
│   └── processed.parquet          # Output data
├── terraform/                     # Option 2: Deploy with Terraform
│   ├── provider.tf                # Docker local provider config
│   ├── variables.tf               # Reusable variables
│   ├── main.tf                    # Resources (containers, networks, volumes, etc.)
│   └── outputs.tf                 # Useful outputs after `terraform apply`
|   ├──  terraform.tfvars.example  # tfvars template
│   └── terraform.tfvars           # tfvars 
├── tests/                         # Unit, integration, and end-to-end tests
│   ├── test_end2end.py
│   ├── test_integration.py
│   └── test_unit.py
│   └── test_cleaning.py
├── .github/                      # GitHub Actions CI workflows
│   └── workflows/
│       └── ci.yml
├── requirements.txt              # Python dependencies
├── custom-airflow.Dockerfile     # Custom Dockerfile shared by both options
├── docker-compose.yml            # Option 1: Deploy with Docker Compose
│── setup_airflow.sh              # bash file to automate Airflow setup steps
└── README.md                    
└── .env
└── .env.example
└── .gitignore   
└── images/                       # gif on Readme
    └── airflow_etl.gif
```
### 📚 Run Steps

#### **Part I**: Run Airflow DAG with docker-compose.yml 
* Put `listing_raw_technical_test.parquet` in folder `/data`
* Use `.env.example` to create `.env` file, update `AIRFLOW__WEBSERVER__SECRET_KEY` value (`openssl rand -hex 32` to generate `airflow_secret_key`)
* **Set up Airflow from scratch, run the first time**: 
  * `chmod +x setup_airflow.sh`
  * `./setup_airflow.sh`
* **Run Airflow with ui**: 
  * Start the Airflow webserver and scheduler: `docker-compose up -d`
  * Access the Airflow UI at: `http://localhost:8080` and run ETL (username: admin and password: admin created during previous step)
 

#### **Part II** Run Tests (Unit, Integration, End-to-End):
    docker-compose run --rm airflow-webserver bash -c "PYTHONPATH=/opt/airflow pytest tests/"

#### **Part III** Local production-like Airflow DAG with Terraform 
* To clean up all resources created by docker-compose: `docker-compose down -v`
* Install Terraform via one of two methods:

  * Method 1: Follow the official HashiCorp tutorial: https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli

  * Method 2:  Manual download and install:

  ```
  1) wget https://releases.hashicorp.com/terraform/1.5.7/terraform_1.5.7_linux_amd64.zip
  2) unzip terraform_1.5.7_linux_amd64.zip
  3) sudo mv terraform /usr/local/bin/
  4) terraform -version
  ```
* Create `terraform.tfvars` based `terraform.tfvars.example` in folder `terraform` (`openssl rand -hex 32` to generate `airflow_secret_key`)
* Run Airflow with terraform
  ```
  1) cd terraform
  2) terraform init
  3) terraform apply -var-file="terraform.tfvars"
  ```
* Access the Airflow UI at: `http://localhost:8080` and run ETL (username: admin and password: admin, variables in main.tf)
* To clean up all resources created by Terraform: `terraform destroy -var-file="terraform.tfvars" -auto-approve` 

### 📚 Useful commands
* Go inside the container: `docker exec -it <CONTAINER NAME> bash` (e.g. `docker exec -it airflow-etl-pipeline-airflow-webserver-1 bash`)
* See logs: `docker logs <CONTAINER NAME>`

### 📚 Recommended Debug Workflow
* Go inside the container: `docker exec -it <CONTAINER NAME> bash` 
* Check if the scheduler is running: `airflow scheduler health`
```
Expected output: 
{"metadatabase": {"status": "healthy"}, "scheduler": {"status": "healthy"}}
```
* (If the scheduler is not running) Start the scheduler: `airflow scheduler`
* List available DAGs: `airflow dags list` 
```commandline
dag_id          | filepath        | owner   | paused
================+=================+=========+=======
etl_parquet_dag | etl_pipeline.py | airflow | False 
```
* Check if the DAG is paused : `airflow dags list | grep <dag_id>`
** If paused: `airflow dags unpause <dag_id>`
* Trigger the DAG manually: `airflow dags trigger <dag_id>`
* Monitor active DAG runs: `airflow dags list-runs -d <dag_id>`
* Check task tree and statuses: `airflow tasks list <dag_id> --tree`
* Follow task logs (live or post-execution): `airflow tasks logs <dag_id> <task_id> <execution_date>`

### 📚 Next steps
* Deduplication based on cosine similarity or using a vector database for intelligent similarity searches on addresses or descriptions.
* Better manage secrets using a specialized tool.
* Implement monitoring and alerting.
* Use Kubernetes for scaling in production.
* Optimize transformation steps with parallel processing (multithreading, multiprocessing, Spark, or Dask) to speed up ETL on large datasets.

### 📚 Other tools to consider:
* Upgrade from LocalExecutor to CeleryExecutor for parallel task execution, then to KubernetesExecutor for scalable distributed execution.
* Secret managers (Vault, AWS Secrets Manager) for security
* DVC for data versioning
* Kafka for real-time ingestion
* ELK/Grafana for monitoring and alerting
* pytest-airflow for better DAG testing support or moto to mock AWS services.
* Handle big data with Spark and Airflow for distributed processing and better scalability



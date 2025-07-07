# Initialize the Airflow Database
# null_resource => run local commands in Terraform
resource "null_resource" "airflow_db_init" {
  provisioner "local-exec" {
    command = "docker exec airflow-webserver airflow db init"
  }

  # Force re-execution of resource on every apply, even if no changes are detected.
  triggers = {
    always_run = timestamp()
  }

  # Ensure that the webserver container is up before initializing the database
  # Webserver must be running for `docker exec`, but it's not ready until DB is initialized.
  depends_on = [docker_container.airflow_webserver]
}

# Create an Airflow user after the DB is initialized and the webserver is running
resource "null_resource" "airflow_create_user" {
  provisioner "local-exec" {
    command = <<EOT
# Wait until the Airflow webserver is fully ready to accept commands
until docker exec airflow-webserver airflow users list > /dev/null 2>&1; do
  echo "Waiting for Airflow to be ready..."
  sleep 5
done

# Create an admin user to access the Airflow UI
docker exec airflow-webserver airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com \
  --password admin
EOT
  }

  # Ensure this step is always re-executed
  triggers = {
    always_run = timestamp()
  }

  # Ensure the DB is initialized first
  depends_on = [null_resource.airflow_db_init]
}

# Define a Docker volume to persist PostgreSQL data
resource "docker_volume" "postgres_data" {
  name = "postgres_data"
}

# Create a dedicated Docker network for the Airflow setup
resource "docker_network" "airflow_network" {
  name = "airflow_network"
}

# Build a custom Airflow Docker image
resource "docker_image" "airflow_custom" {
  name         = var.airflow_image_name
  build {
    context    = "../"
    dockerfile = "custom-airflow.Dockerfile"
  }
}

# Define the PostgreSQL container
resource "docker_container" "postgres" {
  name    = "postgres"
  image   = var.postgres_image
  restart = "always"

  env = [
    "POSTGRES_USER=${var.postgres_user}",
    "POSTGRES_PASSWORD=${var.postgres_password}",
    "POSTGRES_DB=${var.postgres_db}",
  ]

  # Using internal Docker network without exposing ports to the host machine.
  # Advantage: Avoids port conflicts and improves security by isolating the database from external access
  volumes {
    volume_name    = docker_volume.postgres_data.name
    container_path = "/var/lib/postgresql/data"
    # Data stored in Docker volume (managed externally by Docker), not inside container
  }

  # Connect the container to the Airflow network
  networks_advanced {
    name = docker_network.airflow_network.name
  }
}

# Define the Airflow webserver container
resource "docker_container" "airflow_webserver" {
  name    = "airflow-webserver"
  image   = docker_image.airflow_custom.name
  restart = "always"

  env = [
    "AIRFLOW__CORE__SQL_ALCHEMY_CONN=postgresql+psycopg2://${var.postgres_user}:${var.postgres_password}@postgres/${var.postgres_db}",
    "AIRFLOW__CORE__EXECUTOR=SequentialExecutor",
    "AIRFLOW__WEBSERVER__SECRET_KEY=${var.airflow_secret_key}",
    "AIRFLOW__CORE__LOAD_EXAMPLES=False",
  ]

  ports {
    internal = 8080
    external = var.airflow_webserver_port
  }

  # Mount local folders for DAGs, data, and tests into the container
  volumes {
    host_path      = "${path.cwd}/../dags"
    container_path = "/opt/airflow/dags"
  }

  volumes {
    host_path      = "${path.cwd}/../data"
    container_path = "/opt/airflow/data"
  }

  volumes {
    host_path      = "${path.cwd}/../tests"
    container_path = "/opt/airflow/tests"
  }

  networks_advanced {
    name = docker_network.airflow_network.name
  }

  # Start the Airflow webserver
  command = ["airflow", "webserver"]
}

# Define the Airflow scheduler container
resource "docker_container" "airflow_scheduler" {
  name    = "airflow-scheduler"
  image   = docker_image.airflow_custom.name
  restart = "always"

  env = [
    "AIRFLOW__CORE__SQL_ALCHEMY_CONN=postgresql+psycopg2://${var.postgres_user}:${var.postgres_password}@postgres/${var.postgres_db}",
    "AIRFLOW__CORE__EXECUTOR=SequentialExecutor",
    "AIRFLOW__WEBSERVER__SECRET_KEY=${var.airflow_secret_key}",
  ]

  # Mount local folders for DAGs, data, and tests into the container
  volumes {
    host_path      = "${path.cwd}/../dags"
    container_path = "/opt/airflow/dags"
  }

  volumes {
    host_path      = "${path.cwd}/../data"
    container_path = "/opt/airflow/data"
  }

  volumes {
    host_path      = "${path.cwd}/../tests"
    container_path = "/opt/airflow/tests"
  }

  networks_advanced {
    name = docker_network.airflow_network.name
  }

  # Start the Airflow scheduler
  command = ["airflow", "scheduler"]
}

# Output a command to display the Airflow webserver logs
output "airflow_webserver_logs" {
  value = "docker logs -f airflow-webserver"
}

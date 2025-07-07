output "airflow_webserver_url" {
  value = "http://localhost:${var.airflow_webserver_port}"
  description = "Airflow Webserver URL"
}

output "postgres_container_name" {
  value = docker_container.postgres.name
}

output "airflow_webserver_container_name" {
  value = docker_container.airflow_webserver.name
}

output "airflow_scheduler_container_name" {
  value = docker_container.airflow_scheduler.name
}

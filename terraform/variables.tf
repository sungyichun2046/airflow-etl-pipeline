variable "postgres_user" {
  description = "Postgres username"
  type        = string
}

variable "postgres_password" {
  description = "Postgres password"
  type        = string
}

variable "postgres_db" {
  description = "Postgres database name"
  type        = string
}

variable "airflow_secret_key" {
  description = "Airflow webserver secret key"
  type        = string
}

variable "airflow_webserver_port" {
  description = "External port for Airflow Webserver"
  type        = number
  default     = 8080
}

variable "postgres_image" {
  description = "Postgres image"
  type        = string
  default = "postgres:13"
}

variable "airflow_image_name" {
  description = "Airflow image name"
  type        = string
  default = "custom-airflow-image"
}
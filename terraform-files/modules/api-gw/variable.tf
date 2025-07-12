variable "api_name" {
  type = string
}
variable "resource_path" {
  type = string
}
variable "stage_name" {
  type = string
  default = "prod"
}
variable "lambda_invoke_arn" {
  type = string
}
variable "lambda_name" {
  type = string
}
variable "region" {
  type = string
}

variable "bucket"        { type = string }
variable "object_key"    { type = string }
variable "source_code_hash" { type = string }
variable "function_name" { type = string }
variable "handler"       { type = string }
variable "runtime"       { type = string }
variable "role_name"     { type = string }
variable "log_retention" {
  type    = number
  default = 30
}

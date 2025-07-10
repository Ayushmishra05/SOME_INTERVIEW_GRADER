variable "repository_name" {
  description = "Name of the ECR repository"
  type        = string
}

variable "image_tag_mutability" {
  description = "Whether image tags can be overwritten (MUTABLE) or not (IMMUTABLE)"
  type        = string
  default     = "MUTABLE"
}

variable "scan_on_push" {
  description = "Whether to scan images on push for vulnerabilities"
  type        = bool
  default     = true
}

variable "enable_lifecycle_policy" {
  description = "Whether to enable a lifecycle policy to manage old images"
  type        = bool
  default     = true
}

variable "max_image_count" {
  description = "Maximum number of images to keep in the repository (used in lifecycle policy)"
  type        = number
  default     = 10
}

variable "tags" {
  description = "Tags to apply to the ECR repository"
  type        = map(string)
  default     = {}
}
variable "force_delete" {
  description = "Delete repository even if it still contains images"
  type        = bool
  default     = false
}
variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "root_domain" {
  description = "Hosted zone root domain, e.g. clinicline.ai"
  type        = string
  default     = "clinicline.ai"
}

variable "domain_name" {
  description = "Subdomain for API"
  type        = string
  default     = "api.clinicline.ai"
}

variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
}

variable "container_port" {
  description = "Port the container exposes (uvicorn)"
  type        = number
  default     = 8000
}

variable "project_id" {
  type        = string
  description = "gapinc-sandbox"
}

variable "location" {
  type        = string
  description = "The region to deploy the reasoning engine"
  default     = "us-central1"
}

variable "repository_name" {
  type        = string
  description = "The Artifact Registry repository name"
  default     = "agent-repo"
}

variable "image_tag" {
  type        = string
  description = "The tag of the container image to deploy"
  default     = "latest"
}

variable "repository_location" {
  type        = string
  description = "The region or multi-region of the Artifact Registry repository"
  default     = "us"
}
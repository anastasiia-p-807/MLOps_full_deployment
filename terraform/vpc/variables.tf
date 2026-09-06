variable "aws_region" {
  description = "AWS region where VPC resources will be created."
  type        = string
  default     = "eu-central-1"
}

variable "aws_profile" {
  description = "Optional local AWS CLI profile name. Leave empty to use default AWS credential resolution."
  type        = string
  default     = "default"
}

variable "project_name" {
  description = "Project name used in resource names and tags."
  type        = string
  default     = "final-mlops"
}

variable "environment" {
  description = "Environment name used in resource names and tags."
  type        = string
  default     = "dev"
}

variable "cluster_name" {
  description = "EKS cluster name used for Kubernetes subnet tags."
  type        = string
  default     = "final-mlops-dev-eks"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones to use."
  type        = number
  default     = 2
}

variable "public_subnets" {
  description = "CIDR blocks for public subnets."
  type        = list(string)
  default     = ["10.20.1.0/24", "10.20.2.0/24"]
}

variable "private_subnets" {
  description = "CIDR blocks for private subnets."
  type        = list(string)
  default     = ["10.20.11.0/24", "10.20.12.0/24"]
}

variable "enable_nat_gateway" {
  description = "Whether to create NAT Gateway for private subnets."
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "Use one NAT Gateway to reduce lesson environment cost."
  type        = bool
  default     = true
}

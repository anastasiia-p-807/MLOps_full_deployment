variable "aws_region" {
  description = "AWS region where EKS resources will be created. Must match the VPC state region."
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
  description = "EKS cluster name."
  type        = string
  default     = "final-mlops-dev-eks"
}

variable "kubernetes_version" {
  description = "EKS Kubernetes version."
  type        = string
  default     = "1.33"
}

variable "tf_state_bucket" {
  description = "S3 bucket with Terraform remote state."
  type        = string
}

variable "vpc_state_key" {
  description = "S3 key for the VPC Terraform state file."
  type        = string
  default     = "final/vpc/terraform.tfstate"
}

variable "cpu_node_instance_types" {
  description = "Instance types for CPU node group."
  type        = list(string)
  default     = ["t3.medium"]
}

variable "workload_node_instance_types" {
  description = "Instance types for the second workload node group. Defaults to CPU instances to avoid GPU cost."
  type        = list(string)
  default     = ["t3.medium"]
}

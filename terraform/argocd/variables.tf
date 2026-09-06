variable "aws_region" {
  description = "AWS region with the existing EKS cluster."
  type        = string
  default     = "eu-central-1"
}

variable "aws_profile" {
  description = "Local AWS CLI profile used by Terraform."
  type        = string
  default     = "default"
}

variable "cluster_name" {
  description = "Existing EKS cluster name."
  type        = string
  default     = "final-mlops-dev-eks"
}

variable "namespace" {
  description = "Namespace where Argo CD will be installed."
  type        = string
  default     = "mlops-system"
}

variable "argocd_chart_version" {
  description = "argo-cd Helm chart version."
  type        = string
  default     = "10.4.1"
}

variable "gitops_repo_url" {
  description = "Public Git repository URL with namespace/* manifests watched by ApplicationSet."
  type        = string
  default     = "https://github.com/anastasiia-p-807/MLOps_full_deployment.git"
}

variable "gitops_target_revision" {
  description = "Git revision watched by ApplicationSet."
  type        = string
  default     = "HEAD"
}

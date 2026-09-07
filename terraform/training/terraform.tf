terraform {
  required_version = ">= 1.5.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.62"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7"
    }
  }
  backend "s3" {}
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile != "" ? var.aws_profile : null
  default_tags {
    tags = { Project = "final-mlops", ManagedBy = "terraform" }
  }
}

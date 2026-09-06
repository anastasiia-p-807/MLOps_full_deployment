locals {
  name = "${var.project_name}-${var.environment}"
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 21.0"

  name               = var.cluster_name
  kubernetes_version = var.kubernetes_version

  endpoint_public_access                   = true
  enable_cluster_creator_admin_permissions = true

  compute_config = {
    enabled = false
  }

  addons = {
    coredns = {}
    eks-pod-identity-agent = {
      before_compute = true
    }
    kube-proxy = {}
    vpc-cni = {
      before_compute = true
    }
  }

  vpc_id                   = data.terraform_remote_state.vpc.outputs.vpc_id
  subnet_ids               = data.terraform_remote_state.vpc.outputs.private_subnets
  control_plane_subnet_ids = data.terraform_remote_state.vpc.outputs.private_subnets

  eks_managed_node_groups = {
    cpu-nodes = {
      ami_type       = "AL2023_x86_64_STANDARD"
      instance_types = var.cpu_node_instance_types
      capacity_type  = "ON_DEMAND"

      min_size     = 1
      max_size     = 2
      desired_size = 1

      labels = {
        workload = "cpu"
      }
    }

    gpu-nodes = {
      ami_type       = "AL2023_x86_64_STANDARD"
      instance_types = var.workload_node_instance_types
      capacity_type  = "ON_DEMAND"

      min_size     = 0
      max_size     = 1
      desired_size = 0

      labels = {
        workload = "gpu-ready"
      }

      taints = {
        workload = {
          key    = "workload"
          value  = "gpu"
          effect = "NO_SCHEDULE"
        }
      }
    }
  }

  tags = {
    Name = var.cluster_name
  }
}

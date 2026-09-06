data "terraform_remote_state" "vpc" {
  backend = "s3"

  config = merge(
    {
      bucket = var.tf_state_bucket
      key    = var.vpc_state_key
      region = var.aws_region
    },
    var.aws_profile != "" ? { profile = var.aws_profile } : {}
  )
}

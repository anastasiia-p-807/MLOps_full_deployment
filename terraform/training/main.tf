data "aws_caller_identity" "current" {}
data "aws_eks_cluster" "this" { name = var.cluster_name }

locals {
  name        = "final-mlops-training"
  machine_arn = "arn:aws:states:${var.aws_region}:${data.aws_caller_identity.current.account_id}:stateMachine:${local.name}"
}

data "archive_file" "validator" {
  type        = "zip"
  source_file = "${path.module}/../../apps/training/validate_input.py"
  output_path = "${path.module}/.terraform/validate_input.zip"
}

resource "aws_iam_role" "validator" {
  name = "${local.name}-validator"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_cloudwatch_log_group" "validator" {
  name              = "/aws/lambda/${local.name}-validate"
  retention_in_days = 7
}

resource "aws_iam_role_policy" "validator_logs" {
  role = aws_iam_role.validator.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"],
      Resource = "${aws_cloudwatch_log_group.validator.arn}:*"
    }]
  })
}

resource "aws_lambda_function" "validate" {
  function_name    = "${local.name}-validate"
  role             = aws_iam_role.validator.arn
  filename         = data.archive_file.validator.output_path
  source_code_hash = data.archive_file.validator.output_base64sha256
  handler          = "validate_input.handler"
  runtime          = "python3.13"
  timeout          = 10
  memory_size      = 128
  depends_on       = [aws_iam_role_policy.validator_logs]
}

resource "aws_iam_role" "pipeline" {
  name = "${local.name}-pipeline"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow", Principal = { Service = "states.amazonaws.com" }, Action = "sts:AssumeRole",
      Condition = {
        StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id }
        ArnEquals    = { "aws:SourceArn" = local.machine_arn }
      }
    }]
  })
}

resource "aws_iam_role_policy" "pipeline" {
  role = aws_iam_role.pipeline.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["lambda:InvokeFunction"], Resource = aws_lambda_function.validate.arn },
      { Effect = "Allow", Action = ["eks:DescribeCluster"], Resource = data.aws_eks_cluster.this.arn }
    ]
  })
}

resource "aws_eks_access_entry" "pipeline" {
  cluster_name      = var.cluster_name
  principal_arn     = aws_iam_role.pipeline.arn
  kubernetes_groups = ["training-orchestrator"]
  type              = "STANDARD"
}

resource "aws_sfn_state_machine" "training" {
  name     = local.name
  role_arn = aws_iam_role.pipeline.arn
  type     = "STANDARD"
  definition = jsonencode({
    StartAt        = "ValidateInput"
    TimeoutSeconds = 1800
    States = {
      ValidateInput = {
        Type = "Task", Resource = aws_lambda_function.validate.arn, Next = "TrainAndRegister"
      }
      TrainAndRegister = {
        Type           = "Task", Resource = "arn:aws:states:::eks:runJob.sync", End = true,
        TimeoutSeconds = 1700
        Parameters = {
          ClusterName          = var.cluster_name
          CertificateAuthority = data.aws_eks_cluster.this.certificate_authority[0].data
          Endpoint             = data.aws_eks_cluster.this.endpoint
          Namespace            = "mlops-training"
          LogOptions           = { RetrieveLogs = true, RawLogs = true, LogParameters = { tailLines = ["30"], limitBytes = ["16000"] } }
          Job = {
            apiVersion = "batch/v1", kind = "Job"
            metadata   = { "name.$" = "$.job_name", labels = { app = "iris-training" } }
            spec = {
              backoffLimit = 0, activeDeadlineSeconds = 1500, ttlSecondsAfterFinished = 86400
              template = {
                metadata = { labels = { app = "iris-training" } }
                spec = {
                  serviceAccountName           = "training-worker"
                  automountServiceAccountToken = false
                  restartPolicy                = "Never"
                  containers = [{
                    name      = "training", image = "python:3.13-slim"
                    command   = ["python", "-u", "-c", file("${path.module}/../../apps/training/job_bootstrap.py")]
                    resources = { requests = { cpu = "250m", memory = "512Mi" }, limits = { cpu = "1", memory = "1536Mi" } }
                    env = [
                      { name = "TRAINING_GIT_SHA", "value.$" = "$.git_sha" },
                      { name = "DATASET_VERSION", "value.$" = "$.dataset_version" },
                      { name = "MLFLOW_TRACKING_URI", value = "http://mlflow.mlops-system.svc.cluster.local:5000" },
                      { name = "MLFLOW_S3_ENDPOINT_URL", value = "http://minio.mlops-system.svc.cluster.local:9000" },
                      { name = "AWS_DEFAULT_REGION", value = var.aws_region },
                      { name = "AWS_ACCESS_KEY_ID", valueFrom = { secretKeyRef = { name = "training-artifacts", key = "root-user" } } },
                      { name = "AWS_SECRET_ACCESS_KEY", valueFrom = { secretKeyRef = { name = "training-artifacts", key = "root-password" } } }
                    ]
                  }]
                }
              }
            }
          }
        }
      }
    }
  })
  depends_on = [aws_iam_role_policy.pipeline, aws_eks_access_entry.pipeline]
}

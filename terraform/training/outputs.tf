output "state_machine_arn" { value = aws_sfn_state_machine.training.arn }
output "validator_lambda_name" { value = aws_lambda_function.validate.function_name }

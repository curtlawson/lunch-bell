resource "aws_scheduler_schedule" "daily" {
  name       = "${var.project}-daily"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  # Run at 8 AM Central (14:00 UTC) every day
  schedule_expression          = "cron(0 14 * * ? *)"
  schedule_expression_timezone = "America/Chicago"

  target {
    arn      = aws_lambda_function.lunch_bell.arn
    role_arn = aws_iam_role.scheduler.arn
  }
}

data "aws_iam_policy_document" "scheduler_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${var.project}-scheduler"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
}

resource "aws_iam_role_policy" "scheduler" {
  name = "${var.project}-scheduler-policy"
  role = aws_iam_role.scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = aws_lambda_function.lunch_bell.arn
    }]
  })
}

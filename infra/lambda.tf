resource "aws_lambda_function" "lunch_bell" {
  function_name = var.project
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.lambda.repository_url}:latest"

  timeout     = 300
  memory_size = 512

  environment {
    variables = {
      S3_BUCKET             = aws_s3_bucket.ical.id
      CLOUDFRONT_DIST_ID    = aws_cloudfront_distribution.ical.id
      SSM_PREFIX            = "/${var.project}/last-pdf"
      MENU_PAGE_URL         = var.menu_page_url
      ICAL_DOMAIN           = var.domain
    }
  }

  depends_on = [aws_iam_role_policy.lambda]

  # The ECR image must exist before Terraform can create/update the function.
  # On first deploy the image is pushed by CI before `terraform apply` runs.
  lifecycle {
    ignore_changes = [image_uri]
  }
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project}"
  retention_in_days = 30
}

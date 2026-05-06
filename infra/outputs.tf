output "ecr_repository_url" {
  description = "ECR repository URL for the Lambda Docker image"
  value       = aws_ecr_repository.lambda.repository_url
}

output "s3_bucket" {
  description = "S3 bucket serving the .ics files"
  value       = aws_s3_bucket.ical.id
}

output "cloudfront_domain" {
  description = "CloudFront domain name for the iCal feeds"
  value       = aws_cloudfront_distribution.ical.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID (needed for cache invalidation)"
  value       = aws_cloudfront_distribution.ical.id
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.lunch_bell.function_name
}

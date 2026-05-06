resource "aws_s3_bucket" "ical" {
  bucket = "${var.project}-ical-${var.aws_account_id}"
}

resource "aws_s3_bucket_versioning" "ical" {
  bucket = aws_s3_bucket.ical.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "ical" {
  bucket = aws_s3_bucket.ical.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "ical" {
  bucket                  = aws_s3_bucket.ical.id
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

# Allow CloudFront to read from the bucket via OAC
resource "aws_s3_bucket_policy" "ical" {
  bucket = aws_s3_bucket.ical.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "AllowCloudFrontOAC"
      Effect = "Allow"
      Principal = {
        Service = "cloudfront.amazonaws.com"
      }
      Action   = "s3:GetObject"
      Resource = "${aws_s3_bucket.ical.arn}/*"
      Condition = {
        StringEquals = {
          "AWS:SourceArn" = aws_cloudfront_distribution.ical.arn
        }
      }
    }]
  })
}

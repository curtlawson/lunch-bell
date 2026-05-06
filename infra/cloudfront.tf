resource "aws_cloudfront_origin_access_control" "ical" {
  name                              = var.project
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "ical" {
  enabled             = true
  comment             = "${var.project} iCal feeds"
  default_root_object = ""

  origin {
    domain_name              = aws_s3_bucket.ical.bucket_regional_domain_name
    origin_id                = "s3-ical"
    origin_access_control_id = aws_cloudfront_origin_access_control.ical.id
  }

  default_cache_behavior {
    target_origin_id       = "s3-ical"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id = data.aws_cloudfront_cache_policy.caching_optimized.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

data "aws_cloudfront_cache_policy" "caching_optimized" {
  name = "Managed-CachingOptimized"
}

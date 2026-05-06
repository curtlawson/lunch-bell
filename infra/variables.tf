variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
  default     = "973226391740"
}

variable "project" {
  description = "Project name used as a prefix for resource names"
  type        = string
  default     = "lunch-bell"
}

variable "domain" {
  description = "Domain used in iCal UIDs and the CloudFront alias"
  type        = string
  default     = "curtlawson.dev"
}

variable "menu_page_url" {
  description = "District menu page URL to scrape for PDF links"
  type        = string
  default     = "https://www.madisoncity.k12.al.us/Page/3656"
}

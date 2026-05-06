terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket       = "lunch-bell-tfstate-973226391740"
    key          = "lunch-bell/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
    encrypt      = true
    profile      = "personal"
  }
}

provider "aws" {
  region  = var.aws_region
  profile = "personal"
}

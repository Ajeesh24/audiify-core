terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "audifyy-terraform-state"
    key    = "audifyy/terraform.tfstate"
    region = "ap-southeast-1"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Audifyy"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Repository  = "github.com/Ajeesh24/audiify-core"
    }
  }
}

# Data sources for existing resources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Random suffix for unique resource names
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

locals {
  project_name = "audifyy"
  common_tags = {
    Project     = "Audifyy"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  # Generate unique names
  s3_bucket_name       = "${local.project_name}-frontend-${var.environment}-${random_string.suffix.result}"
  lambda_function_name = "${local.project_name}-backend-${var.environment}"
}
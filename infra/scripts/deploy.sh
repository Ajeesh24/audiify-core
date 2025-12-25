#!/bin/bash

# Audifyy Deployment Script
# This script sets up the initial infrastructure and prepares for GitHub Actions deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
ENVIRONMENT=${1:-dev}
AWS_REGION=${AWS_REGION:-ap-southeast-1}
PROJECT_NAME="audifyy"

print_status "Starting Audifyy deployment setup for environment: $ENVIRONMENT"

# Check prerequisites
print_status "Checking prerequisites..."

# Check if AWS CLI is installed and configured
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    print_error "Terraform is not installed. Please install it first."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install it first."
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

print_success "Prerequisites check passed"

# Get AWS Account ID and Region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)
print_status "AWS Account ID: $AWS_ACCOUNT_ID"
print_status "AWS Region: $AWS_REGION"

# Create S3 bucket for Terraform state (if it doesn't exist)
TERRAFORM_BUCKET="${PROJECT_NAME}-terraform-state-${AWS_ACCOUNT_ID}-${AWS_REGION}"
print_status "Creating Terraform state bucket: $TERRAFORM_BUCKET"

if ! aws s3api head-bucket --bucket "$TERRAFORM_BUCKET" 2>/dev/null; then
    aws s3api create-bucket \
        --bucket "$TERRAFORM_BUCKET" \
        --region "$AWS_REGION" \
        --create-bucket-configuration LocationConstraint="$AWS_REGION"

    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket "$TERRAFORM_BUCKET" \
        --versioning-configuration Status=Enabled

    # Enable server-side encryption
    aws s3api put-bucket-encryption \
        --bucket "$TERRAFORM_BUCKET" \
        --server-side-encryption-configuration '{
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }
            ]
        }'

    print_success "Terraform state bucket created: $TERRAFORM_BUCKET"
else
    print_status "Terraform state bucket already exists: $TERRAFORM_BUCKET"
fi

# Create ECR repository for Lambda backend images
ECR_REPOSITORY="${PROJECT_NAME}-lambda-backend"
print_status "Creating ECR repository: $ECR_REPOSITORY"

if ! aws ecr describe-repositories --repository-names "$ECR_REPOSITORY" --region "$AWS_REGION" 2>/dev/null; then
    aws ecr create-repository \
        --repository-name "$ECR_REPOSITORY" \
        --region "$AWS_REGION" \
        --image-scanning-configuration scanOnPush=true

    # Set lifecycle policy to keep only last 10 images
    aws ecr put-lifecycle-policy \
        --repository-name "$ECR_REPOSITORY" \
        --region "$AWS_REGION" \
        --lifecycle-policy-text '{
            "rules": [
                {
                    "rulePriority": 1,
                    "description": "Keep last 10 images",
                    "selection": {
                        "tagStatus": "any",
                        "countType": "imageCountMoreThan",
                        "countNumber": 10
                    },
                    "action": {
                        "type": "expire"
                    }
                }
            ]
        }'

    print_success "ECR repository created: $ECR_REPOSITORY"
else
    print_status "ECR repository already exists: $ECR_REPOSITORY"
fi

# Initialize Terraform
print_status "Initializing Terraform..."
cd infra/terraform

# Update backend configuration
cat > backend.tf << EOF
terraform {
  backend "s3" {
    bucket = "$TERRAFORM_BUCKET"
    key    = "$PROJECT_NAME/terraform.tfstate"
    region = "$AWS_REGION"
  }
}
EOF

terraform init

# Prompt for OpenAI API Key if not set
if [ -z "$OPENAI_API_KEY" ]; then
    print_warning "OpenAI API Key not set in environment variable OPENAI_API_KEY"
    read -s -p "Please enter your OpenAI API Key: " OPENAI_API_KEY
    echo
fi

# Create terraform.tfvars file for local deployment
cat > terraform.tfvars << EOF
aws_region     = "$AWS_REGION"
environment    = "$ENVIRONMENT"
openai_api_key = "$OPENAI_API_KEY"
cors_origins   = ["*"]
EOF

print_success "Terraform configuration completed"

# Plan and apply infrastructure
print_status "Planning Terraform deployment..."
terraform plan -var-file="environments/${ENVIRONMENT}.tfvars" -var="openai_api_key=$OPENAI_API_KEY"

echo
print_warning "Review the Terraform plan above. Do you want to proceed with deployment? (y/N)"
read -r CONFIRM

if [[ $CONFIRM =~ ^[Yy]$ ]]; then
    print_status "Applying Terraform configuration..."
    terraform apply -var-file="environments/${ENVIRONMENT}.tfvars" -var="openai_api_key=$OPENAI_API_KEY" -auto-approve

    # Get outputs
    BACKEND_API_URL=$(terraform output -raw api_gateway_url)
    FRONTEND_BUCKET=$(terraform output -raw frontend_bucket_name)
    CLOUDFRONT_DISTRIBUTION_ID=$(terraform output -raw cloudfront_distribution_id)
    CLOUDFRONT_DOMAIN=$(terraform output -raw cloudfront_domain_name)
    LAMBDA_FUNCTION_ARN=$(terraform output -raw lambda_function_arn)
    ECR_REPOSITORY_URL=$(terraform output -raw ecr_repository_url)

    print_success "Infrastructure deployed successfully!"
    echo
    print_status "=== Deployment Information ==="
    echo "Backend API URL: $BACKEND_API_URL"
    echo "Frontend Bucket: $FRONTEND_BUCKET"
    echo "CloudFront Domain: $CLOUDFRONT_DOMAIN"
    echo "Frontend URL: https://$CLOUDFRONT_DOMAIN"
    echo "Lambda Function ARN: $LAMBDA_FUNCTION_ARN"
    echo
    print_status "=== GitHub Configuration Required ==="
    echo "Add these variables and secrets to your GitHub repository:"
    echo ""
    echo "Variables (Settings > Secrets and variables > Actions > Variables tab):"
    echo "AWS_GITHUB_TRUST_ROLE: <your-gha-trust-role-arn>"
    echo "AWS_DEPLOYMENT_ROLE: <your-gha-cicd-role-arn>"
    echo ""
    echo "Secrets (Settings > Secrets and variables > Actions > Secrets tab):"
    echo "OPENAI_API_KEY: $OPENAI_API_KEY"
    echo
    print_success "Setup completed! You can now use GitHub Actions for Lambda deployments."
else
    print_status "Deployment cancelled."
fi

cd ../..

print_success "Deployment script completed!"
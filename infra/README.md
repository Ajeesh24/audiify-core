# Audifyy AWS Deployment Guide

This guide covers deploying Audifyy to AWS using Lambda + API Gateway with Terraform and GitHub Actions.

## Architecture Overview

- **Frontend**: React PWA hosted on S3 + CloudFront
- **Backend**: FastAPI containerized Lambda function behind API Gateway
- **Storage**: S3 buckets for static assets and audio files
- **CI/CD**: GitHub Actions with AWS OIDC authentication

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured with credentials
3. **Terraform** >= 1.0
4. **Docker** for container builds
5. **Node.js** >= 18 for frontend
6. **Python** >= 3.11 for backend
7. **GitHub repository** with appropriate access

## AWS IAM Roles Setup

You need to create two IAM roles for GitHub Actions:

### 1. GHA-Trust Role (Trust Role)

This role establishes trust between GitHub and AWS using OIDC.

```bash
# Create the trust policy
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::{ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:Ajeesh24/audiify-core:*"
        }
      }
    }
  ]
}
EOF

# Create the role
aws iam create-role \
  --role-name GHA-Trust \
  --assume-role-policy-document file://trust-policy.json
```

### 2. GHA-CICD Role (Execution Role)

This role has permissions to deploy and manage AWS resources.

```bash
# Create the policy for CICD operations
cat > cicd-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:*",
        "cloudfront:*",
        "lambda:*",
        "apigateway:*",
        "ecr:*",
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath",
        "iam:PassRole",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Create the CICD role that can be assumed by the Trust role
cat > cicd-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::{ACCOUNT_ID}:role/GHA-Trust"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the policy
aws iam create-policy \
  --policy-name GHA-CICD-Policy \
  --policy-document file://cicd-policy.json

# Create the role
aws iam create-role \
  --role-name GHA-CICD \
  --assume-role-policy-document file://cicd-trust-policy.json

# Attach the policy
aws iam attach-role-policy \
  --role-name GHA-CICD \
  --policy-arn arn:aws:iam::{ACCOUNT_ID}:policy/GHA-CICD-Policy
```

## GitHub Configuration Setup

Add these variables and secrets to your GitHub repository (Settings > Secrets and variables > Actions):

### Required Variables

Add these in the **Variables** tab:

| Variable Name | Description | Example Value |
|---------------|-------------|---------------|
| `AWS_GITHUB_TRUST_ROLE` | ARN of the GHA-Trust role | `arn:aws:iam::123456789012:role/GHA-Trust` |
| `AWS_DEPLOYMENT_ROLE` | ARN of the GHA-CICD role | `arn:aws:iam::123456789012:role/GHA-CICD` |

### Required Secrets

Add these in the **Secrets** tab:

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `OPENAI_API_KEY` | Your OpenAI API key | `sk-...` |

### Optional Secrets

| Secret Name | Description | Default |
|-------------|-------------|---------|
| `DOMAIN_NAME` | Custom domain for the frontend | CloudFront domain |
| `API_DOMAIN_NAME` | Custom domain for the API | API Gateway domain |
| `CERTIFICATE_ARN` | ACM certificate ARN | None |

## Local Development Setup

1. **Clone the repository:**
```bash
git clone https://Ajeesh24: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@github.com/Ajeesh24/audiify-core.git
cd audiify-core/audifyy-mvp
```

2. **Set up environment variables:**
```bash
export OPENAI_API_KEY="sk-your-openai-key"
export AWS_REGION="ap-southeast-1"
```

3. **Install dependencies:**
```bash
# Backend
cd backend
pip install -r requirements.txt
cd ..

# Frontend
cd frontend
npm install
cd ..
```

4. **Run locally:**
```bash
# Start both services
./start-dev.sh
```

## Initial AWS Deployment

1. **Run the deployment script:**
```bash
chmod +x infra/scripts/deploy.sh
./infra/scripts/deploy.sh dev
```

This script will:
- Create S3 bucket for Terraform state
- Create ECR repository for Lambda container images
- Deploy infrastructure using Terraform
- Provide you with the required GitHub secrets

2. **Add secrets to GitHub:**

   Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

3. **Push code to trigger deployment:**
```bash
git add .
git commit -m "Initial Lambda deployment setup"
git push origin main
```

## Manual Deployment Steps

If you prefer manual deployment:

### 1. Infrastructure Deployment

```bash
cd infra/terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var-file="environments/dev.tfvars" -var="openai_api_key=$OPENAI_API_KEY"

# Apply
terraform apply -var-file="environments/dev.tfvars" -var="openai_api_key=$OPENAI_API_KEY"
```

### 2. Lambda Backend Deployment

```bash
# Get ECR login
aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin {ACCOUNT_ID}.dkr.ecr.ap-southeast-1.amazonaws.com

# Build and push Lambda container image
docker build -t audifyy-lambda-backend .
docker tag audifyy-lambda-backend:latest {ACCOUNT_ID}.dkr.ecr.ap-southeast-1.amazonaws.com/audifyy-lambda-backend:latest
docker push {ACCOUNT_ID}.dkr.ecr.ap-southeast-1.amazonaws.com/audifyy-lambda-backend:latest

# Update Lambda function
aws lambda update-function-code \
  --function-name audifyy-backend-dev \
  --image-uri {ACCOUNT_ID}.dkr.ecr.ap-southeast-1.amazonaws.com/audifyy-lambda-backend:latest
```

### 3. Frontend Deployment

```bash
cd frontend

# Build frontend
npm run build

# Deploy to S3
aws s3 sync dist/ s3://{FRONTEND_BUCKET_NAME} --delete

# Invalidate CloudFront
aws cloudfront create-invalidation --distribution-id {DISTRIBUTION_ID} --paths "/*"
```

## Environment Configuration

### Development Environment (Lambda Optimized)
- **Cost Optimized**: Pay-per-use Lambda execution
- **Memory**: 2GB for AI processing
- **Timeout**: 15 minutes for long article processing
- **CORS**: Allow all origins for development
- **Logging**: API Gateway and Lambda logs enabled

## Monitoring and Maintenance

### Health Checks
- Backend: `{API_GATEWAY_URL}/api/health`
- Frontend: Direct CloudFront access

### Logs Access
```bash
# Lambda logs
aws logs tail /aws/lambda/audifyy-backend-dev --follow

# API Gateway logs
aws logs tail /aws/apigateway/audifyy-dev --follow

# CloudFront logs (if enabled)
aws s3 ls s3://{LOGS_BUCKET}/cloudfront-logs/
```

### Performance Monitoring
```bash
# Lambda metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=audifyy-backend-dev \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Average,Maximum

# API Gateway metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name 4XXError \
  --dimensions Name=ApiName,Value=audifyy-api-dev \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

## Troubleshooting

### Common Issues

1. **CORS Errors**: Check that frontend domain is in CORS origins
2. **Lambda Timeout**: 15-minute max (sufficient for article processing)
3. **Cold Starts**: 2-8 seconds (acceptable for AI processing workload)
4. **502 Bad Gateway**: Check Lambda function logs for errors
5. **Docker Build Fails**: Verify Lambda base image and dependencies

### Debug Commands

```bash
# Check Lambda function status
aws lambda get-function --function-name audifyy-backend-dev

# Test Lambda function directly
aws lambda invoke --function-name audifyy-backend-dev \
  --payload '{"httpMethod":"GET","path":"/api/health"}' \
  response.json

# Check API Gateway status
aws apigateway get-rest-api --rest-api-id {API_ID}

# Test API Gateway health
curl https://{API_GATEWAY_ID}.execute-api.ap-southeast-1.amazonaws.com/dev/api/health
```

## Security Best Practices

1. **Use OIDC**: No long-lived AWS credentials in GitHub
2. **Least Privilege**: IAM roles have minimal required permissions
3. **Secrets Management**: API keys stored in AWS Systems Manager
4. **HTTPS Only**: All traffic encrypted in transit
5. **Private ECR**: Container images in private registry
6. **X-Ray Tracing**: Enabled for API Gateway (optional)

## Cost Estimation

**Monthly costs (ap-southeast-1 region) - Lambda Architecture:**
- Lambda: ~$2-8 (depending on usage)
- API Gateway: ~$1-3 (per million requests)
- S3 + CloudFront: ~$5-15 (depending on traffic)
- ECR: ~$1-5 (depending on images stored)
- **Total: ~$10-30/month** (60-80% savings vs App Runner)

### Cost Breakdown Examples:
```bash
Low Traffic (100 requests/month):
- Lambda executions: ~$1-2
- API Gateway: ~$0.10
- Storage: ~$1-3
Total: ~$3-6/month

Medium Traffic (1000 requests/month):
- Lambda executions: ~$3-8
- API Gateway: ~$0.50
- Storage: ~$3-8
Total: ~$7-17/month

High Traffic (10,000 requests/month):
- Lambda executions: ~$8-25
- API Gateway: ~$3-5
- Storage: ~$10-20
Total: ~$20-50/month
```

## Lambda-Specific Features

### **Automatic Scaling**
- 0 to 1000+ concurrent executions
- No provisioning required
- Scales based on incoming requests

### **Cost Optimization**
- No idle costs (scales to zero)
- Pay only for execution time
- Automatic resource allocation

### **Built-in Features**
- 15-minute maximum execution time
- Up to 10GB temporary storage (/tmp)
- Integrated with CloudWatch
- X-Ray tracing support

## Support

For issues with this Lambda deployment:
1. Check the [GitHub Issues](https://github.com/Ajeesh24/audiify-core/issues)
2. Review AWS CloudWatch Lambda logs
3. Monitor API Gateway metrics
4. Validate all environment variables and secrets
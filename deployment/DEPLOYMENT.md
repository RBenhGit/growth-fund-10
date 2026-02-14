# Production Deployment Guide

This guide walks through deploying the Growth Fund Builder to AWS using Docker, ECS Fargate, and EventBridge for quarterly scheduled execution.

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Local Testing](#local-testing)
- [AWS Infrastructure Setup](#aws-infrastructure-setup)
- [Deployment Process](#deployment-process)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)

## 🏗️ Architecture Overview

### AWS Services Used

- **Amazon ECR**: Docker image registry
- **Amazon ECS Fargate**: Serverless container execution
- **Amazon EventBridge**: Quarterly scheduled triggers
- **Amazon S3**: Fund document storage
- **AWS Secrets Manager**: API key storage
- **Amazon CloudWatch**: Logging and monitoring
- **Amazon VPC**: Network isolation

### Execution Flow

```
EventBridge (Quarterly Schedule)
  → ECS Fargate Task (2 vCPU, 4GB RAM)
    → Docker Container
      → Python Application
        → TwelveData API (Financial Data)
        → yfinance (Pricing Data)
          → Fund Documents
            → S3 Bucket
```

### Quarterly Schedule

- **Q1**: January 1st at 6:00 AM UTC
- **Q2**: April 1st at 6:00 AM UTC
- **Q3**: July 1st at 6:00 AM UTC
- **Q4**: October 1st at 6:00 AM UTC

Both SP500 and TASE125 funds are built on the same schedule.

## ✅ Prerequisites

### Required Tools

1. **AWS Account** with appropriate permissions
2. **AWS CLI** (v2.x or later)
   ```bash
   aws --version
   ```
3. **Terraform** (v1.0 or later)
   ```bash
   terraform version
   ```
4. **Docker** (for local testing)
   ```bash
   docker --version
   ```
5. **Git** (for version control)

### Required Credentials

1. **TwelveData API Key**
   - Sign up at https://twelvedata.com/
   - Recommended: Pro 1597 plan ($XX/month)

2. **AWS Credentials**
   - Access Key ID
   - Secret Access Key
   - Region: `us-east-1` (default)

3. **GitHub Secrets** (for CI/CD)
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `TWELVEDATA_API_KEY`
   - `ALPHAVANTAGE_API_KEY` (optional)

## 🧪 Local Testing

Before deploying to AWS, test the Docker container locally.

### 1. Create `.env` File

```bash
# Copy template
cp .env.template .env

# Edit with your API keys
nano .env
```

Example `.env`:
```bash
TWELVEDATA_API_KEY=your-key-here
US_FINANCIAL_DATA_SOURCE=twelvedata
US_PRICING_DATA_SOURCE=yfinance
TASE_FINANCIAL_DATA_SOURCE=twelvedata
TASE_PRICING_DATA_SOURCE=yfinance
USE_CACHE=true
DEBUG_MODE=false
```

### 2. Build Docker Image

```bash
docker build -f deployment/Dockerfile -t growth-fund-builder:latest .
```

### 3. Test Run - SP500

```bash
docker run --rm \
  --env-file .env \
  -v $(pwd)/Fund_Docs:/app/Fund_Docs \
  growth-fund-builder:latest \
  --index SP500 --debug
```

### 4. Test Run - TASE125

```bash
docker run --rm \
  --env-file .env \
  -v $(pwd)/Fund_Docs:/app/Fund_Docs \
  growth-fund-builder:latest \
  --index TASE125 --debug
```

### 5. Test with Docker Compose

```bash
# Test SP500
docker-compose -f deployment/docker-compose.yml up growth-fund-builder

# Test TASE125
docker-compose -f deployment/docker-compose.yml up growth-fund-builder-tase

# Test data sources
docker-compose -f deployment/docker-compose.yml up test-sources
```

### Expected Output

✅ Fund documents generated in `Fund_Docs/`:
- `Fund_10_SP500_Q1_2026.md`
- `Fund_10_SP500_Q1_2026_Update.md`
- `Fund_10_TASE125_Q1_2026.md`
- `Fund_10_TASE125_Q1_2026_Update.md`

## 🚀 AWS Infrastructure Setup

### Step 1: Configure AWS CLI

```bash
aws configure
# Enter:
#   AWS Access Key ID
#   AWS Secret Access Key
#   Default region: us-east-1
#   Default output format: json
```

Verify:
```bash
aws sts get-caller-identity
```

### Step 2: Create S3 Backend for Terraform State

```bash
# Create S3 bucket for Terraform state
aws s3 mb s3://growth-fund-terraform-state --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket growth-fund-terraform-state \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name growth-fund-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### Step 3: Initialize Terraform

```bash
cd deployment/terraform

# Copy and edit variables
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars

# Initialize Terraform
terraform init
```

### Step 4: Review Terraform Plan

```bash
terraform plan
```

Expected resources to be created:
- 1 VPC with public/private subnets
- 1 ECR repository
- 1 ECS cluster
- 2 ECS task definitions (SP500, TASE125)
- 4 EventBridge rules (Q1-Q4)
- 8 EventBridge targets (4 per index)
- 1 S3 bucket (fund documents)
- 1 Secrets Manager secret (API keys)
- IAM roles and security groups
- CloudWatch log group

**Estimated cost**: ~$5-15/month (plus ECS Fargate execution costs)

### Step 5: Deploy Infrastructure

```bash
terraform apply
```

Type `yes` to confirm.

**Deployment time**: ~5-10 minutes

### Step 6: Note Terraform Outputs

```bash
terraform output
```

Save these values:
- `ecr_repository_url`: For Docker image push
- `s3_bucket_name`: For fund document storage
- `cloudwatch_log_group`: For monitoring

## 📦 Deployment Process

### Option 1: Automated Deployment (GitHub Actions)

**Recommended for production**

#### Setup GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Add the following secrets:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `TWELVEDATA_API_KEY`
   - `ALPHAVANTAGE_API_KEY` (optional)

#### Deploy

Push to `master` branch:
```bash
git push origin master
```

GitHub Actions will automatically:
1. Run tests
2. Build Docker image
3. Push to ECR
4. Update ECS task definitions

### Option 2: Manual Deployment

#### Step 1: Build and Tag Image

```bash
# Get ECR repository URL from Terraform output
ECR_URL=$(terraform output -raw ecr_repository_url)

# Build image
docker build -f deployment/Dockerfile -t growth-fund-builder:latest .

# Tag for ECR
docker tag growth-fund-builder:latest $ECR_URL:latest
docker tag growth-fund-builder:latest $ECR_URL:v1.0
```

#### Step 2: Push to ECR

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ECR_URL

# Push image
docker push $ECR_URL:latest
docker push $ECR_URL:v1.0
```

#### Step 3: Update ECS Task Definitions

```bash
# Update SP500 task
aws ecs update-service \
  --cluster growth-fund-builder-cluster \
  --task-definition growth-fund-builder-sp500 \
  --force-new-deployment

# Update TASE125 task
aws ecs update-service \
  --cluster growth-fund-builder-cluster \
  --task-definition growth-fund-builder-tase125 \
  --force-new-deployment
```

### Option 3: Manual Trigger (On-Demand)

Trigger fund build manually via GitHub Actions:

1. Go to **Actions** → **Manual Fund Build**
2. Click **Run workflow**
3. Select parameters:
   - Index: `SP500`, `TASE125`, or `BOTH`
   - Quarter: Leave empty for auto-detect
   - Year: Leave empty for current year
   - Cache: Enable (recommended)
   - Debug: Enable for troubleshooting

Or use AWS CLI:
```bash
# Run SP500 task
aws ecs run-task \
  --cluster growth-fund-builder-cluster \
  --task-definition growth-fund-builder-sp500 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=DISABLED}"

# Run TASE125 task
aws ecs run-task \
  --cluster growth-fund-builder-cluster \
  --task-definition growth-fund-builder-tase125 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=DISABLED}"
```

## 📊 Monitoring and Maintenance

### CloudWatch Logs

View execution logs:
```bash
aws logs tail /ecs/growth-fund-builder --follow
```

Or in AWS Console:
1. Navigate to **CloudWatch** → **Log groups**
2. Select `/ecs/growth-fund-builder`
3. View log streams for each execution

### S3 Fund Documents

Download fund documents:
```bash
# List documents
aws s3 ls s3://growth-fund-builder-fund-docs-prod/

# Download specific fund
aws s3 cp s3://growth-fund-builder-fund-docs-prod/Fund_10_SP500_Q1_2026.md .
```

### EventBridge Schedules

Check scheduled rules:
```bash
aws events list-rules --name-prefix growth-fund-builder
```

View next scheduled run:
```bash
aws events describe-rule --name growth-fund-builder-quarterly-q1
```

### ECS Task Metrics

View ECS metrics in CloudWatch:
- CPU utilization
- Memory utilization
- Task count
- Network traffic

### Cost Monitoring

Track costs in AWS Cost Explorer:
- ECS Fargate compute
- S3 storage
- Data transfer
- CloudWatch logs
- Secrets Manager

**Expected monthly cost**: $5-15 + ECS execution time

## 🔧 Troubleshooting

### Issue: Task Failed to Start

**Check CloudWatch logs:**
```bash
aws logs tail /ecs/growth-fund-builder --follow
```

**Common causes:**
- Invalid API keys in Secrets Manager
- Insufficient task resources (CPU/memory)
- Network configuration issues

**Solution:**
```bash
# Verify secrets
aws secretsmanager get-secret-value --secret-id growth-fund-builder-api-keys-prod

# Check task definition
aws ecs describe-task-definition --task-definition growth-fund-builder-sp500
```

### Issue: API Rate Limit Exceeded

**Symptoms:**
- `DataSourceRateLimitError` in logs
- Incomplete fund builds

**Solution:**
- Check TwelveData plan limits
- Ensure yfinance is used for pricing (free, unlimited)
- Increase task memory if rate limiter is too aggressive

### Issue: Fund Documents Not in S3

**Check:**
1. Container logs for upload errors
2. IAM role permissions
3. S3 bucket configuration

**Solution:**
```bash
# Verify IAM role has S3 permissions
aws iam get-role-policy --role-name growth-fund-builder-ecs-task-role --policy-name growth-fund-builder-ecs-task-policy

# Test S3 upload manually
aws s3 cp test.txt s3://growth-fund-builder-fund-docs-prod/
```

### Issue: Scheduled Execution Not Running

**Check EventBridge rules:**
```bash
# Verify rule is enabled
aws events describe-rule --name growth-fund-builder-quarterly-q1

# Check rule targets
aws events list-targets-by-rule --rule growth-fund-builder-quarterly-q1
```

**Solution:**
```bash
# Enable rule if disabled
aws events enable-rule --name growth-fund-builder-quarterly-q1
```

### Issue: High AWS Costs

**Reduce costs:**
1. **Decrease task resources**: Reduce CPU/memory in `terraform.tfvars`
   ```hcl
   task_cpu    = "1024"  # 1 vCPU instead of 2
   task_memory = "2048"  # 2GB instead of 4GB
   ```

2. **Use yfinance for all pricing**: Update task environment variables
   ```hcl
   US_PRICING_DATA_SOURCE=yfinance
   TASE_PRICING_DATA_SOURCE=yfinance
   ```

3. **Reduce log retention**: Update CloudWatch log retention to 7 days

4. **Enable S3 lifecycle policies**: Archive old fund documents to Glacier

## 🔄 Updating the Application

### Update Code

1. Make changes to the codebase
2. Commit and push to `master` branch
3. GitHub Actions automatically deploys

Or manually:
```bash
# Rebuild image
docker build -f deployment/Dockerfile -t growth-fund-builder:latest .

# Push to ECR (see Deployment Process)
# ...

# Force new deployment
aws ecs update-service --cluster growth-fund-builder-cluster \
  --task-definition growth-fund-builder-sp500 --force-new-deployment
```

### Update Infrastructure

```bash
cd deployment/terraform

# Edit terraform files or variables
nano terraform.tfvars

# Plan changes
terraform plan

# Apply changes
terraform apply
```

## 🗑️ Teardown

To completely remove all AWS resources:

```bash
cd deployment/terraform

# Destroy all resources
terraform destroy

# Clean up S3 backend (optional)
aws s3 rb s3://growth-fund-terraform-state --force
aws dynamodb delete-table --table-name growth-fund-terraform-locks
```

**Warning**: This will delete all fund documents, logs, and configuration. Make backups first!

## 📚 Additional Resources

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [AWS EventBridge Documentation](https://docs.aws.amazon.com/eventbridge/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Docker Documentation](https://docs.docker.com/)
- [TwelveData API Documentation](https://twelvedata.com/docs)

## 🆘 Support

For issues or questions:
1. Check [CLAUDE.md](../CLAUDE.md) for technical details
2. Review CloudWatch logs
3. Enable debug mode for verbose output
4. Check GitHub Actions workflow logs

---

**Last Updated**: February 2026
**Version**: 1.0
**Production Ready**: ✅

# lunch-bell

Serverless pipeline that scrapes Madison City Schools monthly lunch menu PDFs and publishes iCalendar (`.ics`) subscription feeds — one per school level — so families can subscribe in Apple Calendar, Google Calendar, or any other calendar app.

## Subscription URLs

| School level | URL |
|---|---|
| Elementary | `https://d3n41t2og5paqm.cloudfront.net/elementary.ics` |
| Middle | `https://d3n41t2og5paqm.cloudfront.net/middle.ics` |
| High School | `https://d3n41t2og5paqm.cloudfront.net/high.ics` |

Each lunch day appears as an all-day event. The main dish is the event title; the full menu is in the notes/description.

### Subscribing in Apple Calendar

1. File → New Calendar Subscription…
2. Paste one of the URLs above
3. Set Auto-refresh to **Every day**

### Subscribing in Google Calendar

1. Other calendars → **+** → From URL
2. Paste one of the URLs above

## How it works

```
District website (madisoncity.k12.al.us)
    │
    ▼
discover.py — scrapes the menu page for PDF links (one per school level)
    │
    ▼
parse.py — extracts lunch items from the PDF using positional word layout
    │
    ▼
generate.py — builds RFC 5545 iCalendar files with stable UIDs
    │
    ▼
S3 → CloudFront → calendar app
```

A Lambda function runs the full pipeline daily at 8 AM Central. It compares the current PDF filename against the last-processed value in SSM Parameter Store and skips processing if nothing has changed — so most runs are a cheap no-op.

## Project structure

```
lunch-bell/
├── discover.py          # Scrapes the district menu page for PDF URLs
├── parse.py             # Extracts menu items from PDF using pdfplumber
├── generate.py          # Builds iCalendar files from parsed menu data
├── handler.py           # Lambda entry point
├── Dockerfile           # Lambda container image (python:3.12)
├── requirements.txt
├── scripts/
│   └── empty-before-destroy.sh   # Empties S3 + ECR before terraform destroy
└── infra/               # Terraform — all AWS infrastructure
    ├── versions.tf      # Provider + S3 backend config
    ├── variables.tf
    ├── ecr.tf           # ECR repository for the Lambda image
    ├── s3.tf            # S3 bucket for .ics files
    ├── cloudfront.tf    # CloudFront distribution with OAC
    ├── ssm.tf           # SSM parameters tracking last-processed PDF filenames
    ├── iam.tf           # Lambda execution role
    ├── lambda.tf        # Lambda function + CloudWatch log group
    ├── eventbridge.tf   # Daily EventBridge Scheduler trigger
    ├── github-actions.tf # OIDC provider + IAM role for GitHub Actions
    └── outputs.tf
```

## Infrastructure

All infrastructure is managed with Terraform and deployed to AWS us-east-1.

| Resource | Name |
|---|---|
| Lambda function | `lunch-bell` |
| ECR repository | `lunch-bell` |
| S3 bucket | `lunch-bell-ical-{account_id}` |
| CloudFront distribution | `d3n41t2og5paqm.cloudfront.net` |
| EventBridge schedule | `lunch-bell-daily` (8 AM Central) |
| SSM prefix | `/lunch-bell/last-pdf/` |

## CI/CD

GitHub Actions handles deployments automatically:

- **Pull request → main**: runs `terraform plan` and posts the output as a PR comment
- **Merge to main**: builds and pushes the Docker image to ECR, then runs `terraform apply`

Authentication uses OIDC — no long-lived AWS credentials are stored in GitHub.

## Local development

**Prerequisites**: Python 3.12, Docker, Terraform, AWS CLI with `personal` profile configured.

### Run the pipeline locally

```bash
pip install -r requirements.txt
python generate.py ./output   # writes elementary.ics, middle.ics, high.ics to ./output/
```

### Build and push the Docker image

```bash
docker buildx build --platform linux/amd64 --provenance=false \
  -t 973226391740.dkr.ecr.us-east-1.amazonaws.com/lunch-bell:latest --push .
```

### Deploy infrastructure

```bash
export AWS_PROFILE=personal
cd infra
terraform init
terraform plan -out=tfplan
terraform apply "tfplan"
```

### Tear down

```bash
export AWS_PROFILE=personal
./scripts/empty-before-destroy.sh   # empties S3 bucket and ECR first
cd infra && terraform destroy
```

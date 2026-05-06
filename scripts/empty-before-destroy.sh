#!/usr/bin/env bash
# Run this before `terraform destroy` to empty the S3 bucket and ECR repo,
# which Terraform refuses to delete if they contain objects/images.
set -euo pipefail

PROFILE="personal"
REGION="us-east-1"
BUCKET="lunch-bell-ical-973226391740"
ECR_REPO="lunch-bell"

echo "==> Emptying S3 bucket: $BUCKET"
# Delete all object versions and delete markers (handles versioned buckets)
aws s3api list-object-versions \
    --bucket "$BUCKET" \
    --profile "$PROFILE" \
    --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' \
    --output json | \
  jq 'select(.Objects != null)' | \
  xargs -I{} aws s3api delete-objects \
    --bucket "$BUCKET" \
    --profile "$PROFILE" \
    --delete '{}' 2>/dev/null || true

aws s3api list-object-versions \
    --bucket "$BUCKET" \
    --profile "$PROFILE" \
    --query '{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}' \
    --output json | \
  jq 'select(.Objects != null)' | \
  xargs -I{} aws s3api delete-objects \
    --bucket "$BUCKET" \
    --profile "$PROFILE" \
    --delete '{}' 2>/dev/null || true

echo "    Done."

echo "==> Deleting all images in ECR repo: $ECR_REPO"
IMAGE_IDS=$(aws ecr list-images \
    --repository-name "$ECR_REPO" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'imageIds[*]' \
    --output json)

if [ "$IMAGE_IDS" = "[]" ]; then
  echo "    No images found."
else
  aws ecr batch-delete-image \
      --repository-name "$ECR_REPO" \
      --region "$REGION" \
      --profile "$PROFILE" \
      --image-ids "$IMAGE_IDS"
  echo "    Done."
fi

echo ""
echo "Ready to run: cd infra && terraform destroy"

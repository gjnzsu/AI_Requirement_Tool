#!/usr/bin/env bash
# deploy.sh — build, push, and deploy to GKE
# Usage: PROJECT_ID=my-gcp-project ./deploy.sh

set -euo pipefail

if [[ -z "${PROJECT_ID:-}" ]]; then
  echo "ERROR: PROJECT_ID env var is required"
  echo "  Usage: PROJECT_ID=my-gcp-project ./deploy.sh"
  exit 1
fi

IMAGE="gcr.io/${PROJECT_ID}/ai-requirement-tool:latest"

echo "==> Building image: ${IMAGE}"
docker build -t "${IMAGE}" .

echo "==> Pushing image to GCR"
docker push "${IMAGE}"

echo "==> Patching deployment.yaml with PROJECT_ID"
sed "s|gcr.io/<PROJECT_ID>/|gcr.io/${PROJECT_ID}/|g" k8s/deployment.yaml | kubectl apply -f -

echo "==> Applying remaining manifests"
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/service.yaml

echo ""
echo "NOTE: Apply k8s/secret.yaml manually AFTER filling in real values:"
echo "  kubectl apply -f k8s/secret.yaml"
echo ""
echo "==> Waiting for rollout..."
kubectl rollout status deployment/ai-tool

echo ""
echo "==> External IP (may take a minute to provision):"
kubectl get service ai-tool-service

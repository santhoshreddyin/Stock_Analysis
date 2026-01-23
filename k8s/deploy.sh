#!/bin/bash
# Apply all Kubernetes resources in order

# Check if DOCKERHUB_USERNAME is set
if [ -z "$DOCKERHUB_USERNAME" ]; then
  echo "ERROR: DOCKERHUB_USERNAME environment variable is not set"
  echo "Please set it with: export DOCKERHUB_USERNAME=your-username"
  exit 1
fi

echo "Using DockerHub username: $DOCKERHUB_USERNAME"

# Apply static resources
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f postgres.yaml

# Substitute DOCKERHUB_USERNAME and apply backend/frontend
envsubst < backend.yaml | kubectl apply -f -
envsubst < frontend.yaml | kubectl apply -f -

kubectl apply -f ingress.yaml

# Wait for deployments to be ready
echo "Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/backend -n stock-analysis
kubectl wait --for=condition=available --timeout=300s deployment/frontend -n stock-analysis

# Check status
kubectl get all -n stock-analysis

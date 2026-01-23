# Apply all Kubernetes resources in order
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f postgres.yaml
kubectl apply -f backend.yaml
kubectl apply -f frontend.yaml
kubectl apply -f ingress.yaml

# Wait for deployments to be ready
echo "Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/backend -n stock-analysis
kubectl wait --for=condition=available --timeout=300s deployment/frontend -n stock-analysis

# Check status
kubectl get all -n stock-analysis

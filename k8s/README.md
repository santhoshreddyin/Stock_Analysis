# Kubernetes Deployment Guide

This directory contains Kubernetes manifests for deploying the Stock Analysis application.

## Files Overview

- `namespace.yaml` - Creates the stock-analysis namespace
- `configmap.yaml` - Configuration for backend and database
- `secrets.yaml` - Secrets for API keys and credentials (EDIT BEFORE DEPLOYING)
- `postgres.yaml` - PostgreSQL StatefulSet and Service
- `backend.yaml` - FastAPI backend Deployment and Service
- `frontend.yaml` - React frontend Deployment and Service
- `ingress.yaml` - Ingress rules for routing traffic
- `deploy.sh` - Script to deploy all resources

## Quick Start

### 1. Prerequisites

Ensure you have:
- A running Kubernetes cluster (minikube, k3s, or Docker Desktop)
- kubectl configured to access your cluster
- Nginx Ingress Controller installed

Install Nginx Ingress Controller:
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml
```

### 2. Configure Secrets

**IMPORTANT**: Edit `secrets.yaml` and replace placeholder values with your actual credentials:

```yaml
OPENAI_API_KEY: "your-actual-openai-api-key"
TAVILY_API_KEY: "your-actual-tavily-api-key"
GMAIL_SMTP_USER: "your-email@gmail.com"
GMAIL_APP_PASSWORD: "your-actual-app-password"
TWITTER_BEARER_TOKEN: "your-actual-twitter-token"
```

### 3. Build Docker Images

Build the images locally:
```bash
cd ..  # Go to project root
docker build -t stock-backend:latest -f Dockerfile.backend .
docker build -t stock-frontend:latest -f Dockerfile.frontend .
```

### 4. Deploy to Kubernetes

Run the deployment script:
```bash
chmod +x deploy.sh
./deploy.sh
```

Or manually apply each file:
```bash
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f postgres.yaml
kubectl apply -f backend.yaml
kubectl apply -f frontend.yaml
kubectl apply -f ingress.yaml
```

### 5. Verify Deployment

Check the status:
```bash
kubectl get all -n stock-analysis
```

Wait for all pods to be running:
```bash
kubectl wait --for=condition=ready pod --all -n stock-analysis --timeout=300s
```

### 6. Access the Application

#### Option A: Via Ingress (Recommended)

Add to `/etc/hosts`:
```bash
echo "127.0.0.1 stock-analysis.local" | sudo tee -a /etc/hosts
```

Access at: http://stock-analysis.local

#### Option B: Via Port Forwarding

```bash
# Frontend
kubectl port-forward -n stock-analysis service/frontend-service 8080:80

# Backend
kubectl port-forward -n stock-analysis service/backend-service 8000:8000
```

Access:
- Frontend: http://localhost:8080
- Backend API: http://localhost:8000

#### Option C: Via NodePort (for testing)

Edit services to use NodePort type:
```bash
kubectl patch service frontend-service -n stock-analysis -p '{"spec":{"type":"NodePort"}}'
kubectl patch service backend-service -n stock-analysis -p '{"spec":{"type":"NodePort"}}'

# Get the NodePort
kubectl get services -n stock-analysis
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │              Ingress (Nginx)                   │    │
│  │         stock-analysis.local                   │    │
│  └────────────────┬───────────────────────────────┘    │
│                   │                                      │
│         ┌─────────┴──────────┐                          │
│         │                    │                          │
│         ▼                    ▼                          │
│  ┌─────────────┐      ┌─────────────┐                 │
│  │  Frontend   │      │   Backend   │                 │
│  │   Service   │      │   Service   │                 │
│  │  (Port 80)  │      │ (Port 8000) │                 │
│  └──────┬──────┘      └──────┬──────┘                 │
│         │                    │                          │
│         ▼                    ▼                          │
│  ┌─────────────┐      ┌─────────────┐                 │
│  │  Frontend   │      │   Backend   │                 │
│  │ Deployment  │      │ Deployment  │                 │
│  │ (2 replicas)│      │ (2 replicas)│                 │
│  └─────────────┘      └──────┬──────┘                 │
│                              │                          │
│                              ▼                          │
│                       ┌─────────────┐                  │
│                       │  PostgreSQL │                  │
│                       │   Service   │                  │
│                       │ (Port 5432) │                  │
│                       └──────┬──────┘                  │
│                              │                          │
│                              ▼                          │
│                       ┌─────────────┐                  │
│                       │  PostgreSQL │                  │
│                       │ StatefulSet │                  │
│                       │ (1 replica) │                  │
│                       └──────┬──────┘                  │
│                              │                          │
│                              ▼                          │
│                       ┌─────────────┐                  │
│                       │ Persistent  │                  │
│                       │   Volume    │                  │
│                       │   (10Gi)    │                  │
│                       └─────────────┘                  │
└─────────────────────────────────────────────────────────┘
```

## Configuration

### Resource Requests and Limits

Current configuration:

**Backend:**
- Requests: 512Mi memory, 500m CPU
- Limits: 1Gi memory, 1000m CPU

**Frontend:**
- Requests: 128Mi memory, 100m CPU
- Limits: 256Mi memory, 200m CPU

**PostgreSQL:**
- Requests: 256Mi memory, 250m CPU
- Limits: 512Mi memory, 500m CPU

Adjust these based on your cluster capacity and application needs.

### Scaling

Scale deployments:
```bash
# Scale backend
kubectl scale deployment backend --replicas=3 -n stock-analysis

# Scale frontend
kubectl scale deployment frontend --replicas=3 -n stock-analysis
```

### Health Checks

All services have configured:
- **Liveness Probes**: Restart container if unhealthy
- **Readiness Probes**: Remove from load balancer if not ready

## Monitoring

### View Logs

```bash
# Backend logs
kubectl logs -f deployment/backend -n stock-analysis

# Frontend logs
kubectl logs -f deployment/frontend -n stock-analysis

# PostgreSQL logs
kubectl logs -f statefulset/postgres -n stock-analysis

# All pods
kubectl logs -f -l app=backend -n stock-analysis --all-containers=true
```

### Check Resource Usage

```bash
kubectl top pods -n stock-analysis
kubectl top nodes
```

### Describe Resources

```bash
kubectl describe deployment backend -n stock-analysis
kubectl describe service backend-service -n stock-analysis
kubectl describe ingress stock-analysis-ingress -n stock-analysis
```

## Database Management

### Connect to PostgreSQL

```bash
# Connect via kubectl
kubectl exec -it statefulset/postgres -n stock-analysis -- psql -U stockuser -d stockdb

# Run SQL commands
stockdb=# \dt  # List tables
stockdb=# SELECT * FROM stock_list LIMIT 10;
```

### Backup Database

```bash
# Create backup
kubectl exec statefulset/postgres -n stock-analysis -- \
  pg_dump -U stockuser stockdb > backup.sql

# Restore backup
cat backup.sql | kubectl exec -i statefulset/postgres -n stock-analysis -- \
  psql -U stockuser stockdb
```

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n stock-analysis

# Describe failing pod
kubectl describe pod <pod-name> -n stock-analysis

# Check events
kubectl get events -n stock-analysis --sort-by='.lastTimestamp'
```

### Image Pull Errors

If you see `ImagePullBackOff`:

1. Ensure images are built locally:
   ```bash
   docker images | grep stock
   ```

2. If using Minikube, load images:
   ```bash
   minikube image load stock-backend:latest
   minikube image load stock-frontend:latest
   ```

3. If using k3s, import images:
   ```bash
   docker save stock-backend:latest | sudo k3s ctr images import -
   docker save stock-frontend:latest | sudo k3s ctr images import -
   ```

### Database Connection Issues

```bash
# Check if PostgreSQL is running
kubectl get pods -n stock-analysis -l app=postgres

# Test connection from backend
kubectl exec deployment/backend -n stock-analysis -- \
  python -c "import psycopg2; conn = psycopg2.connect('postgresql://stockuser:stockpassword@postgres-service:5432/stockdb'); print('Connected!')"
```

### Ingress Not Working

```bash
# Check ingress controller
kubectl get pods -n ingress-nginx

# Check ingress resource
kubectl describe ingress stock-analysis-ingress -n stock-analysis

# Check ingress logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx
```

## Cleanup

### Delete All Resources

```bash
kubectl delete namespace stock-analysis
```

### Delete Individual Resources

```bash
kubectl delete -f ingress.yaml
kubectl delete -f frontend.yaml
kubectl delete -f backend.yaml
kubectl delete -f postgres.yaml
kubectl delete -f secrets.yaml
kubectl delete -f configmap.yaml
kubectl delete -f namespace.yaml
```

## Production Considerations

Before deploying to production:

1. **Secrets Management**:
   - Use external secret managers (HashiCorp Vault, AWS Secrets Manager)
   - Enable encryption at rest for Kubernetes secrets
   - Implement secret rotation

2. **High Availability**:
   - Use multiple replicas for all deployments
   - Implement pod anti-affinity rules
   - Set up database replication

3. **Monitoring & Logging**:
   - Install Prometheus and Grafana
   - Set up centralized logging (ELK, Loki)
   - Configure alerting

4. **Security**:
   - Enable Network Policies
   - Use Pod Security Standards
   - Implement RBAC
   - Regular security audits

5. **Backup & Disaster Recovery**:
   - Automated database backups
   - Persistent volume snapshots
   - Documented recovery procedures

6. **Performance**:
   - Set up HPA (Horizontal Pod Autoscaler)
   - Use resource quotas
   - Implement caching strategies

7. **TLS/SSL**:
   - Use cert-manager for automatic certificate management
   - Enable HTTPS on ingress

## Support

For issues or questions:
- Check the main [CICD_DOCUMENTATION.md](../CICD_DOCUMENTATION.md)
- Review Kubernetes logs
- Consult [Kubernetes documentation](https://kubernetes.io/docs/)

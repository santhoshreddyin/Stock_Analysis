# CI/CD Pipeline Documentation

This document provides comprehensive information about the GitHub Actions CI/CD pipeline for the Stock Analysis application with Kubernetes deployment.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Setup Instructions](#setup-instructions)
5. [Workflows](#workflows)
6. [Local Kubernetes Deployment](#local-kubernetes-deployment)
7. [Troubleshooting](#troubleshooting)

## Overview

The CI/CD pipeline automates the build, test, and deployment process for the Stock Analysis application. It consists of:

- **Backend**: FastAPI Python application
- **Frontend**: React application with Vite
- **Database**: PostgreSQL
- **Infrastructure**: Kubernetes

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    GitHub Actions                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────┐    ┌────────────┐    ┌──────────────┐ │
│  │   CI       │    │   CD       │    │  Local K8s   │ │
│  │  Pipeline  │───▶│  Pipeline  │───▶│   Deploy     │ │
│  └────────────┘    └────────────┘    └──────────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  Kubernetes Cluster   │
              ├───────────────────────┤
              │  • Frontend (React)   │
              │  • Backend (FastAPI)  │
              │  • PostgreSQL         │
              │  • Ingress (Nginx)    │
              └───────────────────────┘
```

## Prerequisites

### For GitHub Actions

1. **GitHub Repository Secrets**: Configure the following secrets in your repository settings:
   - `KUBE_CONFIG`: Base64-encoded Kubernetes config file
   - `OPENAI_API_KEY`: OpenAI API key
   - `TAVILY_API_KEY`: Tavily API key
   - `GMAIL_SMTP_USER`: Gmail SMTP username
   - `GMAIL_APP_PASSWORD`: Gmail app password
   - `TWITTER_BEARER_TOKEN`: Twitter API bearer token

2. **Self-Hosted Runner** (for local Kubernetes deployment):
   - Ubuntu Linux machine with Docker installed
   - kubectl installed and configured
   - Access to your local Kubernetes cluster
   - GitHub Actions runner installed and registered

### For Local Development

1. **Docker & Docker Compose**:
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   
   # Install Docker Compose
   sudo apt-get install docker-compose-plugin
   ```

2. **Kubernetes Cluster**:
   - Option 1: Minikube
     ```bash
     curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
     sudo install minikube-linux-amd64 /usr/local/bin/minikube
     minikube start
     ```
   
   - Option 2: k3s (lightweight Kubernetes)
     ```bash
     curl -sfL https://get.k3s.io | sh -
     sudo chmod 644 /etc/rancher/k3s/k3s.yaml
     ```
   
   - Option 3: Docker Desktop with Kubernetes enabled

3. **kubectl**:
   ```bash
   curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
   sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
   ```

4. **Nginx Ingress Controller**:
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml
   ```

## Setup Instructions

### 1. Configure GitHub Repository Secrets

Navigate to your repository → Settings → Secrets and variables → Actions → New repository secret

Add the following secrets:

```yaml
DOCKERHUB_USERNAME: <your-dockerhub-username>
DOCKERHUB_TOKEN: <your-dockerhub-access-token>
KUBE_CONFIG: <base64-encoded-kubeconfig>
OPENAI_API_KEY: <your-openai-key>
TAVILY_API_KEY: <your-tavily-key>
GMAIL_SMTP_USER: <your-email>
GMAIL_APP_PASSWORD: <app-password>
TWITTER_BEARER_TOKEN: <twitter-token>
POSTGRES_PASSWORD: <your-secure-postgres-password>
```

To get DockerHub access token:
1. Go to https://hub.docker.com/settings/security
2. Click "New Access Token"
3. Give it a name and copy the token

To get base64-encoded kubeconfig:
```bash
cat ~/.kube/config | base64 -w 0
```

### 2. Set Up Self-Hosted Runner (for Local K8s)

1. Go to repository → Settings → Actions → Runners → New self-hosted runner
2. Follow the instructions to install and configure the runner on your local machine
3. Start the runner:
   ```bash
   ./run.sh
   ```

### 3. Update Kubernetes Secrets

Before deploying, update the secrets in `k8s/secrets.yaml` with your actual values:

```bash
cd k8s
# Edit secrets.yaml with your actual credentials
kubectl apply -f secrets.yaml
```

### 4. Configure Hosts File (Optional)

Add the following to `/etc/hosts` for local access:

```bash
echo "127.0.0.1 stock-analysis.local" | sudo tee -a /etc/hosts
```

## Workflows

### 1. CI Workflow (`ci.yml`)

**Triggers**: Push to main/develop, Pull requests

**Jobs**:
- **Backend Lint & Test**: Lints Python code, runs type checks
- **Frontend Lint & Build**: Lints and builds React application
- **Security Scan**: Runs Trivy vulnerability scanner

**Usage**:
```bash
# Automatically runs on push/PR
git push origin main
```

### 2. CD Workflow (`cd.yml`)

**Triggers**: Push to main, Manual dispatch

**Jobs**:
- **Build & Push Images**: Builds Docker images, scans for vulnerabilities with Trivy, and pushes to Docker Hub
- **Deploy to Kubernetes**: Updates secrets from GitHub Secrets and deploys to Kubernetes cluster using kubectl

**Manual Trigger**:
1. Go to Actions tab
2. Select "CD - Continuous Deployment"
3. Click "Run workflow"
4. Select environment (production/staging)

### 3. Pipeline Workflow (`pipeline.yml`)

**Triggers**: Push to main/develop, Pull requests, Manual

**Description**: Orchestrates CI and CD workflows together

### 4. Local K8s Deploy Workflow (`local-k8s-deploy.yml`)

**Triggers**: Manual dispatch only

**Jobs**:
- **Build Local**: Builds Docker images without pushing to registry
- **Deploy Local**: Deploys to local Kubernetes cluster

**Usage**:
1. Go to Actions tab
2. Select "Build Docker Images (Local)"
3. Click "Run workflow"

## Local Kubernetes Deployment

### Using Docker Compose (Development)

```bash
# Set environment variables
export OPENAI_API_KEY="your-key"
export TAVILY_API_KEY="your-key"
export GMAIL_SMTP_USER="your-email"
export GMAIL_APP_PASSWORD="your-password"
export TWITTER_BEARER_TOKEN="your-token"

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Using Kubernetes (Production-like)

```bash
# Build images locally
docker build -t stock-backend:latest -f Dockerfile.backend .
docker build -t stock-frontend:latest -f Dockerfile.frontend .

# Deploy to Kubernetes
cd k8s
./deploy.sh

# Check deployment status
kubectl get pods -n stock-analysis
kubectl get services -n stock-analysis
kubectl get ingress -n stock-analysis

# View logs
kubectl logs -f deployment/backend -n stock-analysis
kubectl logs -f deployment/frontend -n stock-analysis

# Access the application
# Frontend: http://stock-analysis.local or http://localhost:30080
# Backend API: http://stock-analysis.local/api or http://localhost:30080/api
```

### Port Forwarding (Alternative Access)

```bash
# Forward backend service
kubectl port-forward -n stock-analysis service/backend-service 8000:8000

# Forward frontend service
kubectl port-forward -n stock-analysis service/frontend-service 8080:80

# Access:
# Backend: http://localhost:8000
# Frontend: http://localhost:8080
```

## Troubleshooting

### Common Issues

#### 1. Images Not Found in Kubernetes

**Problem**: Pods show `ImagePullBackOff` or `ErrImagePull`

**Solution**:
```bash
# For local images, ensure imagePullPolicy is set to IfNotPresent or Never
kubectl set image deployment/backend backend=stock-backend:latest -n stock-analysis
kubectl set image deployment/frontend frontend=stock-frontend:latest -n stock-analysis

# Or edit the deployment
kubectl edit deployment backend -n stock-analysis
# Change imagePullPolicy to IfNotPresent
```

#### 2. Database Connection Issues

**Problem**: Backend can't connect to PostgreSQL

**Solution**:
```bash
# Check if PostgreSQL is running
kubectl get pods -n stock-analysis | grep postgres

# Check logs
kubectl logs -n stock-analysis statefulset/postgres

# Verify service
kubectl get service postgres-service -n stock-analysis

# Test connection from backend pod
kubectl exec -n stock-analysis deployment/backend -- \
  psql -h postgres-service -U stockuser -d stockdb -c "SELECT 1"
```

#### 3. Ingress Not Working

**Problem**: Can't access application via ingress

**Solution**:
```bash
# Check ingress controller is running
kubectl get pods -n ingress-nginx

# If not installed, install it
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml

# Check ingress status
kubectl describe ingress stock-analysis-ingress -n stock-analysis

# Get ingress IP/hostname
kubectl get ingress -n stock-analysis
```

#### 4. Secrets Not Loading

**Problem**: Environment variables are not available in pods

**Solution**:
```bash
# Verify secrets exist
kubectl get secrets -n stock-analysis

# Check secret content
kubectl describe secret backend-secret -n stock-analysis

# Recreate secrets
kubectl delete secret backend-secret -n stock-analysis
kubectl apply -f k8s/secrets.yaml
kubectl rollout restart deployment/backend -n stock-analysis
```

#### 5. Self-Hosted Runner Connection Issues

**Problem**: Runner can't connect to cluster

**Solution**:
```bash
# Check runner status
./run.sh

# Verify kubectl works
kubectl get nodes

# Check kubeconfig
export KUBECONFIG=~/.kube/config
kubectl cluster-info

# For k3s, use correct config path
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
```

### Monitoring and Debugging

```bash
# View all resources
kubectl get all -n stock-analysis

# Describe specific resources
kubectl describe pod <pod-name> -n stock-analysis
kubectl describe deployment backend -n stock-analysis

# View logs
kubectl logs -f deployment/backend -n stock-analysis
kubectl logs -f deployment/frontend -n stock-analysis

# Execute commands in pod
kubectl exec -it deployment/backend -n stock-analysis -- /bin/bash

# Check events
kubectl get events -n stock-analysis --sort-by='.lastTimestamp'

# Resource usage
kubectl top pods -n stock-analysis
kubectl top nodes
```

### Cleanup

```bash
# Delete all resources
kubectl delete namespace stock-analysis

# Or delete individual resources
kubectl delete -f k8s/

# Clean up Docker resources
docker system prune -a
```

## Best Practices

1. **Secrets Management**:
   - Never commit secrets to version control
   - Use Kubernetes secrets or external secret managers (HashiCorp Vault, AWS Secrets Manager)
   - Rotate secrets regularly

2. **Resource Limits**:
   - Always set resource requests and limits
   - Monitor resource usage and adjust as needed

3. **Health Checks**:
   - Implement proper liveness and readiness probes
   - Test probes before deploying to production

4. **Monitoring**:
   - Set up monitoring (Prometheus, Grafana)
   - Configure log aggregation (ELK stack, Loki)
   - Set up alerts for critical issues

5. **Backup**:
   - Regularly backup PostgreSQL database
   - Use persistent volumes for data
   - Test restore procedures

## Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Documentation](https://docs.docker.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)

## Support

For issues or questions:
- Create an issue on GitHub
- Check existing issues for solutions
- Review logs and error messages

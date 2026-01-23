# Quick Start Guide - CI/CD Pipeline

This guide will help you quickly set up and deploy the Stock Analysis application using the CI/CD pipeline.

## 🚀 Quick Deploy Options

Choose one of the following deployment methods:

### Option 1: Local Development with Docker Compose (Fastest)

```bash
# 1. Clone the repository
git clone https://github.com/santhoshreddyin/Stock_Analysis.git
cd Stock_Analysis

# 2. Copy environment template
cp .env.example .env

# 3. Edit .env with your API keys
nano .env  # or use your preferred editor

# 4. Start all services
docker-compose up -d

# 5. Access the application
# Frontend: http://localhost
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Option 2: Local Kubernetes Deployment

```bash
# 1. Prerequisites
# - Install Docker
# - Install kubectl
# - Install Minikube or k3s or enable Kubernetes in Docker Desktop

# 2. Start Kubernetes cluster (if using Minikube)
minikube start

# 3. Install Nginx Ingress Controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml

# 4. Build Docker images
docker build -t stock-backend:latest -f Dockerfile.backend .
docker build -t stock-frontend:latest -f Dockerfile.frontend .

# 5. Load images into Minikube (if using Minikube)
minikube image load stock-backend:latest
minikube image load stock-frontend:latest

# 6. Update secrets with your API keys
cd k8s
nano secrets.yaml  # Edit with your actual credentials

# 7. Deploy to Kubernetes
chmod +x deploy.sh
./deploy.sh

# 8. Access the application
# Add to /etc/hosts: 127.0.0.1 stock-analysis.local
echo "127.0.0.1 stock-analysis.local" | sudo tee -a /etc/hosts

# Access at: http://stock-analysis.local

# Or use port forwarding
kubectl port-forward -n stock-analysis service/frontend-service 8080:80
# Access at: http://localhost:8080
```

### Option 3: GitHub Actions CI/CD Pipeline

#### A. Set Up GitHub Actions for Remote Deployment

```bash
# 1. Configure GitHub Secrets
# Go to: Repository → Settings → Secrets and variables → Actions
# Add these secrets:
OPENAI_API_KEY
TAVILY_API_KEY
GMAIL_SMTP_USER
GMAIL_APP_PASSWORD
TWITTER_BEARER_TOKEN
KUBE_CONFIG  # Base64-encoded kubectl config

# 2. Push to main branch
git push origin main

# 3. GitHub Actions will automatically:
# - Run CI tests and linting
# - Build Docker images
# - Deploy to Kubernetes cluster
```

#### B. Set Up Self-Hosted Runner for Local Kubernetes

```bash
# 1. On your local machine with Kubernetes:
# Go to: Repository → Settings → Actions → Runners → New self-hosted runner

# 2. Follow the installation instructions, then start the runner:
./run.sh

# 3. Trigger the local deployment workflow:
# Go to: Actions → "Build Docker Images (Local)" → Run workflow

# The workflow will:
# - Build Docker images
# - Deploy to your local Kubernetes cluster
```

## 📋 Prerequisites Checklist

### For Docker Compose:
- [ ] Docker installed
- [ ] Docker Compose installed
- [ ] API keys obtained (OpenAI, Tavily, Gmail, Twitter)

### For Kubernetes:
- [ ] Kubernetes cluster running (Minikube/k3s/Docker Desktop)
- [ ] kubectl installed and configured
- [ ] Nginx Ingress Controller installed
- [ ] Docker installed for building images
- [ ] API keys obtained

### For GitHub Actions:
- [ ] GitHub repository access
- [ ] Repository secrets configured
- [ ] Self-hosted runner installed (for local K8s)
- [ ] Kubernetes cluster accessible from runner

## 🔑 Getting API Keys

### OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy and save it securely

### Tavily API Key
1. Go to https://tavily.com/
2. Sign up for an account
3. Get your API key from the dashboard

### Gmail App Password
1. Enable 2-factor authentication on your Google account
2. Go to https://myaccount.google.com/apppasswords
3. Generate a new app password for "Mail"
4. Copy the 16-character password

### Twitter Bearer Token (Optional)
1. Go to https://developer.twitter.com/
2. Create a developer account
3. Create a new project and app
4. Generate a Bearer Token

## 🧪 Testing the Deployment

### Health Checks

```bash
# Docker Compose
curl http://localhost:8000/api/health

# Kubernetes
kubectl exec -n stock-analysis deployment/backend -- curl http://localhost:8000/api/health

# Or via ingress
curl http://stock-analysis.local/api/health
```

### API Testing

```bash
# Get list of stocks
curl http://localhost:8000/api/stocks

# Get stock detail
curl http://localhost:8000/api/stocks/AAPL

# Get key parameters
curl http://localhost:8000/api/key-parameters

# Interactive API docs
# Open in browser: http://localhost:8000/docs
```

### Frontend Testing

```bash
# Docker Compose
open http://localhost

# Kubernetes with ingress
open http://stock-analysis.local

# Kubernetes with port-forward
kubectl port-forward -n stock-analysis service/frontend-service 8080:80
open http://localhost:8080
```

## 🔍 Monitoring

### View Logs

```bash
# Docker Compose
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres

# Kubernetes
kubectl logs -f deployment/backend -n stock-analysis
kubectl logs -f deployment/frontend -n stock-analysis
kubectl logs -f statefulset/postgres -n stock-analysis
```

### Resource Usage

```bash
# Docker
docker stats

# Kubernetes
kubectl top pods -n stock-analysis
kubectl top nodes
```

## 🛠️ Common Commands

### Docker Compose

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Rebuild images
docker-compose build

# View status
docker-compose ps

# Remove all (including volumes)
docker-compose down -v
```

### Kubernetes

```bash
# View all resources
kubectl get all -n stock-analysis

# Describe a resource
kubectl describe pod <pod-name> -n stock-analysis

# Scale deployment
kubectl scale deployment backend --replicas=3 -n stock-analysis

# Update image
kubectl set image deployment/backend backend=stock-backend:latest -n stock-analysis

# Restart deployment
kubectl rollout restart deployment/backend -n stock-analysis

# Delete everything
kubectl delete namespace stock-analysis
```

## 📚 Next Steps

1. **Read Full Documentation**: See [CICD_DOCUMENTATION.md](CICD_DOCUMENTATION.md)
2. **Configure Monitoring**: Set up Prometheus and Grafana
3. **Enable TLS**: Add SSL certificates for HTTPS
4. **Set Up Backups**: Configure automated database backups
5. **Implement CI/CD**: Connect your development workflow

## 🆘 Troubleshooting

### Images not found
```bash
# Docker Compose: Rebuild images
docker-compose build

# Kubernetes: Check images exist
docker images | grep stock

# Minikube: Load images
minikube image load stock-backend:latest
minikube image load stock-frontend:latest
```

### Database connection errors
```bash
# Docker Compose: Check if postgres is running
docker-compose ps postgres

# Kubernetes: Check postgres pod
kubectl get pods -n stock-analysis -l app=postgres
kubectl logs -n stock-analysis statefulset/postgres
```

### Port conflicts
```bash
# Docker Compose: Change ports in docker-compose.yml
# For example, change "80:80" to "8080:80"

# Kubernetes: Use different NodePort or port-forward to different port
kubectl port-forward -n stock-analysis service/frontend-service 8081:80
```

### Permission denied
```bash
# Linux: Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Scripts not executable
chmod +x k8s/deploy.sh
```

## 📞 Support

- **Documentation**: [CICD_DOCUMENTATION.md](CICD_DOCUMENTATION.md)
- **Kubernetes Guide**: [k8s/README.md](k8s/README.md)
- **GitHub Issues**: https://github.com/santhoshreddyin/Stock_Analysis/issues
- **Main README**: [README.md](README.md)

---

**Happy Deploying! 🎉**

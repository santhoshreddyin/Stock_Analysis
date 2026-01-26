# GitHub Actions Workflows

This directory contains GitHub Actions workflows for CI/CD automation.

## Workflows Overview

### 1. `ci.yml` - Continuous Integration
**Triggers**: Push to main/develop branches, Pull Requests

**Purpose**: Validate code quality and security

**Jobs**:
- **Backend Lint & Test**
  - Python code linting with flake8
  - Type checking with mypy
  - Syntax validation
  
- **Frontend Lint & Build**
  - ESLint code linting
  - Build verification
  - Build artifact upload

- **Security Scan**
  - Trivy vulnerability scanning
  - SARIF report generation
  - GitHub Security integration

**Status Badge**:
```markdown
![CI Status](https://github.com/santhoshreddyin/Stock_Analysis/workflows/CI%20-%20Continuous%20Integration/badge.svg)
```

### 2. `cd.yml` - Continuous Deployment
**Triggers**: Push to main branch, Manual dispatch

**Purpose**: Build Docker images and deploy to Kubernetes

**Jobs**:
- **Build & Push Images**
  - Multi-platform Docker builds
  - Push to GitHub Container Registry (ghcr.io)
  - Semantic versioning tags
  - Build caching for faster builds

- **Deploy to Kubernetes**
  - Update Kubernetes secrets
  - Apply manifests
  - Rolling update deployments
  - Rollout verification
  - Smoke tests

**Requirements**:
- Self-hosted runner with kubectl access
- Kubernetes cluster access
- Repository secrets configured

**Status Badge**:
```markdown
![CD Status](https://github.com/santhoshreddyin/Stock_Analysis/workflows/CD%20-%20Continuous%20Deployment/badge.svg)
```

### 3. `pipeline.yml` - Full CI/CD Pipeline
**Triggers**: Push, Pull Requests, Manual dispatch

**Purpose**: Orchestrate CI and CD workflows

**Flow**:
```
PR/Push → CI → (on main) → CD → Deploy
```

**Status Badge**:
```markdown
![Pipeline Status](https://github.com/santhoshreddyin/Stock_Analysis/workflows/CI%2FCD%20Pipeline/badge.svg)
```

### 4. `local-k8s-deploy.yml` - Local Kubernetes Deployment
**Triggers**: Manual dispatch only

**Purpose**: Deploy to local Kubernetes cluster

**Jobs**:
- **Build Local**
  - Build Docker images
  - Export as tar files
  - Upload as artifacts

- **Deploy Local**
  - Download artifacts
  - Load images to Docker
  - Deploy to local K8s cluster

**Use Case**: Testing production deployment locally

## Setup Instructions

### 1. Configure Repository Secrets

Go to: **Settings → Secrets and variables → Actions → New repository secret**

Add the following secrets:

#### Required Secrets:

| Secret Name | Description | How to Get |
|-------------|-------------|------------|
| `DOCKERHUB_USERNAME` | Docker Hub username | Your Docker Hub account username |
| `DOCKERHUB_TOKEN` | Docker Hub access token | https://hub.docker.com/settings/security |
| `OPENAI_API_KEY` | OpenAI API key | https://platform.openai.com/api-keys |
| `TAVILY_API_KEY` | Tavily search API key | https://tavily.com/ |
| `GMAIL_SMTP_USER` | Gmail email address | Your Gmail account |
| `GMAIL_APP_PASSWORD` | Gmail app password | https://myaccount.google.com/apppasswords |
| `TWITTER_BEARER_TOKEN` | Twitter API token (optional) | https://developer.twitter.com/ |
| `POSTGRES_PASSWORD` | PostgreSQL database password | Choose a secure password |
| `KUBE_CONFIG` | Base64-encoded kubeconfig | See below |

#### Generate DockerHub Access Token:

1. Go to https://hub.docker.com/settings/security
2. Click **New Access Token**
3. Give it a name (e.g., "GitHub Actions")
4. Select appropriate permissions (Read, Write, Delete)
5. Copy the token and save as `DOCKERHUB_TOKEN` secret

#### Generate KUBE_CONFIG:

```bash
# Encode your kubeconfig
cat ~/.kube/config | base64 -w 0

# Or for macOS
cat ~/.kube/config | base64

# Copy the output and paste as KUBE_CONFIG secret
```

### 2. Set Up Self-Hosted Runner

For deploying to local Kubernetes, you need a self-hosted runner:

1. **Navigate to Runner Settings**:
   - Go to: **Settings → Actions → Runners**
   - Click: **New self-hosted runner**

2. **Install Runner on Your Machine**:
   ```bash
   # Create a folder
   mkdir actions-runner && cd actions-runner
   
   # Download the latest runner package
   curl -o actions-runner-linux-x64-2.311.0.tar.gz -L \
     https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz
   
   # Extract the installer
   tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz
   
   # Create the runner and start the configuration experience
   ./config.sh --url https://github.com/santhoshreddyin/Stock_Analysis --token YOUR_TOKEN
   
   # Start the runner
   ./run.sh
   ```

3. **Install as a Service** (Optional):
   ```bash
   sudo ./svc.sh install
   sudo ./svc.sh start
   ```

4. **Prerequisites on Runner Machine**:
   - Docker installed
   - kubectl installed and configured
   - Access to your Kubernetes cluster
   - `envsubst` utility (usually part of `gettext` package)

### 3. Docker Hub Registry

The CD workflow pushes images to Docker Hub (hub.docker.com).

**Create Docker Hub Account**:
1. Go to https://hub.docker.com/signup
2. Create an account or sign in
3. Create access token as described above

**Image Naming**:
- Backend image: `<your-username>/stock-backend:latest`
- Frontend image: `<your-username>/stock-frontend:latest`

## Usage

### Running CI Workflow

Automatic on push/PR:
```bash
git push origin main
```

Manual trigger:
1. Go to **Actions** tab
2. Select **CI - Continuous Integration**
3. Click **Run workflow**

### Running CD Workflow

Automatic on push to main (after CI passes):
```bash
git push origin main
```

Manual trigger:
1. Go to **Actions** tab
2. Select **CD - Continuous Deployment**
3. Click **Run workflow**
4. Select environment (production/staging)

### Running Local K8s Deployment

1. Go to **Actions** tab
2. Select **Build Docker Images (Local)**
3. Click **Run workflow**
4. Wait for build and deploy jobs to complete

## Monitoring Workflows

### View Workflow Runs

1. Go to **Actions** tab
2. Select a workflow from the left sidebar
3. Click on a run to see details

### View Logs

1. Open a workflow run
2. Click on a job name
3. Expand steps to view logs

### Check Artifacts

1. Open a workflow run
2. Scroll to **Artifacts** section
3. Download artifacts (e.g., frontend-build, Docker images)

## Troubleshooting

### Common Issues

#### 1. Workflow Fails with "secrets not found"

**Solution**: Ensure all required secrets are configured in repository settings.

#### 2. Docker build fails

**Solution**: 
- Check Docker build logs
- Ensure Dockerfile syntax is correct
- Verify all dependencies are available

#### 3. Kubernetes deployment fails

**Solution**:
- Check if self-hosted runner is online
- Verify KUBE_CONFIG is valid
- Ensure kubectl can access the cluster
- Check if namespace exists

#### 4. Image pull errors in Kubernetes

**Solution**:
- For ghcr.io: Ensure package is public or configure image pull secrets
- For local: Use `imagePullPolicy: IfNotPresent` or `Never`

#### 5. Self-hosted runner offline

**Solution**:
```bash
cd actions-runner
./run.sh

# Or if installed as service
sudo ./svc.sh status
sudo ./svc.sh start
```

### Debugging Tips

1. **Enable Debug Logging**:
   - Repository Settings → Secrets → Actions
   - Add secret: `ACTIONS_STEP_DEBUG` = `true`
   - Add secret: `ACTIONS_RUNNER_DEBUG` = `true`

2. **Use act for Local Testing**:
   ```bash
   # Install act
   curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
   
   # Run workflows locally
   act -l  # List workflows
   act -j lint-and-test-backend  # Run specific job
   ```

3. **SSH to Runner**:
   ```bash
   # Add this step to your workflow for debugging
   - name: Setup tmate session
     uses: mxschmitt/action-tmate@v3
   ```

## Best Practices

1. **Branch Protection**:
   - Require PR reviews
   - Require status checks to pass (CI)
   - Require branches to be up to date

2. **Secrets Management**:
   - Use environment-specific secrets
   - Rotate secrets regularly
   - Never log secrets

3. **Caching**:
   - Use GitHub Actions cache
   - Cache Docker layers
   - Cache dependencies (npm, pip)

4. **Parallel Jobs**:
   - Run independent jobs in parallel
   - Use matrix strategy for multiple versions

5. **Notifications**:
   - Set up Slack/Discord webhooks
   - Configure email notifications
   - Use GitHub status checks

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions)
- [Self-Hosted Runners](https://docs.github.com/en/actions/hosting-your-own-runners)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Main CI/CD Documentation](../CICD_DOCUMENTATION.md)

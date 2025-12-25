#!/bin/bash

# Audifyy Git Repository Setup Script
# This script initializes the git repository and pushes to GitHub

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Configuration
REPO_URL="https://Ajeesh24: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@github.com/Ajeesh24/audiify-core.git"
BRANCH_NAME="main"

print_status "Setting up Audifyy Git repository..."

# Check if we're already in a git repository
if [ -d ".git" ]; then
    print_warning "Already in a Git repository. Checking remote..."

    # Check if remote exists
    if git remote get-url origin >/dev/null 2>&1; then
        CURRENT_REMOTE=$(git remote get-url origin)
        print_status "Current remote: $CURRENT_REMOTE"
    else
        print_status "Adding remote origin..."
        git remote add origin "$REPO_URL"
    fi
else
    print_status "Initializing new Git repository..."
    git init
    git remote add origin "$REPO_URL"
fi

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    print_status "Creating .gitignore file..."
    cat > .gitignore << 'EOF'
# Logs
logs
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Runtime data
pids
*.pid
*.seed
*.pid.lock

# Coverage directory used by tools like istanbul
coverage/
.nyc_output

# Dependency directories
node_modules/
*/node_modules/
backend/venv/
backend/.venv/

# Optional npm cache directory
.npm

# Optional REPL history
.node_repl_history

# Output of 'npm pack'
*.tgz

# Yarn Integrity file
.yarn-integrity

# dotenv environment variables file
.env
.env.local
.env.development.local
.env.test.local
.env.production.local
backend/.env
frontend/.env

# Next.js build output
.next

# Nuxt.js build output
.nuxt

# vuepress build output
.vuepress/dist

# Serverless directories
.serverless

# FuseBox cache
.fusebox/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
ENV/
env/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Terraform
*.tfstate
*.tfstate.*
.terraform/
.terraform.lock.hcl
infra/terraform/backend.tf
infra/terraform/terraform.tfvars

# Audio files
*.mp3
*.wav
*.opus

# Temporary files
tmp/
temp/
*.tmp

# Build artifacts
frontend/dist/
frontend/build/

# Test artifacts
.pytest_cache/
.coverage
htmlcov/
EOF
fi

# Make scripts executable
chmod +x infra/scripts/deploy.sh
chmod +x start-dev.sh

print_status "Staging files..."
git add .

# Check if there are changes to commit
if git diff --staged --quiet; then
    print_warning "No changes to commit."
else
    print_status "Committing changes..."
    git commit -m "feat: Initial Audifyy MVP with AWS infrastructure

- Complete FastAPI backend with LangChain integration
- React PWA frontend with audio streaming
- AWS deployment infrastructure (Terraform)
- GitHub Actions CI/CD workflows
- Docker containerization
- Comprehensive documentation

Features:
- Article-to-audio conversion
- AI-powered summarization
- Multiple TTS voices
- Progressive Web App
- Auto-scaling infrastructure
- Cost-optimized deployment"

    print_status "Pushing to GitHub..."

    # Push to main branch
    git branch -M "$BRANCH_NAME"
    git push -u origin "$BRANCH_NAME"

    print_success "Code pushed successfully to GitHub!"
fi

print_status "Repository setup completed!"
print_status ""
print_status "=== Next Steps ==="
print_status "1. Go to GitHub repository: https://github.com/Ajeesh24/audiify-core"
print_status "2. Set up GitHub Secrets (see infra/README.md)"
print_status "3. Run the deployment script: ./infra/scripts/deploy.sh"
print_status "4. Monitor the GitHub Actions workflow"
print_status ""
print_success "Audifyy is ready for deployment! 🚀"
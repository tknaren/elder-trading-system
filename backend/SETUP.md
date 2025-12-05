# Elder Trading System - GitHub Repository Setup

## 📁 Repository Structure

```
elder-trading-system/
├── .github/
│   └── workflows/
│       └── azure-deploy.yml      # CI/CD pipeline
├── backend/
│   ├── app.py                    # Flask application
│   ├── requirements.txt          # Python dependencies
│   ├── startup.sh                # Azure startup script
│   ├── wsgi.py                   # WSGI entry point
│   └── templates/
│       └── index.html            # Frontend UI
├── docs/
│   └── create_deployment_guide.js
├── azure-config.ini
├── README.md
└── .gitignore
```

## 🚀 One-Time Setup Instructions

### Step 1: Create Azure Resources (if not done)

```bash
# Login to Azure
az login

# Create resource group
az group create --name elder-trading-rg --location uksouth

# Create App Service Plan (Free tier)
az appservice plan create \
  --name elder-trading-plan \
  --resource-group elder-trading-rg \
  --sku F1 \
  --is-linux

# Create Web App
az webapp create \
  --name elder-trading-app \
  --resource-group elder-trading-rg \
  --plan elder-trading-plan \
  --runtime "PYTHON:3.11"

# Configure startup command
az webapp config set \
  --name elder-trading-app \
  --resource-group elder-trading-rg \
  --startup-file "gunicorn --bind=0.0.0.0:8000 --chdir /home/site/wwwroot app:app"
```

### Step 2: Create Azure Service Principal for GitHub Actions

```bash
# Create service principal and get credentials
az ad sp create-for-rbac \
  --name "elder-trading-github-actions" \
  --role contributor \
  --scopes /subscriptions/{subscription-id}/resourceGroups/elder-trading-rg \
  --sdk-auth
```

This will output JSON like:
```json
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "clientSecret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "subscriptionId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  ...
}
```

### Step 3: Add GitHub Secret

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `AZURE_CREDENTIALS`
5. Value: Paste the entire JSON output from Step 2

### Step 4: Create Persistent Storage (Optional but Recommended)

```bash
# Create storage account
az storage account create \
  --name eldertradingstorage \
  --resource-group elder-trading-rg \
  --location uksouth \
  --sku Standard_LRS

# Create file share
az storage share create \
  --name elder-data \
  --account-name eldertradingstorage

# Get storage key
STORAGE_KEY=$(az storage account keys list \
  --account-name eldertradingstorage \
  --query [0].value -o tsv)

# Mount to web app
az webapp config storage-account add \
  --name elder-trading-app \
  --resource-group elder-trading-rg \
  --custom-id ElderData \
  --storage-type AzureFiles \
  --share-name elder-data \
  --account-name eldertradingstorage \
  --access-key $STORAGE_KEY \
  --mount-path /home/data

# Set environment variable for database path
az webapp config appsettings set \
  --name elder-trading-app \
  --resource-group elder-trading-rg \
  --settings DATABASE_PATH=/home/data/elder_trading.db
```

### Step 5: Push to GitHub

```bash
# Initialize git (if not already)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - Elder Trading System"

# Add remote (replace with your repo URL)
git remote add origin https://github.com/YOUR_USERNAME/elder-trading-system.git

# Push to main branch
git push -u origin main
```

## 🔄 How CI/CD Works

1. **On every push to `main`:**
   - Code is checked out
   - Python environment is set up
   - Dependencies are installed
   - Linting runs (flake8)
   - Tests run (if present)
   - Code deploys to Azure

2. **On pull requests:**
   - Same as above, but NO deployment
   - Helps catch issues before merging

3. **Manual trigger:**
   - Go to Actions tab → Select workflow → Run workflow

## 🔧 Customization

### Change Azure Web App Name
Edit `.github/workflows/azure-deploy.yml`:
```yaml
env:
  AZURE_WEBAPP_NAME: your-app-name    # Change this
```

### Add Environment Variables
Add secrets in GitHub, then reference in workflow:
```yaml
- name: Deploy
  env:
    SECRET_KEY: ${{ secrets.SECRET_KEY }}
```

### Add Tests
Create `backend/tests/` directory with pytest files:
```python
# backend/tests/test_app.py
def test_health_check(client):
    response = client.get('/api/health')
    assert response.status_code == 200
```

## 📊 Monitoring Deployment

- **GitHub Actions**: Repository → Actions tab
- **Azure Portal**: App Service → Deployment Center
- **Logs**: `az webapp log tail --name elder-trading-app --resource-group elder-trading-rg`

## 🆘 Troubleshooting

### Deployment fails with "Resource not found"
- Ensure `AZURE_CREDENTIALS` secret is set correctly
- Verify the Web App name matches in workflow file

### App shows 502 Bad Gateway
- Check startup command is correct
- View logs: `az webapp log tail --name elder-trading-app --resource-group elder-trading-rg`

### Database resets after deployment
- Ensure Azure Files mount is configured
- Check DATABASE_PATH environment variable

## 🔗 Useful Links

- **App URL**: https://elder-trading-app.azurewebsites.net
- **Azure Portal**: https://portal.azure.com
- **GitHub Actions Docs**: https://docs.github.com/en/actions

# GitHub Actions Setup Guide

This guide explains how to configure GitHub Actions for automated deployment to Azure Container Apps.

## Prerequisites

- Azure Subscription
- GitHub repository
- Azure CLI installed

## Step 1: Create Service Principal with Federated Credentials (OIDC)

**Recommended approach** - No secrets stored in GitHub!

```bash
# Set variables
SUBSCRIPTION_ID="9c9da4ea-7fc3-49d9-8135-8ac359fd8b05"
RESOURCE_GROUP="rg-keyvault-demo"
GITHUB_REPO="your-username/your-repo"  # Format: owner/repo

# Create Azure AD App Registration
APP_NAME="sp-keyvault-github-actions"

az ad app create --display-name $APP_NAME

APP_ID=$(az ad app list --display-name $APP_NAME --query "[0].appId" -o tsv)

# Create Service Principal
az ad sp create --id $APP_ID

SP_OBJECT_ID=$(az ad sp show --id $APP_ID --query id -o tsv)

# Assign Contributor role to Resource Group
az role assignment create \
  --role Contributor \
  --assignee $APP_ID \
  --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP

# Create Federated Credential for GitHub Actions
az ad app federated-credential create \
  --id $APP_ID \
  --parameters "{
    \"name\": \"github-actions-credential\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"repo:${GITHUB_REPO}:ref:refs/heads/main\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }"

# Get Tenant ID
TENANT_ID=$(az account show --query tenantId -o tsv)

echo "=== GitHub Secrets ==="
echo "AZURE_CLIENT_ID: $APP_ID"
echo "AZURE_TENANT_ID: $TENANT_ID"
echo "AZURE_SUBSCRIPTION_ID: $SUBSCRIPTION_ID"
```

## Step 2: Add Secrets to GitHub Repository

Go to: `https://github.com/your-username/your-repo/settings/secrets/actions`

Add these secrets:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `AZURE_CLIENT_ID` | `<APP_ID>` | Service Principal App ID |
| `AZURE_TENANT_ID` | `<TENANT_ID>` | Azure Tenant ID |
| `AZURE_SUBSCRIPTION_ID` | `<SUBSCRIPTION_ID>` | Azure Subscription ID |

**Note**: With OIDC/Federated Credentials, you DON'T need `AZURE_CLIENT_SECRET`!

## Alternative: Service Principal with Secret (Less Secure)

```bash
# Create Service Principal with secret
SP_OUTPUT=$(az ad sp create-for-rbac \
  --name "sp-keyvault-github-actions" \
  --role Contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP \
  --json-auth)

echo "=== GitHub Secrets ==="
echo "AZURE_CREDENTIALS: $SP_OUTPUT"  # Store entire JSON as secret
```

GitHub Secret:
- `AZURE_CREDENTIALS`: Full JSON output

## Step 3: Configure Container Apps Secret

Store the API token as a Container Apps secret:

```bash
# Add secret to Container App
az containerapp secret set \
  --name ca-keyvault-demo-1769000752 \
  --resource-group rg-keyvault-demo \
  --secrets "api-token=your-secret-token-here"

# Reference secret in env var (already done in deploy.yml)
# --env-vars "API_TOKEN=secretref:api-token"
```

## Step 4: Verify Workflow

### Trigger Deployment

```bash
# Push to main branch
git add .
git commit -m "Initial deployment"
git push origin main
```

### Monitor Workflow

Go to: `https://github.com/your-username/your-repo/actions`

### Check Deployment

```bash
# Get Container App URL
az containerapp show \
  --name ca-keyvault-demo-1769000752 \
  --resource-group rg-keyvault-demo \
  --query properties.configuration.ingress.fqdn \
  -o tsv

# Test health endpoint
curl https://ca-keyvault-demo-1769000752.salmonbush-2010df6d.germanywestcentral.azurecontainerapps.io/health
```

## Step 5: Update Workflow (Optional Customizations)

### Use Azure Container Registry (ACR)

```yaml
- name: Build and push to ACR
  run: |
    az acr build \
      --registry your-acr \
      --image keyvault-app:${{ github.sha }} \
      --image keyvault-app:latest \
      .

- name: Deploy to Container Apps
  run: |
    az containerapp update \
      --name ${{ env.CONTAINER_APP_NAME }} \
      --resource-group ${{ env.AZURE_RESOURCE_GROUP }} \
      --image your-acr.azurecr.io/keyvault-app:${{ github.sha }}
```

### Add Staging Environment

```yaml
jobs:
  deploy-staging:
    # ... deploy to staging container app

  deploy-production:
    needs: deploy-staging
    if: github.ref == 'refs/heads/main'
    # ... deploy to production container app
```

## Troubleshooting

### Permission Denied

```bash
# Verify Service Principal has Contributor role
az role assignment list \
  --assignee $APP_ID \
  --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP
```

### Deployment Fails

```bash
# Check Container App logs
az containerapp logs show \
  --name ca-keyvault-demo-1769000752 \
  --resource-group rg-keyvault-demo \
  --tail 50

# Check deployment status
az containerapp revision list \
  --name ca-keyvault-demo-1769000752 \
  --resource-group rg-keyvault-demo
```

### OIDC Authentication Issues

1. Verify federated credential subject matches: `repo:owner/repo:ref:refs/heads/main`
2. Check GitHub repo name is correct (case-sensitive)
3. Ensure `id-token: write` permission in workflow

## Security Best Practices

✅ **Use OIDC/Federated Credentials** (no secrets in GitHub)
✅ **Principle of Least Privilege** (only Contributor on Resource Group)
✅ **Container Apps Secrets** for sensitive env vars (API_TOKEN)
✅ **Managed Identity** for KeyVault access (no credentials in code)
✅ **Separate Service Principals** per environment (dev, staging, prod)

## References

- [Azure Login Action](https://github.com/Azure/login)
- [Federated Credentials](https://learn.microsoft.com/en-us/azure/active-directory/workload-identities/workload-identity-federation)
- [Container Apps CLI](https://learn.microsoft.com/en-us/cli/azure/containerapp)

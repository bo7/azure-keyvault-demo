# Azure KeyVault FastAPI Application

FastAPI application with Azure KeyVault integration using Managed Identity.

## Features

- 🔐 **Azure KeyVault Integration** with Managed Identity
- 🚀 **FastAPI** REST API with OpenAPI docs
- 🎨 **Simple HTML UI** with interactive buttons
- 🔒 **Bearer Token Authentication** for protected endpoints
- 📦 **Container-ready** with Dockerfile
- ✅ **Production patterns**: caching, error handling, health checks

## Project Structure

```
keyvault-app/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI endpoints
│   ├── auth.py          # Bearer token validation
│   ├── keyvault.py      # KeyVault client wrapper
│   └── models.py        # Pydantic models
├── requirements.txt
├── Dockerfile
└── .env.example
```

## API Endpoints

### Public Endpoints

- `GET /` - HTML UI with buttons
- `GET /health` - Health check
- `POST /secrets` - Create/update secret (Button: **Send**)
- `GET /secrets/{name}` - Get secret value (Button: **Receive**)

### Protected Endpoints (Requires Bearer Token)

- `GET /api/secrets` - List all secret names (Button: **List**)

## Local Development

### Prerequisites

- Python 3.11+
- Azure CLI (`az login`)
- Access to Azure KeyVault (Key Vault Secrets User/Officer role)

### Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your KeyVault URL

# 3. Login to Azure
az login --tenant "2fa4aee9-bc96-498d-aea2-af88f77c9b22"

# 4. Run the application
uvicorn app.main:app --reload
```

Visit: http://localhost:8000

### API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Docker Build & Run

```bash
# Build
docker build -t keyvault-app .

# Run (requires Azure credentials)
docker run -p 8000:8000 \
  -e KEYVAULT_URL="https://kv-demo-1769000021.vault.azure.net/" \
  -e API_TOKEN="your-token" \
  keyvault-app
```

## Azure Container Apps Deployment

```bash
# Set variables
KEYVAULT_URL="https://kv-demo-1769000021.vault.azure.net/"
CONTAINER_APP_NAME="ca-keyvault-demo-1769000752"

# Build and push to Azure Container Registry
az acr build --registry <your-acr> --image keyvault-app:latest .

# Update Container App
az containerapp update \
  --name $CONTAINER_APP_NAME \
  --resource-group rg-keyvault-demo \
  --image <your-acr>.azurecr.io/keyvault-app:latest \
  --set-env-vars "KEYVAULT_URL=$KEYVAULT_URL" "API_TOKEN=secretref:api-token"
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `KEYVAULT_URL` | Yes | Azure KeyVault URL |
| `API_TOKEN` | No | Bearer token for `/api/secrets` (default: `demo-token-123`) |

## Azure RBAC Roles Required

| Identity | Role | Purpose |
|----------|------|---------|
| Container App Managed Identity | **Key Vault Secrets User** | Read secrets |
| Developer/Admin | **Key Vault Secrets Officer** | Manage secrets |

## Authentication

### DefaultAzureCredential Chain

The app uses `DefaultAzureCredential` which tries (in order):

1. **Managed Identity** (in Azure)
2. **Azure CLI** (`az login` for local dev)
3. **Environment Variables** (Service Principal)

### Bearer Token

Protected endpoint `/api/secrets` requires:

```bash
curl -H "Authorization: Bearer demo-token-123" \
  https://your-app.azurecontainerapps.io/api/secrets
```

## Testing

```bash
# Set a secret
curl -X POST http://localhost:8000/secrets \
  -H "Content-Type: application/json" \
  -d '{"name": "test-secret", "value": "my-value"}'

# Get a secret
curl http://localhost:8000/secrets/test-secret

# List secrets (requires token)
curl -H "Authorization: Bearer demo-token-123" \
  http://localhost:8000/api/secrets
```

## Production Considerations

- ✅ **Managed Identity** for KeyVault access (no credentials in code)
- ✅ **RBAC** with principle of least privilege
- ✅ **Caching** with `@lru_cache` for frequently accessed secrets
- ✅ **Error handling** with proper HTTP status codes
- ✅ **Logging** for observability
- ✅ **Health checks** for container orchestration
- ✅ **Non-root user** in Docker for security

### Recommended Improvements

- [ ] Replace simple Bearer token with **Azure AD / Entra ID** authentication
- [ ] Add **rate limiting** (e.g., with `slowapi`)
- [ ] Implement **secret rotation** monitoring
- [ ] Add **Application Insights** for telemetry
- [ ] Use **Azure Key Vault references** in Container Apps for `API_TOKEN`

## License

MIT

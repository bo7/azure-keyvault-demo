"""FastAPI application with Azure KeyVault integration."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from azure.core.exceptions import ResourceNotFoundError, AzureError

from app.models import (
    SecretCreate,
    SecretResponse,
    SecretListResponse,
    HealthResponse
)
from app.keyvault import get_keyvault_client, KeyVaultClient
from app.auth import verify_token

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting FastAPI application")
    # Initialize KeyVault client on startup
    try:
        get_keyvault_client()
        logger.info("KeyVault client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize KeyVault client: {e}")
    yield
    logger.info("Shutting down FastAPI application")


app = FastAPI(
    title="Azure KeyVault Demo API",
    description="FastAPI application with Azure KeyVault integration and Managed Identity",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve a simple HTML UI with buttons."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Azure KeyVault Demo</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 { color: #0078d4; }
            input, button {
                padding: 10px;
                margin: 5px 0;
                font-size: 14px;
                border-radius: 4px;
                border: 1px solid #ddd;
            }
            button {
                background: #0078d4;
                color: white;
                border: none;
                cursor: pointer;
                font-weight: 500;
            }
            button:hover { background: #005a9e; }
            .response {
                margin-top: 20px;
                padding: 15px;
                background: #f9f9f9;
                border-left: 3px solid #0078d4;
                border-radius: 4px;
                font-family: monospace;
                font-size: 12px;
            }
            .section { margin: 30px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 Azure KeyVault Demo</h1>
            <p>Manage secrets with Azure KeyVault and Managed Identity</p>

            <div class="section">
                <h3>Set Secret</h3>
                <input type="text" id="setName" placeholder="Secret name" style="width: 300px;">
                <input type="text" id="setValue" placeholder="Secret value" style="width: 300px;">
                <button onclick="setSecret()">Send</button>
            </div>

            <div class="section">
                <h3>Get Secret</h3>
                <input type="text" id="getName" placeholder="Secret name" style="width: 300px;">
                <button onclick="getSecret()">Receive</button>
            </div>

            <div class="section">
                <h3>List All Secrets (Requires Bearer Token)</h3>
                <input type="text" id="token" placeholder="Bearer token" style="width: 300px;">
                <button onclick="listSecrets()">List</button>
            </div>

            <div id="response" class="response" style="display:none;"></div>
        </div>

        <script>
            function showResponse(data) {
                const el = document.getElementById('response');
                el.style.display = 'block';
                el.textContent = JSON.stringify(data, null, 2);
            }

            async function setSecret() {
                const name = document.getElementById('setName').value;
                const value = document.getElementById('setValue').value;
                try {
                    const res = await fetch('/secrets', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({name, value})
                    });
                    const data = await res.json();
                    showResponse(data);
                } catch (e) {
                    showResponse({error: e.message});
                }
            }

            async function getSecret() {
                const name = document.getElementById('getName').value;
                try {
                    const res = await fetch(`/secrets/${name}`);
                    const data = await res.json();
                    showResponse(data);
                } catch (e) {
                    showResponse({error: e.message});
                }
            }

            async function listSecrets() {
                const token = document.getElementById('token').value;
                try {
                    const res = await fetch('/api/secrets', {
                        headers: {'Authorization': `Bearer ${token}`}
                    });
                    const data = await res.json();
                    showResponse(data);
                } catch (e) {
                    showResponse({error: e.message});
                }
            }
        </script>
    </body>
    </html>
    """


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    kv_client = get_keyvault_client()
    return HealthResponse(
        status="healthy",
        keyvault=kv_client.vault_url,
        version="1.0.0"
    )


@app.post(
    "/secrets",
    response_model=SecretResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update a secret",
    description="Set a secret in Azure KeyVault. Button: 'Send'"
)
async def create_secret(
    secret: SecretCreate,
    kv_client: KeyVaultClient = Depends(get_keyvault_client)
):
    """
    Create or update a secret in KeyVault.

    Requires: Key Vault Secrets Officer role
    """
    try:
        version = kv_client.set_secret(secret.name, secret.value)
        logger.info(f"Secret created: {secret.name}")
        return SecretResponse(
            name=secret.name,
            value=secret.value,
            version=version
        )
    except AzureError as e:
        logger.error(f"Failed to set secret {secret.name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set secret: {str(e)}"
        )


@app.get(
    "/secrets/{name}",
    response_model=SecretResponse,
    summary="Get a secret",
    description="Retrieve a secret from Azure KeyVault. Button: 'Receive'"
)
async def get_secret(
    name: str,
    kv_client: KeyVaultClient = Depends(get_keyvault_client)
):
    """
    Get a secret from KeyVault.

    Requires: Key Vault Secrets User role
    """
    try:
        value, version = kv_client.get_secret(name)
        logger.info(f"Secret retrieved: {name}")
        return SecretResponse(
            name=name,
            value=value,
            version=version
        )
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Secret '{name}' not found"
        )
    except AzureError as e:
        logger.error(f"Failed to get secret {name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get secret: {str(e)}"
        )


@app.get(
    "/api/secrets",
    response_model=SecretListResponse,
    summary="List all secrets (protected)",
    description="List all secret names. Requires Bearer token authentication."
)
async def list_secrets(
    token: str = Depends(verify_token),
    kv_client: KeyVaultClient = Depends(get_keyvault_client)
):
    """
    List all secrets in KeyVault.

    Requires: Bearer token authentication + Key Vault Secrets User role
    """
    try:
        secrets = kv_client.list_secrets()
        logger.info(f"Listed {len(secrets)} secrets")
        return SecretListResponse(
            secrets=secrets,
            count=len(secrets)
        )
    except AzureError as e:
        logger.error(f"Failed to list secrets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list secrets: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

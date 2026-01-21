"""Azure KeyVault client wrapper with caching and error handling."""

import os
import logging
from functools import lru_cache
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.core.exceptions import ResourceNotFoundError, AzureError

logger = logging.getLogger(__name__)


class KeyVaultClient:
    """Wrapper for Azure KeyVault SecretClient with production-ready patterns."""

    def __init__(self, vault_url: str | None = None):
        """
        Initialize KeyVault client.

        Args:
            vault_url: KeyVault URL (e.g., https://myvault.vault.azure.net/)
                      Falls back to KEYVAULT_URL environment variable.
        """
        self.vault_url = vault_url or os.getenv("KEYVAULT_URL")
        if not self.vault_url:
            raise ValueError("KeyVault URL not provided. Set KEYVAULT_URL env var.")

        # DefaultAzureCredential works with:
        # - Managed Identity (in Azure)
        # - Azure CLI (local development with `az login`)
        # - Environment variables (service principal)
        self.credential = DefaultAzureCredential()
        self.client = SecretClient(
            vault_url=self.vault_url,
            credential=self.credential
        )
        logger.info(f"KeyVault client initialized for: {self.vault_url}")

    @lru_cache(maxsize=128)
    def get_secret(self, name: str) -> tuple[str, str]:
        """
        Get secret value with caching.

        Args:
            name: Secret name

        Returns:
            Tuple of (value, version)

        Raises:
            ResourceNotFoundError: Secret not found
            AzureError: Other Azure errors
        """
        try:
            secret = self.client.get_secret(name)
            logger.info(f"Retrieved secret: {name}")
            return secret.value, secret.properties.version
        except ResourceNotFoundError:
            logger.warning(f"Secret not found: {name}")
            raise
        except AzureError as e:
            logger.error(f"Azure error retrieving secret {name}: {e}")
            raise

    def set_secret(self, name: str, value: str) -> str:
        """
        Set secret value (requires Key Vault Secrets Officer role).

        Args:
            name: Secret name
            value: Secret value

        Returns:
            Secret version

        Raises:
            AzureError: Azure operation failed
        """
        try:
            # Clear cache for this secret name
            self.get_secret.cache_clear()

            secret = self.client.set_secret(name, value)
            logger.info(f"Set secret: {name}")
            return secret.properties.version
        except AzureError as e:
            logger.error(f"Azure error setting secret {name}: {e}")
            raise

    def list_secrets(self) -> list[str]:
        """
        List all secret names (not values).

        Returns:
            List of secret names

        Raises:
            AzureError: Azure operation failed
        """
        try:
            secrets = self.client.list_properties_of_secrets()
            secret_names = [s.name for s in secrets]
            logger.info(f"Listed {len(secret_names)} secrets")
            return secret_names
        except AzureError as e:
            logger.error(f"Azure error listing secrets: {e}")
            raise

    def delete_secret(self, name: str) -> None:
        """
        Delete secret (soft delete, recoverable for 90 days).

        Args:
            name: Secret name

        Raises:
            AzureError: Azure operation failed
        """
        try:
            # Clear cache
            self.get_secret.cache_clear()

            self.client.begin_delete_secret(name).wait()
            logger.info(f"Deleted secret: {name}")
        except AzureError as e:
            logger.error(f"Azure error deleting secret {name}: {e}")
            raise


# Singleton instance
_keyvault_client: KeyVaultClient | None = None


def get_keyvault_client() -> KeyVaultClient:
    """
    Get or create KeyVault client singleton.

    Returns:
        KeyVaultClient instance
    """
    global _keyvault_client
    if _keyvault_client is None:
        _keyvault_client = KeyVaultClient()
    return _keyvault_client

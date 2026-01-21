"""Pydantic models for API requests and responses."""

from pydantic import BaseModel, Field


class SecretCreate(BaseModel):
    """Model for creating a new secret."""

    name: str = Field(..., min_length=1, max_length=127, description="Secret name")
    value: str = Field(..., min_length=1, description="Secret value")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "database-password",
                "value": "SuperSecret123!"
            }
        }


class SecretResponse(BaseModel):
    """Model for secret response."""

    name: str
    value: str
    version: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "database-password",
                "value": "SuperSecret123!",
                "version": "abc123"
            }
        }


class SecretListResponse(BaseModel):
    """Model for listing secrets."""

    secrets: list[str]
    count: int

    class Config:
        json_schema_extra = {
            "example": {
                "secrets": ["database-password", "api-key", "jwt-secret"],
                "count": 3
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    keyvault: str | None = None
    version: str = "1.0.0"

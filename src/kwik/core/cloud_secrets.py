"""
Cloud secrets providers for AWS, Azure, and GCP.

This module provides implementations for major cloud secret management services,
with lazy loading of cloud SDK dependencies.
"""

from __future__ import annotations

import logging
from typing import Any

from kwik.core.secrets import SecretProvider, SecretResolutionError

logger = logging.getLogger(__name__)


class AWSSecretsProvider(SecretProvider):
    """
    AWS Secrets Manager provider.

    Supports secret:// URI format: secret://aws/region/secret-name
    or secret://aws/secret-name (uses default region)
    """

    def __init__(self, region: str | None = None, profile: str | None = None) -> None:
        """
        Initialize AWS Secrets Manager provider.

        Args:
            region: AWS region (defaults to boto3 default)
            profile: AWS profile name (defaults to boto3 default)

        """
        self.region = region
        self.profile = profile
        self._client = None

    def _get_client(self):
        """Lazy initialization of boto3 client."""
        if self._client is None:
            try:
                import boto3  # noqa: PLC0415

                session_kwargs = {}
                if self.profile:
                    session_kwargs["profile_name"] = self.profile

                session = boto3.Session(**session_kwargs)

                client_kwargs = {}
                if self.region:
                    client_kwargs["region_name"] = self.region

                self._client = session.client("secretsmanager", **client_kwargs)

            except ImportError as e:
                msg = "boto3 is required for AWS Secrets Manager. Install with: pip install boto3"
                raise SecretResolutionError(msg) from e
            except Exception as e:
                msg = f"Failed to create AWS Secrets Manager client: {e}"
                raise SecretResolutionError(msg) from e

        return self._client

    def get_secret(self, secret_name: str, **kwargs: Any) -> str:
        """Get secret from AWS Secrets Manager."""
        try:
            client = self._get_client()

            # Handle region in secret name (e.g., "us-west-2/my-secret")
            if "/" in secret_name and not secret_name.startswith("arn:"):
                parts = secret_name.split("/", 1)
                if len(parts) == 2 and len(parts[0]) > 2:  # Likely region/secret format
                    region, actual_secret_name = parts
                    # Create region-specific client
                    import boto3  # noqa: PLC0415

                    session_kwargs = {}
                    if self.profile:
                        session_kwargs["profile_name"] = self.profile
                    session = boto3.Session(**session_kwargs)
                    client = session.client("secretsmanager", region_name=region)
                    secret_name = actual_secret_name

            response = client.get_secret_value(SecretId=secret_name)

            # Return the secret string
            if "SecretString" in response:
                return response["SecretString"]
            # Binary secret (base64 decode)
            import base64

            return base64.b64decode(response["SecretBinary"]).decode("utf-8")

        except Exception as e:
            msg = f"Failed to retrieve AWS secret '{secret_name}': {e}"
            raise SecretResolutionError(msg) from e

    def supports_uri(self, uri: str) -> bool:
        """Support secret://aws/ URIs."""
        return uri.startswith("secret://aws/")

    @property
    def provider_name(self) -> str:
        """Provider name."""
        return "AWS Secrets Manager"

    @property
    def is_available(self) -> bool:
        """Check if AWS credentials are available."""
        try:
            client = self._get_client()
            # Try a simple operation to verify credentials
            client.list_secrets(MaxResults=1)
            return True
        except Exception:
            return False


class AzureKeyVaultProvider(SecretProvider):
    """
    Azure Key Vault provider.

    Supports secret:// URI format: secret://azure/vault-name/secret-name
    """

    def __init__(self, credential=None) -> None:
        """
        Initialize Azure Key Vault provider.

        Args:
            credential: Azure credential object (defaults to DefaultAzureCredential)

        """
        self.credential = credential
        self._clients = {}  # Cache clients by vault URL

    def _get_client(self, vault_name: str):
        """Lazy initialization of Azure Key Vault client."""
        vault_url = f"https://{vault_name}.vault.azure.net/"

        if vault_url not in self._clients:
            try:
                from azure.identity import DefaultAzureCredential  # noqa: PLC0415
                from azure.keyvault.secrets import SecretClient  # noqa: PLC0415

                credential = self.credential or DefaultAzureCredential()
                self._clients[vault_url] = SecretClient(vault_url=vault_url, credential=credential)

            except ImportError as e:
                msg = (
                    "azure-keyvault-secrets and azure-identity are required for Azure Key Vault. "
                    "Install with: pip install azure-keyvault-secrets azure-identity"
                )
                raise SecretResolutionError(msg) from e
            except Exception as e:
                msg = f"Failed to create Azure Key Vault client: {e}"
                raise SecretResolutionError(msg) from e

        return self._clients[vault_url]

    def get_secret(self, secret_name: str, **kwargs: Any) -> str:
        """Get secret from Azure Key Vault."""
        # Parse vault/secret format
        if "/" not in secret_name:
            msg = f"Azure secret name must be in format 'vault-name/secret-name', got: {secret_name}"
            raise SecretResolutionError(msg)

        vault_name, actual_secret_name = secret_name.split("/", 1)

        try:
            client = self._get_client(vault_name)

            # Get secret version (defaults to latest)
            version = kwargs.get("version")
            secret = client.get_secret(actual_secret_name, version=version)

            return secret.value

        except Exception as e:
            msg = f"Failed to retrieve Azure Key Vault secret '{secret_name}': {e}"
            raise SecretResolutionError(msg) from e

    def supports_uri(self, uri: str) -> bool:
        """Support secret://azure/ URIs."""
        return uri.startswith("secret://azure/")

    @property
    def provider_name(self) -> str:
        """Provider name."""
        return "Azure Key Vault"

    @property
    def is_available(self) -> bool:
        """Check if Azure credentials are available."""
        try:
            from azure.identity import DefaultAzureCredential  # noqa: PLC0415

            credential = self.credential or DefaultAzureCredential()
            # Try to get a token to verify credentials
            token = credential.get_token("https://vault.azure.net/.default")
            return token is not None
        except Exception:
            return False


class GCPSecretManagerProvider(SecretProvider):
    """
    Google Cloud Secret Manager provider.

    Supports secret:// URI format: secret://gcp/project-id/secret-name
    or secret://gcp/secret-name (uses default project)
    """

    def __init__(self, project_id: str | None = None) -> None:
        """
        Initialize GCP Secret Manager provider.

        Args:
            project_id: GCP project ID (defaults to application default)

        """
        self.project_id = project_id
        self._client = None

    def _get_client(self):
        """Lazy initialization of GCP Secret Manager client."""
        if self._client is None:
            try:
                from google.cloud import secretmanager  # noqa: PLC0415

                self._client = secretmanager.SecretManagerServiceClient()

                # If no project specified, try to get from application default
                if not self.project_id:
                    try:
                        import google.auth  # noqa: PLC0415

                        _, project = google.auth.default()
                        self.project_id = project
                    except Exception:
                        pass  # Will fail later with better error message

            except ImportError as e:
                msg = (
                    "google-cloud-secret-manager is required for GCP Secret Manager. "
                    "Install with: pip install google-cloud-secret-manager"
                )
                raise SecretResolutionError(msg) from e
            except Exception as e:
                msg = f"Failed to create GCP Secret Manager client: {e}"
                raise SecretResolutionError(msg) from e

        return self._client

    def get_secret(self, secret_name: str, **kwargs: Any) -> str:
        """Get secret from GCP Secret Manager."""
        try:
            client = self._get_client()

            # Handle project/secret format
            if "/" in secret_name:
                parts = secret_name.split("/", 1)
                if len(parts) == 2:
                    project_id, actual_secret_name = parts
                else:
                    project_id = self.project_id
                    actual_secret_name = secret_name
            else:
                project_id = self.project_id
                actual_secret_name = secret_name

            if not project_id:
                msg = "GCP project ID is required. Set via provider init or application default credentials"
                raise SecretResolutionError(msg)

            # Get secret version (defaults to latest)
            version = kwargs.get("version", "latest")

            # Build the resource name
            name = f"projects/{project_id}/secrets/{actual_secret_name}/versions/{version}"

            response = client.access_secret_version(request={"name": name})

            return response.payload.data.decode("utf-8")

        except Exception as e:
            msg = f"Failed to retrieve GCP secret '{secret_name}': {e}"
            raise SecretResolutionError(msg) from e

    def supports_uri(self, uri: str) -> bool:
        """Support secret://gcp/ URIs."""
        return uri.startswith("secret://gcp/")

    @property
    def provider_name(self) -> str:
        """Provider name."""
        return "Google Cloud Secret Manager"

    @property
    def is_available(self) -> bool:
        """Check if GCP credentials are available."""
        try:
            client = self._get_client()

            if not self.project_id:
                return False

            # Try to list secrets to verify credentials and project access
            parent = f"projects/{self.project_id}"
            list(client.list_secrets(request={"parent": parent, "page_size": 1}))
            return True
        except Exception:
            return False


def register_cloud_providers(
    secrets_manager,
    aws_region: str | None = None,
    aws_profile: str | None = None,
    azure_credential=None,
    gcp_project_id: str | None = None,
) -> None:
    """
    Register cloud providers with a secrets manager.

    Args:
        secrets_manager: SecretsManager instance
        aws_region: AWS region for AWS provider
        aws_profile: AWS profile for AWS provider
        azure_credential: Azure credential for Azure provider
        gcp_project_id: GCP project ID for GCP provider

    """
    # Add AWS provider
    aws_provider = AWSSecretsProvider(region=aws_region, profile=aws_profile)
    if aws_provider.is_available:
        secrets_manager.add_provider(aws_provider)
        logger.info("Added AWS Secrets Manager provider")
    else:
        logger.debug("AWS Secrets Manager provider not available (credentials not configured)")

    # Add Azure provider
    azure_provider = AzureKeyVaultProvider(credential=azure_credential)
    if azure_provider.is_available:
        secrets_manager.add_provider(azure_provider)
        logger.info("Added Azure Key Vault provider")
    else:
        logger.debug("Azure Key Vault provider not available (credentials not configured)")

    # Add GCP provider
    gcp_provider = GCPSecretManagerProvider(project_id=gcp_project_id)
    if gcp_provider.is_available:
        secrets_manager.add_provider(gcp_provider)
        logger.info("Added GCP Secret Manager provider")
    else:
        logger.debug("GCP Secret Manager provider not available (credentials not configured)")

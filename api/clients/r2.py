"""Cloudflare R2 storage client using AWS S3 signature v4."""

import hashlib
import hmac
from datetime import UTC
from datetime import datetime as dt
from typing import BinaryIO
from urllib.parse import quote

import httpx
from config import settings


class R2Client:
    """Client for Cloudflare R2 object storage (S3-compatible)."""

    def __init__(
        self,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        account_id: str | None = None,
        bucket_name: str | None = None,
    ) -> None:
        """Initialize the R2 client.

        Args:
            access_key_id: R2 access key ID. If not provided, uses settings.r2_access_key_id
            secret_access_key: R2 secret access key
            account_id: Cloudflare account ID
            bucket_name: R2 bucket name
        """
        self.access_key_id = access_key_id or settings.r2_access_key_id
        self.secret_access_key = secret_access_key or settings.r2_secret_access_key
        self.account_id = account_id or settings.cloudflare_account_id
        self.bucket_name = bucket_name or settings.r2_bucket_name
        self.endpoint_url = f"https://{self.account_id}.r2.cloudflarestorage.com"

    def _sign_request(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        payload: bytes,
        timestamp: dt,
    ) -> dict[str, str]:
        """Sign S3 request using AWS Signature Version 4."""
        region = "auto"
        service = "s3"

        # Create canonical request
        canonical_uri = quote(path, safe="/")
        canonical_querystring = ""
        canonical_headers = "\n".join(f"{k.lower()}:{v}" for k, v in sorted(headers.items())) + "\n"
        signed_headers = ";".join(sorted(k.lower() for k in headers.keys()))
        payload_hash = hashlib.sha256(payload).hexdigest()

        canonical_request = (
            f"{method}\n{canonical_uri}\n{canonical_querystring}\n"
            f"{canonical_headers}\n{signed_headers}\n{payload_hash}"
        )

        # Create string to sign
        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{timestamp.strftime('%Y%m%d')}/{region}/{service}/aws4_request"
        string_to_sign = (
            f"{algorithm}\n{timestamp.strftime('%Y%m%dT%H%M%SZ')}\n{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode()).hexdigest()}"
        )

        # Calculate signature
        def _sign(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

        k_date = _sign(f"AWS4{self.secret_access_key}".encode(), timestamp.strftime("%Y%m%d"))
        k_region = _sign(k_date, region)
        k_service = _sign(k_region, service)
        k_signing = _sign(k_service, "aws4_request")
        signature = hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()

        # Add authorization header
        authorization = (
            f"{algorithm} Credential={self.access_key_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        headers["Authorization"] = authorization
        return headers

    async def upload_file(
        self,
        file_data: bytes | BinaryIO,
        key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload a file to R2 using direct HTTP PUT with AWS signature v4.

        Args:
            file_data: File content as bytes or file-like object
            key: Object key (path) in the bucket
            content_type: MIME type of the file

        Returns:
            Public URL of the uploaded file

        Raises:
            Exception: If upload fails
        """
        if not key:
            raise ValueError("Key cannot be empty")

        # Convert BinaryIO to bytes if needed
        if not isinstance(file_data, bytes):
            file_data = file_data.read()

        # Build request
        timestamp = dt.now(UTC)
        url = f"{self.endpoint_url}/{self.bucket_name}/{key}"
        headers = {
            "Host": f"{self.account_id}.r2.cloudflarestorage.com",
            "Content-Type": content_type,
            "x-amz-date": timestamp.strftime("%Y%m%dT%H%M%SZ"),
            "x-amz-content-sha256": hashlib.sha256(file_data).hexdigest(),
        }

        # Sign the request
        headers = self._sign_request(
            "PUT", f"/{self.bucket_name}/{key}", headers, file_data, timestamp
        )

        try:
            # Use longer timeout for large file uploads (5 minutes)
            timeout = httpx.Timeout(300.0, connect=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.put(url, content=file_data, headers=headers)
                response.raise_for_status()

            public_url = f"{settings.r2_public_url}/{key}"
            return public_url

        except Exception as e:
            raise Exception(f"Failed to upload file to R2: {e}") from e

    async def delete_file(self, key: str) -> None:
        """Delete a file from R2 using direct HTTP DELETE with AWS signature v4.

        Args:
            key: Object key (path) in the bucket

        Raises:
            Exception: If deletion fails
        """
        if not key:
            raise ValueError("Key cannot be empty")

        # Build request
        timestamp = dt.now(UTC)
        url = f"{self.endpoint_url}/{self.bucket_name}/{key}"
        headers = {
            "Host": f"{self.account_id}.r2.cloudflarestorage.com",
            "x-amz-date": timestamp.strftime("%Y%m%dT%H%M%SZ"),
            "x-amz-content-sha256": hashlib.sha256(b"").hexdigest(),
        }

        # Sign the request
        headers = self._sign_request(
            "DELETE", f"/{self.bucket_name}/{key}", headers, b"", timestamp
        )

        try:
            # Use reasonable timeout for delete operations
            timeout = httpx.Timeout(30.0, connect=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.delete(url, headers=headers)
                response.raise_for_status()

        except Exception as e:
            raise Exception(f"Failed to delete file from R2: {e}") from e

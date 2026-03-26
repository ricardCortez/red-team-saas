"""S3 Report Storage Service — Phase 14

Provides upload, download (presigned URL), listing, and deletion of
report files stored in AWS S3 with AES-256 server-side encryption.
"""
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_CONTENT_TYPES = {
    "pdf": "application/pdf",
    "html": "text/html; charset=utf-8",
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "json": "application/json",
}


class S3ReportStorage:
    """Wraps boto3 S3 operations for report file management."""

    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        import boto3
        self.bucket_name = bucket_name
        self.s3 = boto3.client("s3", region_name=region)

    # ── Public API ──────────────────────────────────────────────────────────

    def upload_report(
        self,
        report_id,
        content: bytes,
        format: str = None,
        version: int = 1,
        content_type: Optional[str] = None,
        fmt: str = None,
    ) -> Dict:
        """
        Upload report bytes to S3.

        :returns: {s3_key, file_size_bytes, checksum_sha256, url}
        """
        fmt_value = format or fmt or "pdf"
        s3_key = f"reports/{report_id}/v{version}/report.{fmt_value}"
        checksum = hashlib.sha256(content).hexdigest()
        ct = content_type or _CONTENT_TYPES.get(fmt_value, "application/octet-stream")

        metadata = {
            "report-id": str(report_id),
            "version": str(version),
            "format": fmt_value,
            "uploaded-at": datetime.utcnow().isoformat(),
            "checksum": checksum,
        }

        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=content,
            ContentType=ct,
            Metadata=metadata,
            ServerSideEncryption="AES256",
        )

        url = self._presigned_url(s3_key)
        return {
            "s3_key": s3_key,
            "file_size_bytes": len(content),
            "checksum_sha256": checksum,
            "url": url,
            "presigned_url": url,
        }

    def download_report(self, s3_key: str, expires_in: int = 3600) -> Dict:
        """Return a presigned download URL for the given S3 key."""
        return {
            "url": self._presigned_url(s3_key, expires_in),
            "expires_in": expires_in,
        }

    def download_url(self, s3_key: str, expires_in: int = 3600) -> Dict:
        """Alias for download_report."""
        return self.download_report(s3_key, expires_in)

    def list_versions(self, report_id: int) -> List[Dict]:
        """List all S3 objects for a given report (all versions/formats)."""
        prefix = f"reports/{report_id}/"
        response = self.s3.list_objects_v2(
            Bucket=self.bucket_name, Prefix=prefix
        )
        return [
            {
                "key": obj["Key"],
                "size_bytes": obj["Size"],
                "last_modified": obj["LastModified"].isoformat(),
            }
            for obj in response.get("Contents", [])
        ]

    def delete_object(self, s3_key: str) -> None:
        """Delete a single object from S3."""
        self.s3.delete_object(Bucket=self.bucket_name, Key=s3_key)

    def delete_report(self, s3_key_or_report_id) -> int:
        """Delete S3 object(s) for a report. Accepts an s3_key string or report_id."""
        if isinstance(s3_key_or_report_id, str):
            self.s3.delete_object(Bucket=self.bucket_name, Key=s3_key_or_report_id)
            return 1
        versions = self.list_versions(s3_key_or_report_id)
        for obj in versions:
            self.delete_object(obj["key"])
        return len(versions)

    # ── Private ─────────────────────────────────────────────────────────────

    def _presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": s3_key},
            ExpiresIn=expires_in,
        )

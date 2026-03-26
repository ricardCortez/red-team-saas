"""HMAC-SHA256 webhook request signing — Phase 17"""
import hashlib
import hmac
import json
import time


class RequestSigner:

    @staticmethod
    def sign_payload(payload: dict, secret: str) -> str:
        """
        Sign a dict payload with HMAC-SHA256.

        Returns the hex digest.
        """
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hmac.new(
            secret.encode("utf-8"),
            payload_json.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def create_signed_webhook(
        payload: dict,
        secret: str,
        timestamp: int = None,
    ) -> dict:
        """
        Wrap a payload with a timestamp and HMAC-SHA256 signature.

        Returns::

            {
                "payload": {"payload": ..., "timestamp": ...},
                "signature": "<hex>",
                "algorithm": "sha256",
            }
        """
        if timestamp is None:
            timestamp = int(time.time())

        signed_payload = {"payload": payload, "timestamp": timestamp}
        signature = RequestSigner.sign_payload(signed_payload, secret)

        return {
            "payload": signed_payload,
            "signature": signature,
            "algorithm": "sha256",
        }

    @staticmethod
    def verify_webhook_signature(
        payload: dict,
        signature: str,
        secret: str,
        timestamp: int = None,
        tolerance_seconds: int = 300,
    ) -> tuple:
        """
        Verify a webhook signature.

        Returns ``(valid: bool, error: str | None)``.
        """
        # Timestamp freshness check
        if timestamp is not None:
            now = int(time.time())
            if abs(now - timestamp) > tolerance_seconds:
                return (False, f"Timestamp too old (>{tolerance_seconds}s)")

        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        expected = hmac.new(
            secret.encode("utf-8"),
            payload_json.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected):
            return (False, "Signature mismatch")

        return (True, None)

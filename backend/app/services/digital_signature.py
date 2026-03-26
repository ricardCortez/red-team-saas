"""Digital Signature Service — Phase 14

Signs and verifies reports using X.509 certificates (RSA-SHA256).
Provides self-signed certificate generation for development/testing.
"""
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class DigitalSignatureManager:
    """Manages X.509 digital signatures for ReportV2 instances."""

    def __init__(self, db: Session):
        self.db = db

    def sign_report(
        self,
        report_id: int,
        signer_id: int,
        certificate_pem: bytes,
        private_key_pem: bytes,
        private_key_password: Optional[bytes] = None,
        timestamp_authority_url: Optional[str] = None,
    ):
        """
        Digitally sign a report using an X.509 certificate.

        :param report_id: ID of the ReportV2 to sign.
        :param signer_id: User ID of the signer.
        :param certificate_pem: PEM-encoded X.509 certificate bytes.
        :param private_key_pem: PEM-encoded private key bytes.
        :param private_key_password: Optional passphrase for the private key.
        :param timestamp_authority_url: Optional TSA URL.
        :returns: DigitalSignature ORM instance.
        """
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from app.models.report import DigitalSignature, ReportV2, ReportStatusV2

        report = self.db.query(ReportV2).filter(ReportV2.id == report_id).first()
        if not report:
            raise ValueError(f"Report {report_id} not found")

        cert = x509.load_pem_x509_certificate(certificate_pem)
        private_key = serialization.load_pem_private_key(
            private_key_pem, password=private_key_password
        )

        content_to_sign = self._serialize_report(report).encode("utf-8")
        content_hash = hashlib.sha256(content_to_sign).hexdigest()

        signature_value = private_key.sign(
            content_to_sign,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )

        # Strip timezone info for compatibility with naive datetime storage
        not_before = cert.not_valid_before_utc.replace(tzinfo=None) if hasattr(cert, "not_valid_before_utc") else cert.not_valid_before
        not_after = cert.not_valid_after_utc.replace(tzinfo=None) if hasattr(cert, "not_valid_after_utc") else cert.not_valid_after

        digital_sig = DigitalSignature(
            report_id=report_id,
            signer_id=signer_id,
            certificate_pem=certificate_pem,
            certificate_issuer=cert.issuer.rfc4514_string(),
            certificate_subject=cert.subject.rfc4514_string(),
            certificate_valid_from=not_before,
            certificate_valid_to=not_after,
            signature_algorithm="RSA-SHA256",
            signature_value=signature_value,
            signed_content_hash=content_hash,
            timestamp_authority=timestamp_authority_url,
            is_valid=True,
        )
        self.db.add(digital_sig)

        # Update report
        report.signed_by = signer_id
        report.signed_at = datetime.utcnow()
        report.signature_certificate_fingerprint = hashlib.sha256(certificate_pem).hexdigest()
        report.signature_metadata = {
            "algorithm": "RSA-SHA256",
            "issuer": cert.issuer.rfc4514_string(),
            "valid_from": not_before.isoformat(),
            "valid_to": not_after.isoformat(),
        }
        report.status = ReportStatusV2.signed

        self.db.commit()
        self.db.refresh(digital_sig)
        return digital_sig

    def verify_signature(self, signature_id: int) -> Dict:
        """
        Verify the cryptographic validity of a stored signature.

        Returns a dict with keys: valid (bool), reason (str), verified_at (str).
        """
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from app.models.report import DigitalSignature

        sig = self.db.query(DigitalSignature).filter(
            DigitalSignature.id == signature_id
        ).first()
        if not sig:
            return {"valid": False, "reason": "Signature not found"}

        try:
            cert = x509.load_pem_x509_certificate(sig.certificate_pem)
        except Exception as exc:
            return {"valid": False, "reason": f"Cannot parse certificate: {exc}"}

        # Certificate expiry check
        now = datetime.utcnow()
        not_before = cert.not_valid_before_utc.replace(tzinfo=None) if hasattr(cert, "not_valid_before_utc") else cert.not_valid_before
        not_after = cert.not_valid_after_utc.replace(tzinfo=None) if hasattr(cert, "not_valid_after_utc") else cert.not_valid_after
        if now < not_before or now > not_after:
            result = {"valid": False, "reason": "Certificate expired or not yet valid"}
            self._save_verification(sig, result)
            return result

        # Content integrity check
        content = self._serialize_report(sig.report).encode("utf-8")
        current_hash = hashlib.sha256(content).hexdigest()
        if current_hash != sig.signed_content_hash:
            result = {"valid": False, "reason": "Report content has been modified after signing"}
            self._save_verification(sig, result)
            return result

        # Cryptographic signature check
        try:
            cert.public_key().verify(
                sig.signature_value,
                content,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            result = {
                "valid": True,
                "reason": "Signature is valid",
                "verified_at": datetime.utcnow().isoformat(),
                "certificate_issuer": sig.certificate_issuer,
                "certificate_subject": sig.certificate_subject,
            }
        except Exception as exc:
            result = {"valid": False, "reason": f"Cryptographic verification failed: {exc}"}

        self._save_verification(sig, result)
        return result

    def generate_self_signed_cert(
        self,
        common_name: str,
        organization: str = "Red Team",
        country: str = "US",
        days_valid: int = 365,
    ) -> Tuple[bytes, bytes]:
        """
        Generate a self-signed X.509 certificate for testing/development.

        :returns: (certificate_pem, private_key_pem)
        """
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, country),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=days_valid))
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None), critical=True
            )
            .sign(private_key, hashes.SHA256())
        )

        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return cert_pem, key_pem

    # ── Private helpers ─────────────────────────────────────────────────────

    def _serialize_report(self, report) -> str:
        """Canonical JSON serialisation of report fields used for signing."""
        data = {
            "id": report.id,
            "project_id": report.project_id,
            "title": report.title,
            "generated_at": report.generated_at.isoformat() if report.generated_at else None,
            "findings_count": report.findings_count,
            "summary": report.summary_metadata,
        }
        return json.dumps(data, sort_keys=True, default=str)

    def _save_verification(self, sig, result: Dict) -> None:
        sig.is_valid = result.get("valid", False)
        sig.verification_result = result
        self.db.commit()

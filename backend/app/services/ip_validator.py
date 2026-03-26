"""IP whitelist / blacklist validation — Phase 17"""
import ipaddress

from sqlalchemy.orm import Session

from app.models.security import IPWhitelist, RateLimitConfig


class IPValidator:

    @staticmethod
    def is_ip_allowed(user_id: int, client_ip: str, db: Session) -> tuple:
        """
        Validate whether *client_ip* is allowed for *user_id*.

        Returns ``(allowed: bool, reason: str)``.

        Logic:
        1. Blacklist check first — any match → denied.
        2. Whitelist check — if whitelist is non-empty, IP must match.
        3. No restrictions → allowed.
        """
        config = (
            db.query(RateLimitConfig)
            .filter(RateLimitConfig.user_id == user_id)
            .first()
        )

        if not config:
            return (True, "No IP restrictions configured")

        try:
            client_ip_obj = ipaddress.ip_address(client_ip)
        except ValueError:
            return (False, f"Invalid IP address: {client_ip}")

        # Blacklist
        for cidr in (config.ip_blacklist or []):
            try:
                if client_ip_obj in ipaddress.ip_network(cidr, strict=False):
                    return (False, f"IP {client_ip} is blacklisted ({cidr})")
            except ValueError:
                continue

        # Whitelist
        whitelist = config.ip_whitelist or []
        if whitelist:
            for cidr in whitelist:
                try:
                    if client_ip_obj in ipaddress.ip_network(cidr, strict=False):
                        return (True, f"IP in whitelist ({cidr})")
                except ValueError:
                    continue
            return (False, f"IP {client_ip} not in whitelist")

        return (True, "IP allowed")

    @staticmethod
    def add_whitelist_ip(
        user_id: int,
        cidr: str,
        db: Session,
        description: str = None,
    ) -> dict:
        """Add a CIDR entry to the IP whitelist table."""
        try:
            ipaddress.ip_network(cidr, strict=False)
        except ValueError as exc:
            return {"success": False, "error": f"Invalid CIDR: {exc}"}

        entry = IPWhitelist(
            user_id=user_id,
            cidr_block=cidr,
            description=description,
            created_by=user_id,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)

        return {"success": True, "id": entry.id, "cidr": cidr}

    @staticmethod
    def remove_whitelist_ip(entry_id: int, user_id: int, db: Session) -> bool:
        """Soft-disable a whitelist entry. Returns True on success."""
        entry = (
            db.query(IPWhitelist)
            .filter(IPWhitelist.id == entry_id, IPWhitelist.user_id == user_id)
            .first()
        )
        if not entry:
            return False

        entry.is_enabled = False
        db.commit()
        return True

    @staticmethod
    def validate_cidr(cidr: str) -> bool:
        """Return True if *cidr* is a valid network address."""
        try:
            ipaddress.ip_network(cidr, strict=False)
            return True
        except ValueError:
            return False

"""ScopeValidator – checks whether a target string is within a project's authorised scope."""
import ipaddress
from urllib.parse import urlparse
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.target import Target, TargetStatus, TargetType


class ScopeValidator:
    """
    Validates that a scan target is covered by at least one in-scope Target
    entry for the given project.

    Supported target types:
      - ip       : exact IP match
      - cidr     : IP contained in network
      - ip_range : IP within start-end range ("192.168.1.1-192.168.1.50")
      - hostname : exact match, or wildcard prefix (*.example.com)
      - url      : netloc (host[:port]) match after parsing both sides
    """

    def __init__(self, db: Session, project_id: int):
        self.db = db
        self.project_id = project_id
        self._in_scope: Optional[List[Target]] = None

    @property
    def in_scope_targets(self) -> List[Target]:
        if self._in_scope is None:
            self._in_scope = (
                self.db.query(Target)
                .filter(
                    Target.project_id == self.project_id,
                    Target.status == TargetStatus.in_scope,
                )
                .all()
            )
        return self._in_scope

    def is_allowed(self, target: str) -> bool:
        """Return True if *target* is covered by at least one in-scope entry.

        When no scope entries exist, every target is implicitly allowed.
        """
        if not self.in_scope_targets:
            return True

        for scope in self.in_scope_targets:
            if self._matches(target, scope):
                return True
        return False

    # ── private ──────────────────────────────────────────────────────────────

    def _matches(self, target: str, scope: Target) -> bool:
        try:
            if scope.target_type == TargetType.ip:
                return target == scope.value

            elif scope.target_type == TargetType.cidr:
                net = ipaddress.ip_network(scope.value, strict=False)
                return ipaddress.ip_address(target) in net

            elif scope.target_type == TargetType.ip_range:
                start_s, end_s = scope.value.split("-", 1)
                start = ipaddress.ip_address(start_s.strip())
                end   = ipaddress.ip_address(end_s.strip())
                return start <= ipaddress.ip_address(target) <= end

            elif scope.target_type == TargetType.hostname:
                if scope.value.startswith("*."):
                    suffix = scope.value[2:]
                    return target == suffix or target.endswith("." + suffix)
                return target == scope.value

            elif scope.target_type == TargetType.url:
                t_netloc = self._netloc(target)
                s_netloc = self._netloc(scope.value)
                return bool(t_netloc and s_netloc and t_netloc == s_netloc)

        except (ValueError, AttributeError):
            return False
        return False

    @staticmethod
    def _netloc(value: str) -> str:
        if "://" not in value:
            value = "https://" + value
        return urlparse(value).netloc

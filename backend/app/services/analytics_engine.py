"""Analytics Engine — Phase 15

Computes KPIs, project risk scores, tool effectiveness,
and analytics snapshots from DB + Redis data.
"""
import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.analytics import (
    AnalyticsSnapshot,
    KPI,
    KPITypeEnum,
    KPIStatusEnum,
    ProjectRiskScore,
    RiskLevelEnum,
    ToolAnalytics,
    TrendEnum,
)
from app.models.finding import Finding, FindingStatus, Severity

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """Stateless computation engine for Phase 15 analytics."""

    def __init__(self, db: Session, realtime_service=None):
        self.db = db
        self.realtime = realtime_service

    # ── KPI: MTTR ────────────────────────────────────────────────────────────

    def calculate_mttr(self, project_id: int) -> Tuple[Optional[float], float]:
        """
        Mean Time To Remediation in hours.
        Uses updated_at as proxy for resolution time (no dedicated resolved_at column).

        Returns: (mttr_hours | None, trend_percentage)
        """
        resolved = (
            self.db.query(Finding)
            .filter(
                Finding.project_id == project_id,
                Finding.status == FindingStatus.resolved,
            )
            .all()
        )

        if not resolved:
            return None, 0.0

        hours_list = []
        for f in resolved:
            if f.updated_at and f.created_at:
                delta = f.updated_at - f.created_at
                hours_list.append(max(0.0, delta.total_seconds() / 3600))

        if not hours_list:
            return None, 0.0

        mttr = statistics.mean(hours_list)

        # Trend: compare recent 5 to the rest
        trend_pct = 0.0
        if len(hours_list) >= 2:
            split = max(1, len(hours_list) - 5)
            recent = statistics.mean(hours_list[split:])
            prior  = statistics.mean(hours_list[:split])
            if prior > 0:
                trend_pct = ((recent - prior) / prior) * 100

        return round(mttr, 2), round(trend_pct, 2)

    # ── KPI: Remediation Rate ─────────────────────────────────────────────────

    def calculate_remediation_rate(self, project_id: int) -> float:
        """Percentage of findings that have been resolved."""
        total = (
            self.db.query(Finding)
            .filter(Finding.project_id == project_id)
            .count()
        )
        if total == 0:
            return 0.0

        resolved = (
            self.db.query(Finding)
            .filter(
                Finding.project_id == project_id,
                Finding.status == FindingStatus.resolved,
            )
            .count()
        )
        return round((resolved / total) * 100, 2)

    # ── KPI: False Positive Rate ──────────────────────────────────────────────

    def calculate_false_positive_rate(self, project_id: int) -> float:
        """Percentage of findings marked as false positives."""
        total = (
            self.db.query(Finding)
            .filter(Finding.project_id == project_id)
            .count()
        )
        if total == 0:
            return 0.0

        fp = (
            self.db.query(Finding)
            .filter(
                Finding.project_id == project_id,
                Finding.status == FindingStatus.false_positive,
            )
            .count()
        )
        return round((fp / total) * 100, 2)

    # ── Tool Effectiveness ────────────────────────────────────────────────────

    def calculate_tool_effectiveness(
        self, project_id: int, tool_name: str
    ) -> Dict:
        """
        Effectiveness metrics for a single tool:
        - effectiveness_score: 100 − fp_rate (+ critical bonus)
        - false_positive_rate: %
        - findings_by_severity: {critical, high, medium, low, info}
        """
        findings = (
            self.db.query(Finding)
            .filter(
                Finding.project_id == project_id,
                Finding.tool_name == tool_name,
            )
            .all()
        )

        if not findings:
            return {
                "effectiveness_score": 0.0,
                "false_positive_rate": 0.0,
                "true_positive_rate": 0.0,
                "findings_count": 0,
                "severity_breakdown": {},
            }

        total     = len(findings)
        false_pos = sum(1 for f in findings if f.status == FindingStatus.false_positive)
        true_pos  = total - false_pos

        fp_rate = (false_pos / total) * 100
        tp_rate = (true_pos  / total) * 100

        severity_breakdown = {s.value: 0 for s in Severity}
        for f in findings:
            sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            severity_breakdown[sev] = severity_breakdown.get(sev, 0) + 1

        critical_count = severity_breakdown.get("critical", 0)
        # Cap bonus at 20 pts for tools that find critical issues
        critical_bonus = min(20, critical_count * 2)
        effectiveness  = min(100.0, (100 - fp_rate) + critical_bonus * 0.1)

        return {
            "effectiveness_score": round(effectiveness, 2),
            "false_positive_rate": round(fp_rate, 2),
            "true_positive_rate":  round(tp_rate, 2),
            "findings_count":      total,
            "severity_breakdown":  severity_breakdown,
        }

    # ── Project Risk Score ────────────────────────────────────────────────────

    def calculate_risk_score(self, project_id: int) -> ProjectRiskScore:
        """
        Composite 0-100 risk score:
          critical findings  → up to 40 pts
          compliance gap     → up to 30 pts
          remediation lag    → up to 20 pts
          tool coverage      → up to 10 pts

        Higher score = more risk.
        """
        # 1. Critical findings (40%)
        critical_count = (
            self.db.query(Finding)
            .filter(
                Finding.project_id == project_id,
                Finding.severity   == Severity.critical,
                Finding.status     != FindingStatus.resolved,
            )
            .count()
        )
        critical_component = min(40, critical_count * 4)

        # 2. Compliance gap (30%)
        try:
            from app.models.compliance import ComplianceMappingResult
            compliance = (
                self.db.query(ComplianceMappingResult)
                .filter(ComplianceMappingResult.project_id == project_id)
                .order_by(ComplianceMappingResult.created_at.desc())
                .first()
            )
            if compliance:
                gap_pct = 100 - compliance.compliance_score
            else:
                gap_pct = 50.0  # default 50 % gap when no mapping exists
        except Exception:
            gap_pct = 50.0

        compliance_component = round((gap_pct / 100) * 30, 2)

        # 3. Remediation lag (20%): age of oldest open critical/high finding
        old_finding = (
            self.db.query(Finding)
            .filter(
                Finding.project_id == project_id,
                Finding.status.in_([FindingStatus.open, FindingStatus.confirmed]),
                Finding.severity.in_([Severity.critical, Severity.high]),
            )
            .order_by(Finding.created_at.asc())
            .first()
        )
        if old_finding and old_finding.created_at:
            days_lag = (datetime.utcnow() - old_finding.created_at.replace(tzinfo=None)).days
        else:
            days_lag = 0
        remediation_component = min(20, days_lag / 10)

        # 4. Tool coverage (10%) — simplified placeholder
        tool_coverage_pct = 50.0
        tool_component = round((100 - tool_coverage_pct) / 100 * 10, 2)

        overall = int(
            critical_component + compliance_component +
            remediation_component + tool_component
        )
        overall = max(0, min(100, overall))

        # Risk level
        if overall >= 80:
            risk_level = RiskLevelEnum.CRITICAL
        elif overall >= 60:
            risk_level = RiskLevelEnum.HIGH
        elif overall >= 40:
            risk_level = RiskLevelEnum.MEDIUM
        elif overall >= 20:
            risk_level = RiskLevelEnum.LOW
        else:
            risk_level = RiskLevelEnum.MINIMAL

        # Previous score for trend
        prev = (
            self.db.query(ProjectRiskScore)
            .filter(ProjectRiskScore.project_id == project_id)
            .order_by(ProjectRiskScore.calculated_at.desc())
            .first()
        )
        previous_score = prev.overall_score if prev else overall

        rs = ProjectRiskScore(
            project_id       = project_id,
            overall_score    = overall,
            risk_level       = risk_level,
            score_component  = {
                "critical_findings":  int(critical_component),
                "compliance_gap":     int(compliance_component),
                "remediation_lag":    int(remediation_component),
                "tool_coverage":      int(tool_component),
            },
            critical_finding_count      = critical_count,
            days_since_last_remediation = days_lag,
            compliance_gap_percentage   = gap_pct,
            tool_coverage_percentage    = tool_coverage_pct,
            previous_score              = previous_score,
            score_change                = overall - previous_score,
            next_calculation_at         = datetime.utcnow() + timedelta(hours=1),
        )

        self.db.add(rs)
        self.db.commit()
        self.db.refresh(rs)

        # Push to Redis gauge
        if self.realtime:
            self.realtime.set_gauge(str(project_id), "risk_score", overall)

        return rs

    # ── All KPIs ─────────────────────────────────────────────────────────────

    def calculate_all_kpis(self, project_id: int) -> List[KPI]:
        """Calculate and persist all KPIs for a project."""
        kpis: List[KPI] = []

        # MTTR
        mttr_val, trend_pct = self.calculate_mttr(project_id)
        if mttr_val is not None:
            kpi = KPI(
                project_id         = project_id,
                kpi_type           = KPITypeEnum.MTTR,
                current_value      = mttr_val,
                current_unit       = "hours",
                target_value       = 8.0,
                target_unit        = "hours",
                status             = KPIStatusEnum.ON_TRACK if mttr_val <= 8 else KPIStatusEnum.AT_RISK,
                trend              = TrendEnum.IMPROVING if trend_pct < 0 else (TrendEnum.STABLE if trend_pct == 0 else TrendEnum.DEGRADING),
                trend_percentage   = abs(trend_pct),
                calculation_method = "mean(updated_at − created_at) for resolved findings",
            )
            self.db.add(kpi)
            kpis.append(kpi)

        # Remediation Rate
        rem_rate = self.calculate_remediation_rate(project_id)
        kpi_rem = KPI(
            project_id         = project_id,
            kpi_type           = KPITypeEnum.REMEDIATION_RATE,
            current_value      = rem_rate,
            current_unit       = "%",
            target_value       = 80.0,
            target_unit        = "%",
            status             = KPIStatusEnum.ON_TRACK if rem_rate >= 80 else KPIStatusEnum.AT_RISK,
            trend              = TrendEnum.STABLE,
            trend_percentage   = 0.0,
            calculation_method = "(resolved / total_findings) * 100",
        )
        self.db.add(kpi_rem)
        kpis.append(kpi_rem)

        # False Positive Rate
        fp_rate = self.calculate_false_positive_rate(project_id)
        kpi_fp = KPI(
            project_id         = project_id,
            kpi_type           = KPITypeEnum.FALSE_POSITIVE_RATE,
            current_value      = fp_rate,
            current_unit       = "%",
            target_value       = 10.0,
            target_unit        = "%",
            status             = KPIStatusEnum.ON_TRACK if fp_rate <= 10 else KPIStatusEnum.AT_RISK,
            trend              = TrendEnum.STABLE,
            trend_percentage   = 0.0,
            calculation_method = "(false_positive_findings / total_findings) * 100",
        )
        self.db.add(kpi_fp)
        kpis.append(kpi_fp)

        # Critical Findings Count
        critical_open = (
            self.db.query(Finding)
            .filter(
                Finding.project_id == project_id,
                Finding.severity   == Severity.critical,
                Finding.status.in_([FindingStatus.open, FindingStatus.confirmed]),
            )
            .count()
        )
        kpi_crit = KPI(
            project_id         = project_id,
            kpi_type           = KPITypeEnum.CRITICAL_FINDINGS,
            current_value      = float(critical_open),
            current_unit       = "findings",
            target_value       = 0.0,
            target_unit        = "findings",
            status             = KPIStatusEnum.ON_TRACK if critical_open == 0 else KPIStatusEnum.AT_RISK,
            trend              = TrendEnum.STABLE,
            trend_percentage   = 0.0,
            calculation_method = "count of open/confirmed CRITICAL findings",
        )
        self.db.add(kpi_crit)
        kpis.append(kpi_crit)

        # Compliance Score (if available)
        try:
            from app.models.compliance import ComplianceMappingResult
            compliance = (
                self.db.query(ComplianceMappingResult)
                .filter(ComplianceMappingResult.project_id == project_id)
                .order_by(ComplianceMappingResult.created_at.desc())
                .first()
            )
            if compliance:
                kpi_comp = KPI(
                    project_id         = project_id,
                    kpi_type           = KPITypeEnum.COMPLIANCE_SCORE,
                    current_value      = float(compliance.compliance_score),
                    current_unit       = "score",
                    target_value       = 85.0,
                    target_unit        = "score",
                    status             = KPIStatusEnum.ON_TRACK if compliance.compliance_score >= 85 else KPIStatusEnum.AT_RISK,
                    trend              = TrendEnum.STABLE,
                    trend_percentage   = 0.0,
                    calculation_method = "Compliance Engine score from Phase 13",
                )
                self.db.add(kpi_comp)
                kpis.append(kpi_comp)
        except Exception as exc:
            logger.debug("No compliance data for project %s: %s", project_id, exc)

        self.db.commit()
        return kpis

    # ── Tool Analytics ────────────────────────────────────────────────────────

    def compute_tool_analytics(self, project_id: int) -> List[ToolAnalytics]:
        """Compute and upsert ToolAnalytics records for all tools in a project."""
        # Distinct tools used in this project
        from sqlalchemy import distinct
        tool_names = [
            row[0]
            for row in self.db.query(distinct(Finding.tool_name))
            .filter(
                Finding.project_id == project_id,
                Finding.tool_name  != None,  # noqa: E711
            )
            .all()
        ]

        analytics_list: List[ToolAnalytics] = []
        for tool_name in tool_names:
            data = self.calculate_tool_effectiveness(project_id, tool_name)

            # Upsert: delete old, insert new
            self.db.query(ToolAnalytics).filter(
                ToolAnalytics.project_id == project_id,
                ToolAnalytics.tool_name  == tool_name,
            ).delete(synchronize_session=False)

            ta = ToolAnalytics(
                project_id             = project_id,
                tool_name              = tool_name,
                findings_discovered    = data["findings_count"],
                false_positives        = int(data["false_positive_rate"] * data["findings_count"] / 100),
                true_positives         = int(data["true_positive_rate"]  * data["findings_count"] / 100),
                effectiveness_score    = data["effectiveness_score"],
                false_positive_rate    = data["false_positive_rate"],
                findings_by_severity   = data["severity_breakdown"],
                trend_30_days          = TrendEnum.STABLE,
                last_used              = datetime.utcnow(),
            )
            self.db.add(ta)
            analytics_list.append(ta)

        self.db.commit()
        return analytics_list

    # ── Snapshot ─────────────────────────────────────────────────────────────

    def create_analytics_snapshot(
        self, project_id: int, snapshot_type: str = "daily"
    ) -> AnalyticsSnapshot:
        """Persist a point-in-time snapshot of all analytics data."""
        # Real-time metrics
        metrics_snapshot: Dict = {}
        if self.realtime:
            try:
                metrics_snapshot = self.realtime.get_current_metrics(str(project_id))
            except Exception as exc:
                logger.warning("Could not fetch realtime metrics: %s", exc)

        # Latest KPIs
        from app.models.analytics import KPI
        latest_kpis = (
            self.db.query(KPI)
            .filter(KPI.project_id == project_id)
            .order_by(KPI.calculated_at.desc())
            .limit(20)
            .all()
        )
        kpis_snapshot = {
            kpi.kpi_type.value: {
                "value":  kpi.current_value,
                "unit":   kpi.current_unit,
                "status": kpi.status.value,
                "trend":  kpi.trend.value,
            }
            for kpi in latest_kpis
        }

        # Latest risk score
        risk_snapshot: Dict = {}
        latest_risk = (
            self.db.query(ProjectRiskScore)
            .filter(ProjectRiskScore.project_id == project_id)
            .order_by(ProjectRiskScore.calculated_at.desc())
            .first()
        )
        if latest_risk:
            risk_snapshot = {
                "overall_score": latest_risk.overall_score,
                "risk_level":    latest_risk.risk_level.value,
                "components":    latest_risk.score_component,
            }

        # Tool snapshot
        from app.models.analytics import ToolAnalytics
        tools = (
            self.db.query(ToolAnalytics)
            .filter(ToolAnalytics.project_id == project_id)
            .all()
        )
        tool_snapshot = {
            t.tool_name: {
                "effectiveness":     t.effectiveness_score,
                "false_positive_rate": t.false_positive_rate,
            }
            for t in tools
        }

        # Previous snapshot for comparison
        prev = (
            self.db.query(AnalyticsSnapshot)
            .filter(
                AnalyticsSnapshot.project_id   == project_id,
                AnalyticsSnapshot.snapshot_type == snapshot_type,
            )
            .order_by(AnalyticsSnapshot.snapshot_date.desc())
            .first()
        )
        comparison: Dict = {}
        if prev and prev.risk_snapshot:
            prev_score = prev.risk_snapshot.get("overall_score")
            curr_score = risk_snapshot.get("overall_score")
            if prev_score and curr_score:
                comparison["risk_score_change"] = curr_score - prev_score

        snapshot = AnalyticsSnapshot(
            project_id               = project_id,
            snapshot_type            = snapshot_type,
            snapshot_date            = datetime.utcnow(),
            metrics_snapshot         = metrics_snapshot,
            kpis_snapshot            = kpis_snapshot,
            risk_snapshot            = risk_snapshot,
            tool_snapshot            = tool_snapshot,
            comparison_with_previous = comparison,
        )
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        return snapshot

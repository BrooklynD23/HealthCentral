"""
Analytics module.

Handles:
- Trend calculations (deterministic, not LLM)
- Delta summaries
- Abnormal event detection
- Chart data preparation
"""

from typing import Optional
from dataclasses import dataclass
from datetime import datetime
from statistics import mean


@dataclass
class TrendDataPoint:
    """Single point in a trend series."""
    date: datetime
    value: float
    unit: str
    ref_low: Optional[float]
    ref_high: Optional[float]
    is_abnormal: bool
    flag: Optional[str]
    doc_id: str


@dataclass
class TrendSummary:
    """Summary statistics for a trend."""
    analyte: str
    latest_value: float
    latest_date: datetime
    prior_value: Optional[float]
    prior_date: Optional[datetime]
    delta: Optional[float]
    delta_percent: Optional[float]
    trend_direction: str  # "up", "down", "stable"
    is_new_high: bool
    is_new_low: bool
    rolling_average: Optional[float]
    
    # For accessibility
    summary_text: str


@dataclass
class AbnormalEvent:
    """An abnormal value event."""
    observation_id: str
    analyte: str
    value: float
    unit: str
    flag: str
    collected_at: datetime
    severity: str  # "mild", "moderate", "critical"


class AnalyticsModule:
    """
    Analytics service for trend and summary calculations.
    
    All calculations are deterministic - no LLM involved.
    Results are used by the assistant and for chart display.
    """
    
    # Threshold for "stable" trend
    STABLE_THRESHOLD_PERCENT = 5.0
    
    def __init__(self):
        """Initialize analytics module."""
        pass
    
    def calculate_trend(
        self,
        data_points: list[TrendDataPoint],
    ) -> TrendSummary:
        """
        Calculate trend summary for a series of observations.
        
        Args:
            data_points: List of data points, sorted by date ascending
            
        Returns:
            TrendSummary with statistics and narrative
        """
        if not data_points:
            raise ValueError("No data points provided")
        
        # Sort by date
        sorted_points = sorted(data_points, key=lambda p: p.date)
        
        latest = sorted_points[-1]
        prior = sorted_points[-2] if len(sorted_points) > 1 else None
        
        # Calculate delta
        delta = None
        delta_percent = None
        trend_direction = "stable"
        
        if prior:
            delta = latest.value - prior.value
            if prior.value != 0:
                delta_percent = (delta / prior.value) * 100
            
            if delta_percent is not None:
                if delta_percent > self.STABLE_THRESHOLD_PERCENT:
                    trend_direction = "up"
                elif delta_percent < -self.STABLE_THRESHOLD_PERCENT:
                    trend_direction = "down"
        
        # Calculate rolling average (last 5 values)
        recent_values = [p.value for p in sorted_points[-5:]]
        rolling_average = mean(recent_values) if recent_values else None
        
        # Check for new high/low
        all_values = [p.value for p in sorted_points]
        is_new_high = latest.value == max(all_values) and len(all_values) > 1
        is_new_low = latest.value == min(all_values) and len(all_values) > 1
        
        # Generate summary text
        summary_text = self._generate_summary_text(
            analyte="",  # Will be filled by caller
            latest=latest,
            prior=prior,
            delta=delta,
            delta_percent=delta_percent,
            trend_direction=trend_direction,
            is_new_high=is_new_high,
            is_new_low=is_new_low,
        )
        
        return TrendSummary(
            analyte="",  # Will be filled by caller
            latest_value=latest.value,
            latest_date=latest.date,
            prior_value=prior.value if prior else None,
            prior_date=prior.date if prior else None,
            delta=delta,
            delta_percent=delta_percent,
            trend_direction=trend_direction,
            is_new_high=is_new_high,
            is_new_low=is_new_low,
            rolling_average=rolling_average,
            summary_text=summary_text,
        )
    
    def _generate_summary_text(
        self,
        analyte: str,
        latest: TrendDataPoint,
        prior: Optional[TrendDataPoint],
        delta: Optional[float],
        delta_percent: Optional[float],
        trend_direction: str,
        is_new_high: bool,
        is_new_low: bool,
    ) -> str:
        """
        Generate human-readable summary for accessibility.
        
        Uses neutral, non-alarming language.
        """
        parts = []
        
        # Latest value
        parts.append(f"Most recent value: {latest.value} {latest.unit}")
        parts.append(f"on {latest.date.strftime('%B %d, %Y')}")
        
        # Reference range status
        if latest.is_abnormal:
            if latest.flag in ["H", "HH", "HIGH"]:
                parts.append("(above the reference range per report)")
            elif latest.flag in ["L", "LL", "LOW"]:
                parts.append("(below the reference range per report)")
            else:
                parts.append("(flagged as outside reference range per report)")
        else:
            parts.append("(within reference range)")
        
        # Change from prior
        if prior and delta is not None:
            change_word = "increased" if delta > 0 else "decreased"
            if abs(delta_percent or 0) < self.STABLE_THRESHOLD_PERCENT:
                parts.append(f"Stable compared to prior value of {prior.value}")
            else:
                parts.append(f"{change_word.capitalize()} from prior value of {prior.value}")
                if delta_percent is not None:
                    parts.append(f"({abs(delta_percent):.1f}% change)")
        
        # New extremes
        if is_new_high:
            parts.append("This is the highest recorded value.")
        elif is_new_low:
            parts.append("This is the lowest recorded value.")
        
        return " ".join(parts)
    
    def detect_abnormal_events(
        self,
        data_points: list[TrendDataPoint],
    ) -> list[AbnormalEvent]:
        """
        Identify abnormal value events.
        
        Relies on report flags - does not apply additional thresholds.
        """
        events = []
        
        for point in data_points:
            if point.is_abnormal and point.flag:
                severity = self._classify_severity(point.flag)
                events.append(AbnormalEvent(
                    observation_id="",  # Would be filled from DB
                    analyte="",
                    value=point.value,
                    unit=point.unit,
                    flag=point.flag,
                    collected_at=point.date,
                    severity=severity,
                ))
        
        return events
    
    def _classify_severity(self, flag: str) -> str:
        """Classify severity based on flag."""
        flag = flag.upper()
        if flag in ["HH", "LL", "CRITICAL"]:
            return "critical"
        elif flag in ["H", "L", "HIGH", "LOW"]:
            return "mild"
        else:
            return "mild"
    
    def prepare_chart_data(
        self,
        data_points: list[TrendDataPoint],
    ) -> dict:
        """
        Prepare data for chart rendering.
        
        Returns structured data for frontend charting library.
        """
        if not data_points:
            return {"series": [], "reference_range": None}
        
        sorted_points = sorted(data_points, key=lambda p: p.date)
        
        # Get reference range (use latest)
        ref_low = sorted_points[-1].ref_low
        ref_high = sorted_points[-1].ref_high
        
        series = [
            {
                "date": p.date.isoformat(),
                "value": p.value,
                "is_abnormal": p.is_abnormal,
                "flag": p.flag,
            }
            for p in sorted_points
        ]
        
        return {
            "series": series,
            "reference_range": {
                "low": ref_low,
                "high": ref_high,
            } if ref_low is not None or ref_high is not None else None,
            "unit": sorted_points[-1].unit,
        }

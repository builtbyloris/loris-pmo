from enum import StrEnum


class RiskSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


def risk_score(probability: int, impact: int) -> int:
    """Return the authoritative probability-by-impact risk score."""
    if not 1 <= probability <= 5 or not 1 <= impact <= 5:
        raise ValueError("probability and impact must be between 1 and 5")
    return probability * impact


def risk_severity(score: int) -> RiskSeverity:
    """Map a valid 5×5 matrix score to the documented severity band."""
    if not 1 <= score <= 25:
        raise ValueError("risk score must be between 1 and 25")
    if score <= 4:
        return RiskSeverity.LOW
    if score <= 9:
        return RiskSeverity.MEDIUM
    if score <= 16:
        return RiskSeverity.HIGH
    return RiskSeverity.CRITICAL

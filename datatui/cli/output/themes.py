__all__ = [
    "PRIMARY",
    "SECONDARY",
    "SUCCESS",
    "WARNING",
    "ERROR",
    "DIM",
    "HEADER",
    "QUALITY_THRESHOLDS",
    "MISSING_THRESHOLDS",
    "OUTLIER_THRESHOLDS",
    "CORRELATION_STRENGTH",
    "BANNER",
]

PRIMARY = "bold cyan"
SECONDARY = "bold blue"
SUCCESS = "bold green"
WARNING = "bold yellow"
ERROR = "bold red"
DIM = "dim white"
HEADER = "bold white"

QUALITY_THRESHOLDS = {
    "excellent": 90,
    "good": 75,
    "fair": 60,
    "poor": 0,
}

MISSING_THRESHOLDS = {
    "critical": 50,
    "high": 20,
    "medium": 5,
    "low": 0,
}

OUTLIER_THRESHOLDS = {
    "critical": 20,
    "high": 10,
    "medium": 5,
    "low": 0,
}

CORRELATION_STRENGTH = {
    "very_strong": 0.8,
    "strong": 0.6,
    "moderate": 0.4,
    "weak": 0.2,
    "negligible": 0.0,
}

BANNER = r"""
      ██████╗  █████╗ ████████╗ █████╗ ████████╗██╗   ██╗██╗
      ██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗╚══██╔══╝██║   ██║██║
      ██║  ██║███████║   ██║   ███████║   ██║   ██║   ██║██║
      ██║  ██║██╔══██║   ██║   ██╔══██║   ██║   ██║   ██║██║
      ██████╔╝██║  ██║   ██║   ██║  ██║   ██║   ╚██████╔╝██║
      ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime

@dataclass
class UIElement:
    """Represents a UI element from the XML layout"""
    element_type: str
    bounds: Tuple[int, int, int, int]  # left, top, right, bottom
    content_desc: Optional[str]
    text: Optional[str]
    clickable: bool
    focused: bool
    enabled: bool
    resource_id: Optional[str]
    class_name: Optional[str]

@dataclass
class AccessibilityIssue:
    """Represents an accessibility issue found during analysis"""
    category: str
    severity: str
    element_info: Dict
    description: str
    fix_suggestion: str
    bounds: Optional[Tuple[int, int, int, int]] = None

@dataclass
class ContrastIssue:
    """Represents a contrast issue found in the UI"""
    location: Tuple[int, int]
    foreground_color: Tuple[int, int, int]
    background_color: Tuple[int, int, int]
    contrast_ratio: float
    element_size: Tuple[int, int]
    severity: str
    suggested_colors: List[Tuple[int, int, int]]

@dataclass
class AnalysisReport:
    """Represents the complete accessibility analysis report"""
    timestamp: datetime
    total_issues: int
    issues_by_category: Dict[str, List[Dict]]
    summary: Dict[str, Dict[str, int]]
import numpy as np
import cv2
from dataclasses import dataclass
from typing import List, Tuple, Dict
from sklearn.cluster import KMeans
from scipy.spatial import KDTree
from models import ContrastIssue


class ColorContrastAnalyzer:
    def __init__(self):
        # WCAG 2.1 minimum contrast requirements
        self.MIN_CONTRAST_NORMAL_TEXT = 4.5
        self.MIN_CONTRAST_LARGE_TEXT = 3.0
        # Large text is defined as 18pt+ or 14pt+ bold
        self.LARGE_TEXT_MIN_PIXELS = 24  # Approximate conversion from 18pt
        
        # Initialize color palette for suggestions
        self.accessible_colors = self._generate_accessible_color_palette()

    def _generate_accessible_color_palette(self) -> List[Tuple[int, int, int]]:
        """Generate a palette of accessible colors that meet WCAG standards"""
        # Create a basic accessible color palette
        colors = []
        # Generate variations of primary colors with good contrast
        for base in [(0, 0, 0), (255, 255, 255)]:  # Black and white
            for r in range(0, 256, 32):
                for g in range(0, 256, 32):
                    for b in range(0, 256, 32):
                        color = (r, g, b)
                        if self._calculate_contrast_ratio(color, base) >= self.MIN_CONTRAST_NORMAL_TEXT:
                            colors.append(color)
        return list(set(colors))  # Remove duplicates

    def _calculate_relative_luminance(self, rgb: Tuple[int, int, int]) -> float:
        """
        Calculate relative luminance according to WCAG 2.1 specifications
        https://www.w3.org/WAI/GL/wiki/Relative_luminance
        """
        def normalize_and_adjust(value: int) -> float:
            srgb = value / 255.0
            if srgb <= 0.03928:
                return srgb / 12.92
            return ((srgb + 0.055) / 1.055) ** 2.4

        r, g, b = map(normalize_and_adjust, rgb)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def _calculate_contrast_ratio(self, color1: Tuple[int, int, int], 
                                color2: Tuple[int, int, int]) -> float:
        """Calculate contrast ratio according to WCAG 2.1 formula"""
        l1 = self._calculate_relative_luminance(color1)
        l2 = self._calculate_relative_luminance(color2)
        
        lighter = max(l1, l2)
        darker = min(l1, l2)
        
        return (lighter + 0.05) / (darker + 0.05)

    def _find_dominant_colors(self, image: np.ndarray, 
                            region: Tuple[slice, slice], 
                            n_colors: int = 2) -> List[Tuple[int, int, int]]:
        """
        Find dominant colors in an image region using K-means clustering
        """
        pixels = image[region].reshape(-1, 3)
        
        # Use K-means clustering to find dominant colors
        kmeans = KMeans(n_clusters=n_colors, n_init=10)
        kmeans.fit(pixels)
        
        # Convert centers to RGB colors
        colors = []
        for center in kmeans.cluster_centers_:
            colors.append(tuple(map(int, center)))
        
        return colors

    def _suggest_accessible_colors(self, 
                                 background_color: Tuple[int, int, int],
                                 current_color: Tuple[int, int, int]) -> List[Tuple[int, int, int]]:
        """Suggest alternative colors that would meet contrast requirements"""
        suggestions = []
        current_hue = cv2.cvtColor(np.uint8([[current_color]]), cv2.COLOR_BGR2HSV)[0][0][0]
        
        # Create KD-tree for efficient nearest neighbor search
        tree = KDTree(np.array(self.accessible_colors))
        
        # Find colors with similar hue but better contrast
        for color in self.accessible_colors:
            hue = cv2.cvtColor(np.uint8([[color]]), cv2.COLOR_BGR2HSV)[0][0][0]
            if abs(hue - current_hue) < 30:  # Similar hue threshold
                contrast = self._calculate_contrast_ratio(color, background_color)
                if contrast >= self.MIN_CONTRAST_NORMAL_TEXT:
                    suggestions.append(color)
        
        # Sort by contrast ratio and similarity to original color
        suggestions.sort(key=lambda x: (
            self._calculate_contrast_ratio(x, background_color),
            -np.linalg.norm(np.array(x) - np.array(current_color))
        ), reverse=True)
        
        return suggestions[:5]  # Return top 5 suggestions

    def _detect_text_regions(self, image: np.ndarray) -> List[Tuple[slice, slice]]:
        """
        Detect potential text regions in the image using various techniques
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive thresholding to find potential text
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Find contours of potential text regions
        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            # Filter out noise and very large regions
            if w > 10 and h > 10 and w < image.shape[1] * 0.9:
                regions.append((
                    slice(max(0, y-5), min(image.shape[0], y+h+5)),
                    slice(max(0, x-5), min(image.shape[1], x+w+5))
                ))
        
        return regions

    def analyze_contrast(self, image: np.ndarray, detect_text_regions=False) -> List[ContrastIssue]:
        """
        Analyze color contrast in the image and identify accessibility issues
        
        Args:
            image: numpy.ndarray - BGR image to analyze
            
        Returns:
            List[ContrastIssue] - List of identified contrast issues
        """
        issues = []
        
        # Convert to Lab color space for better color difference analysis
        lab_image = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        
        if detect_text_regions:
            # Detect potential text regions
            text_regions = self._detect_text_regions(image)
        else:
            # Use the whole image as a single region
            text_regions = [(slice(0, image.shape[0]), slice(0, image.shape[1]))]
        
        
        for region in text_regions:
            # Find dominant colors in the region
            colors = self._find_dominant_colors(image, region)
            
            if len(colors) >= 2:
                foreground_color = colors[0]
                background_color = colors[1]
                
                # Calculate contrast ratio
                contrast_ratio = self._calculate_contrast_ratio(
                    foreground_color, background_color
                )
                
                # Determine if this is large text
                region_height = region[0].stop - region[0].start
                is_large_text = region_height >= self.LARGE_TEXT_MIN_PIXELS
                
                # Check if contrast is insufficient
                min_required_contrast = (
                    self.MIN_CONTRAST_LARGE_TEXT if is_large_text 
                    else self.MIN_CONTRAST_NORMAL_TEXT
                )
                
                if contrast_ratio < min_required_contrast:
                    # Find suggested colors that would meet contrast requirements
                    suggested_colors = self._suggest_accessible_colors(
                        background_color, foreground_color
                    )
                    
                    severity = "High" if contrast_ratio < min_required_contrast * 0.75 else "Medium"
                    
                    issues.append(ContrastIssue(
                        location=(region[1].start, region[0].start),
                        foreground_color=foreground_color,
                        background_color=background_color,
                        contrast_ratio=contrast_ratio,
                        element_size=(
                            region[1].stop - region[1].start,
                            region[0].stop - region[0].start
                        ),
                        severity=severity,
                        suggested_colors=suggested_colors
                    ))
        
        return issues

def test_color_contrast(screenshot_path: str) -> Dict:
    """
    Test color contrast in a screenshot and generate a detailed report
    
    Args:
        screenshot_path: str - Path to the screenshot image
        
    Returns:
        Dict containing the analysis results and recommendations
    """
    # Load and process image
    image = cv2.imread(screenshot_path)
    if image is None:
        raise ValueError(f"Could not load image from {screenshot_path}")
    
    # Create analyzer instance
    analyzer = ColorContrastAnalyzer()
    
    # Analyze contrast issues
    issues = analyzer.analyze_contrast(image)
    
    # Prepare report
    report = {
        "total_issues": len(issues),
        "issues": [
            {
                "location": f"x: {issue.location[0]}, y: {issue.location[1]}",
                "contrast_ratio": round(issue.contrast_ratio, 2),
                "severity": issue.severity,
                "element_size": f"{issue.element_size[0]}x{issue.element_size[1]}px",
                "current_colors": {
                    "foreground": issue.foreground_color,
                    "background": issue.background_color
                },
                "suggested_colors": [
                    f"RGB{color}" for color in issue.suggested_colors
                ]
            }
            for issue in issues
        ]
    }
    
    return report
import base64
import io
import xml.etree.ElementTree as ET
import numpy as np
import cv2
import os
from PIL import Image
from dataclasses import dataclass
from typing import Any, List, Dict, Tuple, Optional
from datetime import datetime
import json
import logging
from collections import defaultdict
from models import UIElement, AccessibilityIssue, ContrastIssue
from color_contrast_analyzer import ColorContrastAnalyzer


class StaticAccessibilityAnalyzer:
    def __init__(self, base64_screenshot: str, layout_xml: str, image_name: str):
        """
        Initialize analyzer with screenshot and layout information
        
        Args:
            base64_screenshot: Base64 encoded screenshot image
            layout_xml: String containing the XML layout of the screen
        """
        self.logger = logging.getLogger(__name__)
        self.issues: List[AccessibilityIssue] = []
        self.image_name = image_name  # Store the image name
        
        # Parse inputs
        self.base64_screenshot = base64_screenshot
        self.screenshot = self._decode_screenshot()
        self.layout_tree = ET.fromstring(layout_xml)
        self.ui_elements = self._parse_layout()
        
        # Initialize analyzers
        self.contrast_analyzer = ColorContrastAnalyzer()
        
        # Constants
        self.MIN_TOUCH_TARGET_DP = 44
        self.MIN_TEXT_SIZE_SP = 12 # to be used for text scaling; sp - scalable pixels

    def _decode_screenshot(self) -> np.ndarray:
        """Convert base64 screenshot to OpenCV image"""
        try:
            # Decode base64 to image
            img_data = base64.b64decode(self.base64_screenshot)
            img = Image.open(io.BytesIO(img_data))
            
            # Convert to OpenCV format
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        except Exception as e:
            self.logger.error(f"Failed to decode screenshot: {str(e)}")
            raise

    def get_image_dimensions(self):
        try:
            # Load the image from the binary data
            img_data = base64.b64decode(self.base64_screenshot)
            image = Image.open(io.BytesIO(img_data))

            # Get the dimensions of the image
            width, height = image.size

            return [width, height]
        except Exception as e:
            self.logger.error(f"Failed to decode screenshot: {str(e)}")
            return [0,0]
    
    def _parse_layout(self) -> List[UIElement]:
        """Parse XML layout into UIElement objects"""
        elements = []
        
        def parse_bounds(bounds_str: str) -> Tuple[int, int, int, int]:
            """Parse bounds string '[left,top][right,bottom]' into tuple"""
            try:
                coords = bounds_str.strip('[]').split('][')
                left, top = map(int, coords[0].split(','))
                right, bottom = map(int, coords[1].split(','))
                return (left, top, right, bottom)
            except Exception as e:
                self.logger.error(f"Failed to parse bounds '{bounds_str}': {str(e)}")
                return (0, 0, 0, 0)

        def extract_element(node: ET.Element) -> None:
            """Recursively extract elements from XML tree"""
            bounds = parse_bounds(node.get('bounds', '[0,0][0,0]'))
            
            elements.append(UIElement(
                element_type=node.tag,
                bounds=bounds,
                content_desc=node.get('content-desc'),
                text=node.get('text'),
                clickable=node.get('clickable') == 'true',
                focused=node.get('focused') == 'true',
                enabled=node.get('enabled') == 'true',
                resource_id=node.get('resource-id'),
                class_name=node.get('class')
            ))
            
            for child in node:
                extract_element(child)

        extract_element(self.layout_tree)
        return elements

    def analyze_content_descriptions(self) -> None:
        """Analyze content descriptions for accessibility issues"""
        for element in self.ui_elements:
            if element.clickable or element.element_type == 'android.widget.ImageView':
                if not element.content_desc and not element.text:
                    self.issues.append(AccessibilityIssue(
                        category="Content Description",
                        severity="High",
                        element_info={
                            'type': element.element_type,
                            'resource_id': element.resource_id,
                            'class_name': element.class_name
                        },
                        description="Missing content description for interactive or image element",
                        fix_suggestion="Add a descriptive content description that explains the element's purpose",
                        bounds=element.bounds
                    ))
                elif element.content_desc and len(element.content_desc.strip()) < 3:
                    self.issues.append(AccessibilityIssue(
                        category="Content Description",
                        severity="Medium",
                        element_info={
                            'type': element.element_type,
                            'content_desc': element.content_desc,
                            'resource_id': element.resource_id
                        },
                        description="Content description too short to be meaningful",
                        fix_suggestion="Provide a more descriptive content description",
                        bounds=element.bounds
                    ))

    def analyze_touch_targets(self) -> None:
        """Analyze touch target sizes"""
        for element in self.ui_elements:
            if element.clickable:
                left, top, right, bottom = element.bounds
                width = right - left
                height = bottom - top
                
                if width < self.MIN_TOUCH_TARGET_DP or height < self.MIN_TOUCH_TARGET_DP:
                    self.issues.append(AccessibilityIssue(
                        category="Touch Target Size",
                        severity="High" if min(width, height) < self.MIN_TOUCH_TARGET_DP * 0.75 else "Medium",
                        element_info={
                            'type': element.element_type,
                            'resource_id': element.resource_id,
                            'size': f"{width}x{height}dp"
                        },
                        description=f"Touch target size ({width}x{height}dp) smaller than recommended {self.MIN_TOUCH_TARGET_DP}dp",
                        fix_suggestion=f"Increase touch target size to at least {self.MIN_TOUCH_TARGET_DP}x{self.MIN_TOUCH_TARGET_DP}dp",
                        bounds=element.bounds
                    ))

    def analyze_text_contrast(self) -> None:
        """Analyze text elements for color contrast issues"""
        for element in self.ui_elements:
            if element.element_type in ['android.widget.TextView', 'android.widget.EditText']:
                left, top, right, bottom = element.bounds
                if right > left and bottom > top:  # Valid bounds
                    # Extract text region from screenshot
                    region = self.screenshot[top:bottom, left:right]
                    if region.size > 0:  # Valid region
                        issues = self.contrast_analyzer.analyze_contrast(region)
                        
                        for issue in issues:
                            self.issues.append(AccessibilityIssue(
                                category="Color Contrast",
                                severity=issue.severity,
                                element_info={
                                    'type': element.element_type,
                                    'text': element.text,
                                    'contrast_ratio': issue.contrast_ratio,
                                    'colors': {
                                        'foreground': issue.foreground_color,
                                        'background': issue.background_color
                                    }
                                },
                                description=f"Insufficient color contrast ratio: {issue.contrast_ratio:.2f}",
                                fix_suggestion=f"Use suggested colors: {issue.suggested_colors}",
                                bounds=element.bounds
                            ))

    def _estimate_heading_level(self, element: UIElement) -> int:
        """
        Estimate the heading level of a UI element based on its class name or text size.
        
        Args:
            element: The UIElement to estimate the heading level for.
        
        Returns:
            An integer representing the estimated heading level.
        """
        # Check if the class name contains heading indicators
        if element.class_name:
            if 'h1' in element.class_name.lower():
                return 1
            elif 'h2' in element.class_name.lower():
                return 2
            elif 'h3' in element.class_name.lower():
                return 3
            elif 'h4' in element.class_name.lower():
                return 4
            elif 'h5' in element.class_name.lower():
                return 5
            elif 'h6' in element.class_name.lower():
                return 6

        # Fallback: Estimate based on text size if available
        # Assuming we have a way to determine text size, e.g., from element attributes
        if element.text and len(element.text) > 0:
            # Placeholder logic for text size estimation
            # This would require additional data about text size, which is not present in the current model
            text_size = len(element.text)  # Simplified assumption
            if text_size > 20:
                return 1
            elif text_size > 16:
                return 2
            elif text_size > 12:
                return 3
            elif text_size > 8:
                return 4
            else:
                return 5

        # Default to level 6 if no other indicators are found
        return 6

    def analyze_heading_hierarchy(self) -> None:
        """Analyze heading structure and hierarchy"""
        headings = []
        
        for element in self.ui_elements:
            if element.class_name and ('Heading' in element.class_name or 'Title' in element.class_name):
                headings.append(element)
        
        # Check heading levels
        current_level = 1
        for heading in headings:
            # Estimate heading level from text size or class name
            estimated_level = self._estimate_heading_level(heading)
            
            if estimated_level > current_level + 1:
                self.issues.append(AccessibilityIssue(
                    category="Heading Hierarchy",
                    severity="Medium",
                    element_info={
                        'type': heading.element_type,
                        'text': heading.text,
                        'current_level': estimated_level,
                        'expected_level': current_level + 1
                    },
                    description=f"Skipped heading level: jumped from h{current_level} to h{estimated_level}",
                    fix_suggestion="Ensure heading levels are sequential",
                    bounds=heading.bounds
                ))
            
            current_level = estimated_level

    def mark_issues_on_image(self, image: np.ndarray[Any], issues: List[AccessibilityIssue], color: Tuple[int, int, int], output_name: str) -> None:
        """
        Mark issues on a copy of the input image with rectangles.

        Args:
            image: The input image as a numpy array.
            issues: List of AccessibilityIssue objects.
            color: The color of the rectangle (BGR format).
            output_name: The name of the output image file.
        """
        # Create a copy of the image
        marked_image = image.copy()

        # Draw rectangles around the elements with issues
        for issue in issues:
            if issue.bounds is not None:
                left, top, right, bottom = issue.bounds
                cv2.rectangle(marked_image, (left, top), (right, bottom), color, 4)

        # Ensure the output directory exists
        os.makedirs('./marked-output', exist_ok=True)

        # Save the marked image
        cv2.imwrite(f'./marked-output/{output_name}.png', marked_image)

    def mark_issues(self) -> None:
        """
        Process and mark different categories of issues on the image.

        Args:
            image: The input image as a numpy array.
            issues: List of AccessibilityIssue objects.
            image_name: The base name of the input image.
        """
        # Define colors for each category
        colors = {
            "Content Description": (255, 0, 0),  # Blue
            "Touch Target Size": (0, 0, 255),    # Red
            # "Color Contrast": (0, 0, 0),         # Black
            "Color Contrast": (238, 130, 238),         # Violet
            "Heading Hierarchy": (0, 165, 255)   # Orange
        }

        # Group issues by category
        issues_by_category = defaultdict(list)
        for issue in self.issues:
            issues_by_category[issue.category].append(issue)

        # Mark and save images for each category
        for category, category_issues in issues_by_category.items():
            color = colors.get(category, (0, 255, 0))  # Default to green if category not found
            output_name = f"{self.image_name}_{category.replace(' ', '_')}"
            self.mark_issues_on_image(self.screenshot, category_issues, color, output_name)

    # Example usage
    # Assuming `screenshot` is the decoded image and `analyzer.issues` contains the list of issues
    # process_issues(screenshot, analyzer.issues, "input_image_name")
    def generate_report(self) -> dict[str, Any]:
        """Generate comprehensive accessibility report"""
        issues_by_category = defaultdict(list)
        for issue in self.issues:
            issues_by_category[issue.category].append({
                'severity': issue.severity,
                'description': issue.description,
                'fix_suggestion': issue.fix_suggestion,
                'element_info': issue.element_info,
                'bounds': issue.bounds
            })

        return {
            'timestamp': datetime.now().isoformat(),
            'image_dimensions': self.get_image_dimensions(),
            'total_issues': len(self.issues),
            'issues_by_category': dict(issues_by_category),
            'summary': {
                category: {
                    'count': len(issues),
                    'high_severity': len([i for i in issues if i['severity'] == 'High']),
                    'medium_severity': len([i for i in issues if i['severity'] == 'Medium'])
                }
                for category, issues in issues_by_category.items()
            }
        }

    def run_analysis(self) -> dict[str, Any]:
        """Run all accessibility analyses"""
        try:
            self.analyze_content_descriptions()
            self.analyze_touch_targets()
            self.analyze_text_contrast()
            self.analyze_heading_hierarchy()
            
            # self.mark_issues()
            return self.generate_report()
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {str(e)}")
            raise

# def main(base64_screenshot: str, layout_xml: str) -> dict[str, Any]:
#     """
#     Main entry point for static accessibility analysis
    
#     Args:
#         base64_screenshot: Base64 encoded screenshot
#         layout_xml: XML layout string
    
#     Returns:
#         Dict containing accessibility analysis report
#     """
#     analyzer = StaticAccessibilityAnalyzer(base64_screenshot, layout_xml)
#     return analyzer.run_analysis()

# Example usage:
# if __name__ == "__main__":
#     # You would normally get these from your test environment
#     with open('screenshot.txt', 'r') as f:
#         base64_screenshot = f.read()
    
#     with open('layout.xml', 'r') as f:
#         layout_xml = f.read()
    
#     report = main(base64_screenshot, layout_xml)
    
#     # Save report
#     with open('accessibility_report.json', 'w') as f:
#         json.dump(report, f, indent=2)

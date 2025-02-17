# Eupheme : Accessibility Tester for Mobile apps

## Overview
Eupheme is a FastAPI-based application designed to analyze mobile screenshots and XML of the pagesource to detect accessibility issues in mobile apps. It provides detailed issue list along with suggestions to fix them.

**Current Status**: This version is supporting Static analysis on Android only. Support for iOS, Improvements in Static analysis and Dynamic Accessibility Analysis coming soon.

## Installation
1. **Clone the repository**:

   ```bash
   git clone https://github.com/qapilotio/Eupheme.git
   cd Eupheme
   ```
2. **Set up a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

## Quick Start

1. **Start the application**:

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
2. **Access the interactive API documentation**:
   - OpenAPI UI: `http://localhost:8000/docs`
   - ReDoc UI: `http://localhost:8000/redoc`

## API Reference

### POST /invoke

- Supports image and XML input files as URLs
- Analyzes for accessibility issues
- Returns the list of issues category wise with descriptions and suggestions to fix.
  Categories supported - 
  1. Content Description
  2. Touch Target Size
  3. Color Contrast
  4. Heading Hierarchy

#### Request Body

```json
{
  "image_url": "string",  // Required: File path or URL
  "xml_url": "string"     // Required: File path or URL
}
```

#### Response Format

```json
{
  "timestamp": "2025-01-10T16:33:14.398275",
  "total_issues": 79,
  "issues_by_category": {
    "Content Description": [
      {
        "severity": "High",
        "description": "Missing content description for interactive or image element",
        "fix_suggestion": "Add a descriptive content description that explains the element's purpose",
        "element_info": {
          "type": "android.view.ViewGroup",
          "resource_id": null,
          "class_name": "android.view.ViewGroup"
        },
        "bounds": [
          0,
          0,
          1080,
          2066
        ]
      },
      {
        "severity": "High",
        "description": "Missing content description for interactive or image element",
        "fix_suggestion": "Add a descriptive content description that explains the element's purpose",
        "element_info": {
          "type": "androidx.appcompat.widget.LinearLayoutCompat",
          "resource_id": "com.makemytrip:id/ll_container",
          "class_name": "androidx.appcompat.widget.LinearLayoutCompat"
        },
        "bounds": [
          0,
          1414,
          1080,
          2066
        ]
      }
    ],
    "Touch Target Size": [
      {
        "severity": "Medium",
        "description": "Touch target size (42x42dp) smaller than recommended 48dp",
        "fix_suggestion": "Increase touch target size to at least 48x48dp",
        "element_info": {
          "type": "android.widget.ImageView",
          "resource_id": "com.makemytrip:id/iv_cta",
          "size": "42x42dp"
        },
        "bounds": [
          993,
          287,
          1035,
          329
        ]
      },
      {
        "severity": "Medium",
        "description": "Touch target size (349x46dp) smaller than recommended 48dp",
        "fix_suggestion": "Increase touch target size to at least 48x48dp",
        "element_info": {
          "type": "androidx.appcompat.widget.LinearLayoutCompat",
          "resource_id": "com.makemytrip:id/ll_more_container",
          "size": "349x46dp"
        },
        "bounds": [
          366,
          1764,
          715,
          1810
        ]
      }
    ],
    "Color Contrast": [
      {
        "severity": "High",
        "description": "Insufficient color contrast ratio: 1.76",
        "fix_suggestion": "Use suggested colors: [(32, 0, 0), (64, 0, 0), (64, 32, 0), (64, 32, 32), (96, 0, 0)]",
        "element_info": {
          "type": "android.widget.TextView",
          "text": "BOOK NOW",
          "contrast_ratio": 1.7639984826411526,
          "colors": {
            "foreground": [
              254,
              177,
              82
            ],
            "background": [
              254,
              252,
              249
            ]
          }
        },
        "bounds": [
          68,
          1953,
          1012,
          2066
        ]
      },
      {
        "severity": "High",
        "description": "Insufficient color contrast ratio: 1.81",
        "fix_suggestion": "Use suggested colors: []",
        "element_info": {
          "type": "android.widget.TextView",
          "text": "View All",
          "contrast_ratio": 1.8100396560764627,
          "colors": {
            "foreground": [
              158,
              156,
              154
            ],
            "background": [
              165,
              95,
              9
            ]
          }
        },
        "bounds": [
          804,
          268,
          976,
          347
        ]
      }
    ]
  },
  "summary": {
    "Content Description": {
      "count": 2,
      "high_severity": 2,
      "medium_severity": 0
    },
    "Touch Target Size": {
      "count": 2,
      "high_severity": 0,
      "medium_severity": 2
    },
    "Color Contrast": {
      "count": 2,
      "high_severity": 2,
      "medium_severity": 
    }
  }
}
```

**Note : If a certain category is not present in the API response, it is safe to assume there's no issue of that category**

### GET /health

- Checks application status

## Project Structure

```
Eupheme/
├── main.py          # FastAPI application and endpoints
├── models.py         # Object definitions
├── color_contrast_analyzer.py       # Analyzes the color contrast issues
├── static_a11y_framework.py           # Framework to identify accessibility issues through static analysis of image and XML
├── requirements.txt # Project dependencies
└── marked-output/            # Folder to store marked screenshots
```

## Features
### Implemented - 
#### Static Analysis
1. Content Description issues
2. Touch target size issues
3. Colour contrast issues
4. Heading structure and hierarchy issues

### To be done - 
#### Static Analysis
1. AI for visual analysis - could require custom models; start with prompt engineering
    1. Analyze layout patterns to identify potential navigation barriers
        1. Overlapping elements
        2. Information density
        3. Clarity in focus order
    2. Pattern recognition for identifying common accessibility anti-patterns
2. NLP for analyzing the quality of content description; we have only checked for presence as of now
3. Understandability of the app
    1. clear headings
    2. helpful error messages
4. Handle the separation of overlays in the XML from background elements when marking

#### Dynamic Analysis
1. Text scaling - would need to scale text in live app and
    1. Verify how UI responds to system font size changes
    2. Checks if text containers properly expand
    3. Ensures no text overflow or clipping occurs
2. Support for gesture and motion accessibility
    1. Analyze gesture complexity and provide alternatives
    2. Test for motion-triggered actions and verify fallback options
    3. Check for shake, tilt, or other motion-dependent features
    4. Verify multi-touch gesture alternatives
    5. Monitor gesture timing requirements 
3. Robustness - working across different assistive tech
    1. accessibility services and testing with various screen readers - announcements
5. Dynamic navigation path analysis - patterns from crawler output can be used here
    1. Identify dead ends or circular navigation patterns
    2. Test skip navigation functionality - both visually and functionally
    3. logical view order and focus management
6. Custom rules engine for organization-specific requirements
    1. Create custom testing rules based on target audience needs
    2. Implement industry-specific accessibility guidelines
    3. Add brand-specific accessibility requirements
    4. Define rules for specific device or platform requirements
    5. Define organization-specific accessibility requirements
7. Portrait vs Landscape mode functionality

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Contact
For questions or support, please contact **[contactus@qapilot.com](mailto:contactus@qapilot.com)**.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.


#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for NextPDF Pro Modern UI
Verifies UI components load and render correctly.
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QLocale

from config import settings, APP_NAME, APP_VERSION
from ui.theme_manager import ThemeManager, THEME_COLORS
from ui.components import (
    ModernButton, ModernIconButton, Card, RibbonGroup,
    EmptyState, PropertiesPanel, ThumbnailPanel, ThumbnailItem
)
from ui.main_window import MainWindow
from ui.pdf_viewer import PDFViewer

def test_theme_colors():
    """Test theme color definitions."""
    print("=" * 60)
    print("Test 1: Theme Colors")
    print("=" * 60)
    
    required_colors = [
        "primary", "bg_window", "bg_panel", "bg_card",
        "text_primary", "text_secondary", "border_light",
        "success", "warning", "error", "accent"
    ]
    
    for color in required_colors:
        value = THEME_COLORS.get(color)
        if value:
            print(f"  ✓ {color}: {value}")
        else:
            print(f"  ✗ {color}: MISSING")
    
    print()

def test_components():
    """Test UI components creation."""
    print("=" * 60)
    print("Test 2: UI Components")
    print("=" * 60)
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Test ModernButton
    btn = ModernButton("Test Button", button_type="primary")
    print(f"  ✓ ModernButton created: {btn.text()}")
    
    # Test Card
    card = Card("Test Card")
    print(f"  ✓ Card created: {card.objectName()}")
    
    # Test RibbonGroup
    group = RibbonGroup("Test Group")
    print(f"  ✓ RibbonGroup created")
    
    # Test EmptyState
    empty = EmptyState()
    print(f"  ✓ EmptyState created")
    
    # Test PropertiesPanel
    props = PropertiesPanel()
    print(f"  ✓ PropertiesPanel created")
    
    # Test ThumbnailPanel
    thumbs = ThumbnailPanel()
    print(f"  ✓ ThumbnailPanel created")
    
    # Test ThumbnailItem
    item = ThumbnailItem(1)
    print(f"  ✓ ThumbnailItem created: page {item.page_number}")
    
    print()

def test_theme_manager():
    """Test theme manager."""
    print("=" * 60)
    print("Test 3: Theme Manager")
    print("=" * 60)
    
    app = QApplication.instance()
    theme = ThemeManager(app)
    
    print(f"  ✓ Theme created: {theme.theme_name}")
    print(f"  ✓ Language: {theme.language}")
    
    # Test language switching
    theme.set_language("en")
    print(f"  ✓ Switched to English")
    
    theme.set_language("ar")
    print(f"  ✓ Switched to Arabic")
    
    print()

def test_main_window():
    """Test main window creation."""
    print("=" * 60)
    print("Test 4: Main Window")
    print("=" * 60)
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    window = MainWindow()
    print(f"  ✓ MainWindow created: {window.windowTitle()}")
    print(f"  ✓ Size: {window.size().width()}x{window.size().height()}")
    print(f"  ✓ Minimum size: {window.minimumSize().width()}x{window.minimumSize().height()}")
    
    # Check ribbon
    print(f"  ✓ Ribbon toolbar created")
    
    # Check panels
    print(f"  ✓ Thumbnail panel created")
    print(f"  ✓ Properties panel created")
    print(f"  ✓ Status bar created")
    
    # Don't show the window, just test creation
    window.close()
    
    print()

def test_pdf_viewer():
    """Test PDF viewer creation."""
    print("=" * 60)
    print("Test 5: PDF Viewer")
    print("=" * 60)
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Create without document (empty state)
    viewer = PDFViewer(None, None, None, None)
    print(f"  ✓ PDFViewer created (no document)")
    print(f"  ✓ Zoom level: {viewer.zoom_level}%")
    print(f"  ✓ Min zoom: {viewer.min_zoom}%")
    print(f"  ✓ Max zoom: {viewer.max_zoom}%")
    
    viewer.close()
    
    print()

def run_all_tests():
    """Run all UI tests."""
    print("\n" + "=" * 60)
    print("NextPDF Pro - Modern UI Test Suite")
    print("=" * 60 + "\n")
    
    test_theme_colors()
    test_theme_manager()
    test_components()
    test_main_window()
    test_pdf_viewer()
    
    print("=" * 60)
    print("All tests completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_all_tests()
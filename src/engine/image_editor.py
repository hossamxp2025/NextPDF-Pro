#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Image Editor Engine for NextPDF Pro
Handles image operations: insert, replace, resize, rotate, crop, delete.
"""

import logging

# Compatibility: try importing pymupdf first, fall back to fitz
try:
    import pymupdf as fitz
except ImportError:
    import fitz
from typing import Optional, Tuple
from pathlib import Path

from src.models.document import ImageElement, PDFDocument

logger = logging.getLogger("NextPDF")


class ImageEditor:
    """Manages image operations in PDF pages."""
    
    def __init__(self, document: PDFDocument):
        self.doc = document
    
    def insert_image(self, page_number: int, image_path: str,
                     x: float, y: float, width: float, height: float) -> Optional[str]:
        """Insert an image into a page and refresh the element index."""
        try:
            if self.doc.doc is None or not image_path or not Path(image_path).exists():
                return None

            page = self.doc.get_page(page_number)
            if page is None:
                return None

            rect = fitz.Rect(x, y, x + width, y + height)
            xref = page.insert_image(rect, filename=image_path)
            self.doc.refresh()
            self.doc.is_modified = True
            for img in self.doc.get_images_for_page(page_number):
                if img.xref == xref:
                    return img.image_id
            logger.info("Inserted image %s on page %d", image_path, page_number)
            return f"xref_{xref}"

        except Exception as e:
            logger.error(f"Failed to insert image: {e}")
            return None
    
    def replace_image(self, image_id: str, new_image_path: str) -> bool:
        """Replace an existing image."""
        try:
            # Find the image
            target_img = None
            target_page = None
            
            for page_num, imgs in self.doc.images.items():
                for img in imgs:
                    if img.image_id == image_id:
                        target_img = img
                        target_page = page_num
                        break
                if target_img:
                    break
            
            if target_img is None:
                return False
            
            page = self.doc.get_page(target_page)
            if page is None:
                return False
            
            # Delete old image
            page.delete_image(target_img.xref)
            
            # Insert new image
            rect = fitz.Rect(
                target_img.x, target_img.y,
                target_img.x + target_img.width,
                target_img.y + target_img.height
            )
            new_xref = page.insert_image(rect, filename=new_image_path)
            
            # Update image element
            target_img.xref = new_xref
            target_img.source_path = new_image_path
            self.doc.is_modified = True
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to replace image: {e}")
            return False
    
    def delete_image(self, image_id: str) -> bool:
        """Delete an image from a page."""
        try:
            target_img = None
            target_page = None
            
            for page_num, imgs in self.doc.images.items():
                for img in imgs:
                    if img.image_id == image_id:
                        target_img = img
                        target_page = page_num
                        break
                if target_img:
                    break
            
            if target_img is None:
                return False
            
            page = self.doc.get_page(target_page)
            if page:
                page.delete_image(target_img.xref)
            
            self.doc.images[target_page] = [
                img for img in self.doc.images[target_page] 
                if img.image_id != image_id
            ]
            self.doc.is_modified = True
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete image: {e}")
            return False
    
    def resize_image(self, image_id: str, new_width: float, new_height: float,
                     keep_aspect: bool = True) -> bool:
        """Resize an image."""
        try:
            target_img = None
            
            for page_num, imgs in self.doc.images.items():
                for img in imgs:
                    if img.image_id == image_id:
                        target_img = img
                        break
                if target_img:
                    break
            
            if target_img is None:
                return False
            
            if keep_aspect:
                aspect = target_img.width / target_img.height
                if new_width / new_height > aspect:
                    new_width = new_height * aspect
                else:
                    new_height = new_width / aspect
            
            target_img.width = new_width
            target_img.height = new_height
            self.doc.is_modified = True
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to resize image: {e}")
            return False
    
    def rotate_image(self, image_id: str, degrees: float) -> bool:
        """Rotate an image."""
        try:
            target_img = None
            
            for page_num, imgs in self.doc.images.items():
                for img in imgs:
                    if img.image_id == image_id:
                        target_img = img
                        break
                if target_img:
                    break
            
            if target_img is None:
                return False
            
            target_img.rotation = (target_img.rotation + degrees) % 360
            self.doc.is_modified = True
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to rotate image: {e}")
            return False
    
    def move_image(self, image_id: str, new_x: float, new_y: float) -> bool:
        """Move an image to a new position."""
        try:
            target_img = None
            
            for page_num, imgs in self.doc.images.items():
                for img in imgs:
                    if img.image_id == image_id:
                        target_img = img
                        break
                if target_img:
                    break
            
            if target_img is None:
                return False
            
            target_img.x = new_x
            target_img.y = new_y
            self.doc.is_modified = True
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to move image: {e}")
            return False
    
    def extract_image(self, image_id: str, output_path: str) -> bool:
        """Extract an image from the PDF to a file."""
        try:
            target_img = None
            
            for page_num, imgs in self.doc.images.items():
                for img in imgs:
                    if img.image_id == image_id:
                        target_img = img
                        break
                if target_img:
                    break
            
            if target_img is None:
                return False
            
            if self.doc.doc is None:
                return False
            
            # Extract image using PyMuPDF
            pix = fitz.Pixmap(self.doc.doc, target_img.xref)
            
            if pix.n - pix.alpha > 3:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            
            pix.save(output_path)
            pix = None
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to extract image: {e}")
            return False
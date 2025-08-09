import hashlib
import os
from typing import Dict, List, Tuple, Set
from pathlib import Path
import base64
from PIL import Image
import io
from collections import defaultdict
import re
from datetime import datetime

class DuplicateFileFinder:
    """Advanced duplicate file finder with support for various file types"""
    
    def __init__(self):
        self.file_hashes = defaultdict(list)
        self.image_hashes = defaultdict(list)
        self.duplicates = []
        
    def calculate_file_hash(self, file_data: bytes) -> str:
        """Calculate MD5 hash of file data"""
        return hashlib.md5(file_data).hexdigest()
    
    def calculate_image_hash(self, image_data: bytes) -> str:
        """Calculate perceptual hash for images (basic implementation)"""
        try:
            image = Image.open(io.BytesIO(image_data))
            # Resize to 8x8 grayscale for perceptual hashing
            image = image.convert('L').resize((8, 8), Image.Resampling.LANCZOS)
            pixels = list(image.getdata())
            
            # Calculate average
            avg = sum(pixels) / len(pixels)
            
            # Create hash based on pixels above/below average
            hash_bits = ''.join('1' if pixel > avg else '0' for pixel in pixels)
            return hash_bits
        except Exception:
            # Fallback to regular hash if image processing fails
            return self.calculate_file_hash(image_data)
    
    def get_file_size(self, file_data: bytes) -> int:
        """Get file size in bytes"""
        return len(file_data)
    
    def get_file_extension(self, filename: str) -> str:
        """Extract file extension"""
        return Path(filename).suffix.lower()
    
    def is_image_file(self, filename: str) -> bool:
        """Check if file is an image based on extension"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
        return self.get_file_extension(filename) in image_extensions
    
    def add_file(self, filename: str, file_data: bytes, file_id: str = None) -> Dict:
        """Add a file to the duplicate finder and return file info"""
        file_hash = self.calculate_file_hash(file_data)
        file_size = self.get_file_size(file_data)
        file_ext = self.get_file_extension(filename)
        
        file_info = {
            'filename': filename,
            'file_id': file_id,
            'hash': file_hash,
            'size': file_size,
            'extension': file_ext,
            'is_image': self.is_image_file(filename),
            'added_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # For images, also calculate perceptual hash
        if file_info['is_image']:
            try:
                perceptual_hash = self.calculate_image_hash(file_data)
                file_info['perceptual_hash'] = perceptual_hash
                self.image_hashes[perceptual_hash].append(file_info)
            except Exception:
                pass  # Skip perceptual hashing if it fails
        
        # Store by exact hash
        self.file_hashes[file_hash].append(file_info)
        
        return file_info
    
    def find_exact_duplicates(self) -> List[List[Dict]]:
        """Find files with identical content (exact duplicates)"""
        duplicates = []
        for file_hash, files in self.file_hashes.items():
            if len(files) > 1:
                duplicates.append(files)
        return duplicates
    
    def find_similar_images(self, threshold: int = 5) -> List[List[Dict]]:
        """Find similar images using perceptual hashing"""
        similar_groups = []
        processed_hashes = set()
        
        for hash1, files1 in self.image_hashes.items():
            if hash1 in processed_hashes:
                continue
                
            similar_group = list(files1)  # Start with files that have exact perceptual match
            
            # Compare with other hashes
            for hash2, files2 in self.image_hashes.items():
                if hash1 != hash2 and hash2 not in processed_hashes:
                    # Calculate Hamming distance between hashes
                    if len(hash1) == len(hash2):
                        distance = sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
                        if distance <= threshold:
                            similar_group.extend(files2)
                            processed_hashes.add(hash2)
            
            if len(similar_group) > 1:
                # Remove duplicates within the group based on filename
                unique_group = []
                seen_filenames = set()
                for file_info in similar_group:
                    if file_info['filename'] not in seen_filenames:
                        unique_group.append(file_info)
                        seen_filenames.add(file_info['filename'])
                
                if len(unique_group) > 1:
                    similar_groups.append(unique_group)
            
            processed_hashes.add(hash1)
        
        return similar_groups
    
    def get_duplicate_summary(self) -> Dict:
        """Get a summary of all duplicates found"""
        exact_duplicates = self.find_exact_duplicates()
        similar_images = self.find_similar_images()
        
        # Calculate space savings
        total_wasted_space = 0
        for group in exact_duplicates:
            if len(group) > 1:
                file_size = group[0]['size']
                duplicates_count = len(group) - 1  # Keep one original
                total_wasted_space += file_size * duplicates_count
        
        return {
            'total_files_analyzed': sum(len(files) for files in self.file_hashes.values()),
            'exact_duplicate_groups': len(exact_duplicates),
            'exact_duplicate_files': sum(len(group) - 1 for group in exact_duplicates),
            'similar_image_groups': len(similar_images),
            'similar_image_files': sum(len(group) - 1 for group in similar_images),
            'potential_space_saved_bytes': total_wasted_space,
            'potential_space_saved_mb': round(total_wasted_space / (1024 * 1024), 2)
        }
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def generate_report(self) -> str:
        """Generate a detailed report of duplicates found"""
        exact_duplicates = self.find_exact_duplicates()
        similar_images = self.find_similar_images()
        summary = self.get_duplicate_summary()
        
        report = []
        report.append("🔍 **Duplicate File Analysis Report**")
        report.append("")
        
        # Summary
        report.append("📊 **Summary:**")
        report.append(f"• Total files analyzed: {summary['total_files_analyzed']}")
        report.append(f"• Exact duplicate groups: {summary['exact_duplicate_groups']}")
        report.append(f"• Exact duplicate files: {summary['exact_duplicate_files']}")
        report.append(f"• Similar image groups: {summary['similar_image_groups']}")
        report.append(f"• Similar image files: {summary['similar_image_files']}")
        report.append(f"• Potential space saved: {summary['potential_space_saved_mb']} MB")
        report.append("")
        
        # Exact duplicates
        if exact_duplicates:
            report.append("🎯 **Exact Duplicates (Identical Files):**")
            for i, group in enumerate(exact_duplicates, 1):
                file_size = self.format_file_size(group[0]['size'])
                report.append(f"\n**Group {i}** - {len(group)} files ({file_size} each):")
                for j, file_info in enumerate(group):
                    status = "🟢 Keep" if j == 0 else "🔴 Delete"
                    report.append(f"  {status} {file_info['filename']}")
                    if file_info.get('file_id'):
                        report.append(f"    ID: {file_info['file_id']}")
        
        # Similar images
        if similar_images:
            report.append("\n\n🖼️ **Similar Images (Perceptually Similar):**")
            for i, group in enumerate(similar_images, 1):
                report.append(f"\n**Group {i}** - {len(group)} similar images:")
                for j, file_info in enumerate(group):
                    file_size = self.format_file_size(file_info['size'])
                    status = "🟢 Keep" if j == 0 else "⚠️ Review"
                    report.append(f"  {status} {file_info['filename']} ({file_size})")
                    if file_info.get('file_id'):
                        report.append(f"    ID: {file_info['file_id']}")
        
        if not exact_duplicates and not similar_images:
            report.append("✅ **No duplicates found!** Your files are all unique.")
        
        return "\n".join(report)
    
    def get_files_to_delete(self) -> List[Dict]:
        """Get list of files recommended for deletion"""
        files_to_delete = []
        
        # Exact duplicates (keep first, delete rest)
        exact_duplicates = self.find_exact_duplicates()
        for group in exact_duplicates:
            files_to_delete.extend(group[1:])  # Skip first file (keep it)
        
        return files_to_delete
    
    def clear(self):
        """Clear all stored data"""
        self.file_hashes.clear()
        self.image_hashes.clear()
        self.duplicates.clear()


class WhatsAppOptimizedDuplicateFinder(DuplicateFileFinder):
    """WhatsApp-optimized version with adjusted thresholds and handling"""
    
    def __init__(self):
        super().__init__()
        # More lenient thresholds for compressed WhatsApp media
        self.image_similarity_threshold = 8  # More lenient for compressed images
        self.min_file_size = 100  # Ignore very small files (likely thumbnails)
    
    def calculate_image_hash(self, image_data: bytes) -> str:
        """Enhanced image hashing for WhatsApp compressed images"""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # Handle WhatsApp's image processing
            # Resize to standard size first to normalize
            image = image.convert('RGB')  # Ensure consistent format
            
            # Use larger hash for better accuracy with compressed images
            image = image.resize((16, 16), Image.Resampling.LANCZOS)
            image = image.convert('L')  # Convert to grayscale
            
            pixels = list(image.getdata())
            avg = sum(pixels) / len(pixels)
            
            # Create 256-bit hash for better accuracy
            hash_bits = ''.join('1' if pixel > avg else '0' for pixel in pixels)
            return hash_bits
            
        except Exception:
            return self.calculate_file_hash(image_data)
    
    def add_file(self, filename: str, file_data: bytes, file_id: str = None) -> Dict:
        """Enhanced file addition with WhatsApp considerations"""
        
        # Skip very small files (likely thumbnails or corrupted)
        if len(file_data) < self.min_file_size:
            raise ValueError(f"File too small ({len(file_data)} bytes). Minimum size: {self.min_file_size} bytes")
        
        # Check for WhatsApp naming patterns
        original_filename = filename
        if filename.startswith("IMG-") and "WA" in filename:
            # This is a WhatsApp image, normalize the name for better grouping
            file_ext = self.get_file_extension(filename)
            filename = f"whatsapp_image_{file_id or 'unknown'}{file_ext}"
        
        file_info = super().add_file(filename, file_data, file_id)
        file_info['original_filename'] = original_filename
        file_info['is_whatsapp_media'] = self._is_whatsapp_media(original_filename)
        
        return file_info
    
    def _is_whatsapp_media(self, filename: str) -> bool:
        """Detect if file is WhatsApp media based on naming pattern"""
        patterns = [
            r'^IMG-\d{8}-WA\d{4}',  # WhatsApp images
            r'^VID-\d{8}-WA\d{4}',  # WhatsApp videos
            r'^AUD-\d{8}-WA\d{4}',  # WhatsApp audio
            r'^DOC-\d{8}-WA\d{4}'   # WhatsApp documents
        ]
        
        for pattern in patterns:
            if re.match(pattern, filename):
                return True
        return False
    
    def find_similar_images(self, threshold: int = None) -> List[List[Dict]]:
        """Find similar images with WhatsApp-optimized threshold"""
        if threshold is None:
            threshold = self.image_similarity_threshold
        
        return super().find_similar_images(threshold)
    
    def generate_report(self) -> str:
        """Generate WhatsApp-optimized report"""
        exact_duplicates = self.find_exact_duplicates()
        similar_images = self.find_similar_images()
        summary = self.get_duplicate_summary()
        
        report = []
        report.append("🔍 **WhatsApp Duplicate File Analysis**")
        report.append("")
        
        # WhatsApp specific summary
        whatsapp_files = 0
        for files in self.file_hashes.values():
            for file in files:
                if file.get('is_whatsapp_media', False):
                    whatsapp_files += 1
        
        report.append("📊 **Summary:**")
        report.append(f"• Total files analyzed: {summary['total_files_analyzed']}")
        report.append(f"• WhatsApp media files: {whatsapp_files}")
        report.append(f"• Exact duplicate groups: {summary['exact_duplicate_groups']}")
        report.append(f"• Similar image groups: {summary['similar_image_groups']}")
        report.append(f"• Storage to free up: {summary['potential_space_saved_mb']} MB")
        report.append("")
        
        # Exact duplicates with WhatsApp context
        if exact_duplicates:
            report.append("🎯 **Exact Duplicates:**")
            for i, group in enumerate(exact_duplicates, 1):
                file_size = self.format_file_size(group[0]['size'])
                whatsapp_count = sum(1 for f in group if f.get('is_whatsapp_media', False))
                
                report.append(f"\n**Group {i}** - {len(group)} identical files ({file_size} each)")
                if whatsapp_count > 0:
                    report.append(f"  📱 {whatsapp_count} WhatsApp media files in this group")
                
                for j, file_info in enumerate(group):
                    status = "🟢 Keep" if j == 0 else "🔴 Delete"
                    filename = file_info.get('original_filename', file_info['filename'])
                    wa_indicator = " 📱" if file_info.get('is_whatsapp_media') else ""
                    report.append(f"  {status} {filename}{wa_indicator}")
        
        # Similar images
        if similar_images:
            report.append("\n\n🖼️ **Similar Images (May be WhatsApp compressed versions):**")
            for i, group in enumerate(similar_images, 1):
                report.append(f"\n**Group {i}** - {len(group)} similar images:")
                for j, file_info in enumerate(group):
                    file_size = self.format_file_size(file_info['size'])
                    status = "🟢 Keep" if j == 0 else "⚠️ Review"
                    filename = file_info.get('original_filename', file_info['filename'])
                    wa_indicator = " 📱" if file_info.get('is_whatsapp_media') else ""
                    report.append(f"  {status} {filename} ({file_size}){wa_indicator}")
        
        if not exact_duplicates and not similar_images:
            report.append("✅ **No duplicates found!** All your files are unique.")
        else:
            report.append(f"\n💡 **WhatsApp Note:** Similar images might be the same photo in different qualities due to WhatsApp compression.")
        
        return "\n".join(report)


class DuplicateFinderSession:
    """Session-based duplicate finder for managing multiple file uploads"""
    
    def __init__(self, use_whatsapp_optimization: bool = True):
        if use_whatsapp_optimization:
            self.finder = WhatsAppOptimizedDuplicateFinder()
        else:
            self.finder = DuplicateFileFinder()
        self.uploaded_files = {}
        self.session_start_time = datetime.now()
    
    def add_file_from_base64(self, filename: str, base64_data: str, file_id: str = None) -> Dict:
        """Add file from base64 data"""
        try:
            file_data = base64.b64decode(base64_data)
            file_info = self.finder.add_file(filename, file_data, file_id)
            self.uploaded_files[file_id or filename] = file_info
            return file_info
        except Exception as e:
            raise ValueError(f"Failed to process file {filename}: {str(e)}")
    
    def analyze_and_report(self) -> str:
        """Analyze all uploaded files and return report"""
        if not self.uploaded_files:
            return "❌ No files uploaded for analysis. Please upload some files first."
        
        return self.finder.generate_report()
    
    def get_deletion_recommendations(self) -> List[Dict]:
        """Get files recommended for deletion"""
        return self.finder.get_files_to_delete()
    
    def get_deletion_instructions(self) -> str:
        """Generate step-by-step deletion instructions"""
        files_to_delete = self.get_deletion_recommendations()
        
        if not files_to_delete:
            return "✅ **No files need to be deleted!** All your files are unique."
        
        # Separate WhatsApp and regular files
        whatsapp_files = [f for f in files_to_delete if f.get('is_whatsapp_media', False)]
        regular_files = [f for f in files_to_delete if not f.get('is_whatsapp_media', False)]
        
        instructions = [
            "🗑️ **Step-by-Step Deletion Guide**",
            "",
            f"🎯 **Goal:** Delete {len(files_to_delete)} files to save {self.finder.format_file_size(sum(f['size'] for f in files_to_delete))}",
            ""
        ]
        
        if whatsapp_files:
            instructions.extend([
                "📱 **WhatsApp Files to Delete:**",
                "",
                "**How to delete in WhatsApp:**",
                "1. Open WhatsApp",
                "2. Go to the chat where you sent the file",
                "3. Long press on the file",
                "4. Tap 'Delete' → 'Delete for me'",
                "",
                "**Files to delete:**"
            ])
            
            for i, file in enumerate(whatsapp_files, 1):
                filename = file.get('original_filename', file['filename'])
                size = self.finder.format_file_size(file['size'])
                instructions.append(f"☐ {i}. {filename} ({size})")
            
            instructions.append("")
        
        if regular_files:
            instructions.extend([
                "📂 **Regular Files to Delete:**",
                "",
                "**How to delete from phone:**",
                "1. Open File Manager or Gallery",
                "2. Navigate to Downloads/Pictures folder",
                "3. Find and select the file",
                "4. Delete it",
                "",
                "**Files to delete:**"
            ])
            
            for i, file in enumerate(regular_files, 1):
                filename = file.get('original_filename', file['filename'])
                size = self.finder.format_file_size(file['size'])
                instructions.append(f"☐ {i}. {filename} ({size})")
        
        instructions.extend([
            "",
            "💡 **Tips:**",
            "• Check each file before deleting to be sure",
            "• Files marked 🟢 Keep should NOT be deleted",
            "• Similar images (⚠️ Review) - check quality before deleting",
            "• This tool only analyzes files you uploaded here, not all your files"
        ])
        
        return "\n".join(instructions)
    
    def create_deletion_checklist(self) -> str:
        """Create a simple checklist for manual deletion"""
        files_to_delete = self.get_deletion_recommendations()
        
        if not files_to_delete:
            return "✅ **No duplicates found!** Your files are all unique."
        
        checklist = [
            "📝 **Duplicate Deletion Checklist**",
            f"",
            f"🎯 **Goal:** Free up {self.finder.format_file_size(sum(f['size'] for f in files_to_delete))} by deleting {len(files_to_delete)} duplicate files",
            f"📅 **Created:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "**Files to Delete:**"
        ]
        
        total_saved = 0
        for i, file in enumerate(files_to_delete, 1):
            filename = file.get('original_filename', file['filename'])
            size = self.finder.format_file_size(file['size'])
            wa_indicator = " 📱" if file.get('is_whatsapp_media') else ""
            checklist.append(f"☐ {i}. {filename} ({size}){wa_indicator}")
            total_saved += file['size']
        
        checklist.extend([
            "",
            f"💾 **Total Space to Free:** {self.finder.format_file_size(total_saved)}",
            "",
            "✅ **Instructions:**",
            "• Tick each box ☐ as you delete the file",
            "• Keep files marked 🟢 in the analysis report",
            "• Double-check before deleting anything important!"
        ])
        
        return "\n".join(checklist)
    
    def get_session_stats(self) -> Dict:
        """Get current session statistics"""
        return {
            'files_uploaded': len(self.uploaded_files),
            'session_duration': str(datetime.now() - self.session_start_time),
            'total_size_uploaded': sum(f['size'] for f in self.uploaded_files.values()),
            'image_files': sum(1 for f in self.uploaded_files.values() if f['is_image']),
            'whatsapp_files': sum(1 for f in self.uploaded_files.values() if f.get('is_whatsapp_media', False))
        }
    
    def reset_session(self):
        """Clear all data and start fresh"""
        self.finder.clear()
        self.uploaded_files.clear()
        self.session_start_time = datetime.now()


class DuplicateCleanupHelper:
    """Helper class for generating cleanup recommendations and instructions"""
    
    @staticmethod
    def generate_platform_specific_help(platform: str = "whatsapp") -> str:
        """Generate platform-specific deletion help"""
        
        if platform.lower() == "whatsapp":
            return """📱 **WhatsApp File Deletion Guide**

🔧 **Delete from Chat:**
1. Open the chat where you sent the file
2. Long press on the duplicate file
3. Tap "Delete" → "Delete for me"
4. File is removed from chat (original stays in gallery)

📁 **Delete from Phone Storage:**
1. Go to Phone Settings → Apps → WhatsApp → Storage
2. Tap "Manage Storage" 
3. Select chat and review large files
4. Delete unnecessary duplicates

🖼️ **For WhatsApp Images:**
1. Open Gallery/Photos app
2. Look for "WhatsApp Images" folder
3. Find the duplicate files from our report
4. Select and delete them

⚠️ **Important Notes:**
• Deleting from chat ≠ deleting from phone storage
• Check both locations for complete cleanup
• WhatsApp compresses images - keep highest quality version"""

        elif platform.lower() == "android":
            return """🤖 **Android File Deletion Guide**

📂 **Using File Manager:**
1. Open default File Manager app
2. Navigate to Downloads/Pictures/WhatsApp folders
3. Use search to find specific filenames
4. Long press → Delete

📱 **Using Gallery App:**
1. Open Photos/Gallery
2. Use search function for filenames
3. Look in "Downloads" or "WhatsApp" albums
4. Select duplicates and delete

🔍 **Pro Tips:**
• Use "Files by Google" app for better duplicate detection
• Check "Recently Downloaded" for easy access
• Sort by size to find large duplicates first"""

        elif platform.lower() == "ios":
            return """🍎 **iPhone File Deletion Guide**

📷 **Photos App:**
1. Open Photos app
2. Search for specific filenames
3. Check "Recents" and "Albums"
4. Select duplicates and delete

📁 **Files App:**
1. Open Files app
2. Check "Downloads" and "WhatsApp" folders
3. Use search to find specific files
4. Swipe left → Delete

💡 **iOS Tips:**
• Use "Duplicate" album if available (iOS 16+)
• Check "Recently Deleted" to permanently remove
• Use third-party apps like "Gemini Photos" for automatic detection"""
        
        else:
            return """📱 **General File Deletion Guide**

🔍 **Finding Files:**
• Use file manager app to navigate folders
• Search by filename from our report
• Check Downloads, Pictures, WhatsApp folders

🗑️ **Deleting Files:**
• Long press on file → Delete
• Or select multiple files → Delete all
• Empty trash/recycle bin if needed

💡 **Tips:**
• Always check file contents before deleting
• Keep highest quality version of images
• Back up important files before cleanup"""
    
    @staticmethod
    def estimate_cleanup_time(file_count: int) -> str:
        """Estimate time needed for manual cleanup"""
        # Rough estimates based on user experience
        time_per_file = 30  # seconds per file for careful deletion
        total_seconds = file_count * time_per_file
        
        if total_seconds < 60:
            return f"~{total_seconds} seconds"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            return f"~{minutes} minutes"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"~{hours}h {minutes}m"
    
    @staticmethod
    def generate_safety_checklist() -> str:
        """Generate safety checklist before deletion"""
        return """🛡️ **Safety Checklist Before Deleting**

Before you delete any files, please verify:

☐ **Backup Check**
  • Important files are backed up to cloud storage
  • You have copies in other locations if needed

☐ **Content Verification**  
  • Preview each file before deleting
  • Make sure you're deleting the right duplicate
  • Keep the highest quality version

☐ **WhatsApp Specific**
  • Deleting from chat doesn't delete from phone storage
  • Check both chat and phone gallery
  • Consider if others need access to the file

☐ **Final Check**
  • You understand which file is being kept
  • You've confirmed the file is truly a duplicate
  • You won't need multiple copies

✅ **Only proceed with deletion after completing this checklist!**

💡 **Remember:** This tool only analyzes files you uploaded here, not your entire device storage."""
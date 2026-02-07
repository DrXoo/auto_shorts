"""
Script to clean all files from the output directory.
Removes all files from output subdirectories while keeping the folder structure.
"""
import os
import shutil
from pathlib import Path


def clean_output_directory():
    """Delete all files in output subdirectories."""
    # Get the project root (two levels up from this script)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    output_dir = project_root / "output"
    
    if not output_dir.exists():
        print(f"Output directory not found: {output_dir}")
        return
    
    # Subdirectories to clean
    subdirs = [
        "ai_analysis",
        "cropped",
        "extracted",
        "final",
        "transcripts"
    ]
    
    total_deleted = 0
    
    for subdir_name in subdirs:
        subdir_path = output_dir / subdir_name
        
        if not subdir_path.exists():
            print(f"Directory not found: {subdir_name}")
            continue
        
        # Count and delete files
        files_deleted = 0
        for item in subdir_path.iterdir():
            if item.is_file():
                try:
                    item.unlink()
                    files_deleted += 1
                except Exception as e:
                    print(f"Error deleting {item}: {e}")
        
        print(f"Deleted {files_deleted} file(s) from {subdir_name}/")
        total_deleted += files_deleted
    
    # Also delete trending_topics.json if it exists in the root output folder
    trending_topics = output_dir / "trending_topics.json"
    if trending_topics.exists():
        try:
            trending_topics.unlink()
            print(f"Deleted trending_topics.json")
            total_deleted += 1
        except Exception as e:
            print(f"Error deleting trending_topics.json: {e}")
    
    print(f"\nTotal files deleted: {total_deleted}")
    print("Output directory cleaned successfully!")


if __name__ == "__main__":
    # Ask for confirmation before deleting
    response = input("This will delete all files in the output directory. Continue? (y/n): ")
    if response.lower() == 'y':
        clean_output_directory()
    else:
        print("Operation cancelled.")

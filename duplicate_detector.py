#created with Claude. Account: Milobowler

import os
import re
from collections import defaultdict
from pathlib import Path

def normalize_filename(filename):
    """
    Normalize filename by:
    - Removing file extension
    - Converting to lowercase
    - Removing special characters
    - Extracting words and sorting them
    """
    # Remove file extension
    name_without_ext = Path(filename).stem
    
    # Convert to lowercase and remove special characters
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', name_without_ext.lower())
    
    # Split into words and remove empty strings
    words = [word for word in cleaned.split() if word.strip()]
    
    # Sort words to ignore order
    return tuple(sorted(words))

def find_duplicates(directory_path):
    """
    Find duplicate files based on normalized filename comparison
    """
    if not os.path.exists(directory_path):
        print(f"Error: Directory '{directory_path}' does not exist.")
        return {}
    
    file_groups = defaultdict(list)
    
    # Walk through all files in directory and subdirectories
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            full_path = os.path.join(root, file)
            normalized_name = normalize_filename(file)
            
            # Only group files that have at least one word
            if normalized_name:
                file_groups[normalized_name].append(full_path)
    
    # Filter to only groups with duplicates (more than 1 file)
    duplicates = {key: paths for key, paths in file_groups.items() if len(paths) > 1}
    
    return duplicates

def display_duplicates(duplicates):
    """
    Display duplicate groups to user
    """
    if not duplicates:
        print("No duplicate files found!")
        return
    
    print(f"\nFound {len(duplicates)} groups of duplicate files:")
    print("=" * 60)
    
    for i, (normalized_name, file_paths) in enumerate(duplicates.items(), 1):
        print(f"\nGroup {i}: Files with words: {' '.join(normalized_name)}")
        print("-" * 40)
        for j, path in enumerate(file_paths):
            file_size = os.path.getsize(path) if os.path.exists(path) else 0
            print(f"  [{j+1}] {path}")
            print(f"      Size: {file_size:,} bytes")

def delete_selected_files(duplicates):
    """
    Allow user to select files for deletion
    """
    if not duplicates:
        return
    
    total_deleted = 0
    
    for i, (normalized_name, file_paths) in enumerate(duplicates.items(), 1):
        print(f"\n{'='*60}")
        print(f"Group {i}/{len(duplicates)}: Files with words: {' '.join(normalized_name)}")
        print("-" * 40)
        
        for j, path in enumerate(file_paths):
            file_size = os.path.getsize(path) if os.path.exists(path) else 0
            print(f"  [{j+1}] {os.path.basename(path)}")
            print(f"      Path: {path}")
            print(f"      Size: {file_size:,} bytes")
        
        while True:
            choice = input(f"\nEnter the numbers of files to DELETE (e.g., '1,3' or '2') or press Enter to skip: ").strip()
            
            if not choice:
                print("Skipping this group.")
                break
                
            try:
                # Parse user input
                indices = [int(x.strip()) for x in choice.split(',')]
                
                # Validate indices
                if all(1 <= idx <= len(file_paths) for idx in indices):
                    # Confirm deletion
                    print(f"\nYou selected to delete:")
                    for idx in indices:
                        print(f"  - {file_paths[idx-1]}")
                    
                    confirm = input("Are you sure? (y/N): ").strip().lower()
                    
                    if confirm == 'y':
                        for idx in sorted(indices, reverse=True):  # Delete in reverse order
                            file_to_delete = file_paths[idx-1]
                            try:
                                os.remove(file_to_delete)
                                print(f"✓ Deleted: {file_to_delete}")
                                total_deleted += 1
                            except Exception as e:
                                print(f"✗ Error deleting {file_to_delete}: {e}")
                    else:
                        print("Deletion cancelled.")
                    break
                else:
                    print(f"Invalid selection. Please enter numbers between 1 and {len(file_paths)}")
                    
            except ValueError:
                print("Invalid input. Please enter numbers separated by commas (e.g., '1,3' or '2')")
    
    print(f"\n{'='*60}")
    print(f"Summary: {total_deleted} files deleted.")

def main():
    """
    Main function to run the duplicate detector
    """
    print("Duplicate File Detector")
    print("=" * 30)
    
    # Get directory from user
    while True:
        directory = input("Enter the directory path to scan: ").strip()
        
        if directory and os.path.exists(directory):
            break
        elif not directory:
            print("Please enter a directory path.")
        else:
            print(f"Directory '{directory}' does not exist. Please try again.")
    
    print(f"\nScanning directory: {directory}")
    print("Please wait...")
    
    # Find duplicates
    duplicates = find_duplicates(directory)
    
    # Display results
    display_duplicates(duplicates)
    
    if duplicates:
        print(f"\n{'='*60}")
        choice = input("Do you want to delete any files? (y/N): ").strip().lower()
        
        if choice == 'y':
            delete_selected_files(duplicates)
        else:
            print("No files were deleted.")
    
    print("\nProgram completed.")

if __name__ == "__main__":
    main()

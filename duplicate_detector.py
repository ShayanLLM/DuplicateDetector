#created with Claude. Account: Milobowler

import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from collections import defaultdict
from pathlib import Path
import threading
import time
import shutil
import subprocess
import platform

class DuplicateDetectorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Duplicate File Detector")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # Variables
        self.directory_var = tk.StringVar()
        self.duplicates = {}
        self.tree_items = {}
        self.duplicate_count_var = tk.StringVar(value="Duplicates: 0")
        self.eta_var = tk.StringVar(value="ETA: --")
        self.total_files = 0
        self.processed_files = 0
        self.scan_start_time = 0
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Directory selection frame
        dir_frame = ttk.LabelFrame(main_frame, text="Directory Selection", padding="10")
        dir_frame.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))
        dir_frame.columnconfigure(1, weight=1)
        
        ttk.Label(dir_frame, text="Directory:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Entry(dir_frame, textvariable=self.directory_var, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(dir_frame, text="Browse", command=self.browse_directory).grid(row=0, column=2, sticky=tk.W)
        
        # Stats frame
        stats_frame = ttk.LabelFrame(main_frame, text="Statistics", padding="10")
        stats_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(stats_frame, textvariable=self.duplicate_count_var, font=('TkDefaultFont', 10, 'bold')).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(stats_frame, textvariable=self.eta_var, font=('TkDefaultFont', 10)).grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        # Control buttons frame
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(control_frame, text="Scan for Duplicates", command=self.scan_duplicates).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(control_frame, text="Smart Select", command=self.show_smart_select_dialog).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(control_frame, text="Delete Selected", command=self.delete_selected).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(control_frame, text="Create Folder with Selection", command=self.move_selected).grid(row=0, column=3, padx=(0, 5))
        ttk.Button(control_frame, text="Clear Results", command=self.clear_results).grid(row=0, column=4, padx=(0, 10))
        
        # Progress bar
        self.progress = ttk.Progressbar(control_frame, mode='determinate')
        self.progress.grid(row=0, column=5, sticky=(tk.W, tk.E), padx=(10, 0))
        control_frame.columnconfigure(5, weight=1)
        
        # Results frame
        results_frame = ttk.LabelFrame(main_frame, text="Duplicate Files", padding="5")
        results_frame.grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # Treeview for results
        self.tree = ttk.Treeview(results_frame, columns=('size', 'modified', 'path'), show='tree headings')
        self.tree.heading('#0', text='Filename')
        self.tree.heading('size', text='Size (bytes)')
        self.tree.heading('modified', text='Date Modified')
        self.tree.heading('path', text='Full Path')
        
        self.tree.column('#0', width=300)
        self.tree.column('size', width=100)
        self.tree.column('modified', width=150)
        self.tree.column('path', width=400)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(results_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Bind double-click event to open files
        self.tree.bind('<Double-1>', self.on_double_click)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=4, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))
        
    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.directory_var.set(directory)
    
    def normalize_filename(self, filename):
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
    
    def count_files(self, directory_path):
        """Count total files for ETA calculation"""
        total = 0
        try:
            for root, dirs, files in os.walk(directory_path):
                total += len(files)
        except Exception:
            pass
        return total
    
    def update_eta(self, processed, total, start_time):
        """Calculate and update ETA"""
        if processed == 0:
            return
        
        elapsed = time.time() - start_time
        rate = processed / elapsed
        
        if rate > 0:
            remaining = total - processed
            eta_seconds = remaining / rate
            
            if eta_seconds < 60:
                eta_text = f"ETA: {int(eta_seconds)}s"
            elif eta_seconds < 3600:
                eta_text = f"ETA: {int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
            else:
                hours = int(eta_seconds // 3600)
                minutes = int((eta_seconds % 3600) // 60)
                eta_text = f"ETA: {hours}h {minutes}m"
        else:
            eta_text = "ETA: --"
        
        self.eta_var.set(eta_text)
    
    def find_duplicates_thread(self):
        """
        Find duplicates in a separate thread to avoid freezing the GUI
        """
        directory_path = self.directory_var.get()
        
        if not directory_path:
            messagebox.showerror("Error", "Please select a directory first.")
            self.progress.stop()
            self.status_var.set("Ready")
            return
        
        if not os.path.exists(directory_path):
            messagebox.showerror("Error", f"Directory '{directory_path}' does not exist.")
            self.progress.stop()
            self.status_var.set("Ready")
            return
        
        try:
            # Count files for ETA
            self.status_var.set("Counting files...")
            self.total_files = self.count_files(directory_path)
            self.processed_files = 0
            self.scan_start_time = time.time()
            
            # Configure progress bar
            self.progress.configure(maximum=self.total_files)
            
            file_groups = defaultdict(list)
            
            # Walk through all files in directory and subdirectories
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    self.processed_files += 1
                    
                    # Update progress and ETA
                    self.root.after(0, lambda: self.progress.configure(value=self.processed_files))
                    self.root.after(0, lambda: self.update_eta(self.processed_files, self.total_files, self.scan_start_time))
                    self.root.after(0, lambda: self.status_var.set(f"Processing... {self.processed_files}/{self.total_files} files"))
                    
                    full_path = os.path.join(root, file)
                    normalized_name = self.normalize_filename(file)
                    
                    # Only group files that have at least one word
                    if normalized_name:
                        file_groups[normalized_name].append(full_path)
            
            # Filter to only groups with duplicates (more than 1 file)
            self.duplicates = {key: paths for key, paths in file_groups.items() if len(paths) > 1}
            
            # Update UI in main thread
            self.root.after(0, self.update_results)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"An error occurred while scanning: {str(e)}"))
            self.root.after(0, lambda: self.progress.configure(value=0))
            self.root.after(0, lambda: self.status_var.set("Error occurred"))
    
    def scan_duplicates(self):
        """
        Start scanning for duplicates
        """
        self.clear_results()
        self.progress.configure(value=0)
        self.eta_var.set("ETA: Calculating...")
        
        # Run in separate thread to avoid freezing GUI
        thread = threading.Thread(target=self.find_duplicates_thread)
        thread.daemon = True
        thread.start()
    
    def update_results(self):
        """
        Update the treeview with duplicate results
        """
        self.progress.configure(value=self.total_files)
        self.eta_var.set("ETA: Complete")
        
        if not self.duplicates:
            self.status_var.set("No duplicate files found")
            self.duplicate_count_var.set("Duplicates: 0")
            messagebox.showinfo("Results", "No duplicate files found!")
            return
        
        self.tree_items = {}
        duplicate_count = len(self.duplicates)
        
        for i, (normalized_name, file_paths) in enumerate(self.duplicates.items(), 1):
            # Create parent item for the group
            group_name = f"Group {i}: {' '.join(normalized_name)}"
            parent = self.tree.insert('', 'end', text=group_name, values=('', '', ''), tags=('group',))
            
            # Add files to the group
            for file_path in file_paths:
                filename = os.path.basename(file_path)
                try:
                    file_size = os.path.getsize(file_path)
                    modified_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(file_path)))
                except OSError:
                    file_size = 0
                    modified_time = "Unknown"
                
                item = self.tree.insert(parent, 'end', text=filename, 
                                      values=(f"{file_size:,}", modified_time, file_path), tags=('file',))
                self.tree_items[item] = {
                    'path': file_path,
                    'size': file_size,
                    'modified': os.path.getmtime(file_path) if os.path.exists(file_path) else 0
                }
            
            # Expand the group
            self.tree.item(parent, open=True)
        
        # Configure tags
        self.tree.tag_configure('group', background='lightgray')
        self.tree.tag_configure('file', background='white')
        
        self.duplicate_count_var.set(f"Duplicates: {duplicate_count}")
        self.status_var.set(f"Found {duplicate_count} groups of duplicate files")
    
    def show_smart_select_dialog(self):
        """Show dialog for smart selection options"""
        if not self.duplicates:
            messagebox.showwarning("Warning", "Please scan for duplicates first.")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Smart Selection")
        dialog.geometry("300x200")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        ttk.Label(dialog, text="Select files to keep:", font=('TkDefaultFont', 10, 'bold')).pack(pady=10)
        
        selection_var = tk.StringVar(value="newest")
        
        ttk.Radiobutton(dialog, text="Select newest files", 
                       variable=selection_var, value="newest").pack(anchor=tk.W, padx=20, pady=5)
        ttk.Radiobutton(dialog, text="Select oldest files", 
                       variable=selection_var, value="oldest").pack(anchor=tk.W, padx=20, pady=5)
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Apply Selection", 
                  command=lambda: self.apply_smart_selection(selection_var.get(), dialog)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", 
                  command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def apply_smart_selection(self, selection_type, dialog):
        """Apply smart selection based on file dates"""
        dialog.destroy()
        
        # Clear current selection
        self.tree.selection_remove(self.tree.selection())
        
        selected_items = []
        
        # Process each group
        for group_item in self.tree.get_children():
            file_items = self.tree.get_children(group_item)
            if len(file_items) < 2:
                continue
            
            # Get file info for this group
            files_info = []
            for item in file_items:
                if item in self.tree_items:
                    files_info.append((item, self.tree_items[item]['modified']))
            
            if not files_info:
                continue
            
            # Sort by modification time
            files_info.sort(key=lambda x: x[1])
            
            if selection_type == "newest":
                # Select all except the newest (last in sorted list)
                to_select = [item for item, _ in files_info[:-1]]
            else:  # oldest
                # Select all except the oldest (first in sorted list)
                to_select = [item for item, _ in files_info[1:]]
            
            selected_items.extend(to_select)
        
        # Apply selection
        for item in selected_items:
            self.tree.selection_add(item)
        
        messagebox.showinfo("Smart Selection", f"Selected {len(selected_items)} files.")
    
    def move_selected(self):
        """Move selected files to a new folder"""
        selected_items = self.tree.selection()
        
        if not selected_items:
            messagebox.showwarning("Warning", "Please select files to move.")
            return
        
        # Filter to only file items (not group headers)
        files_to_move = []
        for item in selected_items:
            if item in self.tree_items:
                files_to_move.append(self.tree_items[item]['path'])
        
        if not files_to_move:
            messagebox.showwarning("Warning", "Please select individual files to move (not group headers).")
            return
        
        # Get folder name
        folder_name = simpledialog.askstring("Folder Name", "Enter name for the new folder:")
        if not folder_name:
            return
        
        # Get destination directory
        dest_dir = filedialog.askdirectory(title="Select destination directory")
        if not dest_dir:
            return
        
        # Create the new folder
        new_folder_path = os.path.join(dest_dir, folder_name)
        
        try:
            os.makedirs(new_folder_path, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Could not create folder: {str(e)}")
            return
        
        # Move files
        moved_count = 0
        errors = []
        
        for file_path in files_to_move:
            try:
                filename = os.path.basename(file_path)
                dest_path = os.path.join(new_folder_path, filename)
                
                # Handle duplicate names in destination
                counter = 1
                base_name, ext = os.path.splitext(filename)
                while os.path.exists(dest_path):
                    new_name = f"{base_name}_{counter}{ext}"
                    dest_path = os.path.join(new_folder_path, new_name)
                    counter += 1
                
                shutil.move(file_path, dest_path)
                moved_count += 1
                
                # Remove from tree
                for item, info in list(self.tree_items.items()):
                    if info['path'] == file_path:
                        self.tree.delete(item)
                        del self.tree_items[item]
                        break
                        
            except Exception as e:
                errors.append(f"{os.path.basename(file_path)}: {str(e)}")
        
        # Clean up empty groups
        self.cleanup_empty_groups()
        
        # Show results
        if errors:
            error_msg = f"Moved {moved_count} files successfully to:\n{new_folder_path}\n\nErrors:\n" + "\n".join(errors)
            messagebox.showwarning("Move Complete", error_msg)
        else:
            messagebox.showinfo("Move Complete", f"Successfully moved {moved_count} files to:\n{new_folder_path}")
        
        self.status_var.set(f"Moved {moved_count} files to {folder_name}")
    
    def delete_selected(self):
        """
        Delete selected files
        """
        selected_items = self.tree.selection()
        
        if not selected_items:
            messagebox.showwarning("Warning", "Please select files to delete.")
            return
        
        # Filter to only file items (not group headers)
        files_to_delete = []
        for item in selected_items:
            if item in self.tree_items:
                files_to_delete.append(self.tree_items[item]['path'])
        
        if not files_to_delete:
            messagebox.showwarning("Warning", "Please select individual files to delete (not group headers).")
            return
        
        # Confirm deletion
        file_list = "\n".join([f"• {os.path.basename(f)}" for f in files_to_delete])
        message = f"Are you sure you want to delete the following {len(files_to_delete)} file(s)?\n\n{file_list}"
        
        if messagebox.askyesno("Confirm Deletion", message):
            deleted_count = 0
            errors = []
            
            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    
                    # Remove from tree
                    for item, info in list(self.tree_items.items()):
                        if info['path'] == file_path:
                            self.tree.delete(item)
                            del self.tree_items[item]
                            break
                            
                except Exception as e:
                    errors.append(f"{os.path.basename(file_path)}: {str(e)}")
            
            # Clean up empty groups
            self.cleanup_empty_groups()
            
            # Show results
            if errors:
                error_msg = f"Deleted {deleted_count} files successfully.\n\nErrors:\n" + "\n".join(errors)
                messagebox.showwarning("Deletion Complete", error_msg)
            else:
                messagebox.showinfo("Deletion Complete", f"Successfully deleted {deleted_count} files.")
            
            self.status_var.set(f"Deleted {deleted_count} files")
    
    def cleanup_empty_groups(self):
        """
        Remove empty group headers from the tree
        """
        for item in self.tree.get_children():
            if not self.tree.get_children(item):  # If group has no children
                self.tree.delete(item)
        
        # Update duplicate count
        remaining_groups = len([item for item in self.tree.get_children() if self.tree.get_children(item)])
        self.duplicate_count_var.set(f"Duplicates: {remaining_groups}")
    
    def on_double_click(self, event):
        """Handle double-click on tree items to open files"""
        item = self.tree.selection()[0] if self.tree.selection() else None
        
        if not item:
            return
        
        # Check if it's a file item (not a group header)
        if item in self.tree_items:
            file_path = self.tree_items[item]['path']
            
            if os.path.exists(file_path):
                try:
                    # Cross-platform file opening
                    if platform.system() == 'Windows':
                        os.startfile(file_path)
                    elif platform.system() == 'Darwin':  # macOS
                        subprocess.run(['open', file_path])
                    else:  # Linux and other Unix-like systems
                        subprocess.run(['xdg-open', file_path])
                        
                    self.status_var.set(f"Opened: {os.path.basename(file_path)}")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not open file: {str(e)}")
            else:
                messagebox.showwarning("File Not Found", f"File no longer exists:\n{file_path}")
    
    def clear_results(self):
        """
        Clear all results from the tree
        """
        self.tree.delete(*self.tree.get_children())
        self.tree_items = {}
        self.duplicates = {}
        self.duplicate_count_var.set("Duplicates: 0")
        self.eta_var.set("ETA: --")
        self.progress.configure(value=0)
        self.status_var.set("Ready")

def main():
    root = tk.Tk()
    app = DuplicateDetectorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()

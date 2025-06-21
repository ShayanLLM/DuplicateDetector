#created with Claude. Account: Milobowler

import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from collections import defaultdict
from pathlib import Path
import threading

class DuplicateDetectorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Duplicate File Detector")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Variables
        self.directory_var = tk.StringVar()
        self.duplicates = {}
        self.tree_items = {}
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Directory selection frame
        dir_frame = ttk.LabelFrame(main_frame, text="Directory Selection", padding="10")
        dir_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        dir_frame.columnconfigure(1, weight=1)
        
        ttk.Label(dir_frame, text="Directory:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Entry(dir_frame, textvariable=self.directory_var, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(dir_frame, text="Browse", command=self.browse_directory).grid(row=0, column=2, sticky=tk.W)
        
        # Control buttons frame
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(control_frame, text="Scan for Duplicates", command=self.scan_duplicates).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(control_frame, text="Delete Selected", command=self.delete_selected).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(control_frame, text="Clear Results", command=self.clear_results).grid(row=0, column=2, padx=(0, 10))
        
        # Progress bar
        self.progress = ttk.Progressbar(control_frame, mode='indeterminate')
        self.progress.grid(row=0, column=3, sticky=(tk.W, tk.E), padx=(10, 0))
        control_frame.columnconfigure(3, weight=1)
        
        # Results frame
        results_frame = ttk.LabelFrame(main_frame, text="Duplicate Files", padding="5")
        results_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # Treeview for results
        self.tree = ttk.Treeview(results_frame, columns=('size', 'path'), show='tree headings')
        self.tree.heading('#0', text='Filename')
        self.tree.heading('size', text='Size (bytes)')
        self.tree.heading('path', text='Full Path')
        
        self.tree.column('#0', width=300)
        self.tree.column('size', width=100)
        self.tree.column('path', width=400)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(results_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
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
            file_groups = defaultdict(list)
            file_count = 0
            
            # Walk through all files in directory and subdirectories
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    file_count += 1
                    self.status_var.set(f"Scanning... {file_count} files processed")
                    self.root.update_idletasks()
                    
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
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.status_var.set("Error occurred"))
    
    def scan_duplicates(self):
        """
        Start scanning for duplicates
        """
        self.clear_results()
        self.progress.start()
        self.status_var.set("Scanning for duplicates...")
        
        # Run in separate thread to avoid freezing GUI
        thread = threading.Thread(target=self.find_duplicates_thread)
        thread.daemon = True
        thread.start()
    
    def update_results(self):
        """
        Update the treeview with duplicate results
        """
        self.progress.stop()
        
        if not self.duplicates:
            self.status_var.set("No duplicate files found")
            messagebox.showinfo("Results", "No duplicate files found!")
            return
        
        self.tree_items = {}
        
        for i, (normalized_name, file_paths) in enumerate(self.duplicates.items(), 1):
            # Create parent item for the group
            group_name = f"Group {i}: {' '.join(normalized_name)}"
            parent = self.tree.insert('', 'end', text=group_name, values=('', ''), tags=('group',))
            
            # Add files to the group
            for file_path in file_paths:
                filename = os.path.basename(file_path)
                try:
                    file_size = os.path.getsize(file_path)
                except OSError:
                    file_size = 0
                
                item = self.tree.insert(parent, 'end', text=filename, 
                                      values=(f"{file_size:,}", file_path), tags=('file',))
                self.tree_items[item] = file_path
            
            # Expand the group
            self.tree.item(parent, open=True)
        
        # Configure tags
        self.tree.tag_configure('group', background='lightgray')
        self.tree.tag_configure('file', background='white')
        
        self.status_var.set(f"Found {len(self.duplicates)} groups of duplicate files")
    
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
                files_to_delete.append(self.tree_items[item])
        
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
                    for item, path in list(self.tree_items.items()):
                        if path == file_path:
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
    
    def clear_results(self):
        """
        Clear all results from the tree
        """
        self.tree.delete(*self.tree.get_children())
        self.tree_items = {}
        self.duplicates = {}
        self.status_var.set("Ready")

def main():
    root = tk.Tk()
    app = DuplicateDetectorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()

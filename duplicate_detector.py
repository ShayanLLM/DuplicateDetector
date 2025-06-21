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
        self.directories = []
        self.duplicates = {}
        self.all_duplicate_groups = []
        self.selection_set = set() # Store paths of selected files
        self.current_page = 1
        self.groups_per_page = 100
        self.total_pages = 0
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
        dir_frame.columnconfigure(0, weight=1)
        dir_frame.rowconfigure(0, weight=1)

        self.dir_listbox = tk.Listbox(dir_frame, height=4)
        self.dir_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        dir_buttons_frame = ttk.Frame(dir_frame)
        dir_buttons_frame.grid(row=0, column=1, sticky=(tk.N, tk.S))

        ttk.Button(dir_buttons_frame, text="Add Directory", command=self.add_directory).pack(padx=5, pady=2, fill=tk.X)
        ttk.Button(dir_buttons_frame, text="Remove Selected", command=self.remove_directory).pack(padx=5, pady=2, fill=tk.X)
        
        # Stats frame
        stats_frame = ttk.LabelFrame(main_frame, text="Statistics", padding="10")
        stats_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(stats_frame, textvariable=self.duplicate_count_var, font=('TkDefaultFont', 10, 'bold')).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(stats_frame, textvariable=self.eta_var, font=('TkDefaultFont', 10)).grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        # Control buttons frame
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(control_frame, text="Scan for Duplicates", command=self.scan_duplicates).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(control_frame, text="Select All", command=self.select_all_duplicates).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(control_frame, text="Smart Select", command=self.show_smart_select_dialog).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(control_frame, text="Delete Selected", command=self.delete_selected).grid(row=0, column=3, padx=(0, 5))
        ttk.Button(control_frame, text="Create Folder with Selection", command=self.move_selected).grid(row=0, column=4, padx=(0, 5))
        ttk.Button(control_frame, text="Clear Results", command=self.clear_results).grid(row=0, column=5, padx=(0, 10))
        
        # Progress bar
        self.progress = ttk.Progressbar(control_frame, mode='determinate')
        self.progress.grid(row=0, column=6, sticky=(tk.W, tk.E), padx=(10, 0))
        control_frame.columnconfigure(6, weight=1)
        
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
        
        # Pagination frame
        pagination_frame = ttk.Frame(results_frame)
        pagination_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        pagination_frame.columnconfigure(1, weight=1)

        self.prev_button = ttk.Button(pagination_frame, text="<< Previous", command=self.go_to_previous_page, state=tk.DISABLED)
        self.prev_button.grid(row=0, column=0, sticky=tk.W)

        self.page_label = ttk.Label(pagination_frame, text="Page 1 of 1")
        self.page_label.grid(row=0, column=1, sticky=tk.E)

        self.next_button = ttk.Button(pagination_frame, text="Next >>", command=self.go_to_next_page, state=tk.DISABLED)
        self.next_button.grid(row=0, column=2, sticky=tk.E)
        
        # Bind double-click event to open files
        self.tree.bind('<Double-1>', self.on_double_click)
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=4, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))
        
    def add_directory(self):
        if len(self.directories) >= 20:
            messagebox.showwarning("Warning", "You can select up to 20 directories.")
            return
        directory = filedialog.askdirectory()
        if directory and directory not in self.directories:
            self.directories.append(directory)
            self.dir_listbox.insert(tk.END, directory)

    def remove_directory(self):
        selected_indices = self.dir_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select a directory to remove.")
            return

        for index in sorted(selected_indices, reverse=True):
            self.dir_listbox.delete(index)
            del self.directories[index]

    def on_tree_select(self, event):
        """Update selection_set when user selects/deselects in the tree."""
        # This event can be noisy, so we detach the handler while we manually change selection
        self.tree.unbind('<<TreeviewSelect>>')

        # Get all file paths on the current page
        paths_on_page = set()
        for item in self.tree_items:
            paths_on_page.add(self.tree_items[item]['path'])

        # Get selected paths from the tree
        selected_paths_in_tree = set()
        for item in self.tree.selection():
            if item in self.tree_items:
                selected_paths_in_tree.add(self.tree_items[item]['path'])

        # Remove all paths from this page that were in the master selection
        self.selection_set -= paths_on_page
        # Add back only the ones that are currently selected in the tree
        self.selection_set.update(selected_paths_in_tree)
        
        self.status_var.set(f"{len(self.selection_set)} files selected")

        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)

    def select_all_duplicates(self):
        """Select all file items in the tree."""
        if not self.duplicates:
            messagebox.showwarning("Warning", "Please scan for duplicates first.")
            return
        
        self.selection_set.clear()
        for _, file_paths in self.all_duplicate_groups:
            for path in file_paths:
                self.selection_set.add(path)

        self.display_current_page()
        self.status_var.set(f"Selected {len(self.selection_set)} files.")

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
    
    def count_files(self, directory_paths):
        """Count total files for ETA calculation"""
        total = 0
        try:
            for directory_path in directory_paths:
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
        directory_paths = self.directories
        
        if not directory_paths:
            messagebox.showerror("Error", "Please select at least one directory first.")
            self.progress.stop()
            self.status_var.set("Ready")
            return
        
        for path in directory_paths:
            if not os.path.exists(path):
                messagebox.showerror("Error", f"Directory '{path}' does not exist.")
                self.progress.stop()
                self.status_var.set("Ready")
                return
        
        try:
            # Count files for ETA
            self.status_var.set("Counting files...")
            self.total_files = self.count_files(directory_paths)
            self.processed_files = 0
            self.scan_start_time = time.time()
            
            # Configure progress bar
            self.progress.configure(maximum=self.total_files)
            
            file_groups = defaultdict(list)
            
            # Walk through all files in directory and subdirectories
            for directory_path in directory_paths:
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
    
    def display_current_page(self):
        """Clears and repopulates the tree with the current page of results."""
        self.tree.unbind('<<TreeviewSelect>>')
        self.tree.delete(*self.tree.get_children())
        self.tree_items.clear()
        
        if not self.all_duplicate_groups:
            self.page_label.config(text="Page 1 of 1")
            self.prev_button.config(state=tk.DISABLED)
            self.next_button.config(state=tk.DISABLED)
            self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
            return

        start_index = (self.current_page - 1) * self.groups_per_page
        end_index = start_index + self.groups_per_page
        groups_to_display = self.all_duplicate_groups[start_index:end_index]

        for i, (normalized_name, file_paths) in enumerate(groups_to_display, start=start_index + 1):
            group_name = f"Group {i}: {' '.join(normalized_name)}"
            parent = self.tree.insert('', 'end', text=group_name, values=('', '', ''), tags=('group',))

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
                
                if file_path in self.selection_set:
                    self.tree.selection_add(item)
            
            self.tree.item(parent, open=True)
            
        self.tree.tag_configure('group', background='lightgray')
        self.tree.tag_configure('file', background='white')

        self.page_label.config(text=f"Page {self.current_page} of {self.total_pages}")
        self.prev_button.config(state=tk.NORMAL if self.current_page > 1 else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if self.current_page < self.total_pages else tk.DISABLED)
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)

    def go_to_next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.display_current_page()

    def go_to_previous_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.display_current_page()

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
            self.display_current_page() # Refresh to show empty state
            return
        
        self.all_duplicate_groups = sorted(self.duplicates.items())
        duplicate_count = len(self.all_duplicate_groups)
        self.total_pages = (duplicate_count + self.groups_per_page - 1) // self.groups_per_page
        self.current_page = 1
        
        self.display_current_page()
        
        self.duplicate_count_var.set(f"Duplicates: {duplicate_count}")
        self.status_var.set(f"Found {duplicate_count} groups of duplicate files")
    
    def show_smart_select_dialog(self):
        """Show dialog for smart selection options"""
        if not self.duplicates:
            messagebox.showwarning("Warning", "Please scan for duplicates first.")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Smart Selection")
        dialog.geometry("400x250")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        ttk.Label(dialog, text="Select files to keep (all others will be selected):", font=('TkDefaultFont', 10, 'bold')).pack(pady=10)
        
        selection_var = tk.StringVar(value="newest")
        
        ttk.Radiobutton(dialog, text="Keep newest files", 
                       variable=selection_var, value="newest").pack(anchor=tk.W, padx=20, pady=5)
        ttk.Radiobutton(dialog, text="Keep oldest files", 
                       variable=selection_var, value="oldest").pack(anchor=tk.W, padx=20, pady=5)

        # Directory selection option
        dir_frame = ttk.Frame(dialog)
        dir_frame.pack(anchor=tk.W, padx=20, pady=5, fill=tk.X)
        
        dir_radio = ttk.Radiobutton(dir_frame, text="Keep files from a specific directory", 
                                    variable=selection_var, value="directory")
        dir_radio.pack(side=tk.LEFT)
        
        status_label_text = tk.StringVar()
        if len(self.directories) < 2:
            dir_radio.config(state=tk.DISABLED)
            
            tooltip_label = ttk.Label(dir_frame, text="(?)", cursor="hand2")
            tooltip_label.pack(side=tk.LEFT, padx=(5,0))
            
            def show_tip(event):
                status_label_text.set("Add multiple directories to use this option.")

            def hide_tip(event):
                status_label_text.set("")
            
            tooltip_label.bind("<Enter>", show_tip)
            tooltip_label.bind("<Leave>", hide_tip)
        
        status_label = ttk.Label(dialog, textvariable=status_label_text, foreground="gray")
        status_label.pack(pady=(0, 5))
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Apply Selection", 
                  command=lambda: self.apply_smart_selection(selection_var.get(), dialog)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", 
                  command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def apply_smart_selection(self, selection_type, dialog):
        """Apply smart selection based on file dates or directory"""
        dialog.destroy()

        if selection_type == "directory":
            self.show_directory_selection_dialog()
            return
        
        # Clear current selection
        self.selection_set.clear()
        
        selected_paths = []
        
        # Process each group
        for _, file_paths in self.all_duplicate_groups:
            if len(file_paths) < 2:
                continue
            
            # Get file info for this group
            files_info = []
            for path in file_paths:
                try:
                    mtime = os.path.getmtime(path)
                    files_info.append((path, mtime))
                except OSError:
                    continue
            
            if not files_info:
                continue
            
            # Sort by modification time
            files_info.sort(key=lambda x: x[1])
            
            if selection_type == "newest":
                # Select all except the newest (last in sorted list)
                to_select = [path for path, _ in files_info[:-1]]
            else:  # oldest
                # Select all except the oldest (first in sorted list)
                to_select = [path for path, _ in files_info[1:]]
            
            selected_paths.extend(to_select)
        
        # Apply selection
        self.selection_set.update(selected_paths)
        
        # Refresh the current page to show new selections
        self.display_current_page()
        
        self.status_var.set(f"Selected {len(self.selection_set)} files.")
        messagebox.showinfo("Smart Selection", f"Selected {len(self.selection_set)} files.")

    def show_directory_selection_dialog(self):
        dir_dialog = tk.Toplevel(self.root)
        dir_dialog.title("Select Directories to Keep")
        dir_dialog.geometry("450x300")
        dir_dialog.minsize(350, 250)
        dir_dialog.transient(self.root)
        dir_dialog.grab_set()

        # Center the dialog
        dir_dialog.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (dir_dialog.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (dir_dialog.winfo_height() // 2)
        dir_dialog.geometry(f"+{x}+{y}")
        
        main_frame = ttk.Frame(dir_dialog, padding=(10, 10, 10, 0))
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Select directories whose files you want to keep:").pack(pady=(0, 10), anchor=tk.W)

        # --- Button frame at the bottom ---
        button_frame = ttk.Frame(main_frame, padding=(0, 10, 0, 10))
        button_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        def apply_dir_selection():
            keep_dirs = [dir_path for dir_path, var in self.dir_vars.items() if var.get()]
            if not keep_dirs:
                messagebox.showwarning("Warning", "Please select at least one directory to keep.", parent=dir_dialog)
                return
            dir_dialog.destroy()
            self.perform_directory_based_selection(keep_dirs)

        ttk.Button(button_frame, text="Cancel", command=dir_dialog.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Apply", command=apply_dir_selection).pack(side=tk.RIGHT, padx=5)

        # --- Scrollable frame for the checkboxes ---
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.dir_vars = {}
        for dir_path in self.directories:
            var = tk.BooleanVar(value=False)
            self.dir_vars[dir_path] = var
            
            # Create a frame for each checkbutton and label to allow text wrapping
            item_frame = ttk.Frame(scrollable_frame)
            item_frame.pack(anchor=tk.W, padx=10, pady=2, fill=tk.X)

            cb = ttk.Checkbutton(item_frame, variable=var)
            cb.pack(side=tk.LEFT, anchor=tk.NW, padx=(0, 5))

            label = ttk.Label(item_frame, text=dir_path, wraplength=350, justify=tk.LEFT, cursor="hand2")
            label.pack(side=tk.LEFT, fill=tk.X, expand=True)

            # Allow clicking the label to toggle the checkbox
            label.bind("<Button-1>", lambda event, v=var: v.set(not v.get()))

    def perform_directory_based_selection(self, keep_dirs):
        """Selects all duplicate files except those in the keep_dirs."""
        self.selection_set.clear()
        selected_paths = []

        resolved_keep_paths = []
        for keep_dir in keep_dirs:
            try:
                resolved_keep_paths.append(Path(keep_dir).resolve())
            except FileNotFoundError:
                messagebox.showwarning("Warning", f"The directory '{keep_dir}' no longer exists and will be ignored.")
        
        if not resolved_keep_paths:
            messagebox.showerror("Error", "None of the selected 'keep' directories exist.")
            return

        for _, file_paths in self.all_duplicate_groups:
            files_to_select_in_group = []
            files_to_keep_in_group = []

            for path in file_paths:
                is_in_keep_dir = False
                try:
                    file_path_resolved = Path(path).resolve(strict=True)
                    for keep_path in resolved_keep_paths:
                        try:
                            # Check if the file's path is inside one of the directories to keep
                            file_path_resolved.relative_to(keep_path)
                            is_in_keep_dir = True
                            break # Found a keep directory, no need to check others
                        except ValueError:
                            continue # Not in this keep_dir, check the next one
                    
                    if is_in_keep_dir:
                        files_to_keep_in_group.append(path)
                    else:
                        files_to_select_in_group.append(path)

                except FileNotFoundError:
                    # File might have been deleted since scan.
                    files_to_select_in_group.append(path)

            # If there's at least one file to keep, select all the others in the group.
            if files_to_keep_in_group:
                selected_paths.extend(files_to_select_in_group)
            else:
                # If no files are from the keep_dir (e.g., the group only contains
                # files from other selected directories), we apply a safety rule:
                # select all but one file in the group to avoid deleting all copies.
                if len(file_paths) > 1:
                    files_info = []
                    for path in file_paths:
                        try:
                            mtime = os.path.getmtime(path)
                            files_info.append((path, mtime))
                        except OSError:
                            continue
                    
                    if files_info:
                        # Keep the newest file by default
                        files_info.sort(key=lambda x: x[1])
                        paths_to_add = [path for path, _ in files_info[:-1]]
                        selected_paths.extend(paths_to_add)

        self.selection_set.update(selected_paths)
        
        self.display_current_page()
        
        self.status_var.set(f"Selected {len(self.selection_set)} files.")
        messagebox.showinfo("Smart Selection", f"Selected {len(self.selection_set)} files.")
    
    def move_selected(self):
        """Move selected files to a new folder"""
        files_to_move = list(self.selection_set)
        
        if not files_to_move:
            messagebox.showwarning("Warning", "Please select files to move.")
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
                
            except Exception as e:
                errors.append(f"{os.path.basename(file_path)}: {str(e)}")
        
        if moved_count > 0:
            messagebox.showinfo("Move Complete", f"Successfully moved {moved_count} files to:\n{new_folder_path}")
            # Rescan to update the state
            self.scan_duplicates()
        
        if errors:
            error_msg = f"Moved {moved_count} files successfully to:\n{new_folder_path}\n\nErrors:\n" + "\n".join(errors)
            messagebox.showwarning("Move Complete with Errors", error_msg)
        
        self.status_var.set(f"Moved {moved_count} files to {folder_name}")
    
    def delete_selected(self):
        """
        Delete selected files
        """
        files_to_delete = list(self.selection_set)
        
        if not files_to_delete:
            messagebox.showwarning("Warning", "Please select files to delete.")
            return
        
        # Confirm deletion
        # To avoid a huge confirmation dialog, we'll just show the count
        message = f"Are you sure you want to delete {len(files_to_delete)} selected file(s)?"
        
        if messagebox.askyesno("Confirm Deletion", message):
            deleted_count = 0
            errors = []
            
            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                            
                except Exception as e:
                    errors.append(f"{os.path.basename(file_path)}: {str(e)}")
            
            # Rescan to get the fresh state of duplicates
            if deleted_count > 0:
                 messagebox.showinfo("Deletion Complete", f"Successfully deleted {deleted_count} files. Rescanning for remaining duplicates...")
                 self.scan_duplicates()
            
            # Show results
            if errors:
                error_msg = f"Deleted {deleted_count} files successfully.\n\nErrors during deletion:\n" + "\n".join(errors)
                messagebox.showwarning("Deletion Complete with Errors", error_msg)
            
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
        self.all_duplicate_groups = []
        self.selection_set.clear()
        self.current_page = 1
        self.total_pages = 0
        self.display_current_page()
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

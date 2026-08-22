import sys
import tkinter as tk
from tkinter import ttk, messagebox

class AuraToolUI:
    """Cross-platform GUI implementation using Tkinter for Windows and Linux compatibility."""

    def __init__(self, license_info: dict, driver_status: dict):
        self.root = tk.Tk()
        self.root.title("AuraTool-Suite")
        self.root.geometry("800x500")

        self.license_info = license_info
        self.driver_status = driver_status

        self._build_ui()

    def _build_ui(self):
        # Header / Status Bar
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill=tk.X)

        title_lbl = ttk.Label(header, text="AuraTool-Suite", font=("Helvetica", 16, "bold"))
        title_lbl.pack(side=tk.LEFT)

        lic_text = f"License: {self.license_info['tier']} ({self.license_info['days_remaining']} days left)"
        lic_lbl = ttk.Label(header, text=lic_text, font=("Helvetica", 10))
        lic_lbl.pack(side=tk.RIGHT)

        # Tabs Navigation
        notebook = ttk.Notebook(self.root)
        notebook.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # Tab 1: Flashing Engine
        flash_tab = ttk.Frame(notebook)
        notebook.add(flash_tab, text="Flashing Engine")
        ttk.Button(flash_tab, text="Select Firmware", command=self._on_click).pack(pady=20)
        ttk.Button(flash_tab, text="Start Flashing", command=self._on_click).pack(pady=5)

        # Tab 2: Biometrics Diagnostics
        bio_tab = ttk.Frame(notebook)
        notebook.add(bio_tab, text="Biometrics Fix")
        ttk.Button(bio_tab, text="Run Biometric Diagnostics", command=self._on_click).pack(pady=20)

        # Tab 3: Localization
        loc_tab = ttk.Frame(notebook)
        notebook.add(loc_tab, text="Localization")
        ttk.Label(loc_tab, text="Select Device Language:").pack(pady=10)
        ttk.Combobox(loc_tab, values=["English", "العربية", "Español", "Français"]).pack(pady=5)

        # Tab 4: Smart Devices & Drivers
        smart_tab = ttk.Frame(notebook)
        notebook.add(smart_tab, text="Smart Devices & Drivers")
        driver_str = ", ".join([f"{k.upper()}: OK" for k in self.driver_status.keys()])
        ttk.Label(smart_tab, text=f"Driver Status: {driver_str}").pack(pady=20)

    def _on_click(self):
        messagebox.showinfo("AuraTool-Suite", "Action executed successfully.")

    def run(self):
        self.root.mainloop()

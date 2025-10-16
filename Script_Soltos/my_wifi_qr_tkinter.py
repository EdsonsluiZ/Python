# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

"""
Wi-Fi QR Code Generator (GUI version)
Author: Edson Luiz
"""

import tkinter as tk
from tkinter import ttk, messagebox
from wifi_qrcode_generator import wifi_qrcode
from PIL import Image, ImageTk
import os


class WifiQRApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Wi-Fi QR Code Generator")
        self.geometry("400x600")
        self.resizable(False, False)

        # Variables
        self.ssid_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.auth_type_var = tk.StringVar(value="WPA")
        self.hidden_var = tk.BooleanVar()

        # UI
        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self, text="Wi-Fi QR Code Generator", font=("Segoe UI", 16, "bold")).pack(pady=15)

        frame = ttk.Frame(self)
        frame.pack(pady=5, padx=10, fill="x")

        ttk.Label(frame, text="SSID (Network Name):").pack(anchor="w", pady=2)
        ttk.Entry(frame, textvariable=self.ssid_var).pack(fill="x", pady=2)

        ttk.Label(frame, text="Password:").pack(anchor="w", pady=2)
        ttk.Entry(frame, textvariable=self.password_var, show="*").pack(fill="x", pady=2)

        ttk.Label(frame, text="Authentication Type:").pack(anchor="w", pady=2)
        ttk.Combobox(frame, textvariable=self.auth_type_var,
                     values=["WPA", "WEP", "nopass"], state="readonly").pack(fill="x", pady=2)

        ttk.Checkbutton(frame, text="Hidden network", variable=self.hidden_var).pack(anchor="w", pady=5)

        ttk.Button(frame, text="Generate QR Code", command=self.generate_qr).pack(pady=10)

        # Image display
        self.qr_label = ttk.Label(self)
        self.qr_label.pack(pady=10)

    def generate_qr(self):
        ssid = self.ssid_var.get().strip()
        password = self.password_var.get().strip()
        auth_type = self.auth_type_var.get()
        hidden = self.hidden_var.get()

        if not ssid:
            messagebox.showerror("Error", "SSID (network name) is required.")
            return

        try:
            qr = wifi_qrcode(ssid, hidden=hidden, authentication_type=auth_type, password=password)
            qr_img = qr.make_image()
            save_path = os.path.join(os.getcwd(), f"{ssid}_wifi_qr.png")
            qr_img.save(save_path)

            # Show QR image in window
            img = Image.open(save_path).resize((250, 250))
            self.qr_photo = ImageTk.PhotoImage(img)
            self.qr_label.config(image=self.qr_photo)
            messagebox.showinfo("Success", f"QR code saved as:\n{save_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate QR code:\n{e}")


if __name__ == "__main__":
    app = WifiQRApp()
    app.mainloop()

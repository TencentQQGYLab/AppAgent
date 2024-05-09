import sys
import threading
import time
from tkinter import messagebox, filedialog, ttk  
import customtkinter as ctk
import tkinter as tk
import subprocess
import os


class AppAgentGUI(ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.title("Self Explorer")
        self.geometry("900x450")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.navigation_frame = ctk.CTkFrame(self, corner_radius=0)
        self.navigation_frame.grid(row=0, column=0, sticky="nsew")
        self.navigation_frame.grid_rowconfigure(4, weight=1)

        self.navigation_frame_label = ctk.CTkLabel(
            self.navigation_frame,
            text="  Self Explorer",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self.navigation_frame_label.grid(row=0, column=0, padx=20, pady=20)

        self.step1_button = ctk.CTkButton(
            self.navigation_frame,
            corner_radius=0,
            height=40,
            border_spacing=10,
            text="Step 1: App & URL",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            command=None,
        )
        self.step1_button.grid(row=1, column=0, sticky="ew")

        self.step2_button = ctk.CTkButton(
            self.navigation_frame,
            corner_radius=0,
            height=40,
            border_spacing=10,
            text="Step 2: Comments & Persona",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            command=None,
        )
        self.step2_button.grid(row=2, column=0, sticky="ew")

        self.step3_button = ctk.CTkButton(
            self.navigation_frame,
            corner_radius=0,
            height=40,
            border_spacing=10,
            text="Step 3: Results",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            command=None, 
        )
        self.step3_button.grid(row=3, column=0, sticky="ew")

        self.step1_frame = self.create_step1_frame()
        self.step2_frame = self.create_step2_frame()
        self.step3_frame = self.create_step3_frame()

        self.select_frame_by_name("step1")

    def create_step1_frame(self):
        frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(4, weight=1)  # Add this line

        app_label = ctk.CTkLabel(frame, text="What is the name of the target app?", width=20)
        app_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        frame.app_entry = ctk.CTkEntry(frame, placeholder_text="App", width=50)
        frame.app_entry.grid(row=0, column=1, padx=20, pady=20, sticky="ew")

        url_label = ctk.CTkLabel(frame, text="Figma Prototype URL", width=20)
        url_label.grid(row=1, column=0, padx=20, pady=20, sticky="w")
        frame.url_entry = ctk.CTkEntry(frame, placeholder_text="Figma URL", width=50)
        frame.url_entry.grid(row=1, column=1, padx=20, pady=20, sticky="ew")

        password_label = ctk.CTkLabel(frame, text="Figma Prototype Password", width=20)
        password_label.grid(row=2, column=0, padx=20, pady=20, sticky="w")
        frame.password_entry = ctk.CTkEntry(
            frame, placeholder_text="Figma Prototype Password", width=50
        )
        frame.password_entry.grid(row=2, column=1, padx=20, pady=20, sticky="ew")

        frame.next_button = ctk.CTkButton(
            frame, text="Next", state="disabled", command=self.step2_button_event
        )
        frame.next_button.grid(row=5, column=1, padx=20, pady=20, sticky="se")  # Change this line

        frame.app_entry.bind(
            "<KeyRelease>", lambda event: self.check_step1_fields(frame)
        )
        frame.url_entry.bind(
            "<KeyRelease>", lambda event: self.check_step1_fields(frame)
        )

        return frame

    def create_step2_frame(self):
        frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        command_label = ctk.CTkLabel(frame, text="Please enter the description of the task you want me to complete in a few sentences:", width=20)
        command_label.grid(row=0, column=0, padx=(20, 0), pady=(20, 10), sticky="nw")

        frame.command_text = tk.Text(frame, width=1, height=10)
        frame.command_text.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")

        persona_label = ctk.CTkLabel(frame, text="(Optional) Please enter the description of the user persona you'd like me to emulate : ", width=20)
        persona_label.grid(row=2, column=0, padx=(20, 0), pady=(20, 10), sticky="nw")

        frame.persona_text = tk.Text(frame, width=1, height=2)
        frame.persona_text.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        frame.persona_text.bind("<FocusIn>", lambda args: frame.persona_text.delete("1.0", "end"))

        frame.next_button = ctk.CTkButton(frame, text="Next", state="disabled", command=self.step3_button_event)
        frame.next_button.grid(row=4, column=0, padx=20, pady=20, sticky="se")

        frame.command_text.bind("<KeyRelease>", lambda event: self.check_step2_fields(frame))

        return frame

    def check_step1_fields(self, frame):
        app = frame.app_entry.get()
        url = frame.url_entry.get()

        if app and url:
            frame.next_button.configure(state="normal")
        else:
            frame.next_button.configure(state="disabled")

    def check_step2_fields(self, frame):
        if frame.command_text.get("1.0", "end").strip():
            frame.next_button.configure(state="normal")
        else:
            frame.next_button.configure(state="disabled")

    def create_step3_frame(self):
        frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure((0, 1, 2), weight=1)  # Add weights to center widgets vertically

        success_label = ctk.CTkLabel(frame, text="Request successful: Chrome browser will automatically open and perform your task.")
        success_label.grid(row=0, column=0, padx=20, pady=(20, 5))  # Reduce padding at the bottom

        style = ttk.Style()
        style.configure("TProgressbar", thickness=50)
        self.progress = ttk.Progressbar(frame, mode='indeterminate', style="TProgressbar")
        self.progress.grid(row=1, column=0, padx=20, pady=5)  # Reduce padding on the top and bottom

        quit_button = ctk.CTkButton(
            frame,
            text="Quit",
            command=self.quit_app,
        )
        quit_button.grid(row=2, column=0, padx=20, pady=(5, 20))  # Reduce padding at the top

        return frame

    def select_frame_by_name(self, name):
        self.step1_button.configure(fg_color=("gray75", "gray25") if name == "step1" else "transparent")
        self.step2_button.configure(fg_color=("gray75", "gray25") if name == "step2" else "transparent")
        self.step3_button.configure(fg_color=("gray75", "gray25") if name == "step3" else "transparent")

        if name == "step1":
            self.step1_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.step1_frame.grid_forget()
        if name == "step2":
            self.step2_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.step2_frame.grid_forget()
        if name == "step3":
            self.step3_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.step3_frame.grid_forget()

    def step2_button_event(self):
        self.select_frame_by_name("step2")

    def step3_button_event(self):
        self.select_frame_by_name("step3")
        self.progress.start()

        command_text = self.step2_frame.command_text.get("1.0", "end").strip()
        persona_text = self.step2_frame.persona_text.get("1.0", "end").strip()
        app = self.step1_frame.app_entry.get()
        url = self.step1_frame.url_entry.get()
        password = self.step1_frame.password_entry.get()

        threading.Timer(1.0, self.run_script, args=[app, url, command_text, persona_text, password]).start()

    def run_script(self, app, url, command_text, persona_text=None, password=None):
        # Check if the script is running as a PyInstaller bundle
        if getattr(sys, 'frozen', False):
            # If the script is running as a PyInstaller bundle, use the _MEIPASS directory
            root_dir = sys._MEIPASS
            script_path = os.path.join(root_dir, "scripts/self_explorer_figma.py")
            script_args = [script_path, "--app", app, "--url", url, "--task_desc", f'"{command_text}"', "--ui", "True", "--root_dir", root_dir]
        else:
            # If the script is running from a Python interpreter, use without root_dir
            os.chdir(os.path.dirname(os.path.abspath(__file__)))
            script_path = "scripts/self_explorer_figma.py"
            script_args = ["python", script_path, "--app", app, "--url", url, "--task_desc", f'"{command_text}"', "--ui", "True"]


        if password:
            script_args.extend(["--password", password])
        if persona_text:
            script_args.extend(["--persona_desc", f'"{persona_text}"'])

        subprocess.run(script_args)

        # Stop the progress bar
        self.progress.stop()

    def quit_app(self):
        os._exit(0)


if __name__ == "__main__":
    app = AppAgentGUI()
    app.mainloop()
"""Full-screen flashing alert window for OptiQuake Local.
Copyright (c) 2026 Lic. Juan Esteban Ramírez
SPDX-License-Identifier: AGPL-3.0-only

Run as a separate process by quake_alerts.WindowChannel; reads the alert as
JSON from stdin. Exits quietly if tkinter is not available.
"""
import json, sys

def main():
    alert = json.loads(sys.stdin.read() or "{}")
    try:
        import tkinter as tk
    except ImportError:
        return 3
    root = tk.Tk()
    root.title(alert.get("title", "ALERTA"))
    root.attributes("-fullscreen", True)
    root.attributes("-topmost", True)
    strong = alert.get("alert") in ("strong", "local")
    colors = ("#c00000", "#ffffff") if strong else ("#e06000", "#ffffff")
    frame = tk.Frame(root, bg=colors[0])
    frame.pack(fill="both", expand=True)
    title = tk.Label(frame, text=alert.get("title", ""), font=("Segoe UI", 72, "bold"),
                     fg=colors[1], bg=colors[0])
    title.pack(pady=(60, 20))
    width = max(600, root.winfo_screenwidth() - 160)
    labels = []
    for i, line in enumerate(alert.get("lines", [])):
        big = line.isupper() and len(line) < 60
        lbl = tk.Label(frame, text=line, wraplength=width, justify="center",
                       font=("Segoe UI", 44 if big else 22, "bold" if big else "normal"),
                       fg=colors[1], bg=colors[0])
        lbl.pack(pady=8)
        labels.append(lbl)
    tk.Button(frame, text=alert.get("ok", "OK"), font=("Segoe UI", 28, "bold"),
              command=root.destroy, padx=40, pady=10).pack(pady=40)
    root.bind("<Escape>", lambda e: root.destroy())
    state = {"on": False}
    def flash():
        state["on"] = not state["on"]
        bg, fg = (colors[1], colors[0]) if state["on"] else colors
        for w in [frame, title, *labels]:
            w.configure(bg=bg)
        for w in [title, *labels]:
            w.configure(fg=fg)
        root.after(500, flash)
    flash()
    root.after(10 * 60 * 1000, root.destroy)
    root.lift(); root.focus_force()
    root.mainloop()
    return 0

if __name__ == "__main__":
    sys.exit(main())

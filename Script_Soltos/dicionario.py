# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

import tkinter as tk, time, threading, random

responnses = ["Thinking Deeply...", "Analysing...", "Got it! Here´s what I think "]

def respond():
    def run():
        ai_text.set("@ " + random.choice(responnses))
        for _ in range(3):
            time.sleep(0.3)
            ai_text.set(ai_text.get() + ".")
        threading.Thread(target=run).start()

root = tk.Tk()
root.title("AI Prompt Interface")
tk.Label(root, text="Enter your prompt:").pack()
entry = tk.Entry(root, width=40); entry.pack(pady=5)
tk.Button(root, text="Ask AI", command=respond).pack()
ai_text = tk.StringVar()
tk.Label(root, textvariable=ai_text, font=("Courier", 12), fg=("blue")).pack(pady=10)
root.mainloop()
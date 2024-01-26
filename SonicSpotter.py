import pyautogui
import threading
import os
import time
import winsound
import tkinter as tk
from tkinter import filedialog, messagebox
import sys
from pynput.mouse import Listener
import json
import subprocess


current_directory = os.getcwd()
root = tk.Tk()
frequency = 2500  # Set frequency (in Hertz)
duration = 1000  # Set duration (in milliseconds)

# todo clear alert
# todo clear single image from the list
# todo different icon?
# todo help section or readme instruction
# todo logging


def region_change_confirmation():
    for _ in range(2):
        winsound.Beep(frequency=1500, duration=100)
        time.sleep(0.1)


class GUI:
    def __init__(self, master):
        self.master = master
        master.title("Sonic Spotter")
        self.load_image_button = None
        self.image_listbox = None
        self.image_manger_window = None
        self.event = None
        self.program_is_running = True
        self.thread = None
        self.window_closed = False
        self.region = None
        self.alert_sound_file_path = None
        self.listener_thread = None
        self.alert_sound_thread = None
        self.alert_sound_process = None
        self.mouse_click_counter = 0
        self._x, self._y = 0, 0
        self.mouse_listener = None
        self.alert_intervals = 1
        self.searched_objects = []

        self.load_settings()

        # Buttons
        self.select_region_button = tk.Button(self.master, text="Select search region",
                                              command=self.select_region_trigger)
        self.select_region_button.pack(pady=10)

        self.searched_images_manager_button = tk.Button(self.master, text="Searched images manager",
                                                        command=self.searched_objects_manager)
        self.searched_images_manager_button.pack(pady=10)

        self.run_program_button = tk.Button(self.master, fg="white", bg="red", text="Run program",
                                            command=self.run_search)
        self.run_program_button.pack(pady=10)

        # Variables
        self.region_label = tk.Label(master, text=f"Region: {self.region}")
        self.region_label.pack(pady=10)

        # Menu
        self.menu_bar = tk.Menu(self.master)
        self.filemenu = tk.Menu(self.menu_bar, tearoff=0)
        self.filemenu.add_command(label="Change alert sound", command=self.load_sound_file)
        self.filemenu.add_command(label="Change alert intervals", command=self.change_alert_intervals)

        self.filemenu.add_separator()
        self.filemenu.add_command(label="Exit", command=self.save_and_quit)
        self.menu_bar.add_cascade(label="Options", menu=self.filemenu)

        self.master.config(menu=self.menu_bar)

        # https://www.tutorialspoint.com/python/tk_menu.htm

    def save_and_quit(self):
        self.save_settings()
        self.master.destroy()

    def update_run_icon_color(self):
        if self.program_is_running:
            color = "green"
            text = "Stop program"
            command = self.stop_program
        else:
            color = "red"
            text = "Run program"
            command = self.run_search
        self.run_program_button.configure(bg=color, text=text, command=command)

    def change_alert_intervals(self):
        interval_window = tk.Toplevel(root)
        interval_window.title("Change Intervals")
        current_interval = tk.Label(interval_window, text=f"Current interval: {self.alert_intervals}s")
        current_interval.pack(pady=10)

        label = tk.Label(interval_window, text="Enter new interval:")
        label.pack(pady=10)

        entry_var = tk.StringVar()
        entry = tk.Entry(interval_window, textvariable=entry_var)
        entry.pack(pady=10, padx=15)

        def set_interval():
            try:
                new_interval = int(entry_var.get())
                if new_interval < 0:
                    raise ValueError
                self.alert_intervals = new_interval
                current_interval.config(text=f"Current interval: {self.alert_intervals}s")
            except ValueError:
                print("Invalid input. Please enter a valid, non negative, integer.")

        confirm_button = tk.Button(interval_window, text="Set Interval", command=set_interval)
        confirm_button.pack(pady=10)

    def select_region(self):
        def on_click(x, y, button, pressed):
            try:
                if self.mouse_click_counter == 1:
                    self._x, self._y = x, y

                if self.mouse_click_counter > 1:
                    x_, y_ = x, y
                    higher_x_value, lower_x_value = max(x_, self._x), min(x_, self._x)
                    higher_y_value, lower_y_value = max(y_, self._y), min(y_, self._y)
                    self.region = (lower_x_value, lower_y_value, (higher_x_value - lower_x_value),
                                   (higher_y_value - lower_y_value))
                    self.mouse_click_counter = 0
                    self.region_label.config(text=f"Region: {self.region}")
                    self.region_selection_confirmation_thread = threading.Thread(target=region_change_confirmation)
                    self.region_selection_confirmation_thread.start()
                    stop_listener()

                self.mouse_click_counter += 1

            except Exception as e:
                print(f"Error: {e}")

        def start_listener():
            self.listener_thread = threading.Thread(target=run_listener)
            self.listener_thread.start()

        def run_listener():
            with Listener(on_click=on_click) as self.mouse_listener:
                self.mouse_listener.join()

        def stop_listener():
            self.mouse_listener.stop()

        if self.mouse_listener is not None and self.mouse_listener.is_alive():
            stop_listener()
        self.region = None
        self.mouse_click_counter = 0
        time.sleep(0.1)
        start_listener()

    def load_image(self):
        file_path = filedialog.askopenfilename(title="Select an image",
                                               filetypes=[("Image files", "*.png;*.jpg;*.jpeg")])
        if file_path:
            listbox_size = self.image_listbox.size()
            for i in range(listbox_size):
                item = self.image_listbox.get(i)
                if file_path == item:
                    messagebox.showerror(title="Duplicate entry", message="This file is already on the list.")
                    return
            self.searched_objects.append(file_path)
            self.image_listbox.insert(tk.END, file_path)

    def load_sound_file(self):
        file_path = filedialog.askopenfilename(title="Select a sound file",
                                               filetypes=[("Sound files", "*.mp3;*.wav")])
        if file_path:
            self.alert_sound_file_path = file_path

    def searched_objects_manager(self):
        # Image manager
        self.image_manger_window = tk.Toplevel(self.master)
        self.image_manger_window.title("Image Manager")
        self.image_manger_window.geometry("310x300")

        self.image_listbox = tk.Listbox(self.image_manger_window)
        self.image_listbox.pack(ipadx=60, pady=10)
        for image_path in self.searched_objects:
            self.image_listbox.insert(tk.END, image_path)

        self.load_image_button = tk.Button(self.image_manger_window, text="Load Images", command=self.load_image)
        self.load_image_button.pack(pady=10)

        clear_button = tk.Button(self.image_manger_window, text="Clear List", command=self.clear_searched_objects)
        clear_button.pack(pady=10)

    def clear_searched_objects(self):
        self.image_listbox.delete(0, tk.END)
        self.searched_objects.clear()

    def run_search(self):
        if len(self.searched_objects) > 0:
            # Implement the functionality for "Run program" button
            self.thread = threading.Thread(target=self.search_for_object_trigger)
            self.thread.start()
            self.update_run_icon_color()
        else:
            messagebox.showinfo(title="Error", message="Searched object was not declared.")

    def stop_program(self):
        self.program_is_running = False
        self.update_run_icon_color()
        if self.alert_sound_process and self.alert_sound_process.poll() is None:
            self.alert_sound_process.terminate()

    # Need to use the trigger option, as forwarding threading.Thread with function ending with function activator
    # does not allow for separate running of GUI and the search function, thus beating the purpose of threading.
    def search_for_object_trigger(self):
        self.search_for_object(self.searched_objects)

    def select_region_trigger(self):
        self.select_region()

    def search_for_object(self, objects_to_search_for):
        while self.program_is_running:
            object_present = False
            for searched_object in objects_to_search_for:
                if self.window_closed:
                    sys.exit()
                if self.region is not None:
                    try:
                        object_present = pyautogui.locateCenterOnScreen(searched_object,
                                                                        grayscale=False,
                                                                        confidence=0.8,
                                                                        region=self.region)
                    except Exception as e:
                        pass
                else:
                    try:
                        object_present = pyautogui.locateCenterOnScreen(searched_object,
                                                                        grayscale=False,
                                                                        confidence=0.8)
                    except Exception as e:
                        pass
                if object_present:
                    if self.alert_sound_thread is not None and self.alert_sound_thread.is_alive():
                        pass
                    else:
                        self.alert_sound_thread = threading.Thread(target=self.play_alert_sound)
                        self.alert_sound_thread.start()

        self.program_is_running = True

    def play_alert_sound(self):
        alert_file_path = self.alert_sound_file_path
        if alert_file_path:
            try:
                if self.alert_sound_process and self.alert_sound_process.poll() is None:
                    pass
                else:
                    self.alert_sound_process = subprocess.Popen(["powershell", f"(New-Object Media.SoundPlayer "
                                                                               f"'{self.alert_sound_file_path}')"
                                                                               f".PlaySync()"],
                                                                creationflags=subprocess.CREATE_NO_WINDOW)
            except Exception as e:
                print(f'Exception {e}')
                winsound.Beep(frequency=frequency, duration=duration)
            time.sleep(self.alert_intervals)
        else:
            winsound.Beep(frequency=frequency, duration=duration)
            time.sleep(self.alert_intervals)

    def save_settings(self):
        # Save settings to a file
        settings = {'paths': self.searched_objects, 'sound_file_path': self.alert_sound_file_path, 'region': self.region,
                    'intervals': self.alert_intervals}
        with open('settings.json', 'w') as file:
            json.dump(settings, file)

    def load_settings(self):
        try:
            # Load settings from file
            with open('settings.json', 'r') as file:
                settings = json.load(file)
                try:
                    if settings['paths']:
                        self.searched_objects = settings['paths']
                except:
                    pass
                try:
                    if settings['sound_file_path']:
                        self.alert_sound_file_path = settings['sound_file_path']
                except:
                    pass
                try:
                    if settings['region']:
                        self.region = tuple(settings['region'])
                except:
                    pass
                try:
                    if settings['intervals']:
                        self.alert_intervals = settings['intervals']
                except:
                    pass
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    app = GUI(root)

    def on_closing():
        app.save_settings()
        app.window_closed = True
        if app.mouse_listener and app.mouse_listener.is_alive():
            app.mouse_listener.stop()
        root.destroy()

    root.geometry("250x200")
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

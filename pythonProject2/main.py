# Current Date and Time (UTC - YYYY-MM-DD HH:MM:SS formatted): 2025-05-05 18:12:43
# Current User's Login: erik1567

import io
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import cv2
import webbrowser
import datetime
import os
import shutil
import threading
import re
import easyocr
import requests

VALID_COUNTY_CODES = ["DP", "DR", "DT", "RD", "RR", "RT", "RX",
                      "RK", "AX", "TR", "AR", "ZR", "XC", "ZC",
                      "MM", "XM", "XB", "XT", "ZT", "BV", "ZV",
                      "XR", "TF", "XZ", "ZB", "KL", "KC", "CJ",
                      "KT", "KZ", "DX", "DZ", "HD", "MH", "VN",
                      "GL", "ZL", "GG", "MX", "MZ", "IZ", "HR",
                      "XH", "ZH", "NT", "NZ", "AS", "AZ", "PH",
                      "PX", "PK", "KS", "VX", "SM", "KV", "SB",
                      "SR", "OT", "SL", "SZ", "SV", "XV", "TM",
                      "TZ", "DD", "GZ", "MS", "ZS", "TC", "VS", "SX"
                      ]
class DocumentProcessor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.crop = None
        self.ocr_text = None
        image = cv2.imread(file_path)
        if image is None:
            raise ValueError(f"Could not load image from {file_path}")
        lower, upper = (110, 110, 100), (255, 255, 255)
        mask = cv2.inRange(image, lower, upper)
        contours = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = contours[0] if len(contours) == 2 else contours[1]
        if not contours:
            raise ValueError("No contours found in the image")
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        self.crop = image[y:y + h, x:x + w]

    def extract_cnp(self):
        reader = easyocr.Reader(['en'], gpu=False)
        results = reader.readtext(self.crop, detail=0, paragraph=True)
        self.ocr_text = " ".join(results)
        cnp_pattern = r"\bCNP[\s:]*(\d{13})\b"
        print("OCR Text for CNP:", self.ocr_text)
        match = re.search(cnp_pattern, self.ocr_text)
        return match.group(1) if match else None

    def extract_series(self):
        if self.ocr_text is None:
             reader = easyocr.Reader(['en'], gpu=False)
             results = reader.readtext(self.crop, detail=0, paragraph=True)
             self.ocr_text = " ".join(results)
             print("OCR Text for Series:", self.ocr_text)
        county_codes_pattern = "|".join(VALID_COUNTY_CODES)
        pattern = rf"\b({county_codes_pattern})[^\d]*?(\d{{6}})\b"
        matches = re.findall(pattern, self.ocr_text)
        cleaned_series_list = [f"{code}{digits}" for code, digits in matches]
        return cleaned_series_list[0] if cleaned_series_list else None

class WebcamApp:
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)
        self.options_frame = ttk.Frame(window)
        self.options_frame.pack(pady=20)
        self.capture_btn = ttk.Button(self.options_frame, text="Capture Photo", command=self.start_capture)
        self.capture_btn.pack(side=tk.LEFT, padx=10)
        self.upload_btn = ttk.Button(self.options_frame, text="Upload File", command=self.upload_file)
        self.upload_btn.pack(side=tk.LEFT, padx=10)
        self.browser_btn = ttk.Button(self.options_frame, text="Open Browser", command=lambda: webbrowser.open("https://192.168.0.102"))
        self.browser_btn.pack(side=tk.LEFT, padx=10)
        self.save_dir = "captured_frames"
        os.makedirs(self.save_dir, exist_ok=True)
        self.is_capturing = False
        self.window.protocol("WM_DELETE_WINDOW", self.close_app)

    def start_capture(self):
        self.options_frame.pack_forget()
        self.vid = cv2.VideoCapture(0)
        if not self.vid.isOpened():
            messagebox.showerror("Error", "Could not open webcam")
            self.options_frame.pack(pady=20)
            return
        self.canvas = tk.Canvas(self.window, width=int(self.vid.get(3)), height=int(self.vid.get(4)))
        self.canvas.pack(padx=10, pady=10)
        self.btn_frame = ttk.Frame(self.window)
        self.btn_frame.pack(pady=10)
        ttk.Button(self.btn_frame, text="Capture Frame", command=self.capture_frame).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.btn_frame, text="Exit", command=self.exit_capture).pack(side=tk.LEFT, padx=5)
        self.is_capturing = True
        self.update()

    def update(self):
        if self.is_capturing and hasattr(self, 'vid') and self.vid.isOpened():
            ret, frame = self.vid.read()
            if ret:
                self.frame_for_capture = frame
                display_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.photo = ImageTk.PhotoImage(image=Image.fromarray(display_frame))
                self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
            self.window.after(15, self.update)

    def capture_frame(self):
        if hasattr(self, 'frame_for_capture'):
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.save_dir, f"capture_{timestamp}.jpg")
            self.show_preview(frame_bgr=self.frame_for_capture, save_path=filename)
        else:
             messagebox.showwarning("Capture Error", "No frame available.")

    def upload_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
        if file_path:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = os.path.splitext(file_path)[1]
            save_path = os.path.join(self.save_dir, f"upload_{timestamp}{ext}")
            self.show_preview(file_path=file_path, save_path=save_path)

    def show_preview(self, file_path=None, frame_bgr=None, save_path=None):
        preview = tk.Toplevel(self.window)
        preview.title("Image Preview")
        img = None
        try:
            if file_path:
                img = Image.open(file_path)
            elif frame_bgr is not None:
                img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
            else:
                 raise ValueError("No image source provided for preview")
            img.thumbnail((800, 800))
            photo = ImageTk.PhotoImage(img)
            label = tk.Label(preview, image=photo)
            label.image = photo
            label.pack(padx=10, pady=10)
            btn_frame = ttk.Frame(preview)
            btn_frame.pack(pady=10)
            ttk.Button(btn_frame, text="Process", command=lambda: self.process_image(preview, file_path, frame_bgr, save_path)).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Discard", command=preview.destroy).pack(side=tk.LEFT, padx=5)
        except Exception as e:
             messagebox.showerror("Preview Error", f"Failed to show preview: {e}", parent=preview)
             if preview.winfo_exists(): preview.destroy()

    def process_image(self, preview, file_path, frame_bgr, save_path):
        try:
            if frame_bgr is not None:
                cv2.imwrite(save_path, frame_bgr)
            elif file_path:
                shutil.copy(file_path, save_path)
            else:
                raise ValueError("No image data to save.")
            preview.destroy()
            self.send_to_processing_thread(save_path)
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save image: {e}")
            if preview.winfo_exists(): preview.destroy()

    def send_to_processing_thread(self, image_path):
        self.show_loading()
        threading.Thread(target=self.process_with_ocr, args=(image_path,), daemon=True).start()

    def process_with_ocr(self, image_path):
        try:
            doc = DocumentProcessor(image_path)
            cnp = doc.extract_cnp()
            series = doc.extract_series()
            crop_data = doc.crop
            self.window.after(0, self.show_ocr_results, image_path, cnp, series, crop_data)
        except Exception as e:
            self.window.after(0, messagebox.showerror, "Processing Error", str(e))
            self.window.after(0, self.hide_loading)

    def show_ocr_results(self, image_path, cnp, series, crop_data):
        self.hide_loading()
        result_window = tk.Toplevel(self.window)
        result_window.title("OCR Results")
        main_frame = ttk.Frame(result_window)
        main_frame.pack(padx=20, pady=20)
        cnp_display = cnp if cnp else "Not Found"
        series_display = series if series else "Not Found"
        result_text = f"Extracted data:\n  CNP: {cnp_display}\n  Series: {series_display}"
        ttk.Label(main_frame, text=result_text).pack(pady=10)
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=15)

        can_send = cnp and series and crop_data is not None
        send_button_state = tk.NORMAL if can_send else tk.DISABLED

        # --- Store the send button widget ---
        send_button = ttk.Button(
            btn_frame,
            text="Send to Server",
            state=send_button_state
        )
        # --- Assign command, passing the button itself ---
        send_button.config(command=lambda: self.send_to_server(send_button, cnp, series, image_path, crop_data)) # Pass button
        send_button.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="Discard",
            command=lambda: self.discard_action(result_window, image_path)
        ).pack(side=tk.LEFT, padx=5)

    def discard_action(self, window_to_close, image_path):
         window_to_close.destroy()
         if os.path.exists(image_path):
             try:
                 os.remove(image_path)
                 print(f"Discarded and removed: {image_path}")
             except OSError as e:
                 print(f"Error removing discarded file {image_path}: {e}")

    # --- MODIFIED: Accepts send_button, does NOT destroy window ---
    def send_to_server(self, send_button, cnp, series, image_path, cropped_image_data):
        """Sends data using CROPPED image buffer. Keeps results window open."""

        # --- MODIFICATION: Disable button ---
        send_button.config(state=tk.DISABLED)

        # --- MODIFICATION: Removed window destroy ---
        # if result_window.winfo_exists():
        #      result_window.destroy() # DO NOT DESTROY

        self.show_loading()
        image_byte_stream = None
        files_to_send = {}
        try:
            jpeg_quality = 85
            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality]
            print(f"Encoding cropped image with JPEG quality: {jpeg_quality}")
            encode_success, buffer = cv2.imencode('.jpg', cropped_image_data, encode_params)
            if not encode_success:
                raise ValueError("Failed to encode cropped image to JPEG format.")
            image_byte_stream = io.BytesIO(buffer.tobytes())
            filename = f"crop_{cnp}_{series}.jpg"
            files_to_send['image'] = (filename, image_byte_stream, 'image/jpeg')
            print(f"Prepared buffer: {len(image_byte_stream.getvalue())} bytes")
        except Exception as e:
             self.hide_loading()
             messagebox.showerror("Encoding Error", f"Failed to prepare image buffer: {e}")
             if image_byte_stream: image_byte_stream.close()
             # --- MODIFICATION: Re-enable button on encoding error ---
             send_button.config(state=tk.NORMAL)
             return

        data_form = {"cnp": str(cnp), "series": str(series)}

        # Pass the button to the thread args so it can be re-enabled in the callback
        threading.Thread(target=self._send_request_thread,
                         args=(data_form, files_to_send, image_byte_stream, image_path, send_button), # Pass button
                         daemon=True).start()

    # --- MODIFIED: Accepts send_button ---
    def _send_request_thread(self, data_form, files_dict, image_stream_to_close, original_file_path, send_button):
         """Actual network request logic, runs in thread"""
         server_url = 'https://192.168.0.102/api/receive-data/'
         success = False
         response_message = "An unknown error occurred."
         status_code = -1
         try:
            print(f"Sending data for CNP {data_form.get('cnp')}...")
            response = requests.post(server_url, data=data_form, files=files_dict, verify=False)
            status_code = response.status_code
            print(f"Server Response Status: {status_code}")
            if 200 <= status_code < 300:
                try:
                    response_data = response.json()
                    response_message = response_data.get('message', 'Data sent successfully!')
                    success = True
                except requests.exceptions.JSONDecodeError:
                    response_message = "Data sent, but received non-JSON response."
                    success = True
            else:
                 response_message = f"Server returned error: {status_code}\n{response.text[:200]}"
         except requests.exceptions.RequestException as e:
            response_message = f"Network Error: {e}"
            print(f"Network Error: {e}")
         except Exception as e:
            response_message = f"An unexpected error occurred during send: {str(e)}"
            print(f"Unexpected send error: {e}")
         finally:
            if image_stream_to_close:
                image_stream_to_close.close()
                print("Closed image buffer stream.")
            # Schedule UI feedback, passing the button to re-enable
            self.window.after(0, self._handle_server_response_ui, success, response_message, original_file_path, send_button) # Pass button

    # --- MODIFIED: Accepts send_button ---
    def _handle_server_response_ui(self, success, message, original_image_path, send_button):
         """Handles UI updates after server response, runs on main thread"""
         self.hide_loading()
         if success:
            messagebox.showinfo("Success", message)
            # Delete the original saved file on success (only if it still exists)
            if os.path.exists(original_image_path):
                try:
                    os.remove(original_image_path)
                    print(f"Removed successfully processed file: {original_image_path}")
                except OSError as e:
                    print(f"Error removing file {original_image_path} after success: {e}")
                    messagebox.showwarning("File Cleanup Error", f"Could not delete temporary file:\n{original_image_path}")
            # On success, maybe disable send button again if file deleted? Or leave enabled for potential server-side checks?
            # Leaving it enabled for now, assuming user might want to retry if needed.
         else:
            messagebox.showerror("Server Error", message)
            print(f"Send failed. Keeping file: {original_image_path}")

         # --- MODIFICATION: Re-enable the button regardless of success/failure ---
         # Check if button widget still exists before configuring
         if send_button.winfo_exists():
             send_button.config(state=tk.NORMAL)


    def show_loading(self):
        if hasattr(self, 'loading_dialog') and self.loading_dialog.winfo_exists(): return
        self.loading_dialog = tk.Toplevel(self.window)
        self.loading_dialog.title("Processing")
        self.loading_dialog.resizable(False, False)
        ttk.Label(self.loading_dialog, text="Processing... Please wait.").pack(padx=30, pady=20)
        self.loading_dialog.geometry("300x100")
        self.loading_dialog.update_idletasks()
        x = self.window.winfo_x() + (self.window.winfo_width() // 2) - (self.loading_dialog.winfo_width() // 2)
        y = self.window.winfo_y() + (self.window.winfo_height() // 2) - (self.loading_dialog.winfo_height() // 2)
        self.loading_dialog.geometry(f"+{x}+{y}")
        self.loading_dialog.transient(self.window)
        self.loading_dialog.grab_set()

    def hide_loading(self):
        if hasattr(self, 'loading_dialog') and self.loading_dialog.winfo_exists():
            self.loading_dialog.grab_release()
            self.loading_dialog.destroy()

    def exit_capture(self):
        self.is_capturing = False
        if hasattr(self, 'vid') and self.vid.isOpened(): self.vid.release()
        if hasattr(self, 'canvas'): self.canvas.destroy()
        if hasattr(self, 'btn_frame'): self.btn_frame.destroy()
        self.options_frame.pack(pady=20)

    def close_app(self):
        if hasattr(self, 'vid') and self.vid.isOpened(): self.vid.release()
        self.window.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = WebcamApp(root, "Document Processor with OCR")
    root.mainloop()
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image, ImageTk
import io
import requests
import sys
import os

def create_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument("--disable-extensions")
    options.add_argument('--disable-web-security')
    options.add_argument('--allow-running-insecure-content')

    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    driver_path = os.path.join(base_path, 'chromedriver.exe')

    service = Service(driver_path)
    return webdriver.Chrome(service=service, options=options)

def get_warranty_info(serial_number):
    driver = create_driver()
    driver.get("https://support.hp.com/us-en/check-warranty")

    try:
        WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, "inputtextpfinder")))

        serial_input = driver.find_element(By.ID, "inputtextpfinder")
        serial_input.clear()
        serial_input.send_keys(serial_number)

        submit_button = driver.find_element(By.ID, 'FindMyProduct')
        driver.execute_script("arguments[0].disabled = false;", submit_button)
        submit_button.click()

        WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'info-section')))

        product_name = driver.find_element(By.XPATH, "/html/body/app-root/div/app-layout/app-check-warranty/div/div/div[2]/app-warranty-details/div/div[2]/main/div[1]/div[2]/h2").text.strip()
        start_date = driver.find_element(By.XPATH, "//*[@id='directionTracker']/app-layout/app-check-warranty/div/div/div[2]/app-warranty-details/div/div[2]/main/div[4]/div/div[2]/div/div/div[1]/div[4]/div[2]").text.strip()
        end_date = driver.find_element(By.XPATH, "//*[@id='directionTracker']/app-layout/app-check-warranty/div/div/div[2]/app-warranty-details/div/div[2]/main/div[4]/div/div[2]/div/div/div[1]/div[5]/div[2]").text.strip()
        product_image_url = driver.find_element(By.CSS_SELECTOR, ".product-image").get_attribute('src')

        return {
            "Product Name": product_name,
            "Start date": start_date,
            "End date": end_date,
            "Product Image": product_image_url
        }

    except Exception as e:
        print(f"Error: {e}")
        return {"Error": "Warranty Information Not Found!"}
    finally:
        driver.quit()

def get_image_from_url(product_image_url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(product_image_url, headers=headers, verify=False, timeout=3)
        image = Image.open(io.BytesIO(response.content))
        return image
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None

def show_image_spinner():
    image_label.config(image='', text="Loading image...", font=("Arial", 9, "italic"), fg="gray")

def hide_image_spinner():
    image_label.config(text="", fg="black")

def copy_to_clipboard(serial_number, start_date, end_date, product_name, warranty_status):
    clipboard_text = f"Serial Number: {serial_number}\nProduct Name: {product_name}\nStart Date: {start_date}\nEnd Date: {end_date}\nWarranty Status: {warranty_status}"
    root.clipboard_clear()
    root.clipboard_append(clipboard_text)

def clear_result():
    entry.delete(0, tk.END)
    product_name_label.config(text="")
    start_date_label.config(text="")
    end_date_label.config(text="")
    status_heading.config(text="")
    copy_button.config(state=tk.DISABLED)
    clear_button.config(state=tk.DISABLED)
    image_label.config(image='', text='')

def run_warranty_check():
    serial_number = entry.get().strip()
    if not serial_number:
        messagebox.showerror("Input Error", "Please enter a serial number.")
        return

    product_name_label.config(text="Checking warranty...")
    start_date_label.config(text="")
    end_date_label.config(text="")
    image_label.config(image='', text="")
    status_heading.config(text="")

    def threaded_check():
        result = get_warranty_info(serial_number)
        if "Error" in result:
            status_heading.config(text="❌ Error", fg="red")
            product_name_label.config(text=result["Error"])
            start_date_label.config(text="")
            end_date_label.config(text="")
            copy_button.config(state=tk.DISABLED)
            clear_button.config(state=tk.NORMAL)
            return

        product_name = result.get("Product Name", "")
        start_date = result.get("Start date", "")
        end_date = result.get("End date", "")
        product_image_url = result.get("Product Image", "")

        product_name_label.config(text=f"Product Name: {product_name}", font=("Arial", 10, "bold"))
        start_date_label.config(text=f"Start Date: {start_date}", font=("Arial", 10, "bold"))
        end_date_label.config(text=f"End Date: {end_date}", font=("Arial", 10, "bold"))

        try:
            end_date_obj = datetime.strptime(end_date, "%B %d, %Y")
            days_remaining = (end_date_obj - datetime.now()).days
            if days_remaining > 30:
                status_heading.config(text="✔ Warranty Active", fg="green", font=("Arial", 12, "bold"))
                warranty_status = "Active"
            elif days_remaining < 0:
                status_heading.config(text="✘ Warranty Expired", fg="red", font=("Arial", 12, "bold"))
                warranty_status = "Expired"
            else:
                status_heading.config(text="⚠ Warranty Expiring Soon", fg="orange", font=("Arial", 12, "bold"))
                warranty_status = "Expiring Soon"
        except:
            status_heading.config(text="? Warranty Unknown", fg="gray", font=("Arial", 12, "bold"))
            warranty_status = "Unknown"

        copy_button.config(state=tk.NORMAL, command=lambda: copy_to_clipboard(serial_number, start_date, end_date, product_name, warranty_status))
        clear_button.config(state=tk.NORMAL)

        if product_image_url:
            def lazy_load_image(url):
                root.after(0, show_image_spinner)
                product_image = get_image_from_url(url)
                if product_image:
                    product_image = product_image.resize((150, 112))
                    product_image_tk = ImageTk.PhotoImage(product_image)
                else:
                    product_image = Image.new('RGB', (150, 112), color='lightgray')
                    product_image_tk = ImageTk.PhotoImage(product_image)

                def update_image():
                    hide_image_spinner()
                    image_label.config(image=product_image_tk)
                    image_label.image = product_image_tk
                root.after(0, update_image)

            threading.Thread(target=lambda: lazy_load_image(product_image_url)).start()

    threading.Thread(target=threaded_check).start()

# GUI Setup
root = tk.Tk()
root.title("HP Warranty Checker")
root.geometry("750x250")
root.pack_propagate(False)

# Top input row
input_frame = tk.Frame(root)
input_frame.pack(pady=5, padx=10, anchor="w")

tk.Label(input_frame, text="Enter Serial Number:", font=("Arial", 10)).pack(side="left", padx=(0, 5))
entry = tk.Entry(input_frame, width=25, font=("Arial", 11))
entry.pack(side="left", padx=(0, 5))

# Bind Enter key to trigger the warranty check
entry.bind("<Return>", lambda event: run_warranty_check())  

# Middle-align Check Warranty button with entry
check_button_frame = tk.Frame(input_frame)
check_button_frame.pack(side="left", anchor="center")
tk.Button(check_button_frame, text="Check Warranty", command=run_warranty_check).pack(pady=5)

# Warranty frame
warranty_frame = tk.LabelFrame(root, text="Warranty Info", font=("Arial", 10))
warranty_frame.pack(padx=10, pady=1, fill="both", expand=True)

# Side-by-side: Image on left, details on right
content_frame = tk.Frame(warranty_frame)
content_frame.pack(padx=10, pady=10, fill="both", expand=True)

# Image on left
image_label = tk.Label(content_frame)
image_label.pack(side="left", padx=(0, 15), anchor="n")

# Details on right
details_frame = tk.Frame(content_frame)
details_frame.pack(side="left", anchor="n", fill="both", expand=True)

status_heading = tk.Label(details_frame, text="", font=("Arial", 12, "bold"), anchor="w", justify="left")
status_heading.pack(pady=2, anchor="w")

product_name_label = tk.Label(details_frame, text="", font=("Arial", 10), anchor="w", justify="left")
product_name_label.pack(pady=2, anchor="w")

start_date_label = tk.Label(details_frame, text="", font=("Arial", 10), anchor="w", justify="left")
start_date_label.pack(pady=2, anchor="w")

end_date_label = tk.Label(details_frame, text="", font=("Arial", 10), anchor="w", justify="left")
end_date_label.pack(pady=2, anchor="w")

# Bottom buttons
button_frame = tk.Frame(root)
button_frame.pack(side=tk.LEFT, padx=5, pady=10)

copy_button = tk.Button(button_frame, text="Copy Warranty Info", state=tk.DISABLED)
copy_button.pack(side=tk.LEFT, padx=5)

clear_button = tk.Button(button_frame, text="Clear", state=tk.DISABLED, command=clear_result)
clear_button.pack(side=tk.LEFT, padx=5)

root.mainloop()





# Test HP Serial Numbers
# CND20812LQ
# 5CD01437ZB
# 2MQ505094P
# MXL2332NWH
# 2UA6402T8B
# 2UA7291YDB
# 5CG210204S
# CN44492CBR - Monitors
#5CG3171GYT - Serial Number
#4Z8Q4AV - Product Number
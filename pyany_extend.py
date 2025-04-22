from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time, os

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

for _ in range(1, 4):
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options,
    )

    wait = WebDriverWait(driver, 10)

    driver.get("https://www.pythonanywhere.com/")
    print("Navigate to PythonAnywhere")

    login_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "login_link")))
    login_button.click()
    print("Login button clicked")

    print("Filling Credintials")
    username_input = wait.until(EC.presence_of_element_located((By.NAME, "auth-username")))
    # username_input.send_keys(os.getenv("pyany_usr"))
    username_input.send_keys("goto00" + str(_))

    password_input = wait.until(EC.presence_of_element_located((By.NAME, "auth-password")))
    # password_input.send_keys(os.getenv("pyany_passwd"))
    password_input.send_keys(os.getenv("PYANY_PASSWD"))

    submit_button = wait.until(EC.element_to_be_clickable((By.ID, "id_next")))
    submit_button.click()
    print("Login successfully")

    print("Clicking web page button")
    webpage_btn = wait.until(EC.element_to_be_clickable((By.ID, "id_web_app_link")))
    webpage_btn.click()

    print("Clicking update button")
    extend_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "webapp_extend")))
    extend_button.click()

    print("Account {} is done !\n".format(str(_)))
    time.sleep(5)
    driver.quit()

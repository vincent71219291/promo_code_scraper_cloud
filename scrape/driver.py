from typing import Union

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from . import constants

BROWSER_OPTIONS = (
    # "--headless",
    # "--disable-gpu",
    "window-size=1920,1080",  # "window-size=1024,768",
    # "--disable-dev-shm-usage",
    "--no-sandbox",
    "start-maximized",
    "--disable-blink-features=AutomationControlled",
)


def init_driver(options: list | tuple = BROWSER_OPTIONS):
    chrome_options = Options()
    for option in options:
        chrome_options.add_argument(option)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    service = Service()
    return webdriver.Chrome(options=chrome_options, service=service)


def get_element(
    driver: Union[webdriver.Chrome, webdriver.Firefox],
    css_selector: str,
    timeout: int = constants.TIMEOUT,
) -> WebElement:
    element = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
    )
    return element


def get_elements(
    driver: Union[webdriver.Chrome, webdriver.Firefox],
    css_selector: str,
    timeout: int = constants.TIMEOUT,
) -> list[WebElement]:
    elements = WebDriverWait(driver, timeout).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, css_selector))
    )
    return elements


def get_element_texts(
    driver: Union[webdriver.Chrome, webdriver.Firefox],
    css_selector: str,
    timeout: int = constants.TIMEOUT,
) -> list[str]:
    elements = get_elements(driver, css_selector, timeout)
    return [element.text for element in elements]


def click_element(
    driver: Union[webdriver.Chrome, webdriver.Firefox],
    css_selector: str,
    timeout: int = constants.TIMEOUT,
) -> None:
    element = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector))
    )
    element.click()

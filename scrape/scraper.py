import datetime
import time
from dataclasses import dataclass, field
from typing import Tuple, Union

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from scrape.codes import format_codes

from . import constants
from .driver import click_element, get_element, get_element_texts, get_elements
from .utils import generate_hash_key_md5

MONTH_FR_TO_EN = {
    "janvier": "january",
    "février": "february",
    "mars": "march",
    "avril": "april",
    "mai": "may",
    "juin": "june",
    "juillet": "july",
    "août": "august",
    "septembre": "september",
    "octobre": "october",
    "novembre": "november",
    "décembre": "december",
}

CSS_SELECTORS = {
    "reject_cookies": "#cmpwelcomebtnno",
    "website_name": 'div[data-testid="header-widget"] > h1',
    "display_codes_only": 'li[data-testid="Codes"]',
    "see_code": (
        'div[class~="VoucherCard"][class~="hasCaptions"]'
        ':not([class~="expired"]) > div.flexButton > div:last-of-type > div >'
        ' div[role="button"]'
    ),
    "code": 'div[data-testid*="slideShow"] > :first-child span > h4',
    "close_overlay": 'span[data-testid="CloseIcon"]',
}

FIELD_CSS_SELECTORS = {
    "discount": (
        'div[class~="VoucherCard"]:not([class~="expired"])'
        ' > div[class~="flexButton"] > div > div#caption > span'
    ),
    "description": (
        'div[class~="VoucherCard"][class~="hasCaptions"]'
        ':not([class~="expired"]) h3'
    ),
    "expiration_date": (
        'div[class~="VoucherCard"][class~="hasCaptions"]'
        ':not([class~="expired"]) > div.flexButton > div:last-of-type >'
        " div:nth-of-type(2)"
    ),
}


def parse_website_name(
    string: str, substrings: Tuple[str, str] = ("promo ", " valides")
) -> str:
    start, end = [string.find(substring) for substring in substrings]
    start += len(substrings[0])
    return string[start:end]


def format_exp_date(date_string: str):
    today = datetime.date.today()

    if "aujourd'hui" in date_string:
        return today

    if "demain" in date_string:
        return today + datetime.timedelta(1)

    date_string = date_string.split("\n: ")[1]
    for month_fr, month_en in MONTH_FR_TO_EN.items():
        if month_fr in date_string:
            date_string = date_string.replace(month_fr, month_en)
            break

    date = datetime.datetime.strptime(
        f"{date_string} {today.year}", "%d %B %Y"
    )
    if date.date() < today:
        date = datetime.datetime.strptime(
            f"{date_string} {today.year + 1}", "%d %B %Y"
        )

    return date.date()


def get_code_string(
    driver: Union[webdriver.Chrome, webdriver.Firefox],
    see_code_button: WebElement,
    timeout: int = constants.TIMEOUT,
) -> str:
    wait = WebDriverWait(driver, timeout)
    original_windows = driver.window_handles
    n_windows = len(original_windows)

    see_code_button.click()

    # on attend que le nouvel onglet soit ouvert
    wait.until(EC.number_of_windows_to_be(n_windows + 1))

    # on ferme les anciens onglets
    for window in original_windows:
        driver.switch_to.window(window)
        driver.close()

    new_window = driver.window_handles[0]

    driver.switch_to.window(new_window)
    code_str = get_element(driver, CSS_SELECTORS["code"]).text

    click_element(driver, CSS_SELECTORS["close_overlay"])

    return code_str


@dataclass
class ScrapeResult:
    url: str
    website_id: str = field(init=False)
    website_name: str
    website_name_clean: str = field(init=False)
    codes: pd.DataFrame
    date: datetime.date = field(init=False)

    def __post_init__(self):
        self.website_id = generate_hash_key_md5(self.url)
        self.website_name_clean = self.website_name.lower().replace(" ", "_")
        self.date = datetime.date.today()

    @property
    def codes_db_format(self):
        codes = self.codes.copy()
        codes["scraping_date"] = self.date
        codes["website_id"] = self.website_id
        return codes

    @property
    def codes_human_readable(self):
        return format_codes(self.codes)


class CodeScraper:
    def __init__(
        self, driver: Union[webdriver.Chrome, webdriver.Firefox], url: str
    ):
        self.driver = driver
        self.url = url
        self.data: dict = {}

    def scrape(self) -> ScrapeResult:
        codes = []

        self.driver.get(self.url)

        try:
            click_element(self.driver, CSS_SELECTORS["reject_cookies"])
        except TimeoutException:
            pass

        website_name = parse_website_name(
            get_element(self.driver, CSS_SELECTORS["website_name"]).text
        )

        try:
            click_element(self.driver, CSS_SELECTORS["display_codes_only"])
        except TimeoutException:
            print("No codes found.")

        for field, css_selector in FIELD_CSS_SELECTORS.items():
            values = get_element_texts(self.driver, css_selector)
            if field == "expiration_date":
                values = list(map(format_exp_date, values))
            self.data[field] = values

        code_elements = get_elements(self.driver, CSS_SELECTORS["see_code"])
        n_codes = len(code_elements)
        print(f"{n_codes} code(s) found for {website_name}.")

        for i in range(n_codes):
            # on patiente 1 sec pour éviter de surcharger le serveur
            time.sleep(1)
            print(f"Scraping code {i + 1}/{n_codes}...")

            if i:
                # l'onglet/le contexte change à chaque itération, il est donc
                # nécessaire de récupérer à nouveau les éléments
                click_element(self.driver, CSS_SELECTORS["display_codes_only"])
                code_elements = get_elements(
                    self.driver, CSS_SELECTORS["see_code"]
                )
            code_elements[i].location_once_scrolled_into_view
            code_str = get_code_string(self.driver, code_elements[i])
            codes.append(code_str)
            print("Done.")

        self.data["code"] = codes

        current_codes = pd.DataFrame(self.data)
        current_codes["discount"] = current_codes["discount"].map(
            lambda x: int(x.replace("%", ""))
        )
        current_codes = current_codes.sort_values("discount", ascending=False)

        return ScrapeResult(self.url, website_name, current_codes)

    def close_driver(self):
        self.driver.quit()

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

# MONTH_FR_TO_EN = {
#     "janvier": "january",
#     "février": "february",
#     "mars": "march",
#     "avril": "april",
#     "mai": "may",
#     "juin": "june",
#     "juillet": "july",
#     "août": "august",
#     "septembre": "september",
#     "octobre": "october",
#     "novembre": "november",
#     "décembre": "december",
# }

MONTH_FR_TO_EN = {
    "janv.": "january",
    "févr.": "february",
    "mars": "march",
    "avr.": "april",
    "mai": "may",
    "juin": "june",
    "juill.": "july",
    "août": "august",
    "sept.": "september",
    "oct.": "october",
    "nov.": "november",
    "déc.": "december",
}

CSS_SELECTORS = {
    "reject_cookies": "#cmpwelcomebtnno",
    "website_name": 'div[data-testid="header-widget"] h1',
    "display_codes_only": 'div[data-testid="Codes-button"]',
    "see_code": (
        'div[data-testid="active-vouchers-widget"]'
        ' div[data-testid="voucher-card-container"]'
        ' div[data-testid="description-container"]'
        ' div[role="button"]'
    ),
    "see_code_dialog": 'div[role="dialog"] div[role="button"]',
    "code": 'span[data-testid="voucherPopup-codeHolder-voucherType-code"] h4',
    "close_dialog": 'span[data-testid="CloseIcon"]',
}

FIELD_CSS_SELECTORS = {
    "discount": (
        'div[data-testid="active-vouchers-widget"]'
        ' div[data-testid="voucher-card-container"]'
        ' div[data-testid="voucher-card-captions"]'
    ),
    "description": (
        'div[data-testid="active-vouchers-widget"]'
        ' div[data-testid="voucher-card-container"]'
        ' div[data-testid="description-container"]'
        " h3"
    ),
    "expiration_date": (
        'div[data-testid="active-vouchers-widget"]'
        ' div[data-testid="voucher-card-container"]'
        " > div:first-of-type > div:last-of-type > div:last-of-type"
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

    date_string = date_string.split(": ")[1]
    for month_fr, month_en in MONTH_FR_TO_EN.items():
        if month_fr in date_string:
            date_string = date_string.replace(month_fr, month_en)
            break

    date = datetime.datetime.strptime(f"{date_string} {today.year}", "%d %B %Y")
    if date.date() < today:
        date = datetime.datetime.strptime(f"{date_string} {today.year + 1}", "%d %B %Y")

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
    def __init__(self, driver: Union[webdriver.Chrome, webdriver.Firefox], url: str):
        self.driver = driver
        self.url = url
        self.data: dict = {}

    def scrape(self) -> ScrapeResult | None:
        codes = []
        wait = WebDriverWait(self.driver, constants.TIMEOUT)

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
            return None

        for field, css_selector in FIELD_CSS_SELECTORS.items():
            values = get_element_texts(self.driver, css_selector)
            if field == "discount":
                values = [int(value.split("%\n")[0]) for value in values]
            if field == "expiration_date":
                values = list(map(format_exp_date, values))
            self.data[field] = values

        # scraping des codes
        code_elements = get_elements(self.driver, CSS_SELECTORS["see_code"])
        n_codes = len(code_elements)
        print(f"{n_codes} code(s) found for {website_name}.")

        for i in range(n_codes):
            print(f"Scraping code {i + 1}/{n_codes}...")

            # on patiente 1 sec pour éviter de surcharger le serveur
            time.sleep(1)

            original_window = self.driver.current_window_handle
            n_windows = len(self.driver.window_handles)

            if not i:
                code_elements[i].click()
                # pour le premier élément uniquement, on doit cliquer sur le bouton
                # "voir le code" de la boîte de dialogue qui s'affiche dans l'onglet
                # original
                click_element(
                    self.driver, css_selector=CSS_SELECTORS["see_code_dialog"]
                )
            else:
                # l'onglet/le contexte change à chaque itération, on doit donc
                # récupérer les éléments à nouveau
                code_elements = get_elements(self.driver, CSS_SELECTORS["see_code"])
                code_elements[i].click()

            # l'onglet original est redirigé vers le site du marchand, et un nouvel
            # onglet s'ouvre pour afficher le code on attend que le nouvel onglet soit
            # ouvert
            wait.until(EC.number_of_windows_to_be(n_windows + 1))

            # on ferme l'onglet original et on bascule sur le nouvel onglet
            new_window = [
                window
                for window in self.driver.window_handles
                if window != original_window
            ][0]
            self.driver.close()
            self.driver.switch_to.window(new_window)

            code_str = get_element(self.driver, css_selector=CSS_SELECTORS["code"]).text
            codes.append(code_str)
            print("Done.")

            click_element(self.driver, css_selector=CSS_SELECTORS["close_dialog"])

        self.data["code"] = codes

        current_codes = pd.DataFrame(self.data).sort_values("discount", ascending=False)

        return ScrapeResult(self.url, website_name, current_codes)

    def close_driver(self):
        self.driver.quit()

"""
This script generates screenshots for the Monopyly application.

This is a script to automatically take screenshots of pages in the
Monopyly interface. It relies on entries in the development database
(and described in `tests/data.sql`); however, to take production-style
screenshots, Monopyly should be run in local mode:

    monopyly launch local

To use the development database, replace the local database
(e.g., `instance/monopyly.sqlite`) with a copy of the development
database.
"""

from pathlib import Path
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options

SCRIPTS_DIR = Path(__file__).parent
PACKAGE_DIR = SCRIPTS_DIR.parent
SCREENSHOTS_DIR = PACKAGE_DIR / "static/img/about"
MONOPYLY_URL = "http://localhost:5001"


def main():
    # Set Firefox launch options and create the webdriver
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--width=1520")
    options.add_argument("--height=1080")
    driver = webdriver.Firefox(options=options)
    driver.implicitly_wait(3)

    # Take screenshot of the app homepage
    photographer = Photographer(driver, SCREENSHOTS_DIR)
    photographer.screenshot("homepage.png", "/")
    # Login
    driver.get(urljoin(MONOPYLY_URL, "/auth/login"))
    username = driver.find_element(By.ID, "username")
    password = driver.find_element(By.ID, "password")
    username.send_keys("mr.monopyly")
    password.send_keys("MONOPYLY")
    submit_button = driver.find_element(By.CSS_SELECTOR, "input.button")
    submit_button.click()
    # Take a screenshot of the (logged in) app homepage
    photographer.screenshot("homepage-user.png", "/")
    # Take screenshots of the bank account functionality
    photographer.screenshot("bank-accounts.png", "/banking/accounts")
    photographer.screenshot(
        "bank-account-summaries.png", "/banking/account_summaries/2"
    )
    photographer.screenshot("bank-account-details.png", "/banking/account/2")
    # Take screenshots of the credit card functionality
    photographer.screenshot("credit-account-details.png", "/credit/account/3")
    photographer.get("/credit/transactions")
    element = driver.find_element(By.CSS_SELECTOR, "#transaction-5 .more.button")
    photographer.screenshot(
        "credit-transactions.png",
        actions=[photographer.define_click_action(element).pause(1)],
    )
    photographer.screenshot("credit-statement-details.png", "/credit/statement/7")
    driver.quit()


class Photographer:
    """An object to photographs/screenshots of the web application."""

    _base_url = MONOPYLY_URL

    def __init__(self, driver, output_dir):
        self._driver = driver
        self._output_dir = output_dir

    def get(self, url):
        """Get the given URL."""
        self._driver.get(urljoin(self._base_url, url))

    def screenshot(self, filename, url=None, actions=()):
        """Take a screenshot of the given URL."""
        if url:
            self.get(url)
        for action in actions:
            action.perform()
        output_filepath = self._output_dir / filename
        self._driver.save_full_page_screenshot(str(output_filepath))

    def define_click_action(self, element):
        """Define an action that clicks the element."""
        action = ActionChains(self._driver).move_to_element(element)
        action.click()
        return action


if __name__ == "__main__":
    main()

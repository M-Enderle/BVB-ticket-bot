import time
from selenium import common
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from PIL import Image
from selenium.webdriver.common.action_chains import ActionChains
import threading
from datetime import datetime
import sys

""" Only whole numbers allowed here """
number_of_seats = 6

# both
# links_to_follow = ["https://www.eventimsports.de/ols/bvb/de/bundesliga/channel/shop/index", "https://www.eventimsports.de/ols/bvb/de/champions-league/channel/shop/index"]

# only champions league
# links_to_follow = ["https://www.eventimsports.de/ols/bvb/de/champions-league/channel/shop/index"]

# only bundesliga
links_to_follow = ["https://www.eventimsports.de/ols/bvb/de/bundesliga/channel/shop/index"]

options = Options()
options.headless = False
browser = webdriver.Firefox(options=options, executable_path="./geckodriver.exe")
time.sleep(0.1)


class Status:

    def __init__(self):
        self.running = True


def log(msg):
    """Print something to the console with timestamp"""

    now = datetime.now()
    print(now.strftime("%H:%M:%S") + " : " + msg)


def parse_first_screenshot():
    """Takes a screenshot and returns the positions where seats were found"""

    browser.save_screenshot("screenshot.png")
    img = Image.open("screenshot.png")

    known_seats = []
    for x in range(230, 1100):
        for y in range(300, 1000):
            r, g, b, a = img.getpixel((x, y))
            if (abs(r - g) > 20 or abs(b - g) > 20 or abs(r - b) > 20) and not (
                    430 < x < 900 and 522 < y < 800):
                for seat in known_seats:
                    if seat[0] - 20 < x < seat[0] + 20 and seat[1] - 20 < y < seat[1] + 20:
                        break
                else:
                    known_seats.append([x, y])

    if not known_seats:
        return None, None

    if 250 < known_seats[0][0] < 421 and 521 < known_seats[0][1] < 800:
        log("found standing seat")
        return known_seats[0], False
    else:
        if browser.find_element(By.ID, "stepper-input").get_attribute("value") != str(number_of_seats):
            log("switching to multi seated")
            while browser.find_element(By.ID, "stepper-input").get_attribute("value") != str(number_of_seats):
                browser.find_element(By.ID, "stepper-plus").click()
                time.sleep(0.2)
            time.sleep(0.5)
            return parse_first_screenshot()
        else:
            known_seats = sorted(known_seats, key=lambda l: abs(665 - l[0]))
            return known_seats[0], True


def parse_second_screenshot():
    """Takes a screenshot and returns the positions where seats were found"""

    browser.save_screenshot("screenshot.png")
    img = Image.open("screenshot.png")

    known_seats = []
    for x in range(60, 1200):
        for y in range(300, 1100):
            r, g, b, a = img.getpixel((x, y))
            if abs(r - g) > 20 or abs(b - g) > 20 or abs(r - b) > 20:
                for seat in known_seats:
                    if seat[0] - 25 < x < seat[0] + 25 and seat[1] - 25 < y < seat[1] + 25:
                        break
                else:
                    known_seats.append([x, y])

    known_seats = sorted(known_seats, key=lambda l: abs(630 - l[0]))
    return known_seats


def click(x, y):
    """clicks on a location"""
    """
    document.addEventListener('mousemove', (event) => {
	    console.log(`Mouse X: ${event.clientX}, Mouse Y: ${event.clientY}`);
    });
    """

    action = ActionChains(browser)
    action.move_to_element(browser.find_element(By.TAG_NAME, "body"))
    action.move_by_offset(-991 + x, -600 + y).click().perform()


def run(browser, options, status):
    while status.running:
        links = []

        for webpage in links_to_follow:
            try:
                browser.get(webpage)
            except common.exceptions.TimeoutException:
                browser.close()
                browser = webdriver.Firefox(options=options)
                time.sleep(0.2)
                window_size = browser.execute_script("""
                            return [window.outerWidth - window.innerWidth + arguments[0],
                              window.outerHeight - window.innerHeight + arguments[1]];
                            """, 1500, 900)
                browser.set_window_size(*window_size)
                browser.set_page_load_timeout(5)
                continue

            buttons = browser.find_elements(By.CLASS_NAME, "event-card__button")

            for button in buttons:
                links.append(button.find_element(By.TAG_NAME, "a").get_attribute("href"))

        for link in links:
            browser.get(link)
            time.sleep(0.2)
            try:
                browser.find_element(By.ID, "choose-seat-button").click()
            except common.exceptions.NoSuchElementException:
                continue

            try:
                time.sleep(2.5)
                coordinates, multi_seats = parse_first_screenshot()
                if not coordinates:
                    continue
                click(coordinates[0], coordinates[1])

                time.sleep(2.5)

                coordinates = parse_second_screenshot()

                if not coordinates:
                    continue

                if multi_seats:
                    if len(coordinates) >= number_of_seats:
                        y = coordinates[0][1]
                        clicked = 0
                        for coordinate in coordinates:
                            if y - 8 < coordinate[1] < y + 8:
                                click(coordinate[0], coordinate[1])
                                clicked += 1

                            if clicked >= number_of_seats:
                                break

                            time.sleep(0.2)
                else:
                    click(coordinates[0][0], coordinates[0][1])

                time.sleep(1)
                browser.find_element(By.ID, "add-to-cart").click()

            except Exception as e:
                log(str(e))
                continue

            time.sleep(1)

            if browser.find_elements(By.CLASS_NAME, "notification--fail"):
                continue

            log("successfully bought the tickets")


if __name__ == "__main__":
    browser.get("https://www.eventimsports.de/ols/bvb/")
    input("press enter after log in")
    window_size = browser.execute_script("""
        return [window.outerWidth - window.innerWidth + arguments[0],
          window.outerHeight - window.innerHeight + arguments[1]];
        """, 2000, 1200)
    browser.set_window_size(window_size[0], window_size[1])
    browser.set_page_load_timeout(5)
    status = Status()
    myThread = threading.Thread(target=run, args=(browser, options, status))
    myThread.start()
    input("Press Enter to stop")
    print("stopping")
    status.running = False
    input("Press enter to exit")
    sys.exit(1)

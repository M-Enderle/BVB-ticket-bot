# -*- coding: utf-8 -*-

import time
from datetime import datetime
from selenium import common, webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from PIL import Image
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import threading
import ssl

""" Only whole numbers allowed here """
number_of_seats = 2

secret_key = "USE KEY FROM PUSHSAVER"


if number_of_seats > 4:
    number_of_seats = 4
elif number_of_seats < 1:
    number_of_seats = 1

    
def log(msg):
    """Print something to the console with timestamp"""

    now = datetime.now()
    print(now.strftime("%H:%M:%S") + " : " + msg)


def send_second_notification(title, ticket):
    """Set a timer for the second notification"""

    time.sleep(15*60)
    send_notification("Die Tickets sind bald nicht mehr reserviert", ticket, 5, 2)


def send_notification(title, ticket, ttl, prio):
    """Send a notification"""

    url = 'https://www.pushsafer.com/api'
    post_fields = {
        "k": secret_key,
        "d": "a",
        "t": title,
        "s": 11,
        "m": ticket,
        "i": 128,
        "l": ttl,
        "p": prio,
        "g": "8YHIoe55OVnFVKmgSP"
    }

    request = Request(url, urlencode(post_fields).encode())
    gcontext = ssl.SSLContext()
    urlopen(request, context=gcontext).read().decode()

    thread = threading.Thread(target=send_second_notification, args=(title, ticket))
    thread.daemon = True
    thread.start()


def parse_first_screenshot():
    """Takes a screenshot and returns the positions where seats were found"""

    browser.save_screenshot("screenshot.png")
    img = Image.open("screenshot.png")

    known_seats = []
    for x in range(30, 1150):
        for y in range(150, 900):
            r, g, b, a = img.getpixel((x, y))
            if (abs(r - g) > 20 or abs(b - g) > 20 or abs(r - b) > 20) and not (
                    400 < x < 850 and 422 < y < 680):
                for seat in known_seats:
                    if seat[0] - 20 < x < seat[0] + 20 and seat[1] - 20 < y < seat[1] + 20:
                        break
                else:
                    known_seats.append([x, y])

    if not known_seats:
        return None, None

    if 209 < known_seats[0][0] < 388 and 413 < known_seats[0][1] < 698:
        log("found standing seat")
        return known_seats[0], False
    else:
        if browser.find_element_by_id("stepper-input").get_attribute("value") != str(number_of_seats):
            log("switching to multi seated")
            while browser.find_element_by_id("stepper-input").get_attribute("value") != str(number_of_seats):
                browser.find_element_by_id("stepper-plus").click()
                time.sleep(0.2)
            time.sleep(0.5)
            return parse_first_screenshot()
        else:
            known_seats = sorted(known_seats, key=lambda l: abs(630 - l[0]))
            return known_seats[0], True


def parse_second_screenshot():
    """Takes a screenshot and returns the positions where seats were found"""

    browser.save_screenshot("screenshot.png")
    img = Image.open("screenshot.png")

    known_seats = []
    for x in range(60, 1200):
        for y in range(150, 900):
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

    action = ActionChains(browser)
    action.move_to_element(browser.find_element_by_tag_name("body"))
    action.move_by_offset(-954 + x, -494 + y).click().perform()


options = Options()
options.headless = False
browser = webdriver.Firefox(options=options,
                            executable_path='geckodriver.exe')
browser.set_window_size(1920, 1080)
browser.set_page_load_timeout(5)

if __name__ == "__main__":
    try:
        while True:
            links = []

            for webpage in ["https://www.eventimsports.de/ols/bvb/de/bundesliga/channel/shop/index",
                            "https://www.eventimsports.de/ols/bvb/de/champions-league/channel/shop/index",
                            "https://www.eventimsports.de/ols/bvb/de/3liga/channel/shop/index"]:
                try:
                    browser.get(webpage)
                except common.exceptions.TimeoutException:
                    browser.close()
                    browser = webdriver.Firefox(options=options,
                                                executable_path='geckodriver.exe')
                    browser.set_window_size(1920, 1080)
                    continue

                buttons = browser.find_elements_by_class_name("event-card__button")

                for button in buttons:
                    links.append(button.find_element_by_tag_name("a").get_attribute("href"))

            for link in links:
                browser.get(link)
                time.sleep(0.1)
                try:
                    browser.find_element_by_id("choose-seat-button").click()
                except common.exceptions.NoSuchElementException:
                    continue

                try:
                    time.sleep(1.5)
                    coordinates, multi_seats = parse_first_screenshot()
                    if not coordinates:
                        continue
                    click(coordinates[0], coordinates[1])

                    time.sleep(1.5)

                    coordinates = parse_second_screenshot()

                    if not coordinates:
                        continue

                    if multi_seats:
                        if len(coordinates) >= number_of_seats:
                            y = coordinates[0][1]
                            for i in range(number_of_seats):
                                if y - 8 < coordinates[i][1] < y + 8:
                                    click(coordinates[i][0]+3, coordinates[i][1])
                                time.sleep(0.2)
                    else:
                        click(coordinates[0][0], coordinates[0][1])

                    time.sleep(0.7)
                    browser.find_element_by_id("add-to-cart").click()

                except Exception as e:
                    log(str(e))
                    continue

                time.sleep(0.5)

                if browser.find_elements_by_class_name("notification--fail"):
                    continue

                log("successfully bought the tickets")

                if multi_seats:
                    send_notification("Neues Ticket im Warenkorb!", "Sitzplatz", 15, 0)
                else:
                    send_notification("Neues Ticket im Warenkorb!", "Stehplatz", 15, 0)

    except KeyboardInterrupt:
        log("Goodbye")

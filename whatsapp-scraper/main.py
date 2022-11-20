import datetime
import os
from time import sleep

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from sortedcontainers import SortedSet
import traceback

global SCROLL_TO, SCROLL_SIZE
import re

# Download google driver from https://chromedriver.chromium.org/downloads
# you can set the chromedriver path on the system path and remove this variable
CHROMEDRIVER_PATH = 'utils/chromedriver.exe'

CONTACT_NAME_DIV = 'zoWT4'
CONVERSATION_PANEL = '_33LGR'
USER_DATA_DIR = 'D:/user-data'
EXPORT_PATH = 'collected_data/'


class MessageQuoted:
    autore = ""
    messaggio = ""

    def __init__(self, quote, quoteAuthor):
        self.messaggio = quote
        self.autore = quoteAuthor


class Message:
    text = ""
    day = ""
    time = ""
    person = ""
    quote = MessageQuoted
    date = datetime.datetime.now()

    def display(self):
        if self.quote.autore != "":
            print("[%s, %s]  %s %s -'%s: %s' " % (
                self.day, self.time, self.person, self.text, self.quote.autore, self.quote.messaggio))
        if self.day == "":
            print("%s: %s " % (
                self.person, self.text))
        if self.quote.autore == "" and self.day != "":
            print("[%s, %s]  %s %s " % (
                self.day, self.time, self.person, self.text))

    def asString(self):
        if self.quote.autore != "":
            return "[%s, %s]  %s %s -'%s: %s' " % (
                self.day, self.time, self.person, self.text, self.quote.autore, self.quote.messaggio)
        if self.day == "":
            return "%s: %s " % (
                self.person, self.text)
        if self.quote.autore == "" and self.day != "":
            return "[%s, %s]  %s %s " % (
                self.day, self.time, self.person, self.text)

    def __init__(self, text, day, time, person, quote, quoteAuthor):
        self.text = text
        self.day = day
        self.time = time
        self.person = person
        self.quote = MessageQuoted(quote, quoteAuthor)

    def __eq__(self, other):
        return self.date == other.date

    def __lt__(self, other):
        return self.date < other.date

    def __hash__(self):
        return id(self)


def manageHtml(soup):
    messages = SortedSet()
    messagesInDiv = soup.findAll('div', attrs={'class': re.compile(r"message-*")})
    print(len(messagesInDiv))
    lastDay = ""
    lastTime = ""
    for message in messagesInDiv:
        quotedDiv = message.find('div', attrs={'data-testid': 'quoted-message'})
        messaggioQuotato = ""
        autoreQuote = ""
        if (quotedDiv):
            quotedElem = quotedDiv.find('span', attrs={'class': 'quoted-mention'})
            if (quotedElem):
                messaggioQuotato = quotedElem.text
            autoreQuote = quotedDiv.text.replace(messaggioQuotato, '')
        elemento = message.find('div', attrs={'data-pre-plain-text': True})

        if (elemento):
            elem = elemento.attrs['data-pre-plain-text']
            e = message.find('span', attrs={'class': 'selectable-text', 'class': 'copyable-text'})
            if e:
                m = Message(e.text, elem.split(", ")[1].split("]")[0],
                            elem.split(", ")[0].split("[")[1],
                            elem.split(", ")[1].split("]")[1], messaggioQuotato, autoreQuote)
                lastDay = m.day
                lastTime = m.time
                m.date = datetime.datetime(int(m.day.split("/")[2]), int(m.day.split("/")[1]),
                                           int(m.day.split("/")[0]),
                                           int(m.time.split(":")[0]), int(m.time.split(":")[1]))
                messages.add(m)
            else:
                m = Message("", elem.split(", ")[1].split("]")[0],
                            elem.split(", ")[0].split("[")[1],
                            elem.split(", ")[1].split("]")[1], messaggioQuotato, autoreQuote)
                lastDay = m.day
                lastTime = m.time
                m.date = datetime.datetime(int(m.day.split("/")[2]), int(m.day.split("/")[1]),
                                           int(m.day.split("/")[0]),
                                           int(m.time.split(":")[0]), int(m.time.split(":")[1]))
                messages.add(m)
        else:
            tuo = message.find('span', attrs={'aria-label': 'Tu:'})
            suo = message.find('span', attrs={'dir': 'auto'})
            if tuo:
                m = Message("<audio>", lastDay, lastTime, "Tu:", "", "")
                try:
                    m.display()
                    if (m.day):
                        m.date = datetime.datetime(int(m.day.split("/")[2]), int(m.day.split("/")[1]),
                                                   int(m.day.split("/")[0]),
                                                   int(m.time.split(":")[0]), int(m.time.split(":")[1]))
                except Exception as e:
                    traceback.print_exc()
                messages.add(m)
            else:
                m = Message("<audio>", lastDay, lastTime, suo.text, "", "")
                try:
                    m.display()
                    if (m.day):
                        m.date = datetime.datetime(int(m.day.split("/")[2]), int(m.day.split("/")[1]),
                                                   int(m.day.split("/")[0]),
                                                   int(m.time.split(":")[0]), int(m.time.split(":")[1]))
                except Exception as e:
                    traceback.print_exc()
                messages.add(m)
    return messages


def pane_scroll(dr):
    global SCROLL_TO, SCROLL_SIZE

    print('>>> scrolling side pane')
    side_pane = dr.find_element_by_id('pane-side')
    dr.execute_script('arguments[0].scrollTop = ' + str(SCROLL_TO), side_pane)
    sleep(3)
    SCROLL_TO += SCROLL_SIZE


def get_messages(driver, contact_list):
    global SCROLL_SIZE
    print('>>> getting messages')
    conversations = []
    for contact in contact_list:

        if (contact != "Archiviate"):  # ignore archive container
            # if (contact == "Triage forense"):  # to remove this, just for test
            sleep(2)
            try:
                user = driver.find_element_by_xpath('//span[contains(@title, "{}")]'.format(contact))
            except Exception as e:
                traceback.print_exc()
                break
            user.click()
            sleep(3)

            messages = SortedSet()
            scroll = SCROLL_SIZE
            lengthActual = 0
            finished = True
            while finished:  # before I discover all messages and then I wrote them to the list
                conversation_pane = driver.find_element_by_xpath(
                    "//div[@class='" + CONVERSATION_PANEL + "']")
                elements = driver.find_elements_by_xpath("//div[@class='copyable-text']")
                if lengthActual == len(elements):
                    # Find data-testid="conversation-panel-messages" in the DOM to get class name
                    stri = conversation_pane.get_attribute('innerHTML')
                    soup = BeautifulSoup(stri, 'html5lib')
                    messages = manageHtml(soup)
                    finished = False
                else:
                    lengthActual = len(elements)
                    driver.execute_script('arguments[0].scrollTop = -' + str(scroll), conversation_pane)
                    sleep(2)
                    scroll += SCROLL_SIZE
            for message in messages:
                conversations.append(message.asString())

            filename = EXPORT_PATH + '/conversations/{}.txt'.format(
                contact + str(datetime.datetime.now().timestamp()))
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'w', encoding='utf8') as f:
                for line in conversations:
                    f.write(f"{line}{os.linesep}")
    return conversations


def main():
    global SCROLL_TO, SCROLL_SIZE
    SCROLL_SIZE = 600
    SCROLL_TO = 600
    conversations = []

    options = Options()
    options.add_argument(
        'user-data-dir=' + USER_DATA_DIR)  # saving user data so you don't have to scan the QR Code again
    driver = webdriver.Chrome(executable_path=CHROMEDRIVER_PATH, chrome_options=options)
    driver.get('https://web.whatsapp.com/')
    continued = True
    while continued:
        continued = continued != (len(driver.find_elements_by_class_name(CONTACT_NAME_DIV)) > 0)
        sleep(1)

    try:
        # retrieving the contacts
        print('>>> getting contact list')
        contacts = set()
        length = 0
        while True:
            contacts_sel = driver.find_elements_by_class_name(CONTACT_NAME_DIV)  # get just contacts ignoring groups
            contacts_sel = set([j.text for j in contacts_sel])
            conversations.extend(get_messages(driver, list(contacts_sel - contacts)))
            contacts.update(contacts_sel)
            if (length == len(contacts) and length != 0) or length > 10:
                break
            else:
                length = len(contacts)
            pane_scroll(driver)
        print(len(contacts), "contacts retrieved")
        print(len(conversations), "messages retrieved")
        filename = EXPORT_PATH + '/all.json'
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf8') as f:
            for line in conversations:
                f.write(f"{line}{os.linesep}")
        print('Done')
    except Exception as e:
        traceback.print_exc()


if __name__ == "__main__":
    main()

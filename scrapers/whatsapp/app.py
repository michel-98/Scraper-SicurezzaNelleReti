import datetime
import os
import shutil
import traceback
from time import sleep

from bs4 import BeautifulSoup
from flask import Flask, jsonify
from flask_cors import CORS
from flask_restful import Api, request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from sortedcontainers import SortedSet

global SCROLL_TO, SCROLL_SIZE
import re
import json

# Download google driver from https://chromedriver.chromium.org/downloads
# you can set the chromedriver path on the system path and remove this variable
CHROMEDRIVER_PATH = 'utils/chromedriver.exe'

CONTACT_NAME_DIV = 'zoWT4'
CONVERSATION_PANEL = '_33LGR'
USER_DATA_DIR = 'C:/user-data'

app = Flask(__name__)
api = Api(app)
CORS(app)


class MessageQuoted:
    autore = ""
    messaggio = ""

    def __init__(self, quote, quoteAuthor):
        self.messaggio = quote
        self.autore = quoteAuthor


def json_default(value):
    if isinstance(value, datetime.datetime):
        return dict(year=value.year, month=value.month, day=value.day, hour=value.hour, minutes=value.minute)
    elif isinstance(value, Message):
        return dict(autore=value.person,
                    data=dict(year=value.date.year, month=value.date.month, day=value.date.day),
                    giorno=value.day,
                    ora=value.time,
                    messaggio=value.text,
                    messaggioCitato=dict(autore=value.quote.autore, messaggio=value.quote.messaggio))
    else:
        return value.__dict__


class Message:
    text = ""
    day = ""
    time = ""
    person = ""
    quote = MessageQuoted
    date = datetime.datetime.now()

    def __dict__(self):
        return json.dumps(self, default=json_default,
                          sort_keys=True, indent=4)

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
                    if (m.day):
                        m.date = datetime.datetime(int(m.day.split("/")[2]), int(m.day.split("/")[1]),
                                                   int(m.day.split("/")[0]),
                                                   int(m.time.split(":")[0]), int(m.time.split(":")[1]))
                except Exception as e:
                    traceback.print_exc()
                messages.add(m)
    return messages


def get_messages(driver, contact, contatti):
    global SCROLL_SIZE
    conversations = []
    if (contact != "Archiviate") and (
            len(contatti) == 0 or contact.lower() in map(str.lower, contatti)):  # ignore archive container
        # if (contact == "Triage forense"):  # to remove this, just for test
        sleep(2)
        try:
            user = driver.find_element_by_xpath('//span[contains(@title, "{}")]'.format(contact))
            driver.find_element_by_tag_name("body")
        except Exception as e:
            user = ""
            traceback.print_exc()
        if user != "":
            user.click()
            sleep(3)

            messages = SortedSet()
            scroll = SCROLL_SIZE
            lengthActual = 0
            finished = True
            while finished:  # before I discover all messages and then I wrote them to the list
                try:
                    conversation_pane = driver.find_element_by_xpath("//div[@class='" + CONVERSATION_PANEL + "']")
                    elements = driver.find_elements_by_xpath("//div[@class='copyable-text']")
                    # print(contact + '  :' + str(scroll))
                    if lengthActual == len(elements) or scroll > 15000:
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
                except Exception as e:
                    traceback.print_exc()
                    break
            conversations.append({"contatto": contact, "messaggi": list(messages)})
            print(conversations)
    return conversations


def mainCall(contatti):
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
        scroll = 100
        last = -50
        paneSide = driver.find_element_by_id("pane-side")
        listaContatti = set()
        while (paneSide.get_attribute("scrollTop") != scroll):
            scroll = scroll + 100
            if last == paneSide.get_attribute("scrollTop"):
                break
            last = paneSide.get_attribute("scrollTop")
            html = paneSide.get_attribute("innerHTML")
            soup = BeautifulSoup(html, 'html5lib')
            contacts_sel = soup.findAll('div', attrs={'class': 'zoWT4'})
            for j in contacts_sel:
                if hasattr(j, "text") and len(j.text) > 0:
                    if list(listaContatti).count(j.text) == 0:
                        listaContatti.add(j.text)
                        conversations.extend(get_messages(driver, j.text, contatti))
            driver.execute_script('arguments[0].scrollTop = ' + str(scroll), paneSide)
        print(len(conversations), "conversations retrieved")
    except Exception as e:
        traceback.print_exc()
    finally:
        driver.close()
        return conversations


@app.get('/')
def getHello():
    return "hello a sort"


@app.get('/forget')
def forgetUser():
    folder = USER_DATA_DIR
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))
    return "true"


@app.get('/messages')
def getMessages():
    args = request.args

    contatti = args.get("contacts")
    if contatti:
        contatti = contatti.split(",")
    else:
        contatti = []
    return {"messages": json.dumps(mainCall(contatti), default=json_default,
                                   sort_keys=True), "status_code": 200}


def main():
    mainCall([])


if __name__ == "__main__":
    app.run(port=5002)

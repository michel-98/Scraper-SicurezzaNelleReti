import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from time import sleep
from sortedcontainers import  SortedSet
import datetime

global SCROLL_TO, SCROLL_SIZE

# Download google driver from https://chromedriver.chromium.org/downloads
# you can set the chromedriver path on the system path and remove this variable
CHROMEDRIVER_PATH = 'utils/chromedriver.exe'

CONTACT_NAME_DIV = 'zoWT4'
CONVERSATION_PANEL = '_33LGR'
USER_DATA_DIR = 'D:/user-data'
EXPORT_PATH = 'collected_data/'


# test sending a message
# def send_a_message(driver):
#     name = input('Enter the name of a user')
#     msg = input('Enter your message')

#     # saving the defined contact name from your WhatsApp chat in user variable
#     user = driver.find_element_by_xpath('//span[@title = "{}"]'.format(name))
#     user.click()

#     # name of span class of contatct
#     msg_box = driver.find_element_by_class_name('_3uMse')
#     msg_box.send_keys(msg)
#     sleep(5)

class Message:
    text = ""
    day = ""
    time = ""
    person = ""
    date = datetime.datetime.now()

    def display(self):
        print("[%s, %s]  %s: %s" % (self.day, self.time, self.person, self.text))

    def asString(self):
        return "[%s, %s]  %s: %s" % (self.day, self.time, self.person, self.text)

    def __init__(self, text, day, time, person):
        self.text = text
        self.day = day
        self.time = time
        self.person = person

    def __eq__(self, other):
        return self.date == other.date

    def __lt__(self, other):
        return self.date < other.date

    def __hash__(self):
        return id(self)

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
            print(contact)
            if (contact == "Triage forense"): #to remove this, just for test
                sleep(2)
                user = driver.find_element_by_xpath('//span[contains(@title, "{}")]'.format(contact))
                user.click()
                sleep(3)
                conversation_pane = driver.find_element_by_xpath(
                    "//div[@class='" + CONVERSATION_PANEL + "']")  # Find data-testid="conversation-panel-messages" in the DOM to get class name

                messages = SortedSet()
                scroll = SCROLL_SIZE
                lengthActual = 0
                finished = True
                while finished:  # before I discover all messages and then I wrote them to the list
                    elements = driver.find_elements_by_xpath("//div[@class='copyable-text']")
                    if lengthActual == len(elements) \
                            or lengthActual > 20 : #to remove this, just for test
                        for e in elements:
                            elem = e.get_attribute('data-pre-plain-text')
                            m = Message(e.text, elem.split(", ")[1].split("]")[0],
                                        elem.split(", ")[0].split("[")[1],
                                        elem.split(", ")[1].split("]")[1])

                            m.date = datetime.datetime(int(m.day.split("/")[2]), int(m.day.split("/")[1]),
                                                       int(m.day.split("/")[0]),
                                                       int(m.time.split(":")[0]), int(m.time.split(":")[1]))
                            m.display()
                            messages.add(m)
                            finished = False
                    else:
                        lengthActual = len(elements)
                        print(lengthActual)
                        driver.execute_script('arguments[0].scrollTop = -' + str(scroll), conversation_pane)
                        sleep(2)
                        scroll += SCROLL_SIZE
                print(messages)
                for message in messages:
                    conversations.append(message.asString())

                print(conversations)
                filename = EXPORT_PATH + '/conversations/{}.txt'.format(contact)
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                with open(filename, 'w') as f:
                    for line in conversations:
                        f.write(f"{line}{os.linesep}")
                print('Done')
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
        print(len(conversations), "conversations retrieved")
        filename = EXPORT_PATH + '/all.json'
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w') as f:
            for line in conversations:
                f.write(f"{line}{os.linesep}")
        print('Done')
    except Exception as e:
        print(e)
        driver.quit()


if __name__ == "__main__":
    main()

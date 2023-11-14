# Author: Jakub Andrysek
# Website: https://kubaandrysek.cz
# Date: 2023-03-06
# Description EN: Script for downloading marks from SkolaOnLine application
# Description CZ: Skript pro stahování známek z aplikace SkolaOnLine
# Version: 1.0.0
# License: MIT

import re
import requests
from bs4 import BeautifulSoup
from prettytable import PrettyTable
import maskpass

session = requests.Session()


def log_in_sol(user: str, password: str) -> bool:
    url: str = 'https://aplikace.skolaonline.cz/SOL/Prihlaseni.aspx'
    data = {
        "__EVENTTARGET": "dnn$ctr994$SOLLogin$btnODeslat",
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": "",
        "__VIEWSTATEGENERATOR": "",
        "__VIEWSTATEENCRYPTED": "",
        "__PREVIOUSPAGE": "",
        "__EVENTVALIDATION": "",
        "dnn$dnnSearch$txtSearch": "",
        "JmenoUzivatele": user,  # username
        "HesloUzivatele": password,  # password
        "ScrollTop": "",
        "__dnnVariable": "",
        "__RequestVerificationToken": ""
    }
    postLogin = session.post(url, data=data)
    if postLogin.status_code != 200:
        print('Nepodařilo se přihlásit')
        return False
    else:
        print('Pokus o přihlášení proběhl úspěšně')
        return True


def scrape_sol_url(params=None) -> str:
    base = "https://aplikace.skolaonline.cz"
    if params is not None:
        base += params

    r = session.get(base)
    if r.status_code == 200:
        return r.text
    print('Nepodařilo se stáhnout data')
    return ""


def find_marks_in_html(html: str) -> list:
    soup = BeautifulSoup(html, 'lxml')  # load html to BeautifulSoup object
    # xpath //*[@id="ctl00_bodyFooter_boxHodnVypisStud_ctl00_Content"]
    table = soup.find('div', id='ctl00_bodyFooter_boxHodnVypisStud_ctl00_Content')

    # extract from table all rows
    table = table.find('table')

    # get all rows
    rows = table.find_all('tr')

    # get all columns
    columns = [row.find_all('td') for row in rows]

    # get all marks
    marks = []
    for row in columns:
        marks.append(extract_mark_from_html(row))

    return marks


# [<td>Út 10.1.</td>,<td title="Matematika">Matematika</td>,<td><a onclick="window.open('../Hodnoceni/KHO010_HodnVypisDetail.aspx?UdalostID=C37655175&amp;OsobaID=C3023618', 'detail', 'width=430, height=400, resizable, scrollbars')" title="1"><span class="znamka_dobra"><strong>1</strong></span></a></td>]
def extract_mark_from_html(mark_html: str) -> dict:
    mark = {
        'Datum': mark_html[0].text,
        'Předmět': mark_html[1].text,
        'Známka': mark_html[2].text,
    }

    mark.update(extract_mark_details(mark_html))
    return mark


# get window.open link and parse it
def extract_mark_details(mark_html: str):
    try:
        link = mark_html[2].find('a').attrs['onclick']
        # "window.open('../Hodnoceni/KHO010_HodnVypisDetail.aspx?UdalostID=C37917700&OsobaID=C3361427', 'detail', 'width=430, height=400, resizable, scrollbars')"  to "../Hodnoceni/KHO010_HodnVypisDetail.aspx?UdalostID=C37917700&OsobaID=C3361427"
        detail_url = '/SOL/App/' + re.search(r"'...(.*?)'", link)[1]
        detail_html = scrape_sol_url(detail_url)

        soup = BeautifulSoup(detail_html, 'html.parser')
        # //*[@id="tabVysledky"]
        table = soup.find('table', id='tabVysledky')
        mark_details = {}
        for row in table.find_all('tr'):
            try:
                label = row.find('span', class_='FieldLabel SpaceAfterFieldLabel').text
                try:
                    data = row.find('span', id=re.compile(r'LData.*')).text
                except AttributeError:
                    data = None

                mark_details[label.replace(":", "")] = data
            except AttributeError:
                pass
        return mark_details
    except AttributeError:
        return {}


def scrape_sol_to_file():
    html_content = scrape_sol_url("/SOL/App/Spolecne/KZZ010_RychlyPrehled.aspx")
    # save to file
    with open('htmlContent.html', 'w') as f:
        f.write(html_content)


# get mark from file
def load_mark_from_file() -> str:
    with open('htmlContent.html', 'r') as f:
        return f.read()


def print_pretty_table(marks: list):
    table = PrettyTable()
    table.field_names = ['Datum', 'Předmět', 'Známka', 'Druh hodnocení', 'Učitel', 'Komentář', 'Slovní hodnocení']
    for mark in marks:
        table.add_row(
            [mark['Datum'], mark['Předmět'], mark['Známka'], mark['Druh hodnocení'], mark['Učitel'], mark['Komentář'],
             mark['Slovní hodnocení']])
    print(table)


if __name__ == '__main__':
    username = input("Zadejte uživatelské jméno: ")
    password = maskpass.askpass(prompt="Zadejte heslo: ", mask="*")  

    log_in_sol(username, password)
    scrape_sol_to_file()

    html_content = load_mark_from_file()

    try :
        if html_content is not None:
            marks = find_marks_in_html(html_content)
            print_pretty_table(marks)
    except AttributeError:
        print('Nepodařilo se načíst známky ze souboru (pravděpodobně jsi zadal špatné přihlašovací údaje)')

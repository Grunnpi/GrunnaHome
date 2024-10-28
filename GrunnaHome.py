import requests
import json
import os
import argparse
import csv
import os.path
import urllib.parse
import sys
import logging
import http.client as http_client
from http.client import HTTPConnection

import sqlite3

from requests.packages.urllib3.exceptions import InsecureRequestWarning

import telegram

import gspread
from oauth2client.service_account import ServiceAccountCredentials

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


EcoleDirectVersion = 'v4'

proxies = {}
sep = ","


class UnEnfant:
    "Notes"
    prenom = ''
    onglet = ''

    def __init__(self):
        self.prenom = ''
    def __eq__(self, other):
        """Comparaison de deux au pair"""
        return self.prenom == other.prenom
    def toString(self, sep):
        """Format du dump fichier"""
        return self.prenom \
               + sep + self.onglet

class UneNote:
    "Notes"
    periode = ''
    libelleMatiere = ''
    valeur = ''
    noteSur = ''
    coef = ''
    typeDevoir = ''
    devoir = ''
    date = ''
    nonSignificatif = False
    def __init__(self, periode, libelleMatiere,valeur,noteSur,coef,typeDevoir,devoir,date,nonSignificatif):
        self.periode = periode
        self.libelleMatiere = libelleMatiere
        self.valeur = valeur
        self.noteSur = noteSur
        self.coef = coef
        self.typeDevoir = typeDevoir
        self.devoir = devoir
        self.date = date
        self.nonSignificatif = nonSignificatif
    def __eq__(self, other):
        """Comparaison de deux notes"""
        return self.periode == other.periode \
               and self.libelleMatiere == other.libelleMatiere \
               and str(self.devoir) == str(other.devoir) \
               and self.date == other.date
    def __lt__(self, other):
        """Trie de deux notes"""
        if self.periode == other.periode:
            if self.libelleMatiere == other.libelleMatiere:
                if self.date == other.date:
                    if ( str(self.valeur).isnumeric() and str(other.valeur).isnumeric() ):
                        return self.valeur < other.valeur
                    else:
                        return -1
                else:
                    return self.date < other.date
            else:
                return self.libelleMatiere < other.libelleMatiere
        else:
            return self.periode < other.periode
    def toString(self, sep):
        """Format du dump fichier"""
        return self.periode \
               + sep + self.libelleMatiere \
               + sep + self.valeur \
               + sep + self.noteSur \
               + sep + self.coef \
               + sep + self.typeDevoir \
               + sep + self.devoir \
               + sep + self.date

def func(self):
        print('Hello')

def dump( champ, bulletProof ):
    returnMe = ""
    if ( bulletProof ):
        returnMe = repr(str(champ.encode('utf8')))[2:-1]
    else:
        returnMe = "'" + str(champ) + "'"
    returnMe = returnMe.replace("'", "\"")
    return returnMe

def listeNoteGoogle(sheetOnglet):
    all_kid_notes = []
    all_kid_notes_sheet = sheetOnglet.get_all_records()
    #
    for rec in all_kid_notes_sheet:
        uneNote = UneNote('', '', '', '', '', '', '', '','')
        for item in rec.items():
            # print(item[0], " -- ", item[1], "<", item, ">",)
            if ( item[0] == 'periode'):
                uneNote.periode = item[1]
            if ( item[0] == 'libelleMatiere'):
                uneNote.libelleMatiere = item[1]
            if ( item[0] == 'valeur'):
                uneNote.valeur = item[1]
            if ( item[0] == 'noteSur'):
                uneNote.noteSur = item[1]
            if ( item[0] == 'coef'):
                uneNote.coef = item[1]
            if ( item[0] == 'typeDevoir'):
                uneNote.typeDevoir = item[1]
            if ( item[0] == 'devoir'):
                uneNote.devoir = item[1]
            if ( item[0] == 'date'):
                uneNote.date = item[1]
        all_kid_notes.append(uneNote)

    all_kid_notes = sorted(all_kid_notes)
    return all_kid_notes

# fonction pour lister toutes les notes d'un eleve sur base de son ID
def listeNoteSite(eleve_id, token):
    all_kid_notes = []

    payloadNotes = "data={\"anneeScolaire\": \"\"}"
    headersNotes = {'User-Agent':'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1', 'content-type': 'application/x-www-form-urlencoded','X-Token':token}
    r = requests.post("https://api.ecoledirecte.com/v3/eleves/" + str(eleve_id) + "/notes.awp?verbe=get&v=4.33.0",
                      data=payloadNotes, headers=headersNotes, proxies=proxies, verify=False)
    if r.status_code != 200:
        print(r.status_code, r.reason)
    notesEnJSON = json.loads(r.content)
    print(notesEnJSON)
    if len(notesEnJSON['data']['notes']) > 0:
        for note in notesEnJSON['data']['notes']:
            uneNote = UneNote( \
                    note['codePeriode'] \
                ,   note['libelleMatiere'] \
                ,   note['valeur'].replace(".", ",") \
                ,   note['noteSur'] \
                ,   note['coef'].replace(".", ",") \
                ,   note['typeDevoir'] \
                ,   note['devoir'] \
                ,   note['date'] \
                ,   note['nonSignificatif'] \
                )
            all_kid_notes.append(uneNote)
        all_kid_notes = sorted(all_kid_notes)
    else:
        print("pas de notes encore")
    return all_kid_notes


# partie principale
if __name__ == "__main__":

    parser=argparse.ArgumentParser(description='Ecole Direct extact process')

    # Ecole Directe cred
    parser.add_argument('--user', help='ED User', type=str, required=True)
    parser.add_argument('--pwd', help='ED Password', type=str, required=True)
    parser.add_argument('--proxy', help='Proxy if behind firewall : https://uzer:pwd@name:port', type=str, default="")
    # credential google
    parser.add_argument('--cred', help='Google Drive json credential file', type=str, required=True)
    # telegram mode
    parser.add_argument('--token', help='Telegram bot token', type=str, default="")
    parser.add_argument('--chatid', help='Telegram chatid', type=str, default="")
    parser.add_argument('--telegram', help='Telegram flag (use or not)', type=str, default="no")

    #parser.print_help()

    sql_total = "SELECT D3.Date, \
    CAST( D1.Value  AS REAL)/ 1000,\
    CAST( D2.Value  AS REAL)/ 1000,\
    CAST( D3.Value  AS REAL)/ 1000,\
    CAST( D4.Value  AS REAL)/ 1000,\
    CAST( D5.Value  AS REAL)/ 1000,\
    CAST( D6.Value  AS REAL)/ 1000,\
    CAST( D7.Value  AS REAL)/ 1000,\
    CAST( D8.Value  AS REAL)/ 1000,\
    CAST( D9.Value  AS REAL)/ 1000,\
    CAST(D10.Value AS REAL)/ 1000,\
    CAST(D11.Value AS REAL)/ 1000,\
    CAST(D12.Value AS REAL)/ 1000,\
    CAST(D13.Value AS REAL)/ 1000,\
    CAST(D14.Value AS REAL)/ 1000,\
    CAST(D15.Value AS REAL)/ 1000,\
    CAST(D16.Value AS REAL)/ 1000,\
    CAST(D17.Value AS REAL)/ 1000,\
    CAST(D18.Value AS REAL)/ 1000,\
    CAST(D19.Value AS REAL)/ 1000,\
    CAST(D20.Value AS REAL)/ 1000,\
    CAST(D20b.Value AS REAL)/ 1000,\
    CAST(D21.Value AS REAL)/ 1000,\
    CAST(D22.Value AS REAL)/ 1000,\
    CAST(D23.Value AS REAL)/ 1000,\
    CAST(D24.Value AS REAL)/ 1000 \
FROM \
 Meter_Calendar D3 \
 LEFT JOIN Meter_Calendar  D1 ON D3.Date= D1.Date AND  D1.DeviceRowId = 593\
 LEFT JOIN Meter_Calendar  D2 ON D3.Date= D2.Date AND  D2.DeviceRowId = 611\
 LEFT JOIN Meter_Calendar  D4 ON D3.Date= D4.Date AND  D4.DeviceRowId = 587\
 LEFT JOIN Meter_Calendar  D5 ON D3.Date= D5.Date AND  D5.DeviceRowId = 588\
 LEFT JOIN Meter_Calendar  D6 ON D3.Date= D6.Date AND  D6.DeviceRowId = 589\
 LEFT JOIN Meter_Calendar  D7 ON D3.Date= D7.Date AND  D7.DeviceRowId = 651\
 LEFT JOIN Meter_Calendar  D8 ON D3.Date= D8.Date AND  D8.DeviceRowId = 260\
 LEFT JOIN Meter_Calendar  D9 ON D3.Date= D9.Date AND  D9.DeviceRowId = 709\
 LEFT JOIN Meter_Calendar D10 ON D3.Date=D10.Date AND D10.DeviceRowId = 225\
 LEFT JOIN Meter_Calendar D11 ON D3.Date=D11.Date AND D11.DeviceRowId = 659\
 LEFT JOIN Meter_Calendar D12 ON D3.Date=D12.Date AND D12.DeviceRowId = 655\
 LEFT JOIN Meter_Calendar D13 ON D3.Date=D13.Date AND D13.DeviceRowId = 732\
 LEFT JOIN Meter_Calendar D14 ON D3.Date=D14.Date AND D14.DeviceRowId = 713\
 LEFT JOIN Meter_Calendar D15 ON D3.Date=D15.Date AND D15.DeviceRowId = 717\
 LEFT JOIN Meter_Calendar D16 ON D3.Date=D16.Date AND D16.DeviceRowId = 647\
 LEFT JOIN Meter_Calendar D17 ON D3.Date=D17.Date AND D17.DeviceRowId = 604\
 LEFT JOIN Meter_Calendar D18 ON D3.Date=D18.Date AND D18.DeviceRowId = 680\
 LEFT JOIN Meter_Calendar D19 ON D3.Date=D19.Date AND D19.DeviceRowId = 676\
 LEFT JOIN Meter_Calendar D20 ON D3.Date=D20.Date AND D20.DeviceRowId = 672\
 LEFT JOIN Meter_Calendar D20b ON D3.Date=D20b.Date AND D20b.DeviceRowId = 663\
 LEFT JOIN Meter_Calendar D21 ON D3.Date=D21.Date AND D21.DeviceRowId = 268\
 LEFT JOIN Meter_Calendar D22 ON D3.Date=D22.Date AND D22.DeviceRowId = 704\
 LEFT JOIN Meter_Calendar D23 ON D3.Date=D23.Date AND D23.DeviceRowId = 705\
 LEFT JOIN Meter_Calendar D24 ON D3.Date=D24.Date AND D24.DeviceRowId = 706 \
WHERE \
D3.DeviceRowId = 590 AND D3.Date > '{}' ORDER BY D3.Date ASC"

    args=parser.parse_args()

    # use creds to create a client to interact with the Google Drive API
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(str(args.cred), scope)
    client = gspread.authorize(creds)

    # collect all kids and related setup
    notes_ConfigurationSheet = client.open("Maison - electricité - reseau").worksheet("HistoriquekWh")
    list_configuration = notes_ConfigurationSheet.get_all_records()
    listeEnfants = []
    dataMaxi = '2000-01-01'
    googleNextRow = 0
    for rec in list_configuration:
        #print(rec)
        googleNextRow = googleNextRow + 1
        for item in rec.items():
            if ( item[0] == 'DateTime'):
                if ( item[1] > dataMaxi ):
                    dataMaxi = item[1]
    print("**** sboub max : " + dataMaxi + "/ nextrow = " + str(googleNextRow))

    #dataMaxi = '2024-10-25'

    print(sql_total.format(dataMaxi))

    db_file = "/home/pi/domoticz/domoticz.db"
    print("db file exists [" + db_file + "]? " + str(os.path.isfile(db_file)))

    if (not os.path.isfile(db_file)):
        print("***** arg je meure")
        exit(-1)

    sqliteConnection = sqlite3.connect(db_file)
    cur = sqliteConnection.cursor()

    googleNextRow = googleNextRow + 2

    try:
        for rowSQL in cur.execute(sql_total.format(dataMaxi)):
            print(rowSQL)

            row = [rowSQL[0],rowSQL[1],rowSQL[2],rowSQL[3],rowSQL[4],rowSQL[5],rowSQL[6],rowSQL[7],rowSQL[8],rowSQL[9],rowSQL[10],rowSQL[11],rowSQL[12],rowSQL[13],rowSQL[14],rowSQL[15],rowSQL[16],rowSQL[17],rowSQL[18],rowSQL[19],rowSQL[20],rowSQL[21],rowSQL[22],rowSQL[23],rowSQL[24],rowSQL[25]]
            try:
                notes_ConfigurationSheet.insert_row(row, googleNextRow, 'USER_ENTERED')
                googleNextRow = googleNextRow + 1
            except gspread.exceptions.APIError as argh:
                print("Maximum d'ajout pour Google sheet - relancer dans 2 min")
                print("api error : ", argh, file=sys.stderr)
                inventaireNote = "Ajoute Kwh max" + "\n__api.error.max__"
                erreurApiMax = True
                break
    except sqlite3.Error as error:
        print("Error while creating a sqlite table", error)
    finally:
        if sqliteConnection:
            sqliteConnection.close()
            print("sqlite connection is closed")
    cur.close()

    print("**** fin du monde")

    # if ( str(args.telegram) == "yes" ) :
    #     bot = telegram.Bot(token=str(args.token))
    #     bot.send_message(chat_id=str(args.chatid), text=telegram_message, parse_mode=telegram.ParseMode.MARKDOWN)


# Adds a timer to the bottom of the screen, which marks the amount of days until an exam
from aqt import gui_hooks
from datetime import datetime, date
from aqt import mw
from aqt.utils import showInfo
from aqt.deckbrowser import DeckBrowser
from PyQt5 import QtWidgets, QtCore, QtGui
import sqlite3
import pathlib


def days_between(d1, d2):
    d1 = datetime.strptime(d1, "%Y-%m-%d")
    d2 = datetime.strptime(d2, "%Y-%m-%d")
    return (d1 - d2).days


def bold(s):
    return "<b>" + s + "</b>"


def display(deck_browser, content):
    content.stats += """<br><link rel="stylesheet" type="text/css" href="{}/styles.css"/><h3 style="display: inline-block;margin: 0 20px" >Events</h3>
    <div class="settings-btn" onclick='pycmd(\"add-new-event\");'><img src="{}/icons/settings.png"></div>""".format(
        base_url, base_url)
    sortType = config['sort']
    data = cursor.execute(
        '''SELECT * FROM events ORDER by date(date) %s''' % sortType).fetchall()
    today = date.today().strftime("%Y-%m-%d")

    for row in data:
        eventID = row[0]
        due = row[1]
        exam = row[2]
        daysLeft = days_between(due, today)
        if daysLeft < 0:
            deleteEvent(eventID)
        else:
            content.stats += "<br>" + \
                bold(str(daysLeft)) + " days until " + exam


def deleteEvent(eventID):
    cursor.execute('''DELETE FROM events WHERE id=?''', [str(eventID)])
    db.commit()
    mw.deckBrowser.refresh()


class AddEventWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.initUi()

    def initUi(self):
        layout = QtWidgets.QVBoxLayout()

        self.dateLabel = QtWidgets.QLabel()
        self.dateLabel.setText("Select The Date Of The Event")
        self.dateEdit = QtWidgets.QDateEdit()
        self.dateEdit.setDateTime(QtCore.QDateTime.currentDateTime())
        self.dateEdit.setMinimumDate(QtCore.QDate.currentDate())

        self.textLabel = QtWidgets.QLabel()
        self.textLabel.setText("Name / Extra Info")
        self.textbox = QtWidgets.QLineEdit()
        self.textbox.resize(280, 40)

        self.addEventBtn = QtWidgets.QPushButton("Add Event")
        self.addEventBtn.clicked.connect(self.on_click)

        layout.addWidget(self.dateLabel)
        layout.addWidget(self.dateEdit)
        layout.addWidget(self.textLabel)
        layout.addWidget(self.textbox)
        layout.addWidget(self.addEventBtn)

        # adding events
        sortType = config['sort']
        data = cursor.execute(
            '''SELECT id, name FROM events ORDER by date(date) %s''' % sortType).fetchall()

        for eventID, name in data:
            h_layout = QtWidgets.QHBoxLayout()

            self.eventText = QtWidgets.QLabel(name)
            self.deleteButton = QtWidgets.QPushButton("Delete")
            self.deleteButton.setObjectName(str(eventID))
            self.deleteButton.clicked.connect(self.deleteEvent)
            h_layout.addWidget(self.eventText)
            h_layout.addWidget(self.deleteButton)
            layout.addLayout(h_layout)

        h_layout = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel("Sort by: ")
        self.ascending = QtWidgets.QRadioButton("Ascending")
        self.descending = QtWidgets.QRadioButton("Descending")
        self.ascending.toggled.connect(self.changeSortType)
        self.descending.toggled.connect(self.changeSortType)
        sortType = config['sort']
        if sortType == "ASC":
            self.ascending.setChecked(True)
        else:
            self.descending.setChecked(True)
        h_layout.addWidget(lbl)
        h_layout.addWidget(self.ascending)
        h_layout.addWidget(self.descending)
        layout.addLayout(h_layout)

        self.setLayout(layout)
        self.setWindowTitle("Add An Event")

    def deleteEvent(self):
        eventID = self.sender().objectName()
        # delete the value from sql
        cursor.execute('''DELETE FROM events WHERE id=?''', [str(eventID)])
        db.commit()
        self.close()

    def on_click(self):
        name = self.textbox.text()
        if len(name) < 1:
            showInfo("Name Not Entered Correctly")
            return
        date = self.dateEdit.date().toPyDate().strftime("%Y-%m-%d")
        cursor.execute(
            '''INSERT INTO events(date, name) VALUES (?, ?)''', [date, name])
        db.commit()

        self.close()

    def changeSortType(self):
        if self.ascending.isChecked():
            config['sort'] = "ASC"
            mw.addonManager.writeConfig(__name__, config)
        elif self.descending.isChecked():
            config['sort'] = "DESC"
            mw.addonManager.writeConfig(__name__, config)

    def closeEvent(self, event):
        mw.deckBrowser.refresh()


def addButtons(handled, message, context):
    if message == "add-new-event":
        widget = mw.newWidget = AddEventWidget()
        widget.show()

        return (True, None)
    else:
        return handled


# finds path to events.db and opens it
__here__ = pathlib.Path(__file__).resolve().parent
db_file = str(__here__ / 'user_files' / "events.db")
db = sqlite3.connect(db_file)


# permission to access icons
mw.addonManager.setWebExports(__name__, r'.+\.(png|css)')
# get this add-on's root directory name
addon_package = mw.addonManager.addonFromModule(__name__)
# get config
config = mw.addonManager.getConfig(__name__)


base_url = f'/_addons/{addon_package}'


cursor = db.cursor()
cursor.execute(
    '''CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, name TEXT)''')

# converts date from old format (dd/mm/yyyy) to new (yyyy/mm/dd) if old version
if cursor.execute('''PRAGMA user_version''').fetchone()[0] != 2:
    cursor.execute(
        '''UPDATE events SET date=(substr(date, 7, 4) || '-' || substr(date, 4, 2) || '-' || substr(date, 1, 2))''')
    cursor.execute("PRAGMA user_version=2")

db.commit()

gui_hooks.deck_browser_will_render_content.append(display)
gui_hooks.webview_did_receive_js_message.append(addButtons)

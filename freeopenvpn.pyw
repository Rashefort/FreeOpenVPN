# tested on Win 7 32 bit, python 3.6.3
# -*- coding: UTF-8 -*-
from collections import OrderedDict
from queue import Queue
import subprocess
import winreg
import sys
import os
import re

from robobrowser import RoboBrowser
from PyQt5 import QtMultimedia
from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtSql


USER_AGENT = 'Mozilla/5.0 (compatible; RashBrowse 0.5; Syllable)'
WORKER_PLAY = 101
EXIT = 0


#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Password(QtWidgets.QDialog):
    def __init__(self, icon, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle('Подтвердите пароль')
        self.setFixedSize(362, 45)
        self.setWindowIcon(icon)

        tempdir = os.path.join(os.environ['TEMP'], 'captcha.txt')
        with open(tempdir, 'rt') as file:
            password = file.read().strip()

        self.box = QtWidgets.QHBoxLayout()

        path = os.path.join(os.environ['TEMP'], 'captcha.png')
        self.password = QtWidgets.QLabel()
        self.password.setPixmap(QtGui.QPixmap(path))
        self.box.addWidget(self.password)

        self.lineEdit = QtWidgets.QLineEdit()
        self.lineEdit.setText(password)
        self.box.addWidget(self.lineEdit)

        self.button = QtWidgets.QPushButton("&OK")
        self.button.clicked.connect(self.accept)
        self.box.addWidget(self.button)

        self.setLayout(self.box)


#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Worker(QtCore.QThread):
    signal = QtCore.pyqtSignal(str)

    def __init__(self, queue, comboBox, button, sound, parent=None):
        QtCore.QThread.__init__(self, parent)

        self.browser = RoboBrowser(user_agent=USER_AGENT, parser='html.parser')
        self.queue = queue
        self.comboBox = comboBox
        self.button = button
        self.sound = sound
        self.url = None

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'SOFTWARE\\OpenVPN-GUI')
            self.config = winreg.QueryValueEx(key, r'config_dir')[0]
        except:
            self.config = None

        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Tesseract-OCR')
            self.tesseract = winreg.QueryValueEx(key, r'Path')[0]
        except:
            self.tesseract = None


    #---------------------------------------------------------------------------
    def clearing_captcha(self):
        pass


    #---------------------------------------------------------------------------
    def write_config(self, name):
        with open(name, 'rt') as file:
            name = os.path.join(self.config, name.split('\\')[-1])
            country = name.split('\\')[-1].split('_')[0].lower()

            with open(name, 'wt') as config:
                for line in file.readlines():
                    line = line.strip()
                    if line == 'auth-user-pass':
                        line = 'auth-user-pass %s.txt' % country

                    config.write('%s\n' % line)


    #---------------------------------------------------------------------------
    def run(self):
        tempdir = os.environ['TEMP']
        captcha = 'https://www.freeopenvpn.org/logpass/'
        png = os.path.join(tempdir, 'captcha.png')
        txt = png.split('.')[0]

        while True:
            url = self.queue.get()

            if self.url != EXIT:
                self.comboBox.setEnabled(False)
                self.button.setEnabled(False)

                self.browser.open(url)

                if url.find('logpass') >= 0:
                    html = str(self.browser.parsed)
                    captcha += html.split('lnk = \'<img src="')[1].split('"')[0]
                    image = self.browser.session.get(captcha, stream=True)
                    with open(png, 'wb') as file:
                        file.write(image.content)

                    if self.tesseract:
                        current = os.getcwd()
                        os.chdir(self.tesseract)
                        subprocess.call(['tesseract.exe', png, txt])
                        os.chdir(current)

                    country = url.split('/')[-1].split('.')[0].capitalize()
                    url = 'https://www.freeopenvpn.org/ovpn/%s_freeopenvpn_%s.ovpn'

                    for protocol in ('udp', 'tcp'):
                        protocol = url % (country, protocol)
                        config = self.browser.session.get(protocol, stream=True)

                        name = os.path.join(tempdir, protocol.split('/')[-1])
                        with open(name, 'wb') as file:
                            file.write(config.content)

                        self.write_config(name)

                    self.clearing_captcha()

                    name = name.split('\\')[-1].split('_')[0].lower()
                    self.signal.emit(os.path.join(self.config, name))

                else:
                    pass

            else:
                break


#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class FreeOpenVPN(QtWidgets.QWidget):
    def __init__(self, servers, more, sound, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        sound = True if sound else bool(more['sound'])
        tempdir = os.environ['TEMP']

        self.queue = Queue()
        self.servers = servers
        self.more = more

        self.setWindowFlags(
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.WindowCloseButtonHint
        )

        self.icon = QtGui.QIcon(os.path.join(tempdir, 'freeopenvpn.ico'))
        self.setWindowIcon(self.icon)

        self.setWindowTitle('FreeOpenVPN')
        self.setFixedSize(229, 29)

        font = QtGui.QFont()
        font.setPointSize(10)

        self.comboBox = QtWidgets.QComboBox()
        self.comboBox.setDuplicatesEnabled(True)
        self.comboBox.setFixedSize(135, 25)
        self.comboBox.setFont(font)

        for key in servers.keys():
            country = re.split(r'[-.]', self.servers[key].split('/')[-1])[0]
            icon = QtGui.QIcon(os.path.join(tempdir, '%s.png' % country))
            self.comboBox.addItem(icon, key)

        self.comboBox.insertSeparator(self.more['separator'])

        self.button = QtWidgets.QPushButton('Downloads')
        self.button.clicked.connect(self.button_clicked)
        self.button.setFixedSize(90, 27)
        self.button.setFont(font)

        self.thread = Worker(self.queue, self.comboBox, self.button, sound)
        self.thread.signal.connect(self.signal, QtCore.Qt.QueuedConnection)
        self.thread.start()

        self.box = QtWidgets.QHBoxLayout()
        self.box.setContentsMargins(2, 1, 1, 0)
        self.box.addWidget(self.comboBox)
        self.box.addWidget(self.button)

        self.setLayout(self.box)
        self.show()


    #---------------------------------------------------------------------------
    def button_clicked(self):
        self.queue.put(servers[self.comboBox.currentText()])


    #---------------------------------------------------------------------------
    def signal(self, name):
        if name:
            password = Password(self.icon, self)
            password.exec_()

            password = password.lineEdit.text()
            with open('%s.txt' % name, 'wt') as file:
                file.write('freeopenvpn\n%s' % password)

        self.comboBox.setEnabled(True)
        self.button.setEnabled(True)


    #---------------------------------------------------------------------------
    def closeEvent(self, event):
        if self.button.isEnabled():
            self.queue.put(EXIT)
            QtWidgets.QWidget.closeEvent(self, event)

        else:
            QtWidgets.QMessageBox.warning(self,
                'Предупреждение', 'Дождитесь конца загрузки файлов.',
                defaultButton=QtWidgets.QMessageBox.Ok)

            event.ignore()



#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
def datebase():
    tempdir = os.environ['TEMP']

    db = QtSql.QSqlDatabase.addDatabase('QSQLITE')
    db.setDatabaseName('freeopenvpn.db')
    db.open()

    query = QtSql.QSqlQuery()

    query.exec("SELECT * FROM Files")
    if query.isActive():
        query.first()
        while query.isValid():
            fullname = os.path.join(tempdir, query.value('name'))
            with open(fullname, 'wb') as file:
                file.write(query.value('file'))
                query.next()
    else:
        text = 'Файл freeopenvpn.dta отсутствует или поврежден.'
        QtWidgets.QMessageBox.critical(None, 'Ошибка', text,
            defaultButton=QtWidgets.QMessageBox.Ok)
        raise SystemExit

    servers = OrderedDict()
    query.exec("SELECT * FROM Servers")
    if query.isActive():
        query.first()
        while query.isValid():
            servers[query.value('name')] = query.value('url')
            query.next()
    else:
        text = 'Файл freeopenvpn.dta отсутствует или поврежден.'
        QtWidgets.QMessageBox.critical(None, 'Ошибка', text,
            defaultButton=QtWidgets.QMessageBox.Ok)
        raise SystemExit

    more = dict()
    query.exec("SELECT * FROM More")
    if query.isActive():
        query.first()
        while query.isValid():
            more[query.value('name')] = query.value('value')
            query.next()
    else:
        text = 'Файл freeopenvpn.dta отсутствует или поврежден.'
        QtWidgets.QMessageBox.critical(None, 'Ошибка', text,
            defaultButton=QtWidgets.QMessageBox.Ok)
        raise SystemExit

    db.close()

    return servers, more


#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    servers, more = datebase()
    sound = True if len(sys.argv) == 2 and sys.argv[1] == '--sound' else False

    window = FreeOpenVPN(servers, more, sound)

    sys.exit(app.exec_())

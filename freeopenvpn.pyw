# tested on Win 7 32 bit, python 3.6.3
# -*- coding: UTF-8 -*-
from collections import OrderedDict
from queue import Queue
import sys
import os
import re

from robobrowser import RoboBrowser
from PyQt5 import QtMultimedia
from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtSql


PLAY = 101
EXIT = 0


#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class Worker(QtCore.QThread):
    signal = QtCore.pyqtSignal(bool)

    def __init__(self, queue, comboBox, button, sound, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.queue = queue
        self.comboBox = comboBox
        self.button = button
        self.sound = sound
        self.url = None


    #---------------------------------------------------------------------------
    def run(self):
        while True:
            self.url = self.queue.get()

            if self.url != EXIT:



                self.sleep(10)
                print('03. end -> sleep')

                self.comboBox.setEnabled(True)
                self.button.setEnabled(True)

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

        icon = QtGui.QIcon(os.path.join(tempdir, 'freeopenvpn.ico'))
        self.setWindowIcon(icon)

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
        # self.thread.signal.connect(self.signal, QtCore.Qt.QueuedConnection)
        self.thread.start()

        box = QtWidgets.QHBoxLayout()
        box.setContentsMargins(2, 1, 1, 0)
        box.addWidget(self.comboBox)
        box.addWidget(self.button)

        self.setLayout(box)
        self.show()


    #---------------------------------------------------------------------------
    def button_clicked(self):
        self.comboBox.setEnabled(False)
        self.button.setEnabled(False)
        self.queue.put('test')


    #---------------------------------------------------------------------------
    # def signal(self, result):
    #     print(result)
    #     if result:
    #         self.comboBox.setEnabled(True)
    #         self.button.setEnabled(True)


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

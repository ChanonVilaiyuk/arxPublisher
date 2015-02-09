# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'U:/extensions/studioTools/python/arxPublisher/loader.ui'
#
# Created: Sun Nov 09 02:29:47 2014
#      by: pyside-uic 0.2.14 running on PySide 1.2.0
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_loadWindow(object):
    def setupUi(self, loadWindow):
        loadWindow.setObjectName("loadWindow")
        loadWindow.resize(174, 43)
        self.centralwidget = QtGui.QWidget(loadWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.load_label = QtGui.QLabel(self.centralwidget)
        self.load_label.setGeometry(QtCore.QRect(50, 10, 71, 21))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.load_label.setFont(font)
        self.load_label.setObjectName("load_label")
        loadWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(loadWindow)
        QtCore.QMetaObject.connectSlotsByName(loadWindow)

    def retranslateUi(self, loadWindow):
        loadWindow.setWindowTitle(QtGui.QApplication.translate("loadWindow", "Arxanima", None, QtGui.QApplication.UnicodeUTF8))
        self.load_label.setText(QtGui.QApplication.translate("loadWindow", "Loading ...", None, QtGui.QApplication.UnicodeUTF8))


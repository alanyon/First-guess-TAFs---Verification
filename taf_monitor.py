#!/usr/bin/python
# (C) British Crown Copyright 2018-2019 Met Office.
# All rights reserved.
#
# This file is part of TAF Monitor.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""
###############################################################################
#                                                                             #
#           TAF Monitor - Checks METAR observations against TAFS.             #
#                      - Written by B Ayliffe 2016 -                          #
#                                                                             #
###############################################################################
"""
import os.path as osp
import platform
import sys
from datetime import datetime as dt

from checking import CheckTafThread, airfield_benches
from retard_alert import RetardThread

if platform.system() == "Linux":
    from PySide2 import QtCore  # pylint: disable=import-error
    from PySide2 import QtWidgets as QtGui  # pylint: disable=import-error
    from PySide2.QtCore import SIGNAL  # pylint: disable=import-error
    from PySide2.QtGui import QIcon  # pylint: disable=import-error
    from PySide2.QtMultimedia import QSound  # pylint: disable=import-error
else:
    from PyQt4 import QtCore, QtGui  # pylint: disable=import-error
    from PyQt4.QtCore import SIGNAL  # pylint: disable=import-error
    from PyQt4.QtGui import QIcon, QSound  # pylint: disable=import-error

######################################
#                                    #
#               GUI                  #
#                                    #
######################################


# GUI written as QT4 widget - Presents dialogue to allow user to select bench,
# start/stop operation, and change options.


class qtwindow(QtGui.QWidget):
    def __init__(self):
        super(qtwindow, self).__init__()
        # self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.initUI()

    # Establish window with drop down list and selection button
    def initUI(self):
        # Set window geometry.
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)
        self.setLayout(grid)

        # Create and populate drop down list.
        self.option = QtGui.QComboBox(self)
        grid.addWidget(self.option, 1, 1)
        for item in list(airfield_benches.keys()):
            self.option.addItem(item)
        self.bench_selected = str(self.option.currentText())
        self.option.currentIndexChanged.connect(self.airfield_change)

        # Create and position start/stop run button.
        self.btn = QtGui.QPushButton("Start", self)
        self.btn.resize(self.btn.sizeHint())
        self.btn.start = True
        grid.addWidget(self.btn, 1, 2)
        self.btn.clicked.connect(self.buttonclick)

        # Create and position repeat message button.
        self.last_message = ""
        self.btn_lastmessage = QtGui.QPushButton("Show last message", self)
        self.btn_lastmessage.setEnabled(False)
        self.btn_lastmessage.resize(self.btn_lastmessage.sizeHint())
        grid.addWidget(self.btn_lastmessage, 2, 2)
        self.btn_lastmessage.clicked.connect(self.showlastmessage)

        # Create and position show airfields button.
        self.btn_airfields = QtGui.QPushButton("List airfields", self)
        self.btn_airfields.setEnabled(True)
        self.btn_airfields.resize(self.btn_airfields.sizeHint())
        grid.addWidget(self.btn_airfields, 2, 1)
        self.btn_airfields.clicked.connect(self.show_airfields)

        # Check box for retard reminders
        self.retard_cb = QtGui.QCheckBox("Retard TAF reminders", self)
        grid.addWidget(self.retard_cb, 3, 1)
        self.activeretard = False
        self.retard_cb.stateChanged.connect(self.retard_alerts)

        # Check box to enable sounds
        self.sound_opt = QtGui.QCheckBox("Play alert sounds", self)
        grid.addWidget(self.sound_opt, 4, 1)

        # Check box to enable jump to front
        # self.front_opt = QtGui.QCheckBox('Pop-up to front', self)
        # grid.addWidget(self.front_opt, 4, 1)

        # Add instruction label.
        self.label_bottom = QtGui.QLabel("Select aviation bench.", self)
        grid.addWidget(self.label_bottom, 3, 2)

        # Centre window on screen.
        self.setFixedSize(360, 140)
        self.center()
        self.setWindowTitle("TAF Monitor")

        self.show()

    # Start TAF Monitor when RETURN key is pressed
    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Return:
            self.start_taf_monitor()

    # Start TAF Monitor when button is clicked
    def buttonclick(self):
        if self.btn.start:
            self.btn.setText("Stop")
            self.btn.setStyleSheet("background-color: None")
            self.btn.start = False
            self.start_taf_monitor()
        else:
            self.btn.setText("Start")
            self.btn.start = True
            self.stop_taf_monitor()

    # Grab bench name and send to principle code.
    def start_taf_monitor(self):
        # TAF Monitor thread
        self.bench_selected = str(self.option.currentText())
        self.get_thread = CheckTafThread(self.bench_selected)
        self.get_thread.start()
        self.connect(
            self.get_thread, SIGNAL("finish_check(QString)"), self.complete_taf_check
        )

        # Optional retard alert thread
        if self.retard_cb.isChecked():
            self.activeretard = True
            self.retard_thread = RetardThread(self.bench_selected)
            self.retard_thread.start()
            self.connect(
                self.retard_thread,
                SIGNAL("retard_result(QString)"),
                self.complete_retard_check,
            )

    def stop_taf_monitor(self):
        # self.get_thread = CheckTafThread(self.bench_selected)
        self.get_thread.interrupt()
        if self.activeretard:
            self.retard_thread.terminate()

    def airfield_change(self):
        if not self.btn.start:
            self.stop_taf_monitor()
            self.btn.setText("Start")
            self.btn.setStyleSheet("background-color: #fe5757; color: white")
            self.btn.start = True
        self.bench_selected = str(self.option.currentText())

    # Get display geometry to centre window.
    def center(self):
        qr = self.frameGeometry()
        cp = QtGui.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    # Show last message when clicked
    def showlastmessage(self):
        self.print_message(self.last_message, "LAST", False)

    # Show list of airfields in current list
    def show_airfields(self):
        current_airfields = airfield_benches[self.bench_selected]
        airfield_message = ", ".join(current_airfields)
        self.print_airfields(airfield_message)

    def retard_alerts(self):
        if not self.btn.start:
            if not self.retard_cb.isChecked():
                self.activeretard = False
                self.retard_thread.terminate()
            else:
                self.activeretard = True
                self.retard_thread = RetardThread(self.bench_selected)
                self.retard_thread.start()
                self.connect(
                    self.retard_thread,
                    SIGNAL("retard_result(QString)"),
                    self.complete_retard_check,
                )

    def complete_taf_check(self, taf_string):
        self.label_bottom.setText("Last TAF check at " + dt.now().strftime("%H:%M"))
        if taf_string:
            self.btn_lastmessage.setText(
                "Show last message (" + dt.now().strftime("%H:%M") + ")"
            )
            self.print_message(taf_string, "TAF", self.sound_opt.isChecked())

    def complete_retard_check(self, retard_string):
        if retard_string:
            self.btn_lastmessage.setText(
                "Show last message (" + dt.now().strftime("%H:%M") + ")"
            )
            self.print_message(retard_string, "RETARD", self.sound_opt.isChecked())

    def print_message(self, message_in, message_type, playsound):
        self.btn_lastmessage.setEnabled(True)
        self.last_message = message_in
        msg = QtGui.QMessageBox()
        msg.setText(message_in)

        if message_type == "TAF":
            msg.setIcon(QtGui.QMessageBox.Warning)
            msg.setWindowTitle(str("TAF Status - " + self.bench_selected))
            alert_sound = (
                "C:\\Windows\\winsxs\\amd64_microsoft-windows-s"
                "..soundthemes-savanna_31bf3856ad364e35_6.1.7600."
                "16385_none_8501e89d0b011992\\Windows "
                "Exclamation.wav"
            )
        elif message_type == "LAST":
            msg.setIcon(QtGui.QMessageBox.Information)
            msg.setWindowTitle(str("Last Message"))
        elif message_type == "RETARD":
            msg.setIcon(QtGui.QMessageBox.Information)
            msg.setWindowTitle(str("Retard TAF Alert"))
            alert_sound = (
                "C:\\Windows\\winsxs\\amd64_microsoft-windows-s"
                "..soundthemes-savanna_31bf3856ad364e35_6.1.7600."
                "16385_none_8501e89d0b011992\\Windows Print "
                "complete.wav"
            )

        self.setWindowState(
            self.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive
        )
        msg.activateWindow()
        if playsound:
            try:
                QSound(alert_sound).play()
            except IOError:
                pass
        msg.exec_()

    def print_airfields(self, message_in):
        msg = QtGui.QMessageBox()
        msg.setText(message_in)
        msg.setIcon(QtGui.QMessageBox.Information)
        msg.setWindowTitle("Airfields on bench {}".format(self.bench_selected))
        msg.exec_()

    def closeEvent(self, event):
        quit_msg = "Closing this window will stop TAF Monitor. Continue?"
        reply = QtGui.QMessageBox.question(
            self, "Message", quit_msg, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No
        )

        if reply == QtGui.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


# End of GUI coding.


############################################
#                                          #
#              GLOBAL ROUTINE              #
#                                          #
############################################

# Create GUI for user selection of bench.

# Gives program unique ID to separate it from other python apps being run.
myappid = "metoffice.tafmonitor.version.one"
# ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

app = QtGui.QApplication(sys.argv)
# Sets icon for window corner and task bar.
icon_path = osp.join(osp.dirname(sys.modules[__name__].__file__), "../etc/TM.xpm")
app.setWindowIcon(QIcon(icon_path))

w = qtwindow()
sys.exit(app.exec_())

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

import platform
from datetime import datetime as dt
from datetime import timedelta as timedelta

from airfields_and_thresholds import define_airfields, define_benches
from data_retrieval import RetrieveObservations

if platform.system() == "Linux":
    from PySide2.QtCore import SIGNAL, QThread  # pylint: disable=import-error
else:
    from PyQt4.QtCore import SIGNAL, QThread  # pylint: disable=import-error

airfield_benches = define_benches()
all_airfields = define_airfields()


class RetardThread(QThread):
    def __init__(self, bench_selected):
        QThread.__init__(self)
        self.bench_selected = bench_selected

    def __del__(self):
        self.wait()

    def interrupt(self):
        self._active = False

    def run(self):
        self._active = True
        while self._active:
            self.RetardChecker()
            self.sleep(300)

    def RetardChecker(self):
        time_now = dt.utcnow()
        start_time = time_now - timedelta(hours=2)
        end_time = time_now + timedelta(hours=1)

        airfields = airfield_benches[self.bench_selected]

        retards_to_send = []
        retard_format = "Send RETARD TAF - {icao}"

        for icao in airfields:
            taf = RetrieveObservations(icao, "T", time_now).operation()

            # If a TAF exists and has not been cancelled, assume no new TAF is
            # required.
            if taf[0] != "NoRecord" and "CNL" not in taf:
                continue

            # Retrieve metars for the morning period from 00Z to 12Z
            # Retards are not usually issued outside this window.
            metars = RetrieveObservations(
                icao,
                "M",
                time_now,
                latest_only=False,
                start_time=start_time,
                end_time=end_time,
            ).operation()
            n_metars = len(metars)

            # No metars so no TAF
            if metars[0] != "NoRecord":
                continue

            # If only one ob recieved and it is an AUTO no TAF to be issued.
            if n_metars == 1 and "AUTO" in metars[-1]:
                continue

            # If the last ob was an AUTO no TAF to be issued.
            if "AUTO" in metars[-1]:
                continue

            # The last ob was a manual, so single_metar_issue sites get a TAF
            # e.g. Hawarden
            if all_airfields[icao]["single_metar_issue"]:
                retards_to_send.append(retard_format.format(icao=icao))
                continue

            # Several overnight AUTOs followed by a single manual observation
            # e.g. Tiree
            n_autos = sum(["AUTO" in metar for metar in metars])
            if n_autos > 1 and n_autos == n_metars - 1:
                retards_to_send.append(retard_format.format(icao=icao))
                continue

            # Sites requiring two manual obs as no overnight AUTOs
            # e.g. Oban
            if n_metars > 1 and "AUTO" not in metars[-2]:
                retards_to_send.append(retard_format.format(icao=icao))
                continue

        if retards_to_send:
            self.emit(SIGNAL("retard_result(QString)"), "\n".join(retards_to_send))

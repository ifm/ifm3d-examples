#! /usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2021 ifm electronic gmbh
#
# THE PROGRAM IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND.
#


import errno
import json
import logging
import select
import socket
import time
from nexxT.Qt.QtCore import QTimer, Qt
from nexxT.Qt.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from nexxT.interface import Filter, DataSample, Services
from ifm_o3r_algodebug.Receiver import ConnectionLost

logger = logging.getLogger(__name__)

class DiagReceiver(Filter):
    def __init__(self, env):
        super().__init__(False, False, env)
        self._rcv_bufsize = 4096
        self._outp = self.addStaticOutputPort("errors")
        pc = self.propertyCollection()
        pc.defineProperty("IPAdress", "192.168.0.69", "Sensor ip address.")

    def _connect(self):
        self._disconnect()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._socket.connect((self.propertyCollection().getProperty("IPAdress"), 50009))

    def _disconnect(self):
        if hasattr(self, "_socket"):
            self._socket.close()
            del self._socket

    def onStart(self):
        self._connect()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(0)
        self.timer.timeout.connect(self.waitForData)
        self.timer.start()
        self._recvall_state = None
        self._timebarrier = None
        self.activeErrors = {}

    def onStop(self):
        self.timer.stop()
        self._disconnect()
        del self._recvall_state
        del self.timer

    def _recvall(self, msg_len):
        if self._recvall_state is None:
            self._recvall_state = [bytearray(msg_len), 0]
        max_msg_size = self._rcv_bufsize
        view = memoryview(self._recvall_state[0])[self._recvall_state[1]:]
        while self._recvall_state[1] < msg_len:
            nbytes = 0
            try:
                if self._timebarrier is not None:
                    timeout = max(0, self._timebarrier - time.monotonic())
                    select.select([self._socket], [], [], timeout)
                try:
                    nbytes = self._socket.recv_into(view, min(msg_len - self._recvall_state[1], max_msg_size))
                except BlockingIOError as ioerr:
                    if (self._timebarrier is None or timeout > 0) and ioerr.errno in [errno.EAGAIN, errno.EWOULDBLOCK]:
                        continue
                    raise ioerr
                view = view[nbytes:]
            except BlockingIOError as ioerr:
                if ioerr.errno in [errno.EAGAIN, errno.EWOULDBLOCK]:
                    raise TimeoutError("timeout, try again")
                logger.exception("Received exception during socket.recv.")
                raise ConnectionLost()
            except:
                logger.exception("Received exception during socket.recv.")
                raise ConnectionLost()
            if nbytes == 0:
                logger.debug("received 0 bytes -> connection lost")
                raise ConnectionLost()
            self._recvall_state[1] += nbytes
        ret = self._recvall_state[0]
        self._recvall_state = None
        return ret

    def _readAnswer(self, reqTicket = None):
        while True:
            answer = self._recvall(16)
            ticket = answer[0:4]
            ansLen = int(answer.split(b"L")[1])
            res = self._recvall(ansLen)
            assert res[:4] == ticket and len(res) == ansLen
            if reqTicket is None or ticket == reqTicket:
                break
        # skip the repeated ticket number and the "\r\n" end
        return res[4:-2], ticket

    def waitForData(self):
        try:
            self._timebarrier = time.monotonic() + 0.5
            self._socket.setblocking(False)
            answer, ticket = self._readAnswer()
            res = json.loads(answer[answer.index(b":")+1:])
            if isinstance(res, dict) and "events" in res:
                res = res["events"]
            for err in res:
                self.activeErrors["%d-%s" % (err["id"], err["source"])] = err
            d = json.dumps(self.activeErrors).encode("utf-8")
            self._outp.transmit(DataSample(d, "json", DataSample.currentTime()))
        except TimeoutError:
            pass
        except ConnectionLost:
            self._connect()
        finally:
            self.timer.start()

class DiagDisplay(Filter):
    def __init__(self, env):
        super().__init__(False, False, env)
        self._inp = self.addStaticInputPort("errors")
        self.propertyCollection().defineProperty("SubplotID", "Diagnosis", "Subplot ID for the diagnosis widget")

    def onOpen(self):
        srv = Services.getService("MainWindow")
        self.gui = QTableWidget(0, 5) # 5 columns: ID, NAME, SOURCE, STATE, COUNT
        self.gui.setHorizontalHeaderLabels(["ID", "Name", "Source", "State", "Count"])
        self.gui.sortByColumn(3, Qt.AscendingOrder)
        self.gui.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.gui.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.gui.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.gui.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.gui.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.subplotID = self.propertyCollection().getProperty("SubplotID")
        self.idsToItems = {}
        srv.subplot(self.subplotID, self, self.gui)

    def onClose(self):
        srv = Services.getService("MainWindow")
        srv.releaseSubplot(self.gui)
        del self.idsToItems
        del self.gui
        del self.subplotID

    def onPortDataChanged(self, port):
        sample = port.getData()
        if sample.getDatatype() == "json":
            errors = json.loads(bytearray(sample.getContent()))
            unseenIDs = set(self.idsToItems.keys())
            self.gui.setSortingEnabled(False)
            for idsrc in errors:
                e = errors[idsrc]
                k = (e["id"], e["source"])
                if k in unseenIDs:
                    unseenIDs.remove(k)
                if k in self.idsToItems:
                    self.idsToItems[k][3].setText("%s" % e["state"])
                    self.idsToItems[k][4].setText("%d" % e["stats"]["count"])
                else:
                    self.idsToItems[k] = [QTableWidgetItem("%08d" % e["id"]),
                                          QTableWidgetItem("%s" % e["name"]),
                                          QTableWidgetItem("%s" % e["source"]),
                                          QTableWidgetItem("%s" % e["state"]),
                                          QTableWidgetItem("%d" % e["stats"]["count"])]
                    r = self.gui.rowCount()
                    self.gui.setRowCount(r + 1)
                    for c,item in enumerate(self.idsToItems[k]):
                        item.setToolTip(e["description"])
                        self.gui.setItem(r, c, item)
                font = self.idsToItems[k][0].font()
                if e["state"] == "dormant":
                    font.setBold(False)
                    font.setStrikeOut(True)
                else:
                    font.setBold(True)
                    font.setStrikeOut(False)
                for item in self.idsToItems[k]:
                    item.setFont(font)
            for k in unseenIDs:
                self.gui.removeRow(self.idsToItems[k][0].row())
            self.gui.setSortingEnabled(True)

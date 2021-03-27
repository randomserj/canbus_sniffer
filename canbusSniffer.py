import sys
import time
import serial
from serial.tools import list_ports
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import QThread, pyqtSignal
import canbusSnifferGUI

PREFIX = 'aa55aa55'


def converter(base16, format=10):
    converted = int(base16, 16)
    if format == 2:
        converted = bin(converted)
    return converted


class readSerialPort(QThread):
    data = pyqtSignal(str)

    def __init__(self, window, flag, parent=None):
        super().__init__()
        self.window = window
        self.stopFlag = flag

    def run(self):
        while self.window.serial_port.isOpen() and not self.stopFlag:
            can_msg = self.window.serial_port.readline()
            line = can_msg.decode('latin1')[:-2]             # to remove \r\n at the end of the can_msg
            if len(line) > 0:
                self.data.emit(line)

    def send(self, packet):
        if self.window.serial_port.isOpen():
            self.window.serial_port.write(packet)

    def stop(self):
        self.stopFlag = True

class Sniffer(QMainWindow, canbusSnifferGUI.Ui_canbusSniffer):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.canbusDataReceived.setHorizontalHeaderLabels(["ID", "DLC", "Byte1", "Byte2", "Byte3", "Byte4", "Byte5", "Byte6", "Byte7", "Byte8"])
        self.canbusPacketToSend.setHorizontalHeaderLabels(["ID", "DLC", "Byte1", "Byte2", "Byte3", "Byte4", "Byte5", "Byte6", "Byte7", "Byte8"])
        self.getSerialDevices()
        self.canbusSetStatus.clicked.connect(self.setStatusSerialDevice)
        self.canbusSendPacket.clicked.connect(self.sendPacket)
        self.canbusSendingPacket.clicked.connect(self.sendingPacket)

    def guiRepaint(self):       # to fix not updating widgets
        self.canbusSetStatus.repaint()
        self.canbusStatus.repaint()

    def getSerialDevices(self):
        devices = serial.tools.list_ports.comports()
        for device in devices:
            if device[0] != 'n/a':
                self.canbusSelect.addItem(device[0])

    def setStatusSerialDevice(self):
        if self.canbusSetStatus.text() == 'Connect':
            if self.canbusSelect.currentText() != '':
                selected_device = str(self.canbusSelect.currentText())
                selected_speed = int(self.canbusSpeed.currentText())
                try:
                    self.serial_port = serial.Serial(selected_device, selected_speed, timeout=1)
                    self.readSerialPortThread = readSerialPort(window=self, flag=False)
                    self.readSerialPortThread.data.connect(self.getSerialData)
                    self.canbusDataReceived.setRowCount(0)
                    self.readSerialPortThread.start()
                    self.canbusStatus.setText('Connected')
                    self.canbusSetStatus.setText('Disconnect')
                    self.guiRepaint()
                except:
                    self.canbusStatus.setText('Incorrect port')
                    self.guiRepaint()
        else:
            self.readSerialPortThread.stop()
            self.readSerialPortThread.terminate()
            self.readSerialPortThread.wait()
            self.serial_port.close()
            self.canbusStatus.setText('Disconnected')
            self.canbusSetStatus.setText('Connect')
            self.guiRepaint()

    def getSerialData(self, line):
        packet_prefix, packet = [line[:len(PREFIX)], line[len(PREFIX):]]
        if packet_prefix == PREFIX and len(packet) > 0:
            packet_id, packet_dlc, data = packet.split(' ', 2)
            packet_data = data.split(' ')
            self.sortSerialData(packet_id, packet_dlc, packet_data)

    def sortSerialData(self, p_id, p_len, p_data):
        new_byte = None
        rows = self.canbusDataReceived.rowCount()
        for i in range(rows):
            current_id = self.canbusDataReceived.item(i, 0).text()
            if current_id == p_id and int(p_len) <= 8:
                for j in range(int(p_len)):
                    old_byte = self.canbusDataReceived.item(i, j+2).text()
                    new_byte = p_data[j]
                    if new_byte != old_byte:
                        self.canbusDataReceived.setItem(i, j+2, QtWidgets.QTableWidgetItem(new_byte))
                        self.canbusDataReceived.item(i, j+2).setBackground(QtGui.QColor('red'))
                    if new_byte == old_byte:
                        self.canbusDataReceived.item(i, j+2).setBackground(QtGui.QColor('white'))
                continue
        if new_byte is None and p_len != '' and p_len != '0':
            self.canbusDataReceived.insertRow(rows)
            self.canbusDataReceived.setItem(rows, 0, QtWidgets.QTableWidgetItem(p_id))
            self.canbusDataReceived.setItem(rows, 1, QtWidgets.QTableWidgetItem(p_len))
            for j in range(min(int(p_len), 8)):
                self.canbusDataReceived.setItem(rows, j+2, QtWidgets.QTableWidgetItem(p_data[j]))
                self.canbusDataReceived.item(rows, j+2).setBackground(QtGui.QColor('red'))

    def combinePacketToSend(self):
        try:
            p_id = self.canbusPacketToSend.item(0, 0).text()
            p_len = self.canbusPacketToSend.item(0, 1).text()
            p = p_id + p_len
            if p_len != '':
                for i in range(int(p_len)):
                    p += self.canbusPacketToSend.item(0, i+2).text()
                #packet = bytes.fromhex(p)
                packet = p.encode('ascii')
                return(packet)
        except:
            print('Wrong packet structure')
        else:
            print('ID or DLC is missing')


    def sendPacket(self):
        p = self.combinePacketToSend()
        if p:
            print(p)
            self.readSerialPortThread.send(packet=p)

    def sendingPacket(self):
        p = self.combinePacketToSend()
        if p:
            for i in range(10):
                self.readSerialPortThread.send(packet=p)
                time.sleep(0.01)


def main():
    app = QApplication(sys.argv)
    window = Sniffer()
    window.show()
    app.exec()



if __name__ == '__main__':
    main()

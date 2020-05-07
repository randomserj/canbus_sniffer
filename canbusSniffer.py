import sys
import time
import serial
from serial.tools import list_ports
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import QThread, pyqtSignal
import canbusSnifferGUI

can_separator = b'\xaa\x55\xaa\x55'         # 0xAA55AA55 used to separate packets
#can_500_start = ''


class readSerialPort(QThread):
    data = pyqtSignal(str)

    def __init__(self, window, flag, parent=None):
        super().__init__()
        self.window = window
        self.stopFlag = flag

    def run(self):
        while self.window.serial_port.isOpen() and not self.stopFlag:
            can_msg = self.window.serial_port.read_until(can_separator)
            line = can_msg[:-4].decode('ascii')        # to remove last 4 bits 0xAA55AA55
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
        else:
            self.readSerialPortThread.stop()
            self.readSerialPortThread.terminate()
            self.readSerialPortThread.wait()
            self.serial_port.close()
            self.canbusStatus.setText('Disconnected')
            self.canbusSetStatus.setText('Connect')
            self.guiRepaint()

    def getSerialData(self, line):
        if len(line) > 4:
            packet_id = line[:3]
            packet_dlc = line[3]
            packet_data = [line[i:i+2] for i in range(4, len(line), 2)]
            self.checkPacket(packet_id, packet_dlc, packet_data)
            self.sortSerialData(packet_id, packet_dlc, packet_data)

    def checkPacket(self, p_id, p_dlc, p_data):
        if p_id == '999':
            if p_data[0] == '01':
                print(p_data)
                self.readSerialPortThread.send('9996can500'.encode('ascii'))
            if p_data[0] == '02':
                print(p_data)
                self.readSerialPortThread.send('9998canstart'.encode('ascii'))

    def sortSerialData(self, p_id, p_len, p_data):
        new_byte = None
        rows = self.canbusDataReceived.rowCount()
        for i in range(rows):
            current_id = self.canbusDataReceived.item(i, 0).text()
            if current_id == p_id and int(p_len) < 9:
                for j in range(int(p_len)):
                    old_byte = self.canbusDataReceived.item(i, j+2).text()
                    new_byte = p_data[j]
                    if new_byte != old_byte:
                        self.canbusDataReceived.setItem(i, j+2, QtWidgets.QTableWidgetItem(new_byte))
                        self.canbusDataReceived.item(i, j+2).setBackground(QtGui.QColor('red'))
                    if new_byte == old_byte:
                        self.canbusDataReceived.item(i, j+2).setBackground(QtGui.QColor('white'))
                continue
        if new_byte is None and p_len != '':
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

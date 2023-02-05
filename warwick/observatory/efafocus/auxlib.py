# Library for communicating with devices that use the "Aux" protocol.
# Examples include the PlaneWave EFA Kit, Delta-T dew heater,
# and Mirror Cover controller.
# Written by Kevin Ivarsen
# Copyright 2014-2021 PlaneWave Instruments

import socket
import struct
import serial


class Enum:
    """
    Utility class for creating a set of named constants.
    Name can be converted to value, and value and be converted to string name.

    Example:

    commands = Constants(
        GET_TEMP = 0x01,
        GET_RATE = 0x02,
        SET_RATE = 0x03
        )

    sendCommand(commands.GET_TEMP)
    print commands.getName(0x01) # GET_TEMP
    """

    def __init__(self, **kwargs):
        self._namesToValues = kwargs
        self._valuesToNames = dict()
        for k, v in list(self._namesToValues.items()):
            self._valuesToNames[v] = k

    def getName(self, value):
        return self._valuesToNames.get(value, "UNKNOWN(%r)" % value)

    def __getattr__(self, name):
        return self._namesToValues[name]


class SerialCommSession:
    BAUD_RATE = 19200  # Default baud rate for EFA Kit. For devices with built-in USB ports, this does not matter.

    def __init__(self, comPort, useRtsCts):
        self.port = serial.Serial(comPort, self.BAUD_RATE)
        self.useRtsCts = useRtsCts

        if self.useRtsCts:
            # Lower the RTS line
            # Otherwise we monopoloze the serial network and handcontroller
            # doesn't work
            self.port.setRTS(False)

    def setTimeout(self, timeout_sec):
        if "setTimeout" in dir(self.port):
            # Earlier versions of pyserial used setTimeout()
            self.port.setTimeout(timeout_sec)
        else:
            # More recent versions use "timeout" property
            self.port.timeout = timeout_sec

    def close(self):
        self.port.close()

    def takeBus(self):
        if self.useRtsCts:
            while self.port.getCTS() == True:
                # print "Waiting for CTS..."
                pass

            self.port.setRTS(True)

    def releaseBus(self):
        if self.useRtsCts:
            self.port.setRTS(False)

    def readByte(self):
        return self.port.read(1)

    def write(self, bytes):
        self.port.write(bytes)


class TcpCommSession:
    def __init__(self, host, tcpPort):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, tcpPort))

    def setTimeout(self, timeout_sec):
        self.socket.settimeout(1)

    def close(self):
        self.socket.close()

    def takeBus(self):
        pass  # This concept doesn't apply to TCP connections

    def releaseBus(self):
        pass  # This concept doesn't apply to TCP connections

    def readByte(self):
        return self.socket.recv(1)

    def write(self, bytes):
        self.socket.sendall(bytes)


class AuxSession:
    def __init__(self, myAddress=0x20):
        self.myAddress = myAddress  # Default address of the PC
        self.debug = False  # If true, print some extra logging messages
        self.abortOnTimeout = True

    def openSerial(self, comPort, useRtsCts=False):
        self.comm = SerialCommSession(comPort, useRtsCts)

        # The EFA kit allows multiple devices to communicate simultaneously
        # (e.g. a hand controller and the PC), and uses the RTS/CTS lines
        # to negotiate who is in control of the bus.
        # Devices with native USB ports (such as the Delta-T and the
        # mirror cover controller) do not use this.
        self.useRtsCts = useRtsCts

        # Set the receive timeout to 1 second.
        self.comm.setTimeout(1)

    def openTcp(self, host, tcpPort):
        self.comm = TcpCommSession(host, tcpPort)
        self.comm.setTimeout(5)
        self.useRtsCts = False

    def close(self):
        self.comm.close()

    def send(self, receiverAddress, command, *data):
        packet = AuxPacket(self.myAddress, receiverAddress, command, *data)

        if self.debug:
            print("Send: %r" % packet.toHexString())

        self.comm.takeBus()

        self.comm.write(packet.toBytes())

    def sendReceive(self, receiverAddress, command, *data):
        """
        Send a packet, and return the response packet
        """

        self.send(receiverAddress, command, *data)

        if self.useRtsCts:
            # An EFA kit echoes everything back, so expect to
            # read the packet that we just sent.
            # USB-based devices (Delta-T, mirror cover controller)
            # will simply send back the response straight away
            ackPacket = self.readNextPacket()
            if ackPacket is None:
                print("(timeout on ack)")
                return None  # Timeout

            self.comm.releaseBus()

        while True:
            response = self.readNextPacket()
            if response is None:
                print("(timeout on response packet)")
                return None  # Timeout

            if self.debug:
                print("Response: " + response.description())

            if response.receiverAddress == self.myAddress:
                return response
            elif self.debug:
                print("  (Ignored by PC)")

    def readNextByte(self):
        c = self.comm.readByte()
        if len(c) == 0:
            return None
        return ord(c)

    def readNextPacket(self):
        # scan for SOM
        while True:
            c = self.readNextByte()
            if c == None:
                if self.abortOnTimeout:
                    return None  # No packet on timeout
                else:
                    print("...")
                    continue

            if c == AuxPacket.SOM:
                break

            if self.debug:
                print("Ignore: %02X (%s)" % (c, chr(c)))

        numBytes = self.readNextByte()
        sourceAddress = self.readNextByte()
        receiverAddress = self.readNextByte()
        command = self.readNextByte()

        data = []
        for i in range(numBytes - 3):  # After SrcAdr, DstAdr, and Cmd, the rest of the numbered bytes are data
            data.append(self.readNextByte())

        checksum = self.readNextByte()

        packet = AuxPacket(sourceAddress, receiverAddress, command, *data)
        packet.receivedChecksumByte = checksum

        return packet


# Handles encoding and decoding the packets exchanged by Aux devices.
# Format (each field is 1 byte):
#   SOM LEN SRC RCV CMD PL1 PL2 PL3 ... CHK
# where:
#   SOM: Start of message byte (0x3B)
#   LEN: Length of the packet, excluding the SOM, LEN, and CHK bytes.
#        A packet with no data payload (only SRC, RCV, and CMD) would have LEN=3.
#        A packet with 3 bytes of data payload would have LEN=6.
#   SRC: The address of the sender. For the PC, this is commonly 0x20.
#   RCV: The address of the receiver.
#   CMD: The command byte
#   PL1: (optional) The first byte of the payload.
#   PL2: (optional) The second byte of the payload.
#   PL3: (optional) The third byte of the payload.
#   ...: Additional payload bytes
#        Note: The definition of the payload depends on the CMD byte being sent.
#   CHK: The checksum
class AuxPacket:
    SOM = 0x3B  # Start of Message byte

    def __init__(self, sourceAddress, receiverAddress, command, *dataBytes):
        self.sourceAddress = sourceAddress
        self.receiverAddress = receiverAddress
        self.command = command
        self.data = dataBytes

        self.receivedChecksumByte = None  # Caller can set this when a received packet includes a checksum

        # Make sure things are in range
        for byte in self.data:
            if byte < 0 or byte > 255:
                raise Exception("EfaPacket data byte out of range: cmd=%02X, data=%r" % (self.command, self.data))

    def calculatedChecksum(self):
        return self.toBytes()[-1]

    def isChecksumOk(self):
        """
        Depends on caller first setting receivedChecksumByte
        """

        print("CHK Calculated: %02X  Received: %02X" % (self.calculatedChecksum(), self.receivedChecksumByte))
        return self.receivedChecksumByte == self.calculatedChecksum()

    def toBytes(self):
        numBytes = 3 + len(self.data)

        packetFormat = "BBBBB" + ("B" * len(self.data)) + "B"

        packetFields = [AuxPacket.SOM, numBytes, self.sourceAddress, self.receiverAddress, self.command]
        packetFields.extend(self.data)

        checksum = sum(
            packetFields[1:])  # Sum of fields, excluding SOM (and CHK, which we haven't included yet of course)
        checksum = -checksum & 0xFF  # LSB of the two's complement
        packetFields += [checksum]

        return struct.pack(packetFormat, *packetFields)

    def toHexString(self):
        bytes = self.toBytes()
        hexString = " ".join(["%02X" % x for x in bytes])
        return hexString

    def dataAsByteString(self):
        """
        Return the data array as a string of bytes
        """

        return bytes(self.data)

    def parseData(self):
        """
        Assuming the data payload contains an integer encoded
        as one or more MSB-first bytes, return the value
        """

        value = 0

        for byte in self.data:
            value = value << 8 | byte

        return value

    def description(self):
        if self.receivedChecksumByte is None:
            checksumOk = "??"
        elif self.isChecksumOk():
            checksumOk = "OK"
        else:
            checksumOk = "FAILED"

        if len(self.data) <= 3:
            parsedValue = self.parseData()
        else:
            parsedValue = "N/A"

        return "Addr 0x%02X -> Addr 0x%02X: Cmd=%02X Data=%r  [value: %s; checksum: %s]\n[hex bytes: %s]" % (
            self.sourceAddress,
            self.receiverAddress,
            self.command,
            self.data,
            parsedValue,
            checksumOk,
            self.toHexString())

    def __str__(self):
        return self.description()

    def __repr__(self):
        return str(self)

    @staticmethod
    def intTo3Bytes(value):
        """
        Values sent to the EFA are commonly encoded as 3 bytes
        packed MSB first. Given an integer value, return a
        tuple of 3 bytes that encode that value
        """

        lsb = value & 0xFF
        value >>= 8
        middle = value & 0xFF
        value >>= 8
        msb = value & 0xFF
        return (msb, middle, lsb)

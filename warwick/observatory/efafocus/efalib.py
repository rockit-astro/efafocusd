# Library for communicating with an EFA Kit (or other devices that use the "AUX" protocol) from Python.
# Written by Kevin Ivarsen
# Copyright 2014-2018 PlaneWave Instruments

import time
from .auxlib import AuxPacket, AuxSession, Enum

# Device addresses recognized by the EFA
Address = Enum(
    PC=0x20,       # User's computer
    HC=0x0D,       # EFA hand controller
    FOC_TEMP=0x12, # EFA focus motor and temp sensors
    ROT_FAN=0x13,  # EFA rotator motor and fan control
    DELTA_T=0x32   # Delta-T dew heater
)

# Temperature sensors.
# NOTE: Not all telescope configurations include all temp sensors!
TempSensor = Enum(
    PRIMARY = 0,
    AMBIENT = 1,
    SECONDARY = 2,
    BACKPLATE = 3,
    M3 = 4
)

# Commands recognized by the EFA. See protocol documentation for more details.
Command = Enum(
    MTR_GET_POS = 0x01,
    MTR_GOTO_POS2 = 0x17,
    MTR_OFFSET_CNT = 0x04,
    MTR_GOTO_OVER = 0x13,
    MTR_PTRACK = 0x06,
    MTR_NTRACK = 0x07,
    MTR_SLEWLIMITMIN = 0x1A,
    MTR_SLEWLIMITMAX = 0x1B,
    MTR_SLEWLIMITGETMIN = 0x1C,
    MTR_SLEWLIMITGETMAX = 0x1D,
    MTR_PMSLEW_RATE = 0x24,
    MTR_NMSLEW_RATE = 0x25,
    TEMP_GET = 0x26,
    FANS_SET = 0x27,
    FANS_GET = 0x28,
    MTR_GET_CALIBRATION_STATE = 0x30,
    MTR_SET_CALIBRATION_STATE = 0x31,
    MTR_GET_STOP_DETECT = 0xEE,
    MTR_STOP_DETECT = 0xEF,
    MTR_GET_APPROACH_DIRECTION = 0xFC,
    MTR_APPROACH_DIRECTION = 0xFD,
    GET_VERSION = 0xFE,
)

class EfaSession:
    def __init__(self, comPort):
        self.aux = AuxSession()
        self.aux.openSerial(comPort, useRtsCts=True)

    def getVersion(self):
        response = self.aux.sendReceive(Address.FOC_TEMP,
                                    Command.GET_VERSION)
        version = "%d.%d" % (response.data[0], response.data[1])
        return version

    def gotoPos2(self, target, useRotator=False):
        if useRotator:
            address = Address.ROT_FAN
        else:
            address = Address.FOC_TEMP

        response = self.aux.sendReceive(address,
                                    Command.MTR_GOTO_POS2,
                                    *AuxPacket.intTo3Bytes(target))

        return response

    def monitorGotoPos2(self, useRotator=False, printPosStatus=True, tickConversion=0):
        """
        Monitor movement status of an axis until a gotoPos2 command is complete
        """

        numErrors = 0 # Count the number of consecutive communication errors
        while True:
            # NOTE: near the end of a gotoPos2, it is possible for the EFA
            # to stop responding to commands for about 100 milliseconds.
            # We should be willing to retry these commands

            posRaw = self.getMotorPosition(useRotator)
            isGotoOverRaw = self.isGotoOver(useRotator)

            if posRaw is None or isGotoOverRaw is None:
                numErrors += 1
                print("Warning - no response during goto (maybe normal) - attempt %d of 3" % numErrors)
                if numErrors > 3:
                    raise Exception("Communication error while checking goto status")
            else:
                numErrors = 0
                currentPosTicks = posRaw.parseData()
                isGotoOver = isGotoOverRaw.parseData()
                if printPosStatus:
                    currentPos = currentPosTicks
                    posUnits = "counts"
                    if tickConversion != 0:
                        currentPos = currentPosTicks / tickConversion
                        if useRotator:
                            posUnits = "degs"
                        else:
                            posUnits = "microns"

                    print("Arriving, %.4f %s" % (currentPos, posUnits))

                if isGotoOver == 0xFF:
                    print("Goto2 Finished!")
                    return
                elif isGotoOver == 0xFE:
                    print("Goto2 ABORTED")
                    return
            time.sleep(0.5)

    def isGotoOver(self, useRotator=False):
        if useRotator:
            address = Address.ROT_FAN
        else:
            address = Address.FOC_TEMP

        response = self.aux.sendReceive(address,
                                    Command.MTR_GOTO_OVER)

        return response

    def slewPositive(self, rate, useRotator=False):
        """
        rate = 0 (stopped) to 9 (fastest)
        useRotator: if true, move Rotator motor; else move Focus motor

        rates in motor ticks/sec, measured on an IRF90:
            9	69907
            8	46603
            7	23306
            6	12459
            5	3117
            4	1557
            3	779
            2	195
            1	96
            0	0
        """

        if useRotator:
            address = Address.ROT_FAN
        else:
            address = Address.FOC_TEMP

        response = self.aux.sendReceive(address,
                                    Command.MTR_PMSLEW_RATE,
                                    rate)

        return response

    def slewNegative(self, rate, useRotator=False):
        """
        rate = 0 (stopped) to 9 (fastest)
        useRotator: if true, move Rotator motor; else move Focus motor
        """

        if useRotator:
            address = Address.ROT_FAN
        else:
            address = Address.FOC_TEMP

        response = self.aux.sendReceive(address,
                                    Command.MTR_NMSLEW_RATE,
                                    rate)

        return response

    def trackPositive(self, rate, useRotator=False):
        if useRotator:
            address = Address.ROT_FAN
        else:
            address = Address.FOC_TEMP

        byte1, byte2, byte3 = AuxPacket.intTo3Bytes(rate)
        response = self.aux.sendReceive(address,
                                    Command.MTR_PTRACK,
                                    byte1, byte2, byte3)

        return response

    def trackNegative(self, rate, useRotator=False):
        if useRotator:
            address = Address.ROT_FAN
        else:
            address = Address.FOC_TEMP

        byte1, byte2, byte3 = AuxPacket.intTo3Bytes(rate)
        response = self.aux.sendReceive(address,
                                    Command.MTR_NTRACK,
                                    byte1, byte2, byte3)

        return response

    def track(self, rate, useRotator=False):
        if rate < 0:
            self.trackNegative(abs(rate), useRotator)
        else:
            self.trackPositive(rate, useRotator)

    def trackNegativeTicksPerSec(self, ticksPerSec, useRotator=False):
        rate = int(ticksPerSecondToTrackRate(ticksPerSec))
        self.trackNegative(rate, useRotator)

    def trackPositiveTicksPerSec(self, ticksPerSec, useRotator=False):
        rate = int(ticksPerSecondToTrackRate(ticksPerSec))
        self.trackPositive(rate, useRotator)

    def trackTicksPerSec(self, ticksPerSec, useRotator=False):
        rate = int(ticksPerSecondToTrackRate(ticksPerSec))
        self.track(rate, useRotator)


    def stop(self, useRotator=False):
        self.trackPositive(0, useRotator)

    def ticksPerSecondToTrackRate(self, ticksPerSec):
        # Given a desired number of encoder ticks per second,
        # return the native rate value to send to trackPositive()
        # or trackNegative()
        return int(ticksPerSec * 79.101)


    def getMotorPosition(self, useRotator=False):
        if useRotator:
            address = Address.ROT_FAN
        else:
            address = Address.FOC_TEMP

        response = self.aux.sendReceive(address,
                                    Command.MTR_GET_POS)
        return response

    def setEncoder(self, newEncoderValueTicks, useRotator=False):
        if useRotator:
            address = Address.ROT_FAN
        else:
            address = Address.FOC_TEMP

        byte1, byte2, byte3 = AuxPacket.intTo3Bytes(newEncoderValueTicks)

        response = self.aux.sendReceive(address,
                                    Command.MTR_OFFSET_CNT, byte1, byte2, byte3)

        return response

    def getFanState(self):
        response = self.aux.sendReceive(Address.ROT_FAN,
                                    Command.FANS_GET)

        return response

    def setFanState(self, isOn):
        if isOn:
            value = 1
        else:
            value = 0

        response = self.aux.sendReceive(Address.ROT_FAN,
                                    Command.FANS_SET,
                                    value)

        return response

    def getTemperature(self, tempAddress):
        """
        tempAddress:
          0 = Primary
          1 = Ambient
          2 = Secondary
          3 = Backplate
          4 = M3
        """

        response = self.aux.sendReceive(Address.FOC_TEMP,
                                    Command.TEMP_GET,
                                    tempAddress)

        if tuple(response.data) == (127, 127):
            return None # no temp sensor at this address
        else:
            # Temperature is returned LSB-first
            return (256*response.data[1] + response.data[0]) / 16.0


def rawTemperatureToCelsius(rawTemp, byte2=None):
    """
    Accepts as arguments either (MSB, LSB) or a single raw temperature value
    """

    # Combine bytes if two args provided
    if byte2 is not None:
        rawTemp = rawTemp + byte2*256

    if rawTemp & 0x8000: # Is high bit set? If so, value is negative
        rawTemp = rawTemp - 0x10000

    # Raw temperature is expressed in 16ths of a degree C
    # A simple division gives us C
    return rawTemp / 16.0

def celsiusToRawTemperature(celsius):
    rawTemp = int(celsius*16)
    if rawTemp < 0:
        rawTemp += 65536
    return rawTemp

def celsiusToRawTemperatureBytes(celsius):
    rawTemp = celsiusToRawTemperature(celsius)
    byte1, byte2, byte3 = AuxPacket.intTo3Bytes(rawTemp)
    return byte3, byte2 # LSB, MSB (which seems to be the format produced by EFA hardware

def trackRateToTicksPerSecond(trackRate):
    """
    Convert the value given to MTR_PTRACK / MTR_NTRACK to
    some number of ticks per second. Determined empirically on
    the prototype IRF90
    """

    return trackRate / 79.101

def ticksPerSecondToTrackRate(ticksPerSecond):
    """
    Find the value to be given to MTR_PTRACK / MTR_NTRACK to
    achieve some number of ticks per second. Determined empirically on
    the prototype IRF90
    """
    return ticksPerSecond * 79.101

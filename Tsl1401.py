from migen import *
from litex.build.generic_platform import *
from migen.fhdl.verilog import convert
from litex.soc.interconnect.csr import *
from Adcs7476 import Adcs7476


class Tsl1401(Module):
    ''' expected to run on a 20 MHz clock '''
    def __init__(self):
        self.o_CLK = Signal()
        self.o_SI = Signal()

        ###

        self.submodules.adc = Adcs7476()

        fsm = FSM()
        fsm.act("IDLE",

        )
        fsm.act("IDLE",

        )
        pixelIndex = Signal(8)
        self.sync += [
            If(self.adc.o_valid,
                pixelIndex.eq(pixelIndex + 1)
                If(pixelIndex == 0,
                    self.o_SI.eq(1)
                )
                If(pixelIndex >= 128,
                    pixelIndex.eq(0)
                )
            )
        ]


from migen import *
from litex.build.generic_platform import *
from migen.fhdl.verilog import convert
from migen.genlib.misc import timeline
from litex.soc.interconnect.csr import *

class Adcs7476(Module, AutoCSR):
    ''' expected to run on a 20 MHz clock '''

    def __init__(self):
        # Pins
        self.o_nCS = Signal(reset=1)    # A conversion process begins on the falling edge of CS.
        self.i_SDATA = Signal()         # The output words are clocked out of this pin
        self.o_SCLK = Signal()          # guaranteed performance at 20 MHz

        # Samples
        self.o_dat = Signal(12)
        self.o_valid = Signal()         # Single cycle pulse when o_dat is valid
        self.i_trig = Signal()          # Start a conversion (can be hardwired to 1 for continuous mode)

        ###

        self.peekReg = CSR(size=12)
        shiftReg = Signal(12)
        self.comb += [
            self.o_SCLK.eq(ClockSignal()),
            self.peekReg.w.eq(self.o_dat)
        ]
        self.sync += [
            self.o_valid.eq(0),
            shiftReg.eq(Cat(self.i_SDATA, shiftReg[:-1])),
            timeline(self.i_trig, [
                ( 0, [self.o_nCS.eq(0)]),
                (15, [self.o_nCS.eq(1)]),
                (16, [
                    self.o_dat.eq(shiftReg),
                    self.o_valid.eq(1)
                ]),
            ])
        ]


    def connectToPmod(self, platform):
        ext = [("Adcs7476", 0,
            Subsignal("SS",   Pins("PMOD:0"), IOStandard("LVCMOS33")),
            Subsignal("MISO", Pins("PMOD:2"), IOStandard("LVCMOS33")),
            Subsignal("SCK",  Pins("PMOD:3"), IOStandard("LVCMOS33"))
        )]
        platform.add_extension(ext)
        r = platform.request("Adcs7476")
        self.comb += [
            r.SS.eq(self.o_nCS),
            r.SCK.eq(self.o_SCLK),
            self.i_SDATA.eq(r.MISO)
        ]
        return ext


def dut_tb(dut):
    # 5 idle clock cycles
    for i in range(5):
        yield
    # Trigger ADC
    yield dut.i_trig.eq(1)
    for i in range(1000):
        # Clock in 0x800 as the 12 bit data word
        if i == 4:
            yield dut.i_SDATA.eq(1)
        else:
            yield dut.i_SDATA.eq(0)
        yield


def main():
    fName = __file__[:-3]
    convert(Adcs7476()).write(fName + ".v")
    dut = Adcs7476()
    run_simulation(dut, dut_tb(dut), vcd_name=fName+".vcd", clocks={"sys": 50})

if __name__ == '__main__':
    main()

from migen import *
from migen.fhdl.verilog import convert
from litex.soc.interconnect.wishbone import SRAM, Interface
from litex.soc.interconnect.csr import *
from Adcs7476 import Adcs7476


class Tsl1401(Module, AutoCSR):
    ''' expected to run on a 20 MHz clock '''
    def __init__(self):
        self.i_tau = CSRStorage(32, reset=128)  # Integration cycles
        self.i_trig = Signal()
        self.o_CLK = Signal()
        self.o_SI = Signal()
        self.b_wishbone = Interface()

        ###

        tauCnt = Signal(32)
        trig0 = Signal()
        trig1 = Signal()
        self.submodules.adc = Adcs7476()
        mem = Memory(12, 128)
        p = mem.get_port(write_capable=True)
        # self.submodules.sram = SRAM(mem, read_only=True, bus=self.b_wishbone)

        pixelIndex = Signal(8)
        self.comb += [
            p.adr.eq(pixelIndex-1),
            p.dat_w.eq(self.adc.o_dat),
            p.we.eq(self.adc.o_valid),
            self.o_CLK.eq(self.adc.o_valid | trig1),
            trig0.eq(self.i_trig & (pixelIndex == 0)),
            self.o_SI.eq(trig0 | trig1),
            self.adc.i_trig.eq((pixelIndex > 0) & (pixelIndex < 128))
        ]
        self.sync += [
            trig1.eq(trig0),
            Case(pixelIndex, {
                0:
                    If(trig0,
                        tauCnt.eq(0),
                        pixelIndex.eq(1)
                    ),
                "default":
                    If(self.adc.o_valid,
                        pixelIndex.eq(pixelIndex + 1)
                    ),
                128:
                    If(tauCnt < self.i_tau.storage,
                        tauCnt.eq(tauCnt + 1),
                    ).Else(
                        pixelIndex.eq(0)
                    )
            })
        ]



def dut_tb(dut):
    # 5 idle clock cycles
    for i in range(5):
        yield
    # Trigger ADC
    yield dut.i_trig.eq(1)
    yield
    for i in range(2500):
        if i == 4:
            # yield dut.i_trig.eq(0)
            yield dut.adc.i_SDATA.eq(1)
        else:
            yield dut.adc.i_SDATA.eq(0)
        yield


def main():
    fName = __file__[:-3]
    dut = Tsl1401()
    convert(dut, ios={dut.i_trig, dut.o_CLK, dut.o_SI}).write(fName + ".v")
    dut = Tsl1401()
    run_simulation(dut, dut_tb(dut), vcd_name=fName+".vcd", clocks={"sys": 50} )

if __name__ == '__main__':
    main()

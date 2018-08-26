# Send a continuous data stream
# Source is a memory of certain size
# Receiver must know the size of the memory
# A sync byte is sent first to mark start of transmission

from migen import *
from math import ceil
from litex.soc.interconnect.csr import *
from migen.fhdl.verilog import convert
from litex.soc.cores import uart
from migen.genlib.misc import chooser


class MemoryDumper(Module):
    def __init__(self, phy, mem, syncWord=0x42):
        self.o_done = Signal()
        self.o_tx = Signal()
        self.i_trig = Signal()

        ###

        self.specials.p = p = mem.get_port(write_capable=False)
        dataByte = Signal(8)
        wordIndMax = mem.depth - 1
        byteIndMax = ceil(mem.width / 8) - 1
        print("MemoryDumper: byteIndMax={} wordIndMax={}".format(byteIndMax, wordIndMax))
        byteInd = Signal(max=byteIndMax+1)
        byteInd_ce = Signal()       # Pulse to increment byte / addr pointer
        is_last_byte = Signal()     # Latches high when last byte was sent

        self.sync += [
            # Logic for incrementing data pointers: byteInd / p.adr
            If(byteInd_ce,
                If(byteInd >= byteIndMax,
                    byteInd.eq(0),
                    If(p.adr >= wordIndMax,
                        is_last_byte.eq(1),
                        p.adr.eq(0)
                    ).Else(
                        p.adr.eq(p.adr + 1),
                    )
                ).Else(
                    byteInd.eq(byteInd + 1)
                )
            ),
            self.o_done.eq(0),
            byteInd_ce.eq(0)
        ]

        self.submodules.fsm = fsm = FSM()
        fsm.act("IDLE",
            If(self.i_trig,
                NextState("SYNC")
            )
        )
        fsm.act("SYNC",
            phy.sink.valid.eq(1),
            phy.sink.data.eq(syncWord),
            NextState("WAIT")
        )
        fsm.act("SEND",
            phy.sink.valid.eq(1),
            phy.sink.data.eq(dataByte),
            NextValue(byteInd_ce, 1),
            NextState("WAIT")
        )
        fsm.act("WAIT",
            If(phy.sink.ready,
                If(is_last_byte,
                    NextState("IDLE"),
                    NextValue(self.o_done, 1),
                    NextValue(is_last_byte, 0)
                ).Else(
                    NextState("SEND")
                )
            )
        )
        self.comb += [
            chooser(        # Selects one byte of the dat_r word
                p.dat_r,
                byteInd,
                dataByte,
                n=ceil(mem.width / 8),
                reverse=True
            )
        ]


class UartMemoryDumper(MemoryDumper, AutoCSR):
    def __init__(self, pads, mem, clk_freq=100e6, baudrate=115200):
        twVal = int((baudrate / clk_freq) * 2**32)
        self.tuneWord = CSRStorage(size=32, reset=twVal)
        self.submodules.uart = uart.RS232PHYTX(pads, self.tuneWord.storage)
        MemoryDumper.__init__(self, self.uart, mem)


def dut_tb(dut):
    yield dut.tuneWord.storage.eq(0x80000000)
    # 5 idle clock cycles
    for i in range(5):
        yield
    # Trigger
    yield dut.i_trig.eq(1)
    yield
    yield dut.i_trig.eq(0)
    for i in range(500):
        yield

def getDut():
    mem = Memory(16, 4, init=[0x1122, 0x3344, 0x5566, 0x7788])
    # mem = Memory(32, 2, init=[0x11223344, 0x55667788])
    dut = UartMemoryDumper(uart.UARTPads(), mem)
    dut.specials += mem
    return dut

def main():
    fName = __file__[:-3]
    dut = getDut()
    convert(dut, ios={dut.i_trig, dut.o_done}).write(fName + ".v")
    dut = getDut()
    run_simulation(dut, dut_tb(dut), vcd_name=fName+".vcd", clocks={"sys": 50} )

if __name__ == '__main__':
    main()

import argparse
from migen import *
from litex.boards.platforms import cmod_a7
from litex.build.generic_platform import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.cores import dna, xadc, gpio, uart
from litex.soc.interconnect.wishbone import SRAM
from migen.genlib.resetsync import AsyncResetSynchronizer
from litex.soc.cores.uart import UARTWishboneBridge
from UartMemoryDumper import *
from Adcs7476 import Adcs7476
from Tsl1401 import Tsl1401


class BaseSoC(SoCCore):
    # Peripherals CSR declaration
    csr_peripherals = [
        # "adc"
        "ccd",
        "ccd_mem",
        "mem_dump_mem",
        "mem_dump"
    ]
    sInd = max(SoCCore.csr_map.values()) + 1
    for v, name in enumerate(csr_peripherals, start=sInd):
        SoCCore.csr_map[name] = v
    print(SoCCore.csr_map)

    def __init__(self, **kwargs):
        print("BaseSoC:", kwargs)
        platform = cmod_a7.Platform()
        platform.add_source("./xilinx7_clocks.v")

        self.clock_domains.cd_sys = ClockDomain()   #  20 MHz
        sys_clk_freq = 10 * 1000000
        self.clock_domains.cd_fast = ClockDomain()  # 100 MHz
        pll_locked = Signal()
        self.specials += [
            Instance("xilinx7_clocks",
                p_DIFF_CLKIN="FALSE",
                p_CLKIN_PERIOD=int(platform.default_clk_period),
                p_MULT=50,
                i_reset=platform.request("user_btn",0),
                i_sysclk_p=platform.request("clk12"),
                p_DIV0=60,
                o_clk_out0=self.cd_sys.clk,
                p_DIV1=6,
                o_clk_out1=self.cd_fast.clk,
                o_locked=pll_locked
            ),
            AsyncResetSynchronizer(self.cd_sys, ~pll_locked),
            AsyncResetSynchronizer(self.cd_fast,~pll_locked)
        ]

        # SoC init (No CPU, we controlling stuff from python)
        SoCCore.__init__(
            self, platform, sys_clk_freq,
            cpu_type=None,
            csr_data_width=32,
            with_uart=False,
            with_timer=False,
            integrated_sram_size=0,
            ident="My first System On Chip", ident_version=True,
            **kwargs
        )

        #----------------------------
        # Serial to Wishbone bridge
        #----------------------------
        self.add_cpu_or_bridge(UARTWishboneBridge(
            platform.request("serial"),
            sys_clk_freq,
            baudrate=115200
        ))
        self.add_wb_master(self.cpu_or_bridge.wishbone)

        #----------------------------
        # Shared memory for CCD data
        #----------------------------
        mem = Memory(16, 128)
        self.specials += mem
        self.submodules.ccd_ram = SRAM(mem, read_only=True)
        self.register_mem("ccd", 0x50000000, self.ccd_ram.bus, 128)

        #----------------------------
        # CCD module (includes ADC)
        #----------------------------
        self.submodules.ccd = Tsl1401(mem)
        self.ccd.connectToCmod(platform)

        #----------------------------
        # Serial memory dumper
        #----------------------------
        platform.add_extension([("serial", 1,
            Subsignal("tx", Pins("GPIO:PIO3"), IOStandard("LVCMOS33"))
        )])
        self.submodules.mem_dump = UartMemoryDumper(
            platform.request("serial", 1), mem, sys_clk_freq, baudrate=115200
        )

        self.comb += [
            self.ccd.i_trig.eq(~self.platform.request("user_btn", 1)),
            platform.request("user_led", 1).eq(self.ccd.adc.i_trig),
            self.mem_dump.i_trig.eq(1)
        ]


def main():
    parser = argparse.ArgumentParser(description="CmodA7 basic system")
    builder_args(parser)
    soc_core_args(parser)
    args = parser.parse_args()
    print(args)
    soc = BaseSoC(**soc_core_argdict(args))
    builder = Builder(soc, **builder_argdict(args))
    builder.build()


if __name__ == "__main__":
    main()


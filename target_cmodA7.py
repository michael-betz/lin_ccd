import argparse
from migen import *
from litex.boards.platforms import cmod_a7
from litex.build.generic_platform import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.cores import dna, xadc, gpio
from migen.genlib.resetsync import AsyncResetSynchronizer
from litex.soc.cores.uart import UARTWishboneBridge
from Adcs7476 import Adcs7476
from Tsl1401 import Tsl1401


class BaseSoC(SoCCore):
    # Peripherals CSR declaration
    csr_peripherals = [
        # "adc"
        "ccd"
    ]
    sInd = max(SoCCore.csr_map.values()) + 1
    for v, name in enumerate(csr_peripherals, start=sInd):
        SoCCore.csr_map[name] = v

    def __init__(self, **kwargs):
        print("BaseSoC:", kwargs)
        platform = cmod_a7.Platform()
        platform.add_source("./xilinx7_clocks.v")

        self.clock_domains.cd_sys = ClockDomain()   #  20 MHz
        sys_clk_freq = 20 * 1000000
        self.clock_domains.cd_fast = ClockDomain()  # 100 MHz
        pll_locked = Signal()
        self.specials += [
            Instance("xilinx7_clocks",
                p_DIFF_CLKIN="FALSE",
                p_CLKIN_PERIOD=int(platform.default_clk_period),
                p_MULT=50,
                i_reset=platform.request("user_btn",0),
                i_sysclk_p=platform.request("clk12"),
                p_DIV0=30,
                o_clk_out0=self.cd_sys.clk,
                p_DIV1=6,
                o_clk_out1=self.cd_fast.clk,
                o_locked=pll_locked
            ),
            AsyncResetSynchronizer(self.cd_sys, ~pll_locked),
            AsyncResetSynchronizer(self.cd_fast,~pll_locked)
        ]

        # SoC init (No CPU, we controlling the SoC with UART)
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

        # No CPU, use Serial to control Wishbone bus
        self.add_cpu_or_bridge(
            UARTWishboneBridge(
                platform.request("serial"),
                sys_clk_freq,
                baudrate=1000000
            )
        )
        self.add_wb_master(self.cpu_or_bridge.wishbone)

        # # ADC chip
        # self.submodules.adc = Adcs7476()
        # self.adc.connectToPmod(platform)
        # self.comb += self.adc.i_trig.eq(1)

        # CCD module (includes ADC)
        self.submodules.ccd = Tsl1401()
        self.ccd.connectToCmod(platform)
        self.comb += [
            self.ccd.i_trig.eq(~self.platform.request("user_btn",1)),
            platform.request("user_led", 1).eq(self.ccd.adc.i_trig)
        ]
        self.register_mem("ccd", 0x50000000, self.ccd.b_wishbone, 128)


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


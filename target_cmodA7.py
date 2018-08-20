import argparse
from migen import *
from litex.boards.platforms import cmod_a7
from litex.build.generic_platform import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.cores import dna, xadc, gpio
from litex.soc.cores.uart import UARTWishboneBridge
from Adcs7476 import Adcs7476


class BaseSoC(SoCCore):
    # Peripherals CSR declaration
    csr_peripherals = [
        "dna",
        "xadc",
        "rgbled",
        "leds",
        "buttons",
        "adc"
    ]
    sInd = max(SoCCore.csr_map.values()) + 1
    for v, name in enumerate(csr_peripherals, start=sInd):
        SoCCore.csr_map[name] = v

    def __init__(self, **kwargs):
        print("BaseSoC:", kwargs)
        platform = cmod_a7.Platform()
        sys_clk_freq = int(1e9/platform.default_clk_period)
        print("sys_clk_freq:", sys_clk_freq)
        # SoC init (No CPU, we controlling the SoC with UART)
        SoCCore.__init__(
            self, platform, sys_clk_freq,
            cpu_type=None,
            csr_data_width=32,
            with_uart=False,
            with_timer=False,
            ident="My first System On Chip", ident_version=True,
            **kwargs
        )

        # Clock Reset Generation
        self.submodules.crg = CRG(platform.request("clk12"))

        # No CPU, use Serial to control Wishbone bus
        self.add_cpu_or_bridge(
            UARTWishboneBridge(
                platform.request("serial"),
                sys_clk_freq,
                baudrate=115200
            )
        )
        self.add_wb_master(self.cpu_or_bridge.wishbone)

        # FPGA identification
        self.submodules.dna = dna.DNA()

        # FPGA Temperature/Voltage
        self.submodules.xadc = xadc.XADC()

        # Leds
        user_leds = Cat(*[platform.request("user_led", i) for i in range(2)])
        self.submodules.leds = gpio.GPIOOut(user_leds)

        # Buttons
        user_buttons = Cat(*[platform.request("user_btn", i) for i in range(2)])
        self.submodules.buttons = gpio.GPIOIn(user_buttons)

        # ADC chip
        self.submodules.adc = Adcs7476()
        self.adc.connectToPmod(platform)


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

"""
    Play tones according to the brightness of a linear CCD sensor.
    Sensor data come in through UART
"""

import argparse
from numpy import *
import scipy.signal
from matplotlib.pyplot import *
import pyaudio

from time import sleep
import threading
from serial import Serial
import atexit

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tty_dump", default="/dev/ttyUSB0",
        help="UartMemoryDumper for data")
    parser.add_argument("--br_dump", default=115200, type=int,
        help="UartMemoryDumper baudrate")
    args = parser.parse_args()

    ccdData = zeros(128, dtype=float)
    #----------------------------------
    # Setup pyaudio, write audio stream
    #----------------------------------
    F_SAMPLE = 44100
    p = pyaudio.PyAudio()
    # 16 bit per channel, and 1 channel audio
    stream = p.open(
        format=p.get_format_from_width(2, False),    # Always signed
        channels=1,
        rate=F_SAMPLE,
        output=True
    )

    def audioPlayer():
        freqs = logspace(-2, 4.5, 128) * 2 * pi / F_SAMPLE
        phs = 2 * pi * (random.rand(freqs.size) * 2 - 1)
        amps = ones_like(freqs)
        chunk = arange(128)  # How many samples to generate per iteration
        offs = 1
        freqsv, chunkv = meshgrid(freqs, chunk)
        while True:
            # phs = 2 * pi * ccdData
            amps[:] = ccdData
            dats = amps * sin(freqsv * (offs + chunkv) + phs)
            samples = mean(dats, 1)
            stream.write((samples * 2**15).astype(int16).tostring())
            offs += chunk.size
    threading.Thread(target=audioPlayer).start()

    #----------------------------------------------
    # Setup serial reader thread
    #----------------------------------------------
    # Line plot
    fig, ax = subplots(1, 1, figsize=(6, 3))
    l, = ax.plot(arange(128), zeros(128), "-o")
    ax.axis((0, 128, 0, 1))
    fig.tight_layout()
    ser = Serial(args.tty_dump, args.br_dump)

    def read_from_port():
        while ser.isOpen():
            ser.read_until(b"\x42")
            buf = ser.read(256)
            ccdData[:] = (fromstring(buf, dtype=">u2").astype(float) / 4096)**2
            # Update plot
            l.set_ydata(ccdData)
            fig.canvas.draw_idle()
    atexit.register(ser.close)
    threading.Thread(target=read_from_port).start()
    show()


if __name__ == '__main__':
    main()

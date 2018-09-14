"""
    Play tones according to the brightness of a linear CCD sensor.
    Sensor data come in through UART
"""

import argparse
from numpy import *
from matplotlib.pyplot import *
import pyaudio
import threading
from serial import Serial
import atexit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tty_dump", default="/dev/ttyUSB0", help="UartMemoryDumper data")
    parser.add_argument("--br_dump", default=115200, type=int, help="UartMemoryDumper baudrate")
    parser.add_argument("--freq_file", help="File with a list of frequencies to map to the CCD pixels. Falls back on a pentatonic scale")
    parser.add_argument("--base_freq", default=25, type=float, help="Pentatonic scale: fundamental frequency in Hz")
    parser.add_argument("--n_octaves", default=7, type=int, help="Pentatonic scale: number of octaves")
    parser.add_argument("--ch_width", default=2, type=int, help="Bytes per sample")
    args = parser.parse_args()

    #----------------------------------
    # Setup pyaudio, write audio stream
    #----------------------------------
    F_SAMPLE = 44100
    CH_WIDTH = args.ch_width
    p = pyaudio.PyAudio()
    # 16 bit per channel, and 1 channel audio
    stream = p.open(
        format=p.get_format_from_width(CH_WIDTH, False),    # Always signed
        channels=1,
        rate=F_SAMPLE,
        output=True
    )

    #----------------------------------
    # Load freq_file
    #----------------------------------
    if args.freq_file:
        # Load frequency list from a file
        freq = genfromtxt(args.freq_file, skip_header=1, usecols=(1), comments=None)
        print(args.freq_file, freq)
    else:
        # Construct a pentatonic scale
        # https://www.lightnote.co/music-theory/pentatonic/
        ratios = array([1, 9/8, 5/4, 3/2, 5/3])
        scale = []
        for i in range(args.n_octaves):
            scale.extend(args.base_freq * ratios * 2**i)
        freq = array(scale)
    omega = freq * 2 * pi / F_SAMPLE    # Tone normalized frequency
    amps = zeros_like(freq)             # Tone amplitude
    phs = zeros_like(freq)              # Tone initial phase
    # phs = 2 * pi * (random.rand(freq.size) * 2 - 1)
    W = 2**((CH_WIDTH * 8) - 1)

    def audioPlayer():
        chunk = arange(64)  # How many samples to generate per iteration
        iSample = 1         # Sample index
        omega_v, chunk_v = meshgrid(omega, chunk)
        minValue = maxValue = 0
        while True:
            dats = amps * sin(omega_v * (iSample + chunk_v) + phs)
            samples = mean(dats, 1)
            maxValue = amax(hstack((maxValue, samples)))
            minValue = amin(hstack((minValue, samples)))
            print(minValue, maxValue)
            samples_bytes = (samples * (W - 1)).astype('<i{}'.format(CH_WIDTH))
            stream.write(samples_bytes.tobytes())
            iSample += chunk.size
    threading.Thread(target=audioPlayer).start()

    #----------------------------------------------
    # Setup plot and serial reader thread
    #----------------------------------------------
    # Line plot
    fig, ax = subplots(1, 1, figsize=(6, 3))
    l, = ax.plot(freq / 1e3, amps, "-o")
    ax.axis((amin(freq / 1e3), amax(freq / 1e3), 0, 1))
    ax.set_xlabel("Frequency [kHz]")
    # ax.set_xscale("log")
    fig.tight_layout()
    ser = Serial(args.tty_dump, args.br_dump)

    def read_from_port():
        ccdPos = linspace(freq[0], freq[-1], 128)
        while ser.isOpen():
            ser.read_until(b"\x42")
            buf = ser.read(256)
            ccdData = fromstring(buf, dtype=">u2").astype(float) / 4096
            # linearly map the CCD pixel 0 ... 128 to freq[0] ... freq[-1]
            amps[:] = interp(freq, ccdPos, ccdData**2)
            # Update plot
            l.set_ydata(amps)
            fig.canvas.draw_idle()
    atexit.register(ser.close)
    threading.Thread(target=read_from_port).start()
    show()


if __name__ == '__main__':
    main()

"""
    Play back an audio file and filter it in real time.
    The frequency response is changed during playback according to the brightness
    of a linear CCD sensor
    Needs 2 Uarts. One for the WishboneUart bridge for control and a
    second one for the UartMemoryDumper.
"""

import argparse
from numpy import *
import scipy.signal
from matplotlib.pyplot import *
from PIL import Image
import soundfile as sf
import pyaudio
from FIR import FIR

from time import sleep
import threading
from serial import Serial
import atexit

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio_file",
        help=".ogg or .wav file to playback and filter. Fallback: white noise")
    parser.add_argument("--tty_dump", default="/dev/ttyUSB2",
        help="UartMemoryDumper for data")
    parser.add_argument("--br_dump", default=115200, type=int,
        help="UartMemoryDumper baudrate")
    args = parser.parse_args()

    #----------------------------------
    # Read soundfile
    #----------------------------------
    chunkSize = 256
    if args.audio_file:
        aDat, fSample = sf.read(args.audio_file, always_2d=True)
        # Make it mono
        aDat = mean(aDat, 1)
        # Make it loud
        aDat /= amax(aDat)
        aDat.resize(int(ceil(aDat.size / chunkSize)), chunkSize)
        print("Read audio file:", fSample, aDat.shape)
    else:
        # Fallback is white noise
        fSample = 22400

        def wng():
            while True:
                yield random.rand(chunkSize) * 2 - 1
        aDat = wng()

    #----------------------------------
    # Setup pyaudio, write audio stream
    #----------------------------------
    p = pyaudio.PyAudio()
    # 16 bit per channel, and 1 channel audio
    stream = p.open(
        format=p.get_format_from_width(2),
        channels=1,
        rate=fSample,
        output=True
    )
    f = FIR(zeros(128))

    def audioPlayer():
        for chunk in aDat:
            # Filter the chunk of samples
            sOut = f.filtChunk(chunk)
            # Play result
            stream.write((sOut * 2**15).astype(int16).tostring())
    threading.Thread(target=audioPlayer).start()

    #----------------------------------------------
    # Setup serial reader thread
    #----------------------------------------------
    # Line plot
    fig, ax = subplots(1, 1, figsize=(6, 3))
    l, = ax.plot(arange(128), zeros(128), "-o")
    ax.axis((0, 1, 0, 1))
    fig.tight_layout()
    ser = Serial(args.tty_dump, args.br_dump)

    def read_from_port():
        while ser.isOpen():
            ser.read_until(b"\x42")
            buf = ser.read(256)
            readData = fromstring(buf, dtype=">u2").astype(float) / 4096
            # readData = roll(readData, 64)
            readData = (readData)**2
            # Update the filter coefficients
            h_t = f.setCoeffs(readData, False)
            # Update plot
            w, h_ff = scipy.signal.freqz(h_t)
            l.set_data(w / pi, abs(h_ff))
            # l.set_ydata(h_t)
            fig.canvas.draw_idle()
    atexit.register(ser.close)
    threading.Thread(target=read_from_port).start()
    show()


if __name__ == '__main__':
    main()

"""
    Play back an audio file and filter it in real time.
    The frequency response is changed during playback according to the brightness of a line of pixels from an image.
    The line is swept down the image. This is to simulate a CCD line sensor, which will eventually control the filter.
"""

import argparse
from numpy import *
import scipy.signal
from PIL import Image
import soundfile as sf
import pyaudio

class FIR(object):
    """ helper class for simple real time FIR filters """

    def __init__(self, coeffs=ones(128)):
        self.coeffs = coeffs / sum(coeffs)
        self.X = zeros_like(coeffs)
        self.M = coeffs.size              # Number of FIR coefficients
        self.scratch = zeros(self.M - 1)  # For overlap save algo.

    def setCoeffs(self, row):
        """ row is one line of pixels from an image / CCD """
        if row.size != self.M:
            raise ValueError("Invalid size of row")
        # Normalize amplitudes for maximum effect
        row -= amin(row)
        row /= amax(row)
        # Get impulse response
        h_t = fft.irfft(row)
        # Truncate and window impulse response
        # according to http://www.dspguide.com/ch17/1.htm
        h_t = roll(h_t, h_t.size // 2)
        trunc_start = h_t.size // 2 - self.M // 2
        trunc_stop = h_t.size // 2 + self.M // 2
        h_t = h_t[trunc_start: trunc_stop]
        h_t *= hamming(h_t.size)
        self.coeffs[:] = h_t

    def filt(self, xIn):
        """ process a single sample (very slow!) """
        self.X[:] = roll(self.X, 1)
        self.X[0] = xIn
        return sum(self.X * self.coeffs)

    def filtChunk(self, xIn):
        """ process a chunk of samples """
        res = scipy.signal.convolve(
            hstack((self.scratch, xIn)), self.coeffs, mode="valid"
        )
        self.scratch[:] = xIn[-self.scratch.size:]
        return res

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image_file", help="image file which will provide the filter coefficients")
    parser.add_argument("--audio_file", help=".ogg or .wav file to playback and filter. If not given, white noise is used.")
    parser.add_argument("--scan_rate", type=float, default=10.0, help="how many seconds per scan through the image")
    parser.add_argument("--x_offs", default=0, type=int, help="horizontal image offset in pixel")
    args = parser.parse_args()

    #----------------------------------
    # Read soundfile
    #----------------------------------
    if args.audio_file:
        aDat, fSample = sf.read(args.audio_file, always_2d=True)
        # Make it mono
        aDat = mean(aDat, 1)
        # Make it loud
        aDat /= amax(aDat)
        print("Read audio file:", fSample, aDat.shape)
    else:
        # Fallback is white noise
        fSample = 44100
        aDat = random.rand(int(fSample * args.scan_rate * 2)) * 2 - 1

    #----------------------------------
    # Read image file
    #----------------------------------
    img = Image.open(args.image_file).convert("L")
    img = img.crop([args.x_offs, 0, args.x_offs + 128, img.size[1]])
    print("Read image file:", img.size)
    imgDat = asarray(img)

    #----------------------------------
    # Setup pyaudio
    #----------------------------------
    p = pyaudio.PyAudio()
    # 16 bit per channel, and 1 channel audio
    stream = p.open(format=p.get_format_from_width(2), channels=1, rate=fSample, output=True)

    #----------------------------------
    # Filter parameters
    #----------------------------------
    samplesPerScan = fSample * args.scan_rate
    samplesPerUpdate = int(samplesPerScan / imgDat.shape[0])
    print("Filter update rate: {:.1f} Hz".format(fSample / samplesPerUpdate))

    f = FIR(ones(imgDat.shape[1]))
    rowIndex = 0
    # Split aDat up in `samplesPerUpdate` sized chunks
    aDat.resize(int(ceil(aDat.size / samplesPerUpdate)), samplesPerUpdate)
    for chunk in aDat:
        # Filter the chunk of samples
        sOut = f.filtChunk(chunk)
        # Play result
        stream.write((sOut * 2**15).astype(int16).tostring())
        # Update the filter coefficients
        f.setCoeffs(imgDat[rowIndex, :].astype("float"))
        # Scan through the image line by line
        rowIndex += 1
        if rowIndex >= imgDat.shape[0]:
            print("*", end="", flush=True)
            rowIndex = 0

if __name__ == '__main__':
    main()

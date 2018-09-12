"""
    Play back an audio file and filter it in real time.
    The frequency response is changed during playback according to the brightness of a line of pixels from an image.
    The line is swept down the image. This is to simulate a CCD line sensor, which will eventually control the filter.
"""

import argparse
from numpy import *
from PIL import Image
import soundfile as sf
import pyaudio
from FIR import FIR


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

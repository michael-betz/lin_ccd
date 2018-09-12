from numpy import *
import scipy.signal


def getMiddle(arr, N):
    """ return N elements from the center of arr """
    iStart = arr.size // 2 - N // 2
    iStop = arr.size // 2 + N // 2
    if N % 2:
        iStop += 1
    return arr[iStart: iStop]


class FIR(object):
    """ helper class for simple real time FIR filters """

    def __init__(self, coeffs=zeros(128)):
        self.coeffs = coeffs
        self.X = zeros_like(self.coeffs)
        self.scratch = zeros(self.coeffs.size - 1)  # For overlap save algo.

    def setCoeffs(self, row, normalize=True):
        """ row is one line of pixels from an image / CCD """
        if normalize:
            # Normalize amplitudes for maximum effect
            h_f = row - amin(row)
            h_f /= amax(h_f)
        else:
            h_f = row
        # Get impulse response
        h_t = fft.irfft(h_f, 256)
        # Truncate and window impulse response
        # according to http://www.dspguide.com/ch17/1.htm
        h_t = roll(h_t, h_t.size // 2)
        h_t = getMiddle(h_t, self.coeffs.size)
        h_t *= hamming(h_t.size)
        self.coeffs[:] = h_t
        return h_t

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

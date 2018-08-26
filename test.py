from litex.soc.tools.remote import RemoteClient
from time import sleep
from numpy import *
from matplotlib.animation import FuncAnimation
from serial import Serial
import atexit

def startAni():
    xdata = arange(128)
    ydata = zeros(128)
    ydata[1] = 4096
    l, = plot(xdata, ydata, "-o")
    def update(frame):
        dat = ws.read(ws.mems.ccd.base, ws.mems.ccd.size)
        print(dat[0])
        l.set_ydata(dat)
        return l
    ani = FuncAnimation(gcf(), update, interval=1000)
    return ani

def startAni2():
    xdata = arange(128)
    ydata = zeros(128)
    ydata[1] = 4096
    l, = plot(xdata, ydata, "-o")

    def update(frame):
        b = s.read_until(b"\x42")
        if len(b) == 257:
            dat = fromstring(b[1:], dtype=uint16)
            l.set_ydata(dat)
        else:
            print("E", end="", flush=True)
        return l
    ani = FuncAnimation(gcf(), update, interval=10)
    return ani

ws = RemoteClient(csr_csv="./build/csr.csv")
atexit.register(ws.close)
ws.open()
print("ws.regs.")
for k in ws.regs.__dict__.keys():
    print(k)
s = Serial("/dev/ttyUSB0", 115200)
atexit.register(s.close)

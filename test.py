from litex.soc.tools.remote import RemoteClient
from time import sleep
from numpy import linspace
from matplotlib.animation import FuncAnimation
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

ws = RemoteClient(csr_csv="./build/csr.csv")
atexit.register(ws.close)
ws.open()
print("ws.regs.")
for k in ws.regs.__dict__.keys():
    print(k)


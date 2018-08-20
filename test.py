from litex.soc.tools.remote import RemoteClient
from time import sleep
from numpy import linspace
import atexit

ws = RemoteClient(csr_csv="./build/csr.csv")
atexit.register(ws.close)
ws.open()
print("ws.regs.")
for k in ws.regs.__dict__.keys():
    print(k)

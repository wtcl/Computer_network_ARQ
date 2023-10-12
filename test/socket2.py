# sender
# https://www.jianshu.com/p/c8c199e7d4e1
# https://www.cnblogs.com/guyuyun/p/11185832.html

import socket
import threading

s=socket.socket()
host=socket.gethostname()
port=12345
print(host)

s.connect(('127.0.0.1', port))
print(s.recv(1024))

def package(to_pack_data):   #制作帧
    to_pack_data='EEEEEE'+'000000'+'08'+to_pack_data+'0001'
    return to_pack_data


data=[format(i,'08b') for i in range(2**9)]
t=[]
while True:
    if len(t)<8 and len(data)!=0:
        t.append(package(data[0]))
        data=data[1:]
        s.send(t[-1].encode())
        rec=(s.recv(1024)).decode()
        print(rec)
        if str(rec) in t:
            t.remove(rec)
        print(t)
    else:
        s.close()
        break
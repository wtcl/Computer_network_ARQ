# reciever
import socket
import time
import random

s=socket.socket()
port=12345
s.bind(('127.0.0.1',port))
s.listen(5)

content=[]
c,addr=s.accept()
c.send(b'Hello')
while True:
    time.sleep(random.randint(0,10))
    content.append(c.recv(1024))
    if content[-1]:
        print(content[-1])
        c.send(content[-1])
    else:
        s.close()
        break


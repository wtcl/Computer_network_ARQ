from flask import Flask, request,render_template,session,make_response
import requests,time,crcmod,random,json,logging
from flask_cors import CORS

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

crc32_func = crcmod.mkCrcFun(0x104C11DB7, initCrc=0, xorOut=0xFFFFFFFF)
global window,filecontent,site,w,frames,naknum,getid
window, filecontent, site = [None] * 8, [[]], [0, 7]
w={"recv":[{"id": 0, "status": "empty"}, {"id": 1, "status": "empty"}, {"id": 2, "status": "empty"}, {"id": 3, "status": "empty"}, {"id": 4, "status": "empty"}, {"id": 5, "status": "empty"}, {"id": 6, "status": "empty"}, {"id": 7, "status": "empty"}]}
frames={"frame":[]}
naknum=[]
getid=[]

app=Flask(__name__)
CORS(app,resource=r'/*')   # 解决了展示页面多个ajax调用跨域问题

def initial():   # 初始化函数，重置所有状态
    w["recv"] = [{"id": 0, "status": "empty"}, {"id": 1, "status": "empty"}, {"id": 2, "status": "empty"},
                 {"id": 3, "status": "empty"}, {"id": 4, "status": "empty"}, {"id": 5, "status": "empty"},
                 {"id": 6, "status": "empty"}, {"id": 7, "status": "empty"}]
    frames["frame"] = []
    with open('recv_file.txt', 'wb') as f:
        f.write(b'')
    filecontent[0] = []
    while len(getid):
        getid.pop(0)
    site[0], site[1] = 0, 7

def get_frame_seqnum(frame):  # 获取帧对应的序列号
    num = frame[8:10]
    num = int.from_bytes(num, 'little', signed=False)
    return num

def get_frame_data(frame):    # 获取帧中的内容
    data = frame[24:-4]
    return data

def detect_frame(frame):      # 进行校验
    CRC = frame[-4:]
    data = frame[:-4]
    CRC_detect = crc32_func(data).to_bytes(4, 'little', signed=False)
    if CRC == CRC_detect:   # 正确返回TRUE
        return True
    else:                   # 错误返回False
        return False

def content_return(content):   # 返回ack函数
    try:
        print('return_ack：',(content))
        if random.randint(0, 5):  # 模拟ack lost
            requests.post('http://127.0.0.1:8080/receive',data=((content)%16).to_bytes(2,'big',signed = True))
        else:
            print("ack_lost: ",(content))
    #     返回下一个帧的编号
    except Exception as e:
        print(e)
    return

def recover_file(con):   # 向上层传送数据
    with open('recv_file.txt','wb+') as f:  # 向文件中写入数据
        f.write(con)

def refresh_window():   # 动态更新窗口信息
    for i in range(8):
        if window[i]==None:   # 如果这个位置为None，即为空
            w["recv"][i]["status"]="empty"
        else:                 # 如果这个位置不为None，即不是空
            w["recv"][i]["status"]="full"

def store_status(frameid,status):  # 储存信息
    frames["frame"].append(
        {'id': (frameid), 'time': time.strftime("%Y-%m-%d %H:%M:%S"),
         'state': status})
    #     就是加入当前操作帧的编号，时间和状态到全局变量中

def frame_in(a,b,c):   # 判断帧是否在接收窗口中
    if a<=c:  # 如果a,c都在一轮0-15中
        if a<=b<=c:  # 直接比较大小
            return 1
        else:
            return 0
    else:  # 如果c在下一轮中
        if a<=b:   # 如果a,b是在一轮0-15
            return 1
        else:      # 如果a,b是在一轮0-15
            if b<=c:   # 此处代表b和c是一轮0-15，如果b<=c，则正常
                return 1
            else:
                return 0

def frame_site(a,b):    # 计算新的帧应该在窗口的什么位置
    if a<=b:
        return b-a
    else:
        return 16-a+b

@app.route('/')
def hello():
    return 'Hello,请访问8080端口！'

@app.route('/initial',methods=['POST'])
def reset():   # 初始化功能
    if request.method=='POST':
        initial()
        return b'initial over!'

@app.route('/api',methods=['POST','GET'])
def refres():
    if request.method=='POST':
        if request.get_data()==b"window":   # 如果post的data为b"window",返回w（实时的窗口情况）
            return json.dumps(w)
        elif request.get_data()==b"frame":   # 如果post的data为b"frame",返回frames（实时的数据帧发送接收情况）
            return json.dumps(frames)
        else:
            pass


# 主要的接收函数
@app.route('/receive',methods={'POST',"GET"})
def receive():
    if request.method == 'POST':
        data=request.get_data()
        # time.sleep(random.randint(1,5))   # 模拟传送中时间
        time.sleep(2)
        if random.randint(0,5):  # 模拟数据帧的丢失
            if detect_frame(data) == True and random.randint(0, 5):  # 传输过程中未损坏，加了random模拟损坏
                if frame_in(site[0], int(get_frame_seqnum(data)), site[1]):  # 发送的序号可以加入窗口中
                    print("receive:", get_frame_seqnum(data))  # 打印接收帧序号
                    while 1:
                        if site[0] == get_frame_seqnum(data):  # 先判断得到的是不是窗口第一个的数据
                            print("naknum",naknum)
                            print("site:", site)
                            window[0] = data  # 加入窗口
                            while 1:  # 如果窗口的第一个位置有数据，就不断循环往上层传数据，否则暂停
                                if window[0] != None:
                                    filecontent[0].append(get_frame_data(window[0]))  # 先将帧数据存入filecontent
                                    recover_file(b''.join(filecontent[0]))  # 将数据上传
                                    getid.append(get_frame_seqnum(window[0]))
                                    window.pop(0)  # 窗口移动
                                    window.append(None)  # 窗口移动
                                    site[0] = (site[0] + 1) % 16  # 窗口开头位置标号移动
                                    site[1] = (site[1] + 1) % 16  # 窗口结尾位置标号移动
                                    refresh_window()  # 更新窗口信息
                                else:
                                    break
                            print("site:", site)
                            content_return(site[0])  # 返回ack
                            store_status(get_frame_seqnum(data), 'accepted')  # 保存信息
                            break
                        elif frame_site(site[0],get_frame_seqnum(data))<=7:  # 收到的不是第一个位置的帧
                            if get_frame_seqnum(data) not in naknum:
                                try:
                                    requests.post("http://127.0.0.1:8080/nakreceive",
                                                  data=(site[0]).to_bytes(2, 'big', signed=True), timeout=0.1)
                                except:
                                    naknum.append(site[0])  # 加入其中
                                    print("send nak:", (site[0]))
                                    store_status(site[0], "nak_send")
                            store_status(get_frame_seqnum(data), 'accepted')  # 保存信息
                            window[frame_site(site[0], get_frame_seqnum(data))] = data  # 加入窗口
                            refresh_window()  # 更新窗口状态信息
                            break
                        else:
                            content_return(site[0])
                else:
                    content_return(site[0])
                    store_status(get_frame_seqnum(data), 'frame-alreadyin')  # 如果加入不了，存储数据无法加入的信息
            else:
                store_status(get_frame_seqnum(data), 'checknum-error')  # 如果帧损坏，加入校验错误的信息
        else:
            store_status(get_frame_seqnum(data),"frame-lost")
            print("frame:",get_frame_seqnum(data),"is lost!")  # 数据帧发送中丢失
        print(getid)

if __name__=='__main__':
    initial()
    print("请访问 http://127.0.0.1:8080/ 进入实验平台！")
    app.run(host='127.0.0.1', port=8081, debug=True,threaded=True)
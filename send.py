from flask import Flask, request,render_template
import requests,json,time,copy,crcmod,logging
from concurrent.futures import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from urllib import parse
from flask_cors import CORS


log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

crc32_func = crcmod.mkCrcFun(0x104C11DB7, initCrc=0, xorOut=0xFFFFFFFF)

global window,w,frames,file_window,sending
window=[]
w={"send":[{"id": 0, "status": "empty"}, {"id": 1, "status": "empty"}, {"id": 2, "status": "empty"}, {"id": 3, "status": "empty"}, {"id": 4, "status": "empty"}, {"id": 5, "status": "empty"}, {"id": 6, "status": "empty"}, {"id": 7, "status": "empty"}]}
frames={"frame":[]}
file_window=[[]]
sending=[0]

executor = ThreadPoolExecutor(1)
app=Flask(__name__)
CORS(app,resource=r'/*')

def initial():
    w["send"] = [{"id": 0, "status": "empty"}, {"id": 1, "status": "empty"}, {"id": 2, "status": "empty"},
                  {"id": 3, "status": "empty"}, {"id": 4, "status": "empty"}, {"id": 5, "status": "empty"},
                  {"id": 6, "status": "empty"}, {"id": 7, "status": "empty"}]
    frames["frame"]=[]
    file_window[0] = []
    sending[0]=0
    try:
        requests.post('http://127.0.0.1:8081/initial',data=b'1',timeout=1)
    except:
        pass
    job.remove_all_jobs()

def get_data(filename):  # 获取上层数据，作为传输的数据
    with open(filename, "rb") as f:  # 以二进制形式读取文件数据
        data = f.read()
    datalist=[]
    for i in range(len(data)//1500+1):   # 按照最大帧长来打包帧
        datalist.append(makeFrame(data[:1500],i%16))
        data=data[1500:]
    return datalist  # 返回所有帧列表

def makeFrame(data, seq_num): # 用于帧的封装
    """:param data: 传入合适大小的数据,长度由函数外进行确定
       :param seq_num: 该帧对应的序列号"""
    prefix = b'\x55' * 7
    SFD = b'\xab'
    # SFD为前导符，用来进行同步，实质上可以认为是用来提醒接收方准备接受一个新的帧
    src = b'sender'
    dst = b'recver'
    if len(data)<46:
        data=data.zfill(46)
    frame_len = (28 + len(data)).to_bytes(2, 'little', signed=False)  # 后续拼接之后进行设置
    # 28 = 7(prefix) + 1(SFD) + 6(src) + 6(dst) + 2(seq_num) + 2(frame_len) + 4(CRC)
    t = prefix + SFD + seq_num.to_bytes(2, 'little', signed=False) + src + dst + frame_len + data
    CRC = crc32_func(t)
    CRC = CRC.to_bytes(4, 'little', signed=False)
    return t + CRC

def get_frame_seqnum(frame):  # 获取帧对应的序列号
    num = frame[8:10]
    num = int.from_bytes(num, 'little', signed=False)
    return num

def get_distence(a,b):    # 获取两个标号间的距离
    if a<=b:  # 如果a<=b，就正常获取
        return b-a
    else:    # 如果a>b，说明b是下一轮的标号，需要+16处理
        return 16-a+b

def refresh_window():   # 窗口更新函数
    s=[get_distence(window[0],window[i]) for i in range(len(window))]  # 先获取当前窗口被占用位置到列表中
    for i in range(8):
        if i in s:  # 如果位置为满，标为full
            w["send"][i]["status"]="full"
        else:   # 如果位置为空，标为empty
            w["send"][i]["status"]="empty"


def send_again(frame):   # 重发函数，和发送函数作用一样
    try:
        requests.post('http://127.0.0.1:8081/receive', data=frame, timeout=0.5)
    except:
        print('resend: ', get_frame_seqnum(frame))
        store_status(get_frame_seqnum(frame),'timeout')

def store_status(frameid,status):  # 更新发送接收信息函数
    frames["frame"].append({"id": (frameid), "time": time.strftime("%Y-%m-%d %H:%M:%S"),"state": status})
#     就是加入当前帧的编号，时间和状态到全局变量中

def send_main(filename):         # 主要发送函数
    job.remove_job('main')  # 清楚主程序的job
    sending[0]=1
    datas = get_data(filename) # 从上层获取帧数据，存入data列表中
    print(time.strftime("%Y-%m-%d %H:%M:%S"),"上层数据帧已打包完成。\n获取帧的数量为：",len(datas))
    example_data = copy.deepcopy(datas)  # 参照数据
    for i in range(len(datas)):  # 此处的i仅仅用于表示发送数据，不作其它用处
        time.sleep(1)  # 每个帧发送前等待1秒，防止一下全部都发出去
        print(time.strftime("%Y-%m-%d %H:%M:%S"),"ready_to_send:",get_frame_seqnum(datas[i]))  # 准备发送的数据帧
        ww = 1   # 设置ww的目的是为了解决当前帧因为各种原因没能成功发送，需要等待的问题。这个ww可以使其处于发送循环中，直到被发送跳出循环，进入下一个帧的发送
        while ww:
            try:
                if len(window) == 0 or len(example_data) == 0 or (get_distence(window[0], window[-1]) < 7 and get_distence(window[0], get_frame_seqnum(datas[i])) < 8):
                    # 三个判断条件：一个是窗口里面没有数据时，即开始；一个是参照数据为空时；一个是窗口未满，且当前的帧的编号可以加进去
                    # 上面这行会出现一个和运行时间以及全局变量变化时间的问题，于是我在外面又套了个try，为了防止当前面len(window)！=0而后面第三个判断的时候window为空.
                    print(window)
                    try:
                        requests.post('http://127.0.0.1:8081/receive', data=datas[i], timeout=0.5)
                        # 因为post请求需要返回才能往下一步运行，所以我加了timeout，让其既能发出数据，又不会卡住
                    except:
                        # 因为上一步设了timeout，所以，这步一定会继续运行
                        job.add_job(send_again, 'interval', seconds=15, id=str(get_frame_seqnum(datas[i])),args=[datas[i]])
                        # 这个语句是加入定时器，设置了再次发送的任务，每隔15秒发送一次。设置15秒是为了更好的观察整体的动态过程，时间间隔过短的话，对于具体的模拟细节无法观察到
                        print(time.strftime("%Y-%m-%d %H:%M:%S"),'send: ', get_frame_seqnum(datas[i]))  # 打印发送的帧的编号
                        ww = 0  # 终止当前循环
                        window.append(get_frame_seqnum(datas[i]))   # 将发送的帧的编号加入窗口
                        refresh_window()   # 更新窗口信息
                        example_data.pop(0)  # 对已经发送过的数据帧进行删除
                        print('add: ', window)  # 打印更新后的窗口信息
                        store_status(get_frame_seqnum(datas[i]),'sended')  # 更新log信息
                        file_window[0].append(datas[i])  # 加入存储
            except:
                time.sleep(1)
    sending[0]=0

# 这个是用于数据交互的api接口，设置了请求回答，返回实时状态数据
@app.route('/api',methods=['POST'])
def refres():
    if request.method=='POST':  # 设置接收post请求
        if request.get_data()==b"window":  # 如果post的data为b"window",返回w（实时的窗口情况）
            return json.dumps(w)
        elif request.get_data()==b"frame": # 如果post的data为b"frame",返回frames（实时的数据帧发送接收情况）
            return json.dumps(frames)
        else:
            pass

# 此路由是主路由，用于进入实验
@app.route('/',methods=['GET','POST'])
def index():
    if request.method=='GET':  # 正常访问的时候，是get请求，所以，返回开始欢迎页面
        return render_template('start.html')
    else:                      # 如果是post的话，就说明已经准备开始实验了
        name=request.get_data().decode('utf-8')
        name=parse.unquote(name)
        # 以上两步是因为发过来的数据是url编码，需要url解码
        print(name)   # 打印读取文件路径
        initial()   # 初始化状态
        job.add_job(send_main, 'interval', seconds=5, id='main',args=[name[5:]])  # 设置发送函数定时器，让其5秒后开始发送，保证了用户端可以打开展示页面
        return render_template('frame_status.html')  # 返回展示页面

# 主要用于接收ack帧
@app.route('/receive',methods={'POST',"GET"})
def receive():
    if request.method == 'POST':
        datan=request.get_data()
        datan=int.from_bytes(datan,byteorder='big',signed=True)  # 将字节型转为数字整型
        print('receive: ',datan)  # 打印出接收的帧
        s=-1
        try:
            s=window.index((datan-1+16)%16)
        except:
            pass
        twindow=window[::]
        for i in range(s+1):
            try:
                job.remove_job(str(twindow[i]))
            except:
                pass
            file_window[0].pop(0)
            window.pop(0)
        # 因为ack是指向下一个的，同时标号是0-15循环，所以，这里处理的时候减去了1然后加上了16，再模16，防止出现负值和过值
        refresh_window()  # 因为窗口状态改变，所以动态改变w（窗口状态列表）
        print('remove: ',window)  # 打印出窗口内帧的标号
        store_status(datan, 'ack_received')   # 储存接收log记录
        return 'True'
    else:  # 防止误访问
        print("Error")

# 主要用于接收nak帧
@app.route('/nakreceive', methods={'POST'})
def nakreceive():
    if request.method == 'POST':
        datan = request.get_data()
        print(window)
        print(job.get_jobs())
        try:
            job.remove_job(str(int.from_bytes(datan,byteorder='big',signed=True)))
        except:
            pass
        frame = file_window[0][window.index((int.from_bytes(datan, byteorder='big', signed=True)))]
        send_again(frame)
        job.add_job(send_again, 'interval', seconds=15,
                        id=str(str(int.from_bytes(datan, byteorder='big', signed=True))),
                        args=[file_window[0][window.index((int.from_bytes(datan, byteorder='big', signed=True)))]])

if __name__=='__main__':
    job = BackgroundScheduler(timezone='utc')
    job.start()
    print("请访问 http://127.0.0.1:8080/ 进入实验平台！")
    app.run(host='127.0.0.1',port=8080,debug=True,threaded=True)

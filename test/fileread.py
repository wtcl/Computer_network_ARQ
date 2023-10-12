import math
import os
import random
import crcmod

crc32_func = crcmod.mkCrcFun(0x104C11DB7, initCrc=0, xorOut=0xFFFFFFFF)


def get_data() -> bytes:
    """
    :return: 产生随机数字模拟上层产生的数据，也可以通过读取文本来进行测试，这样比较能直接反应收到的数据是正确的
    """
    with open("data/sendfile.txt", "rb") as f:
        data = f.read()
    return data


def makeFrame(data: bytes) -> list:  # 产生帧
    # 最小帧长为46字节，最大帧长为1500字节
    data_len = len(data)
    frame_count = math.ceil(data_len / 1500)
    prefix = b'\x55' * 7
    SFD = b'\xab'
    src = b'sender'
    dst = b'recver'
    frames = []
    for i in range(0, frame_count * 1500, 1500):
        if i + 1500 > data_len:
            frame_data = data[i:]
            if len(frame_data) < 46:
                # 长度没有达到最小帧长，进行填充
                frame_data.zfill(46)
        else:
            frame_data = data[i:i + 1500]
        # 表示最后一个帧的长度没有达到最大长度
        frame_len = (26 + len(frame_data)).to_bytes(2, 'little', signed=False)  # 后续拼接之后进行设置
        t = prefix + SFD + src + dst + frame_len + frame_data
        CRC = crc32_func(t)
        CRC = CRC.to_bytes(4, 'little', signed=False)
        frames.append(t + CRC)
    return frames


def detect_frame(frame):   # 校验帧
    CRC = frame[-4:]  # crc校验位
    frame_data = frame[:-4]   # crc前面的数据
    CRC_detect = crc32_func(frame_data).to_bytes(4, 'little', signed=False)  # crc检验
    if CRC == CRC_detect:
        with open("data/recv.txt", "ab+") as f:
            f.write(frame[22:-4])   # 写入有效数据
        return True
    else:
        return False


if __name__ == '__main__':
    data = get_data()
    frames = makeFrame(data)
    for i in range(len(frames)):
        print(frames[i])
        detect_frame(frames[i])

import crcmod

crc32_func = crcmod.mkCrcFun(0x104C11DB7, initCrc=0, xorOut=0xFFFFFFFF)


def get_data() -> bytes:
    """
    :return: 通过读取文本来进行测试，这样比较能直接反应收到的数据是正确的
    """
    with open("./data.txt", "rb") as f:
        data = f.read()
    return data


def makeFrame(data: bytes, seq_num: int) -> bytes:
    """
    :param data: 传入合适大小的数据,长度由函数外进行确定
    :param seq_num: 该帧对应的序列号
    :return: 封装好的一个帧
    """
    prefix = b'\x55' * 7
    SFD = b'\xab'
    # SFD为前导符，用来进行同步，实质上可以认为是用来提醒接收方准备接受一个新的帧
    src = b'sender'
    dst = b'recver'
    frame_len = (28 + len(data)).to_bytes(2, 'little', signed=False)  # 后续拼接之后进行设置
    # 28 = 7(prefix) + 1(SFD) + 6(src) + 6(dst) + 2(seq_num) + 2(frame_len) + 4(CRC)
    t = prefix + SFD + seq_num.to_bytes(2, 'little', signed=False) + src + dst + frame_len + data
    CRC = crc32_func(t)
    CRC = CRC.to_bytes(4, 'little', signed=False)
    return t + CRC


def get_frame_seqnum(frame: bytes) -> int:
    """
    函数放回该帧对应的序列号
    :param frame:
    :return:
    """
    num = frame[8:10]
    num = int.from_bytes(num, 'little', signed=False)
    return num


def get_frame_data(frame: bytes) -> bytes:
    """
    函数返回帧中的内容
    :param frame:
    :return:
    """
    data = frame[24:-4]
    return data


def detect_frame(frame):
    """
    函数判断帧校验和是否正确
    :param frame:
    :return: 正确返回true
    """
    CRC = frame[-4:]
    data = frame[:-4]
    CRC_detect = crc32_func(data).to_bytes(4, 'little', signed=False)
    if CRC == CRC_detect:
        return True
    else:
        return False


if __name__ == '__main__':
    data = get_data()
    print(len(data))
    data = data[:150]
    frame = makeFrame(data, 9)
    if detect_frame(frame):
        print(get_frame_seqnum(frame))
        print(get_frame_data(frame))

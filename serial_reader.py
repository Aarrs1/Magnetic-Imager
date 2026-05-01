# -*- coding: utf-8 -*-
"""
串口通信：后台线程读取传感器数据并写入 DataStore。

协议：每行数据为空格分隔的 8 个数值，如 "100 200 150 160 170 180 190 200"。
命令：通过 write() 向串口写入单字符命令（L/S/1-4），末尾自动追加换行。
自动扫描系统可用串口，优先使用第一个。
"""

import threading
import time
import serial
import serial.tools.list_ports

from config import BAUD_RATE, MAX_SIZE


class SerialReader:
    """串口读写管理器。后台守护线程持续读取，主线程通过 write() 发送命令。"""

    def __init__(self, datastore):
        self.datastore = datastore
        self.ser = None         # pyserial Serial 对象
        self.running = False    # 后台线程运行标志
        self.thread = None      # 后台读取线程（daemon）
        self.status_callback = None  # 状态消息回调 (message, status_type)
        self.playback_rows = 0  # 回放计数

    def connect(self, port=None):
        """自动扫描并连接串口。port 为 None 时用第一个可用端口。返回是否连接成功。"""
        ports = list(serial.tools.list_ports.comports())
        print("Available Serial Ports:")
        for p in ports:
            print(f"  {p.device}")
        if not ports:
            print("No serial ports available. Running without serial. / 无可用串口，以无串口模式运行")
            return False
        if port is None:
            port = ports[0].device
        print(f"Using port: {port}")
        print("This can be changed in the main() function. / 可在 main() 函数中修改")
        try:
            self.ser = serial.Serial(port, BAUD_RATE, timeout=0.1)
            self.running = True
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
            return True
        except Exception as e:
            print(f"Failed to open serial port: {e}")
            return False

    def _read_loop(self):
        """后台循环：逐行读取串口数据并解析。遇到异常休眠 0.1s 后重试。"""
        while self.running:
            try:
                if self.ser and self.ser.is_open:
                    line = self.ser.readline()
                    if line:
                        self._parse_line(line.decode("utf-8", errors="ignore"))
            except Exception as e:
                print(f"Serial read error: {e}")
                time.sleep(0.1)

    def _parse_line(self, line):
        """解析一行串口数据。状态消息通过 callback 转发。"""
        line = line.strip()
        if not line:
            return

        # 状态消息：REC_START / REC N/100 / REC_DONE / PLAY_START / PLAY_DONE
        if line.startswith("REC_") or line.startswith("PLAY_") or line.startswith("REC "):
            print(f"[SERIAL] {line}")
            if self.status_callback:
                if "START" in line:
                    self.status_callback(line, "info")
                elif "DONE" in line:
                    self.status_callback(line, "success")
                else:
                    self.status_callback(line, "info")
            if "START" in line:
                self.datastore.reset_idx()
                self.playback_rows = 0
            if "DONE" in line and "REC_" in line:
                pass  # REC_DONE, not playback
            elif "DONE" in line:
                print(f"[SERIAL] Playback received {self.playback_rows} data rows")
            return

        parts = line.split(" ")
        if len(parts) < 2:
            if line != "*":  # '*' 是帧分隔符，不重置索引
                self.datastore.reset_idx()
            return
        try:
            vals = [float(x) for x in parts]
            if len(vals) != MAX_SIZE:
                return
            self.datastore.add_row(vals)
            self.playback_rows += 1
        except ValueError:
            pass

    def write(self, cmd):
        """向串口写入单字符命令（如 "L"、"S"、"1"），末尾追加 '\n'。"""
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(f"{cmd}\n".encode())
            except Exception as e:
                print(f"Serial write error: {e}")

    def close(self):
        """停止读取线程并关闭串口连接。"""
        self.running = False
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass

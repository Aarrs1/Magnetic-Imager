# -*- coding: utf-8 -*-
"""数据存储：8×8 传感器阵列数据管理、校准"""

import threading

from config import MAX_SIZE, MAX_CALIB_FRAMES, MAX_VALUE

# DRV5053 VA conversion constants
_ADC_VREF = 3.3
_ADC_MAX = 65536.0
_SENSITIVITY = 0.090  # V/mT, negative slope


def _adc_to_mt(adc):
    """Convert raw ADC reading (0-65535) to mT for DRV5053 VA.
        B(mT) = (1.0 − VOUT) / 0.090,  where VOUT = ADC × 3.3 / 65536."""
    vout = adc * _ADC_VREF / _ADC_MAX
    return (1.0 - vout) / _SENSITIVITY


class DataStore:
    """线程安全的 8×8 传感器数据存储与校准管理。

    数据填充方式：逐行写入（add_row），每 8 行完成一帧。
    校准过程：采集 MAX_CALIB_FRAMES 帧（默认 200）后取平均作为背景，
    后续 get_snapshot() 返回 data − data_calib 修正值。
    所有数据以 mT 为单位存储。
    """

    def __init__(self):
        # 原始数据（默认填充 0 mT）
        self.data = [[0.0] * MAX_SIZE for _ in range(MAX_SIZE)]
        # 校准背景（校准帧累加器，完成后除以帧数取均值）
        self.data_calib = [[0.0] * MAX_SIZE for _ in range(MAX_SIZE)]
        self.cur_data_idx = 0           # 当前写入行索引 (0..7)
        self.num_calib_frames = 0        # 已采集的校准帧数
        self.calibration_enabled = False # 校准是否进行中
        self.is_calibrated = False       # 校准是否已完成
        self.lock = threading.RLock()     # 线程锁（串口线程 + 主线程）

    def add_row(self, values):
        """串口线程调用：写入一行 8 个 ADC 值，自动转换为 mT。"""
        with self.lock:
            for j in range(MAX_SIZE):
                mt = _adc_to_mt(values[j])
                self.data[self.cur_data_idx][j] = mt
                if self.calibration_enabled:
                    self.data_calib[self.cur_data_idx][j] += mt

            self.cur_data_idx += 1
            if self.cur_data_idx >= MAX_SIZE:
                self.cur_data_idx = 0
                if self.calibration_enabled:
                    self.num_calib_frames += 1
                    if self.num_calib_frames >= MAX_CALIB_FRAMES:
                        self.calibration_enabled = False
                        self._calibrate()

    def _calibrate(self):
        with self.lock:
            print("Calibration Data (mT):")
            for i in range(MAX_SIZE):
                for j in range(MAX_SIZE):
                    self.data_calib[i][j] = (
                        self.data_calib[i][j] / MAX_CALIB_FRAMES
                    )
                    print(f"{self.data_calib[i][j]:7.3f}  ", end="")
                print()
            self.is_calibrated = True

    def reset_idx(self):
        with self.lock:
            self.cur_data_idx = 0

    def start_calibration(self):
        with self.lock:
            for i in range(MAX_SIZE):
                for j in range(MAX_SIZE):
                    self.data_calib[i][j] = 0
            self.num_calib_frames = 0
            self.calibration_enabled = True
            self.is_calibrated = False

    def cancel_calibration(self):
        with self.lock:
            self.calibration_enabled = False

    def reset_calibration(self):
        with self.lock:
            self.data_calib = [[0.0] * MAX_SIZE for _ in range(MAX_SIZE)]
            self.num_calib_frames = 0
            self.calibration_enabled = False
            self.is_calibrated = False

    def clear_data(self):
        with self.lock:
            for i in range(MAX_SIZE):
                for j in range(MAX_SIZE):
                    self.data[i][j] = 0.0
            self.cur_data_idx = 0

    def fill_gradient(self):
        """填充对角渐变（无串口时默认显示）：+max → −max mT"""
        with self.lock:
            max_ij = (MAX_SIZE - 1) * 2
            for i in range(MAX_SIZE):
                for j in range(MAX_SIZE):
                    t = (i + j) / max_ij
                    self.data[i][j] = MAX_VALUE * (1 - 2 * t)
            self.cur_data_idx = 0

    def get_snapshot(self):
        """线程安全快照：返回 (data深拷贝, data_calib深拷贝, is_calibrated)。"""
        with self.lock:
            data = [row[:] for row in self.data]
            data_calib = [row[:] for row in self.data_calib]
            is_calibrated = self.is_calibrated
        return data, data_calib, is_calibrated

    def get_calib_progress(self):
        """返回校准进度 0.0–1.0。非校准状态下返回 0.0。"""
        with self.lock:
            if not self.calibration_enabled:
                return 0.0
            return min(1.0, self.num_calib_frames / MAX_CALIB_FRAMES)

    def print_calib_data(self):
        with self.lock:
            print("Calibration Data (mT):")
            for i in range(MAX_SIZE):
                for j in range(MAX_SIZE):
                    print(f"{self.data_calib[i][j]:7.3f}  ", end="")
                print()

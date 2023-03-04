# import re
import sys
import traceback
from datetime import date
from time import perf_counter_ns

# import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyqtgraph as pg
# import pyvisa
import serial
# from matplotlib.figure import Figure
# from pylablib.devices import Thorlabs
from PyQt5 import QtCore
from PyQt5.QtCore import (QObject, QRunnable, QSize, Qt, QThread, QThreadPool,
                          QTimer, pyqtSignal, pyqtSlot)
# from PyQt5.QtGui import QFont
# from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
# from PyQt5.QtCore import QSize
# from PyQt5 import QtGui
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
                             QDoubleSpinBox, QFileDialog, QGridLayout,
                             QHBoxLayout, QLabel, QLineEdit, QMainWindow,
                             QMessageBox, QPushButton, QSlider, QSpinBox,
                             QVBoxLayout, QWidget)
# from scipy.optimize import curve_fit
from serial.tools import list_ports

# https://matplotlib.org/3.5.0/gallery/user_interfaces/embedding_in_qt_sgskip.html
# from matplotlib.backends.qt_compat import QtWidgets
# from matplotlib.backends.backend_qtagg import FigureCanvas
# from matplotlib.backends.backend_qtagg import \
    # NavigationToolbar2QT as NavigationToolbar


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ports = [p.name for p in list_ports.comports()]
        self.UI()
        # self.qtimer()
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(self.threadpool.maxThreadCount())

        self.const_c1 = np.array(1.196051641e-3)
        self.const_c2 = np.array(2.228227940e-4) 
        self.const_c3 = np.array(1.352729757e-7)
        # self.const_a = np.array(3.354016e-3)
        # self.const_b = np.array(2.567090e-4) 
        # self.const_c = np.array(2.39213e-6)
        # self.const_d = np.array(-7.68347e-8)

        self.indicator_c1.setValue(self.const_c1 * 1e3)
        self.indicator_c2.setValue(self.const_c2 * 1e4)
        self.indicator_c3.setValue(self.const_c3 * 1e7)

    def UI(self):
        self.setWindowTitle("Keithley")
        self.setStyleSheet("background-color: white;")
        # self.setFixedSize(QSize(1100, 1100))

        # Create Widgets
        self.btn_start = QPushButton("Start")
        self.btn_stop = QPushButton("Stop")
        self.btn_load_data = QPushButton("Load Data")
        self.btn_save_data = QPushButton("Save Data")
        self.btn_clear_plot = QPushButton("Clear Plot")

        self.label_checkbox_continuous_acquisition = QLabel('Continuous Acquisition')
        self.checkbox_continuous_acquisition = QCheckBox()

        self.label_mode = QLabel("Mode")
        self.cb_mode = QComboBox()
        self.cb_mode.addItems(["R 2-Wire", "R 4-Wire"])
        self.cb_mode.setCurrentIndex(-1)
        self.label_mode.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_pd_address = QLabel("COM Port")
        self.cb_comport = QComboBox()
        self.cb_comport.addItems(self.ports)
        self.cb_comport.setCurrentIndex(-1)
        self.label_pd_address.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_acquisition_time = QLabel("Acquisition Time")
        self.label_acquisition_time.setAlignment(QtCore.Qt.AlignHCenter)
        self.acquisition_time = QDoubleSpinBox()
        self.acquisition_time.setMinimum(0)
        self.acquisition_time.setMaximum(np.inf)
        self.acquisition_time.setValue(10)
        self.acquisition_time.setSingleStep(1)
        self.acquisition_time.setDecimals(0)
        self.acquisition_time.setSuffix(" s")

        self.label_box_min = QLabel("ROI Lower Bound")
        self.label_box_min.setAlignment(QtCore.Qt.AlignHCenter)
        self.box_min = QDoubleSpinBox()
        self.box_min.setMinimum(0)
        self.box_min.setMaximum(np.inf)
        self.box_min.setValue(0)
        self.box_min.setSingleStep(1)
        self.box_min.setDecimals(7)
        self.box_min.setSuffix(" s")

        self.label_box_max = QLabel("ROI Upper Bound")
        self.label_box_max.setAlignment(QtCore.Qt.AlignHCenter)
        self.box_max = QDoubleSpinBox()
        self.box_max.setMinimum(0)
        self.box_max.setMaximum(np.inf)
        self.box_max.setValue(0)
        self.box_max.setSingleStep(1)
        self.box_max.setDecimals(4)

        self.label_c1 = QLabel("C1")
        self.label_c1.setAlignment(QtCore.Qt.AlignHCenter)
        self.indicator_c1 = QDoubleSpinBox()
        self.indicator_c1.setMinimum(-np.inf)
        self.indicator_c1.setMaximum(np.inf)
        self.indicator_c1.setValue(0)
        self.indicator_c1.setSingleStep(1)
        self.indicator_c1.setDecimals(10)
        self.indicator_c1.setSuffix(' e-3')

        self.label_c2 = QLabel("C2")
        self.label_c2.setAlignment(QtCore.Qt.AlignHCenter)
        self.indicator_c2 = QDoubleSpinBox()
        self.indicator_c2.setMinimum(-np.inf)
        self.indicator_c2.setMaximum(np.inf)
        self.indicator_c2.setValue(0)
        self.indicator_c2.setSingleStep(1)
        self.indicator_c2.setDecimals(10)
        self.indicator_c2.setSuffix(' e-4')

        self.label_c3 = QLabel("C3")
        self.label_c3.setAlignment(QtCore.Qt.AlignHCenter)
        self.indicator_c3 = QDoubleSpinBox()
        self.indicator_c3.setMinimum(-np.inf)
        self.indicator_c3.setMaximum(np.inf)
        self.indicator_c3.setValue(0)
        self.indicator_c3.setSingleStep(1)
        self.indicator_c3.setDecimals(10)
        self.indicator_c3.setSuffix(' e-7')

        self.label_rolling_average_indicator = QLabel("Rolling Average Window")
        self.rolling_average_indicator = QSpinBox()
        self.rolling_average_indicator.setRange(1, int(1e9))
        self.rolling_average_indicator.setValue(1)
        self.rolling_average_indicator.setSingleStep(5)
        self.label_rolling_average_indicator.setAlignment(QtCore.Qt.AlignHCenter)
        self.rolling_average_indicator.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_mean_indicator1 = QLabel("Mean")
        self.mean_indicator1 = QDoubleSpinBox()
        self.mean_indicator1.setReadOnly(True)
        self.mean_indicator1.setButtonSymbols(2)
        self.mean_indicator1.setSuffix(" C")
        self.mean_indicator1.setRange(int(-1e10), int(1e10))
        self.mean_indicator1.setDecimals(10)
        self.label_mean_indicator1.setAlignment(QtCore.Qt.AlignHCenter)
        self.mean_indicator1.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_error_indicator1 = QLabel("Std. Dev.")
        self.error_indicator1 = QDoubleSpinBox()
        self.error_indicator1.setReadOnly(True)
        self.error_indicator1.setButtonSymbols(2)
        self.error_indicator1.setSuffix(" C")
        self.error_indicator1.setRange(int(-1e10), int(1e10))
        self.error_indicator1.setDecimals(10)
        self.label_error_indicator1.setAlignment(QtCore.Qt.AlignHCenter)
        self.error_indicator1.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_min_indicator1 = QLabel("Min")
        self.min_indicator1 = QDoubleSpinBox()
        self.min_indicator1.setReadOnly(True)
        self.min_indicator1.setButtonSymbols(2)
        self.min_indicator1.setSuffix(" C")
        self.min_indicator1.setRange(int(-1e10), int(1e10))
        self.min_indicator1.setDecimals(10)
        self.label_min_indicator1.setAlignment(QtCore.Qt.AlignHCenter)
        self.min_indicator1.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_max_indicator1 = QLabel("Max")
        self.max_indicator1 = QDoubleSpinBox()
        self.max_indicator1.setReadOnly(True)
        self.max_indicator1.setButtonSymbols(2)
        self.max_indicator1.setSuffix(" C")
        self.max_indicator1.setRange(int(-1e10), int(1e10))
        self.max_indicator1.setDecimals(10)
        self.label_max_indicator1.setAlignment(QtCore.Qt.AlignHCenter)
        self.max_indicator1.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_rolling_mean_indicator1 = QLabel("Rolling Mean")
        self.rolling_mean_indicator1 = QDoubleSpinBox()
        self.rolling_mean_indicator1.setReadOnly(True)
        self.rolling_mean_indicator1.setButtonSymbols(2)
        self.rolling_mean_indicator1.setSuffix(" C")
        self.rolling_mean_indicator1.setRange(int(-1e10), int(1e10))
        self.rolling_mean_indicator1.setDecimals(10)
        self.label_rolling_mean_indicator1.setAlignment(QtCore.Qt.AlignHCenter)
        self.rolling_mean_indicator1.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_rolling_error_indicator1 = QLabel("Rolling Std. Dev.")
        self.rolling_error_indicator1 = QDoubleSpinBox()
        self.rolling_error_indicator1.setReadOnly(True)
        self.rolling_error_indicator1.setButtonSymbols(2)
        self.rolling_error_indicator1.setSuffix(" C")
        self.rolling_error_indicator1.setRange(int(-1e10), int(1e10))
        self.rolling_error_indicator1.setDecimals(10)
        self.label_rolling_error_indicator1.setAlignment(QtCore.Qt.AlignHCenter)
        self.rolling_error_indicator1.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_rolling_min_indicator1 = QLabel("Rolling Min")
        self.rolling_min_indicator1 = QDoubleSpinBox()
        self.rolling_min_indicator1.setReadOnly(True)
        self.rolling_min_indicator1.setButtonSymbols(2)
        self.rolling_min_indicator1.setSuffix(" C")
        self.rolling_min_indicator1.setRange(int(-1e10), int(1e10))
        self.rolling_min_indicator1.setDecimals(10)
        self.label_rolling_min_indicator1.setAlignment(QtCore.Qt.AlignHCenter)
        self.rolling_min_indicator1.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_rolling_max_indicator1 = QLabel("Rolling Max")
        self.rolling_max_indicator1 = QDoubleSpinBox()
        self.rolling_max_indicator1.setReadOnly(True)
        self.rolling_max_indicator1.setButtonSymbols(2)
        self.rolling_max_indicator1.setSuffix(" C")
        self.rolling_max_indicator1.setRange(int(-1e10), int(1e10))
        self.rolling_max_indicator1.setDecimals(10)
        self.label_rolling_max_indicator1.setAlignment(QtCore.Qt.AlignHCenter)
        self.rolling_max_indicator1.setAlignment(QtCore.Qt.AlignHCenter)

        self.plot_widget = pg.GraphicsLayoutWidget()

        self.plot_widget.setBackground("w")
        self.region_xy = pg.LinearRegionItem()
        self.region_xy.setZValue(10)

        self.plot_label = self.plot_widget.addLabel(
            text="",
            row=0,
            col=0,
        )
        self.plot_xy = self.plot_widget.addPlot(row=1, col=0)
        self.plot_xy_roi = self.plot_widget.addPlot(
            row=2, col=0, labels={"bottom": "Time [s]"}
        )

        self.plot_xy.setLabel("bottom", "Time [s]")
        self.plot_xy.setLabel("left", "Temp [C]")
        self.plot_xy_roi.setLabel("bottom", "Time [s]")
        self.plot_xy_roi.setLabel("left", "Temp [C]")
        self.plot_xy.getAxis("left").setPen("k")
        self.plot_xy.getAxis("left").setTextPen("k")
        self.plot_xy.getAxis("bottom").setPen("k")
        self.plot_xy.getAxis("bottom").setTextPen("k")
        self.plot_xy.setTitle("Temp. vs Time", color="k")
        self.plot_xy_roi.getAxis("left").setPen("k")
        self.plot_xy_roi.getAxis("left").setTextPen("k")
        self.plot_xy_roi.getAxis("bottom").setPen("k")
        self.plot_xy_roi.getAxis("bottom").setTextPen("k")

        # Create Layouts
        self.layout = QGridLayout()
        self.init_layout = QVBoxLayout()
        self.experiment_layout = QVBoxLayout()
        self.experiment_layout1 = QHBoxLayout()
        self.experiment_layout2 = QHBoxLayout()
        self.experiment_layout3 = QHBoxLayout()
        self.experiment_layout4 = QHBoxLayout()
        self.experiment_layout5 = QHBoxLayout()
        self.experiment_layout6 = QHBoxLayout()
        self.experiment_layout7 = QHBoxLayout()
        self.experiment_layout8 = QHBoxLayout()
        self.experiment_layout9 = QHBoxLayout()
        self.experiment_layout10 = QHBoxLayout()
        self.experiment_layout11 = QHBoxLayout()
        self.experiment_layout12 = QHBoxLayout()
        self.experiment_layout13 = QHBoxLayout()
        self.plot_layout = QHBoxLayout()

        # nesting layouts
        self.experiment_layout.addLayout(self.experiment_layout1)
        self.experiment_layout.addLayout(self.experiment_layout2)
        self.experiment_layout.addLayout(self.experiment_layout3)
        self.experiment_layout.addLayout(self.experiment_layout4)
        self.experiment_layout.addLayout(self.experiment_layout5)
        self.experiment_layout.addLayout(self.experiment_layout6)
        self.experiment_layout.addLayout(self.experiment_layout7)
        self.experiment_layout.addLayout(self.experiment_layout8)
        self.experiment_layout.addLayout(self.experiment_layout9)
        self.experiment_layout.addLayout(self.experiment_layout10)
        self.experiment_layout.addLayout(self.experiment_layout11)
        self.experiment_layout.addLayout(self.experiment_layout12)
        self.experiment_layout.addLayout(self.experiment_layout13)

        self.layout.addLayout(self.experiment_layout, 0, 3)
        self.layout.addLayout(self.plot_layout, 1, 0, 1, 6)
        self.layout.setColumnMinimumWidth(0, 50)
        self.layout.setColumnMinimumWidth(2, 50)
        self.layout.setColumnMinimumWidth(4, 50)
        self.layout.setColumnMinimumWidth(6, 50)
        self.layout.setRowStretch(1, 1)

        # Set QWidget as the central window that will contain all widgets and layouts
        self.widget = QWidget()
        self.widget.setLayout(self.layout)
        self.setCentralWidget(self.widget)

        # Experiment Block
        self.experiment_layout1.addWidget(self.label_pd_address)
        self.experiment_layout2.addWidget(self.cb_comport)
        self.experiment_layout1.addWidget(self.label_mode)
        self.experiment_layout2.addWidget(self.cb_mode)
        self.experiment_layout1.addWidget(self.label_c1)
        self.experiment_layout2.addWidget(self.indicator_c1)
        self.experiment_layout1.addWidget(self.label_c2)
        self.experiment_layout2.addWidget(self.indicator_c2)
        self.experiment_layout1.addWidget(self.label_c3)
        self.experiment_layout2.addWidget(self.indicator_c3)
        self.experiment_layout5.addWidget(self.label_checkbox_continuous_acquisition)
        self.experiment_layout6.addWidget(self.checkbox_continuous_acquisition)
        self.experiment_layout5.addWidget(self.label_acquisition_time)
        self.experiment_layout6.addWidget(self.acquisition_time)
        self.experiment_layout7.addWidget(self.btn_start)
        self.experiment_layout7.addWidget(self.btn_stop)
        self.experiment_layout7.addWidget(self.btn_save_data)
        self.experiment_layout7.addWidget(self.btn_load_data)
        self.experiment_layout7.addWidget(self.btn_clear_plot)
        self.experiment_layout8.addWidget(self.label_mean_indicator1)
        self.experiment_layout8.addWidget(self.label_error_indicator1)
        self.experiment_layout8.addWidget(self.label_min_indicator1)
        self.experiment_layout8.addWidget(self.label_max_indicator1)
        self.experiment_layout9.addWidget(self.mean_indicator1)
        self.experiment_layout9.addWidget(self.error_indicator1)
        self.experiment_layout9.addWidget(self.min_indicator1)
        self.experiment_layout9.addWidget(self.max_indicator1)
        self.experiment_layout10.addWidget(self.label_rolling_average_indicator)
        self.experiment_layout11.addWidget(self.rolling_average_indicator)
        self.experiment_layout10.addWidget(self.label_box_min)
        self.experiment_layout11.addWidget(self.box_min)
        self.experiment_layout10.addWidget(self.label_box_max)
        self.experiment_layout11.addWidget(self.box_max)
        self.experiment_layout12.addWidget(self.label_rolling_mean_indicator1)
        self.experiment_layout12.addWidget(self.label_rolling_error_indicator1)
        self.experiment_layout12.addWidget(self.label_rolling_min_indicator1)
        self.experiment_layout12.addWidget(self.label_rolling_max_indicator1)
        self.experiment_layout13.addWidget(self.rolling_mean_indicator1)
        self.experiment_layout13.addWidget(self.rolling_error_indicator1)
        self.experiment_layout13.addWidget(self.rolling_min_indicator1)
        self.experiment_layout13.addWidget(self.rolling_max_indicator1)
        self.experiment_layout.addStretch(0)

        # Graph Block
        self.plot_layout.addWidget(self.plot_widget)
        # self.show()

        # UI Event Triggers
        self.btn_start.clicked.connect(self.start0)
        self.btn_stop.clicked.connect(self.stop)
        self.btn_save_data.clicked.connect(self.saveFileDialog)
        self.btn_load_data.clicked.connect(self.openFileNameDialog)
        self.btn_clear_plot.clicked.connect(self.clear_plots)
        self.cb_comport.currentIndexChanged.connect(self.init_controller)
        self.region_xy.sigRegionChanged.connect(self.update_UI)
        self.box_min.valueChanged.connect(self.update_box)
        self.box_max.valueChanged.connect(self.update_box)
        self.cb_mode.currentIndexChanged.connect(self.update_mode)
        self.checkbox_continuous_acquisition.stateChanged.connect(self.continuous_acquisition_directory)
        # self.indicator_c1.valueChanged.connect(self.update_c_constants)
        # self.indicator_c2.valueChanged.connect(self.update_c_constants)
        # self.indicator_c3.valueChanged.connect(self.update_c_constants)
        self.rolling_average_indicator.valueChanged.connect(self.update_rolling_average)
    
    def update_rolling_average(self):
        try:
            self.rolling_average(self.arrays)
            self.plot(self.arrays)
            self.update_UI()
        except:
            pass

    # def update_c_constants(self):
    #     self.const_c1 = np.array(self.indicator_c1.value()) * 1e-3 
    #     self.const_c2 = np.array(self.indicator_c2.value()) * 1e-4
    #     self.const_c3 = np.array(self.indicator_c3.value()) * 1e-7

    def continuous_acquisition_directory(self):
        if self.checkbox_continuous_acquisition.isChecked() == True:
            self.directory = QFileDialog.getExistingDirectory(
                self,
                "Choose Directory to Save Data To:",
                "",
            )
            print(self.directory)

    def update_mode(self):
        if self.cb_mode.currentText() == 'R 2-Wire':
            self.inst.write(b":CONF:RES\r")
        if self.cb_mode.currentText() == 'R 4-Wire':
            self.inst.write(b":CONF:FRES\r")
        print('Mode Changed')

    def init_controller(self):
        self.inst = serial.Serial(port = self.cb_comport.currentText(), baudrate=19200, timeout=0.1)

    def stop(self):
        self.stop_button_pressed = True
        print(self.stop_button_pressed)

    def query_keithley(self):
        self.inst.write(b":READ?\r")
        read = b''
        queue = self.inst.in_waiting
        while b'\r' not in read:
            queue = self.inst.in_waiting
            if queue > 0:
                read += self.inst.read(queue)
        return read

    def calculate_temp(self, R):
        T1 = (1 / (self.const_c1 + (self.const_c2 * np.log(R*1000)) + (self.const_c3 * (np.log(R*1000)**3)))) - 273.15
        result = T1
        return result

    def manage_arrays(self, mode, *args):
        # Initialize the appropriate arrays only on the first iteration
        if args:
            #comma here because *args defaults to tuple
            df, = args
        if Worker.index == -1:
            df = pd.DataFrame(
                np.nan,
                index=np.arange(0, 100),
                columns=mode,
                dtype=np.float64,
            )
        # Double the appropriate array size if data exceeds the size
        if Worker.index >= df.shape[0]:
            df_tmp = df
            # Double array size
            df = pd.DataFrame(
                np.nan,
                index=np.arange(0, df.shape[0] * 2),
                columns=mode,
                dtype=np.float64,
            )
            # Fill doubled array with previously acquired data
            df[: df_tmp.shape[0]] = df_tmp
        return df

    def start0(self):
        """Initialize Scatter program"""
        self.stop_button_pressed = False
        try:
            self.button_pressed = self.sender().text()
        except:
            pass
        Worker.index = -1
        self.mode = ['Time (s)', 'Temp Converted 3-constants (C)', 'Epoch Time']
        self.arrays = self.manage_arrays(self.mode)
        self.col0 = self.arrays.columns[0]
        self.col1 = self.arrays.columns[1]
        self.col2 = self.arrays.columns[2]
        self.clear_plots()
        self.create_plot_references()
        self.initial_time = self.epoch_time_s()

        self.start1()

    def start1(self):
        """Threaded data collection"""
        Worker.index += 1
        self.arrays = self.manage_arrays(self.mode, self.arrays)

        worker = Worker(self.query_keithley)
        worker.signals.result.connect(self.start2)
        self.threadpool.tryStart(worker)

    def start2(self, fn_name, result):
        Resistance = float(result.decode()) / 1000
        Tconst3 = self.calculate_temp(Resistance)
        self.arrays.loc[Worker.index, self.col0] = self.time_elapsed(self.initial_time)
        self.arrays.loc[Worker.index, self.col1] = Tconst3
        self.arrays.loc[Worker.index, self.col2] = perf_counter_ns()

        # Condition so that len(array) > 2; avoid slicing errors
        if (Worker.index > 0) and (Worker.index % 10 == 0):
            self.rolling_average(self.arrays)
            self.plot(self.arrays)
            self.update_UI()
        # Loop/Stop condition
        if (
            self.arrays.loc[Worker.index, self.col0] <= self.acquisition_time.value()
            and self.stop_button_pressed == False
        ):
            self.start1()
        # Continually acquire data and save to csv if checkbox is checked
        else:
            if self.stop_button_pressed == True:
                self.checkbox_continuous_acquisition.setChecked(False)
            elif (self.checkbox_continuous_acquisition.isChecked() == True):
                self.arrays.to_csv(self.directory + '/' + str(perf_counter_ns()) + '_' + 'temperature.csv')
                self.start0()
            else:
                print('Acquisition Stopped') 

    def rolling_average(self, df):
        filt = ~(df[self.col0].isnull()) & ~(df[self.col1].isnull())
        self.df_rolling_average = df.loc[filt].rolling(self.rolling_average_indicator.value(), center = True).mean()
        filt = ~(self.df_rolling_average[self.col0].isnull()) 
        self.df_rolling_average = self.df_rolling_average.loc[filt]

    def plot(self, arrays):
        # plot data
        xdata = arrays.loc[: Worker.index, self.col0].to_numpy()
        ydata = arrays.loc[: Worker.index, self.col1].to_numpy()
        self.line_ref_xy.setData(xdata, ydata)
        # self.region_xy.setBounds((xdata.min(), xdata.max()))

        # Rolling Average
        # if Worker.index > self.rolling_average_indicator.value():
        try:
            self.line_ref_xy_rolling.setData(
            self.df_rolling_average.loc[:, self.col0].to_numpy(), 
            self.df_rolling_average.loc[:, self.col1].to_numpy()
            )
        except:
            pass

    def create_plot_references(self):
        self.plot_xy.addItem(self.region_xy, ignoreBounds=True)
        self.line_ref_xy = self.plot_xy.plot(pen="k")
        self.line_ref_xy_roi = self.plot_xy_roi.plot(pen="k")

        self.line_ref_xy_rolling = self.plot_xy.plot(pen="r")
        self.line_ref_xy_roi_rolling = self.plot_xy_roi.plot(pen="r")    

    def update_UI(self):
        # Get lower and upper bound of region
        self.lb, self.ub = self.region_xy.getRegion()
        self.dx = self.ub - self.lb
        filt = (self.arrays.loc[:, self.col0] >= self.lb) & (self.arrays.loc[:, self.col0] <= self.ub)
        self.line_ref_xy_roi.setData(self.arrays.loc[filt, self.col0].to_numpy(), self.arrays.loc[filt, self.col1].to_numpy())

        # if Worker.index > self.rolling_average_indicator.value():
            # self.rolling_roi = self.arrays.loc[filt, self.col2]
            # self.line_ref_xy_roi_rolling.setData(self.arrays.loc[filt, self.col0].to_numpy(), self.arrays.loc[filt, self.col2].to_numpy())
        # Calculate and show Stats
        # self.average = self.rolling_roi.mean()
        self.mean1 = self.arrays.loc[filt, self.col1].mean()
        self.std_dev1 = self.arrays.loc[filt, self.col1].std()
        self.min1 = self.arrays.loc[filt, self.col1].min()
        self.max1 = self.arrays.loc[filt, self.col1].max()

        # Update Indicators
        self.mean_indicator1.setValue(self.mean1)
        self.error_indicator1.setValue(self.std_dev1)
        self.min_indicator1.setValue(self.min1)
        self.max_indicator1.setValue(self.max1)
    
        try:
            self.line_ref_xy_roi_rolling.setData(
                self.df_rolling_average.loc[filt, self.col0].to_numpy(), 
                self.df_rolling_average.loc[filt, self.col1].to_numpy()
            )

            self.rolling_mean = self.df_rolling_average.loc[filt, self.col1].mean()
            self.rolling_std_dev = self.df_rolling_average.loc[filt, self.col1].std()
            self.rolling_min = self.df_rolling_average.loc[filt, self.col1].min()
            self.rolling_max = self.df_rolling_average.loc[filt, self.col1].max()

            self.rolling_mean_indicator1.setValue(self.rolling_mean)
            self.rolling_error_indicator1.setValue(self.rolling_std_dev)
            self.rolling_min_indicator1.setValue(self.rolling_min)
            self.rolling_max_indicator1.setValue(self.rolling_max)

        except:
            pass

    def update_box(self):
        self.region_xy.setRegion((self.box_min.value(), self.box_max.value()))
        self.plot_xy_roi.setRange(xRange = (self.box_min.value(), self.box_max.value()))

    def clear_plots(self):
        self.plot_xy.clear()
        self.plot_xy_roi.clear()

    def epoch_time_s(self):
        return perf_counter_ns() / 1e9

    def time_elapsed(self, initial_time):
        return self.epoch_time_s() - initial_time

    def saveFileDialog(self):
        fileName, _ = QFileDialog.getSaveFileName(
            self,
            "Save As...",
            "",
            "All Files (*);;Text Files (*.csv)",
        )
        # Screenshot
        # pix = window.grab()
        # pix.save(f"{fileName.split('.txt')[0]}.png")
        if fileName:
            todays_date = date.today().strftime("%m-%d-%y")
            self.arrays.to_csv(fileName, index=False)

    def openFileNameDialog(self):
        fileName, _ = QFileDialog.getOpenFileName(
            self,
            "QFileDialog.getOpenFileName()",
            "",
            "All Files (*);;Text Files (*.csv)",
        )
        if fileName:
            self.create_plot_references()

            self.arrays = pd.read_csv(fileName)
            self.col0, self.col1, self.col2 = self.arrays.columns
            filt = ~(self.arrays[self.col0].isnull())
            # Worker.index = self.arrays.loc[filt, self.col0].shape[0] - 1

            self.line_ref_xy.setData(
                self.arrays.loc[filt, self.col0].to_numpy(), 
                self.arrays.loc[filt, self.col1].to_numpy()
            )
            self.region_xy.setRegion(
                (self.arrays.loc[filt, self.col0].min(), 
                self.arrays.loc[filt, self.col0].max())
            )
            self.region_xy.setBounds(
                (self.arrays.loc[filt, self.col0].min(), 
                self.arrays.loc[filt, self.col0].max())
            )
            self.rolling_average(self.arrays.loc[filt])
            self.plot(self.arrays.loc[filt])
            self.update_UI(self.arrays.loc[filt])
                # Rolling Average
                # This filtered data avoids edge effects in the rolling average
                # self.arrays.loc[:, self.col2] = (
                #     self.arrays.loc[:, self.col1]
                #     .rolling(self.averaging_window.value(), center=True)
                #     .mean()
                # )
                # filt = ~(self.arrays[self.col2].isnull())
                # self.line_ref_xy_rolling.setData(
                #     self.arrays.loc[filt, self.col0].to_numpy(), 
                #     self.arrays.loc[filt, self.col2].to_numpy()
                # )

    # Executes when window is closed
    def closeEvent(self, *args, **kwargs):
        super(QMainWindow, self).closeEvent(*args, **kwargs)
        if self.cb_comport.currentText() != "":
            self.inst.close()
        print("Good-Bye Alex!")

class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        tuple (exctype, value, traceback.format_exc() )

    result
        object data returned from processing, anything

    progress
        int indicating % progress

    """

    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object, object)
    progress = pyqtSignal(int)


class Worker(QRunnable):
    index = 0

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        """
        Initialise the runner function with passed args, kwargs.
        """

        # Retrieve args/kwargs here; and fire processing using them
        try:
            self.result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(
                self.fn.__name__, self.result
            )  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    # if fullscreen desired, uncomment the following line
    # window.showMaximized()
    app.exec()

# rm = pyvisa.ResourceManager()
# rm.list_resources()
# inst = rm.open_resource('GPIB0::1::INSTR')
# inst.read_termination = "\n"
# inst.write_termination = "\n"
# inst.query("*IDN?")
# inst.query("TEC:T?")
# inst.close()
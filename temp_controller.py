import pyvisa
import re
import sys
import traceback
from datetime import date
from time import perf_counter_ns

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyqtgraph as pg
# https://matplotlib.org/3.5.0/gallery/user_interfaces/embedding_in_qt_sgskip.html
# from matplotlib.backends.qt_compat import QtWidgets
from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.backends.backend_qtagg import \
    NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from pylablib.devices import Thorlabs
from PyQt5 import QtCore
from PyQt5.QtCore import (QObject, QRunnable, QSize, Qt, QThread, QThreadPool,
                          QTimer, pyqtSignal, pyqtSlot)
from PyQt5.QtGui import QFont
# from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
# from PyQt5.QtCore import QSize
# from PyQt5 import QtGui
from PyQt5.QtWidgets import (QApplication, QComboBox, QDialog, QDoubleSpinBox,
                             QFileDialog, QGridLayout, QHBoxLayout, QLabel,
                             QLineEdit, QMainWindow, QMessageBox, QPushButton,
                             QSlider, QSpinBox, QVBoxLayout, QWidget)
from scipy.optimize import curve_fit

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.rm = pyvisa.ResourceManager()
        self.UI()
        self.qtimer()
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(self.threadpool.maxThreadCount())

        self.const_c1 = np.array(1.196051641e-3)
        self.const_c2 = np.array(2.228227940e-4) 
        self.const_c3 = np.array(1.352729757e-7)
        self.const_a = np.array(3.354016e-3)
        self.const_b = np.array(2.567090e-4) 
        self.const_c = np.array(2.39213e-6)
        self.const_d = np.array(-7.68347e-8)

        self.indicator_c1.setValue(self.const_c1 * 1e3)
        self.indicator_c2.setValue(self.const_c2 * 1e4)
        self.indicator_c3.setValue(self.const_c3 * 1e7)
        self.indicator_a.setValue(self.const_a * 1e3)
        self.indicator_b.setValue(self.const_b * 1e4)
        self.indicator_c.setValue(self.const_c * 1e6)
        self.indicator_d.setValue(self.const_d * 1e8)

    def UI(self):
        self.setWindowTitle("Hi Alex!")
        self.setStyleSheet("background-color: white;")
        # self.setFixedSize(QSize(1100, 1100))

        # Create Widgets
        self.btn_fit= QPushButton("Fit")
        self.btn_update_constants = QPushButton("Update \n Internal Constants")
        self.btn_get_constants = QPushButton("Get \n Internal Constants")
        self.btn_start = QPushButton("Start")
        self.btn_stop = QPushButton("Stop")
        self.btn_load_data = QPushButton("Load Data")
        self.btn_save_data = QPushButton("Save Data")
        self.btn_clear_plot = QPushButton("Clear Plot")
        self.btn_clear_fit = QPushButton("Clear Fits")

        self.label_mode = QLabel("Mode")
        self.placeholder_text = QLabel("      ")
        self.cb_mode = QComboBox()
        self.cb_mode.addItems(["R", "T", "ITE"])
        self.label_mode.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_pd_address = QLabel("COM Port")
        self.cb_pd_address = QComboBox()
        self.cb_pd_address.addItems(self.rm.list_resources())
        self.cb_pd_address.setCurrentIndex(-1)
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
        self.indicator_c1.setMinimum(0)
        self.indicator_c1.setMaximum(10)
        self.indicator_c1.setValue(0)
        self.indicator_c1.setSingleStep(1)
        self.indicator_c1.setDecimals(10)
        self.indicator_c1.setSuffix(' e-3')


        self.label_c2 = QLabel("C2")
        self.label_c2.setAlignment(QtCore.Qt.AlignHCenter)
        self.indicator_c2 = QDoubleSpinBox()
        self.indicator_c2.setMinimum(0)
        self.indicator_c2.setMaximum(10)
        self.indicator_c2.setValue(0)
        self.indicator_c2.setSingleStep(1)
        self.indicator_c2.setDecimals(10)
        self.indicator_c2.setSuffix(' e-4')

        self.label_c3 = QLabel("C3")
        self.label_c3.setAlignment(QtCore.Qt.AlignHCenter)
        self.indicator_c3 = QDoubleSpinBox()
        self.indicator_c3.setMinimum(0)
        self.indicator_c3.setMaximum(10)
        self.indicator_c3.setValue(0)
        self.indicator_c3.setSingleStep(1)
        self.indicator_c3.setDecimals(10)
        self.indicator_c3.setSuffix(' e-7')

        self.label_a = QLabel("a")
        self.label_a.setAlignment(QtCore.Qt.AlignHCenter)
        self.indicator_a = QDoubleSpinBox()
        self.indicator_a.setMinimum(0)
        self.indicator_a.setMaximum(np.inf)
        self.indicator_a.setValue(0)
        self.indicator_a.setSingleStep(1)
        self.indicator_a.setDecimals(10)
        self.indicator_a.setSuffix(' e-3')


        self.label_b = QLabel("b")
        self.label_b.setAlignment(QtCore.Qt.AlignHCenter)
        self.indicator_b = QDoubleSpinBox()
        self.indicator_b.setMinimum(0)
        self.indicator_b.setMaximum(np.inf)
        self.indicator_b.setValue(0)
        self.indicator_b.setSingleStep(1)
        self.indicator_b.setDecimals(10)
        self.indicator_b.setSuffix(' e-4')

        self.label_c = QLabel("c")
        self.label_c.setAlignment(QtCore.Qt.AlignHCenter)
        self.indicator_c = QDoubleSpinBox()
        self.indicator_c.setMinimum(0)
        self.indicator_c.setMaximum(np.inf)
        self.indicator_c.setValue(0)
        self.indicator_c.setSingleStep(1)
        self.indicator_c.setDecimals(10)
        self.indicator_c.setSuffix(' e-6')

        self.label_d = QLabel("d")
        self.label_d.setAlignment(QtCore.Qt.AlignHCenter)
        self.indicator_d = QDoubleSpinBox()
        self.indicator_d.setMinimum(-np.inf)
        self.indicator_d.setMaximum(np.inf)
        self.indicator_d.setValue(0)
        self.indicator_d.setSingleStep(1)
        self.indicator_d.setDecimals(10)
        self.indicator_d.setSuffix(' e-8')

        self.label_internal_constants = QLabel('Internal Constants')
        self.indicator_internal_constants = QLineEdit()

        self.label_averaging_window = QLabel("Rolling Average Window")
        self.averaging_window = QSpinBox()
        self.averaging_window.setRange(1, int(1e9))
        self.averaging_window.setValue(1)
        self.averaging_window.setSingleStep(5)
        self.label_averaging_window.setAlignment(QtCore.Qt.AlignHCenter)
        self.averaging_window.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_error_indicator1 = QLabel("Error Acquired")
        self.error_indicator1 = QDoubleSpinBox()
        self.error_indicator1.setReadOnly(True)
        self.error_indicator1.setButtonSymbols(2)
        self.error_indicator1.setSuffix(" C")
        self.error_indicator1.setRange(0, int(1e10))
        self.error_indicator1.setDecimals(10)
        self.label_error_indicator1.setAlignment(QtCore.Qt.AlignHCenter)
        self.error_indicator1.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_error_indicator2 = QLabel("Error Calculated 3-const")
        self.error_indicator2 = QDoubleSpinBox()
        self.error_indicator2.setReadOnly(True)
        self.error_indicator2.setButtonSymbols(2)
        self.error_indicator2.setSuffix(" C")
        self.error_indicator2.setRange(0, int(1e10))
        self.error_indicator2.setDecimals(10)
        self.label_error_indicator2.setAlignment(QtCore.Qt.AlignHCenter)
        self.error_indicator2.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_error_indicator3 = QLabel("Error Calculated 4-const")
        self.error_indicator3 = QDoubleSpinBox()
        self.error_indicator3.setReadOnly(True)
        self.error_indicator3.setButtonSymbols(2)
        self.error_indicator3.setSuffix(" C")
        self.error_indicator3.setRange(0, int(1e10))
        self.error_indicator3.setDecimals(10)
        self.label_error_indicator3.setAlignment(QtCore.Qt.AlignHCenter)
        self.error_indicator3.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_min_indicator1 = QLabel("Min Acquired")
        self.min_indicator1 = QDoubleSpinBox()
        self.min_indicator1.setReadOnly(True)
        self.min_indicator1.setButtonSymbols(2)
        self.min_indicator1.setSuffix(" C")
        self.min_indicator1.setRange(0, int(1e10))
        self.min_indicator1.setDecimals(10)
        self.label_min_indicator1.setAlignment(QtCore.Qt.AlignHCenter)
        self.min_indicator1.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_max_indicator1 = QLabel("Max Acquired")
        self.max_indicator1 = QDoubleSpinBox()
        self.max_indicator1.setReadOnly(True)
        self.max_indicator1.setButtonSymbols(2)
        self.max_indicator1.setSuffix(" C")
        self.max_indicator1.setRange(0, int(1e10))
        self.max_indicator1.setDecimals(10)
        self.label_max_indicator1.setAlignment(QtCore.Qt.AlignHCenter)
        self.max_indicator1.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_min_indicator2 = QLabel("Min Calculated")
        self.min_indicator2 = QDoubleSpinBox()
        self.min_indicator2.setReadOnly(True)
        self.min_indicator2.setButtonSymbols(2)
        self.min_indicator2.setSuffix(" C")
        self.min_indicator2.setRange(0, int(1e10))
        self.min_indicator2.setDecimals(10)
        self.label_min_indicator2.setAlignment(QtCore.Qt.AlignHCenter)
        self.min_indicator2.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_max_indicator2 = QLabel("Max Calculated")
        self.max_indicator2 = QDoubleSpinBox()
        self.max_indicator2.setReadOnly(True)
        self.max_indicator2.setButtonSymbols(2)
        self.max_indicator2.setSuffix(" C")
        self.max_indicator2.setRange(0, int(1e10))
        self.max_indicator2.setDecimals(10)
        self.label_max_indicator2.setAlignment(QtCore.Qt.AlignHCenter)
        self.max_indicator2.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_min_indicator3 = QLabel("Min Calculated")
        self.min_indicator3 = QDoubleSpinBox()
        self.min_indicator3.setReadOnly(True)
        self.min_indicator3.setButtonSymbols(2)
        self.min_indicator3.setSuffix(" C")
        self.min_indicator3.setRange(0, int(1e10))
        self.min_indicator3.setDecimals(10)
        self.label_min_indicator3.setAlignment(QtCore.Qt.AlignHCenter)
        self.min_indicator3.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_max_indicator3 = QLabel("Max Calculated")
        self.max_indicator3 = QDoubleSpinBox()
        self.max_indicator3.setReadOnly(True)
        self.max_indicator3.setButtonSymbols(2)
        self.max_indicator3.setSuffix(" C")
        self.max_indicator3.setRange(0, int(1e10))
        self.max_indicator3.setDecimals(10)
        self.label_max_indicator3.setAlignment(QtCore.Qt.AlignHCenter)
        self.max_indicator3.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_slope_indicator1 = QLabel("Slope\n(Acquired Directly)")
        self.slope_indicator1 = QDoubleSpinBox()
        self.slope_indicator1.setReadOnly(True)
        self.slope_indicator1.setButtonSymbols(2)
        self.slope_indicator1.setRange(0, int(1e10))
        self.slope_indicator1.setDecimals(10)
        self.label_slope_indicator1.setAlignment(QtCore.Qt.AlignHCenter)
        self.slope_indicator1.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_slope_error_indicator1 = QLabel("Slope Error")
        self.slope_error_indicator1 = QDoubleSpinBox()
        self.slope_error_indicator1.setReadOnly(True)
        self.slope_error_indicator1.setButtonSymbols(2)
        self.slope_error_indicator1.setRange(0, int(1e10))
        self.slope_error_indicator1.setDecimals(10)
        self.label_slope_error_indicator1.setAlignment(QtCore.Qt.AlignHCenter)
        self.slope_error_indicator1.setAlignment(QtCore.Qt.AlignHCenter)
    
        self.label_slope_indicator2 = QLabel("Slope\n(Calculated 3-const)")
        self.slope_indicator2 = QDoubleSpinBox()
        self.slope_indicator2.setReadOnly(True)
        self.slope_indicator2.setButtonSymbols(2)
        self.slope_indicator2.setRange(0, int(1e10))
        self.slope_indicator2.setDecimals(10)
        self.label_slope_indicator2.setAlignment(QtCore.Qt.AlignHCenter)
        self.slope_indicator2.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_slope_error_indicator2 = QLabel("Slope Error")
        self.slope_error_indicator2 = QDoubleSpinBox()
        self.slope_error_indicator2.setReadOnly(True)
        self.slope_error_indicator2.setButtonSymbols(2)
        self.slope_error_indicator2.setRange(0, int(1e10))
        self.slope_error_indicator2.setDecimals(10)
        self.label_slope_error_indicator2.setAlignment(QtCore.Qt.AlignHCenter)
        self.slope_error_indicator2.setAlignment(QtCore.Qt.AlignHCenter)
    
        self.label_slope_indicator3 = QLabel("Slope\n(Calculated 4-const)")
        self.slope_indicator3 = QDoubleSpinBox()
        self.slope_indicator3.setReadOnly(True)
        self.slope_indicator3.setButtonSymbols(2)
        self.slope_indicator3.setRange(0, int(1e10))
        self.slope_indicator3.setDecimals(10)
        self.label_slope_indicator3.setAlignment(QtCore.Qt.AlignHCenter)
        self.slope_indicator3.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_slope_error_indicator3 = QLabel("Slope Error")
        self.slope_error_indicator3 = QDoubleSpinBox()
        self.slope_error_indicator3.setReadOnly(True)
        self.slope_error_indicator3.setButtonSymbols(2)
        self.slope_error_indicator3.setRange(0, int(1e10))
        self.slope_error_indicator3.setDecimals(10)
        self.label_slope_error_indicator3.setAlignment(QtCore.Qt.AlignHCenter)
        self.slope_error_indicator3.setAlignment(QtCore.Qt.AlignHCenter)
    
        self.label_intercept_indicator1 = QLabel("Intercept\n(Acquired Directly)")
        self.intercept_indicator1 = QDoubleSpinBox()
        self.intercept_indicator1.setReadOnly(True)
        self.intercept_indicator1.setButtonSymbols(2)
        self.intercept_indicator1.setRange(0, int(1e10))
        self.intercept_indicator1.setDecimals(10)
        self.label_intercept_indicator1.setAlignment(QtCore.Qt.AlignHCenter)
        self.intercept_indicator1.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_intercept_error_indicator1 = QLabel("Intercept Error")
        self.intercept_error_indicator1 = QDoubleSpinBox()
        self.intercept_error_indicator1.setReadOnly(True)
        self.intercept_error_indicator1.setButtonSymbols(2)
        self.intercept_error_indicator1.setRange(0, int(1e10))
        self.intercept_error_indicator1.setDecimals(10)
        self.label_intercept_error_indicator1.setAlignment(QtCore.Qt.AlignHCenter)
        self.intercept_error_indicator1.setAlignment(QtCore.Qt.AlignHCenter)
    
        self.label_intercept_indicator2 = QLabel("Intercept\n(Calculated 3-const)")
        self.intercept_indicator2 = QDoubleSpinBox()
        self.intercept_indicator2.setReadOnly(True)
        self.intercept_indicator2.setButtonSymbols(2)
        self.intercept_indicator2.setRange(0, int(1e10))
        self.intercept_indicator2.setDecimals(10)
        self.label_intercept_indicator2.setAlignment(QtCore.Qt.AlignHCenter)
        self.intercept_indicator2.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_intercept_error_indicator2 = QLabel("Intercept Error")
        self.intercept_error_indicator2 = QDoubleSpinBox()
        self.intercept_error_indicator2.setReadOnly(True)
        self.intercept_error_indicator2.setButtonSymbols(2)
        self.intercept_error_indicator2.setRange(0, int(1e10))
        self.intercept_error_indicator2.setDecimals(10)
        self.label_intercept_error_indicator2.setAlignment(QtCore.Qt.AlignHCenter)
        self.intercept_error_indicator2.setAlignment(QtCore.Qt.AlignHCenter)
    
        self.label_intercept_indicator3 = QLabel("Intercept\nCalculated 4-const)")
        self.intercept_indicator3 = QDoubleSpinBox()
        self.intercept_indicator3.setReadOnly(True)
        self.intercept_indicator3.setButtonSymbols(2)
        self.intercept_indicator3.setRange(0, int(1e10))
        self.intercept_indicator3.setDecimals(10)
        self.label_intercept_indicator3.setAlignment(QtCore.Qt.AlignHCenter)
        self.intercept_indicator3.setAlignment(QtCore.Qt.AlignHCenter)

        self.label_intercept_error_indicator3 = QLabel("Intercept Error")
        self.intercept_error_indicator3 = QDoubleSpinBox()
        self.intercept_error_indicator3.setReadOnly(True)
        self.intercept_error_indicator3.setButtonSymbols(2)
        self.intercept_error_indicator3.setRange(0, int(1e10))
        self.intercept_error_indicator3.setDecimals(10)
        self.label_intercept_error_indicator3.setAlignment(QtCore.Qt.AlignHCenter)
        self.intercept_error_indicator3.setAlignment(QtCore.Qt.AlignHCenter)

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
        self.plot_xy.setTitle("Temp. vs Time: Black = Acquired Directly, Red = Calculated from R 3-constants, Blue = Calculated from R 4-constants", color="k")
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

        self.layout.addLayout(self.experiment_layout, 0, 3)
        self.layout.addLayout(self.plot_layout, 1, 0, 1, 6)
        self.layout.setColumnMinimumWidth(0, 50)
        self.layout.setColumnMinimumWidth(2, 50)
        self.layout.setColumnMinimumWidth(4, 50)
        self.layout.setColumnMinimumWidth(6, 50)
        # self.layout.setColumnMinimumWidth(8, 50)
        self.layout.setRowStretch(1, 1)

        # Set QWidget as the central window that will contain all widgets and layouts
        self.widget = QWidget()
        self.widget.setLayout(self.layout)
        self.setCentralWidget(self.widget)

        # Experiment Block
        self.experiment_layout1.addWidget(self.label_pd_address)
        self.experiment_layout2.addWidget(self.cb_pd_address)
        self.experiment_layout1.addWidget(self.label_c1)
        self.experiment_layout2.addWidget(self.indicator_c1)
        self.experiment_layout1.addWidget(self.label_c2)
        self.experiment_layout2.addWidget(self.indicator_c2)
        self.experiment_layout1.addWidget(self.label_c3)
        self.experiment_layout2.addWidget(self.indicator_c3)
        self.experiment_layout1.addWidget(self.label_a)
        self.experiment_layout2.addWidget(self.indicator_a)
        self.experiment_layout1.addWidget(self.label_b)
        self.experiment_layout2.addWidget(self.indicator_b)
        self.experiment_layout1.addWidget(self.label_c)
        self.experiment_layout2.addWidget(self.indicator_c)
        self.experiment_layout1.addWidget(self.label_d)
        self.experiment_layout2.addWidget(self.indicator_d)
        self.experiment_layout3.addWidget(self.label_internal_constants)
        self.experiment_layout4.addWidget(self.indicator_internal_constants)
        self.experiment_layout3.addWidget(self.label_mode)
        self.experiment_layout4.addWidget(self.cb_mode)
        self.experiment_layout3.addWidget(self.placeholder_text)
        self.experiment_layout3.addWidget(self.placeholder_text)
        self.experiment_layout4.addWidget(self.btn_get_constants)
        self.experiment_layout4.addWidget(self.btn_update_constants)
        self.experiment_layout5.addWidget(self.label_acquisition_time)
        self.experiment_layout6.addWidget(self.acquisition_time)
        self.experiment_layout5.addWidget(self.label_box_min)
        self.experiment_layout6.addWidget(self.box_min)
        self.experiment_layout5.addWidget(self.label_box_max)
        self.experiment_layout6.addWidget(self.box_max)
        self.experiment_layout7.addWidget(self.btn_start)
        self.experiment_layout7.addWidget(self.btn_stop)
        self.experiment_layout7.addWidget(self.btn_save_data)
        self.experiment_layout7.addWidget(self.btn_load_data)
        self.experiment_layout7.addWidget(self.btn_clear_plot)
        self.experiment_layout7.addWidget(self.btn_fit)
        self.experiment_layout8.addWidget(self.label_error_indicator1)
        self.experiment_layout8.addWidget(self.label_error_indicator2)
        self.experiment_layout8.addWidget(self.label_error_indicator3)
        self.experiment_layout8.addWidget(self.label_min_indicator1)
        self.experiment_layout8.addWidget(self.label_min_indicator2)
        self.experiment_layout8.addWidget(self.label_min_indicator3)
        self.experiment_layout8.addWidget(self.label_max_indicator1)
        self.experiment_layout8.addWidget(self.label_max_indicator2)
        self.experiment_layout8.addWidget(self.label_max_indicator3)
        self.experiment_layout9.addWidget(self.error_indicator1)
        self.experiment_layout9.addWidget(self.error_indicator2)
        self.experiment_layout9.addWidget(self.error_indicator3)
        self.experiment_layout9.addWidget(self.min_indicator1)
        self.experiment_layout9.addWidget(self.min_indicator2)
        self.experiment_layout9.addWidget(self.min_indicator3)
        self.experiment_layout9.addWidget(self.max_indicator1)
        self.experiment_layout9.addWidget(self.max_indicator2)
        self.experiment_layout9.addWidget(self.max_indicator3)

        self.experiment_layout10.addWidget(self.label_slope_indicator1)
        self.experiment_layout10.addWidget(self.label_slope_error_indicator1)
        self.experiment_layout10.addWidget(self.label_intercept_indicator1)
        self.experiment_layout10.addWidget(self.label_intercept_error_indicator1)

        self.experiment_layout10.addWidget(self.label_slope_indicator2)
        self.experiment_layout10.addWidget(self.label_slope_error_indicator2)
        self.experiment_layout10.addWidget(self.label_intercept_indicator2)
        self.experiment_layout10.addWidget(self.label_intercept_error_indicator2)

        self.experiment_layout10.addWidget(self.label_slope_indicator3)
        self.experiment_layout10.addWidget(self.label_slope_error_indicator3)
        self.experiment_layout10.addWidget(self.label_intercept_indicator3)
        self.experiment_layout10.addWidget(self.label_intercept_error_indicator3)

        self.experiment_layout11.addWidget(self.slope_indicator1)
        self.experiment_layout11.addWidget(self.slope_error_indicator1)
        self.experiment_layout11.addWidget(self.intercept_indicator1)
        self.experiment_layout11.addWidget(self.intercept_error_indicator1)

        self.experiment_layout11.addWidget(self.slope_indicator2)
        self.experiment_layout11.addWidget(self.slope_error_indicator2)
        self.experiment_layout11.addWidget(self.intercept_indicator2)
        self.experiment_layout11.addWidget(self.intercept_error_indicator2)

        self.experiment_layout11.addWidget(self.slope_indicator3)
        self.experiment_layout11.addWidget(self.slope_error_indicator3)
        self.experiment_layout11.addWidget(self.intercept_indicator3)
        self.experiment_layout11.addWidget(self.intercept_error_indicator3)
        # self.experiment_layout8.addWidget(self.toggle, stretch=0)
        self.experiment_layout.addStretch(0)

        # Graph Block
        self.plot_layout.addWidget(self.plot_widget)
        # self.show()

        # UI Event Triggers
        self.btn_fit.clicked.connect(self.fit_data)
        self.btn_update_constants.clicked.connect(self.update_internal_constants)
        self.btn_get_constants.clicked.connect(self.get_internal_constants)
        self.btn_start.clicked.connect(self.start0)
        self.btn_stop.clicked.connect(self.stop)
        self.btn_save_data.clicked.connect(self.saveFileDialog)
        self.btn_load_data.clicked.connect(self.openFileNameDialog)
        self.btn_clear_plot.clicked.connect(self.clear_plots)
        self.cb_pd_address.currentIndexChanged.connect(self.init_controller)
        self.region_xy.sigRegionChanged.connect(self.update_UI)
        self.box_min.valueChanged.connect(self.update_box)
        self.box_max.valueChanged.connect(self.update_box)
        self.cb_mode.currentIndexChanged.connect(self.update_mode)
        # self.indicator_c1.valueChanged.connect(self.update_c_constants)
        # self.indicator_c2.valueChanged.connect(self.update_c_constants)
        # self.indicator_c3.valueChanged.connect(self.update_c_constants)
        # self.indicator_a.valueChanged.connect(self.update_letter_constants)
        # self.indicator_b.valueChanged.connect(self.update_letter_constants)
        # self.indicator_c.valueChanged.connect(self.update_letter_constants)
        # self.indicator_d.valueChanged.connect(self.update_letter_constants)
        # self.averaging_window.valueChanged.connect(self.update_rolling_average)
    
    # def update_c_constants(self):
    #     self.const_c1 = np.array(self.indicator_c1.value()) * 1e-3 
    #     self.const_c2 = np.array(self.indicator_c2.value()) * 1e-4
    #     self.const_c3 = np.array(self.indicator_c3.value()) * 1e-7

    # def update_letter_constants(self):
        # self.const_a = np.array(self.indicator_a.value())
        # self.const_b = np.array(self.indicator_b.value())
        # self.const_c = np.array(self.indicator_c.value())
        # self.const_d = np.array(self.indicator_d.value())
    def update_mode(self):
        if self.cb_mode.currentText == 'R':
            self.inst.write('TEC:MODE:R')
        if self.cb_mode.currentText == 'T':
            self.inst.write('TEC:MODE:T')
        if self.cb_mode.currentText == 'ITE':
            self.inst.write('TEC:MODE:ITE')
        print('Mode Changed')

    def fit_data(self):
        def linear(x, m, b):
            result = m*x + b
            return result
        
        filt = (self.arrays.loc[:, self.col0] >= self.lb) & (self.arrays.loc[:, self.col0] <= self.ub)
        xdata = self.arrays.loc[filt, self.col0].to_numpy()
        ydata1 = self.arrays.loc[filt, self.col1].to_numpy()
        ydata2 = self.arrays.loc[filt, self.col2].to_numpy()
        ydata3 = self.arrays.loc[filt, self.col3].to_numpy()
        # self.line_ref_xy_roi2.setData(self.arrays.loc[filt, self.col0].to_numpy(), self.arrays.loc[filt, self.col2].to_numpy())
        
        popt1, pcov1 = curve_fit(linear, xdata, ydata1)
        slope1 = popt1[0]
        intercept1 = popt1[1]
        perr1 = np.sqrt(np.diag(pcov1))  # error
        error_slope1 = perr1[0]
        error_intercept1 = perr1[1]

        print('Acquired T directly:', 'slope:', slope1, 'slope error:', error_slope1, 'intercept:', intercept1, 'intercept error:', error_intercept1)
        self.line_ref_xy_roi_fit1.setData(xdata, linear(xdata, popt1[0], popt1[1]))
        self.slope_indicator1.setValue(slope1)
        self.slope_error_indicator1.setValue(error_slope1)
        self.intercept_indicator1.setValue(intercept1)
        self.intercept_error_indicator1.setValue(error_intercept1)

        popt2, pcov2 = curve_fit(linear, xdata, ydata2)
        slope2 = popt2[0]
        intercept2 = popt2[1]
        perr2 = np.sqrt(np.diag(pcov2))  # error
        error_slope2 = perr2[0]
        error_intercept2 = perr2[1]
        print('calculated 3-constants:', 'slope:', slope2, 'slope error:', error_slope2, 'intercept:', intercept2, 'intercept error:', error_intercept2)
        self.line_ref_xy_roi_fit2.setData(xdata, linear(xdata, popt2[0], popt2[1]))
        self.slope_indicator2.setValue(slope2)
        self.slope_error_indicator2.setValue(error_slope2)
        self.intercept_indicator2.setValue(intercept2)
        self.intercept_error_indicator2.setValue(error_intercept2)

        popt3, pcov3 = curve_fit(linear, xdata, ydata3)
        slope3 = popt3[0]
        intercept3 = popt3[1]
        perr3 = np.sqrt(np.diag(pcov3))  # error
        error_slope3 = perr3[0]
        error_intercept3 = perr3[1]
        print('calculated 4-constants:', 'slope:', slope3, 'slope error:', error_slope3, 'intercept:', intercept3, 'intercept error:', error_intercept3)
        self.line_ref_xy_roi_fit3.setData(xdata, linear(xdata, popt3[0], popt3[1]))
        self.slope_indicator3.setValue(slope3)
        self.slope_error_indicator3.setValue(error_slope3)
        self.intercept_indicator3.setValue(intercept3)
        self.intercept_error_indicator3.setValue(error_intercept3)
        # self.line_ref_xy_roi1.setData(self.arrays.loc[filt, self.col0].to_numpy(), self.arrays.loc[filt, self.col1].to_numpy())
    
    def update_internal_constants(self):
        c1 = np.array(self.indicator_c1.value())
        c2 = np.array(self.indicator_c2.value())
        c3 = np.array(self.indicator_c2.value())
        self.inst.write(f'TEC:CONST {c1:.3f},{c2:.3f},{c3:.3f}')

    def get_internal_constants(self):
        self.indicator_internal_constants.setText(self.inst.query("TEC:CONST?"))


    def init_controller(self):
        self.inst = self.rm.open_resource(str(self.cb_pd_address.currentText()))
        self.inst.read_termination = "\n"
        self.inst.write_termination = "\n"
        self.inst.timeout = 1000
        self.indicator_internal_constants.setText(self.inst.query("TEC:CONST?"))

    def stop(self):
        self.stop_button_pressed = True
        print(self.stop_button_pressed)

    def start0(self):
        """Initialize Scatter program"""
        self.stop_button_pressed = False
        self.button_pressed = self.sender().text()
        Worker.index = -1
        self.mode = ['Time (s)', 'Temp (C)', 'Temp Converted 3-constants (C)', 'Temp Converted 4-constants (C)']
        self.arrays = self.manage_arrays(self.mode)
        self.col0 = self.arrays.columns[0]
        self.col1 = self.arrays.columns[1]
        self.col2 = self.arrays.columns[2]
        self.col3 = self.arrays.columns[3]
        self.clear_plots()
        self.create_plot_references()
        self.initial_time = self.epoch_time_s()

        self.start1()

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

    # Define Qtimers
    def qtimer(self):
        self.timer = QtCore.QTimer()
        # self.timer.timeout.connect(self.workers_start)
        self.set_interval()

    # Set Loop Interval
    def set_interval(self):
        pass
        # self.timer.setInterval(self.interval)

    def start1(self):
        """Threaded data collection"""
        Worker.index += 1
        self.arrays = self.manage_arrays(self.mode, self.arrays)

        worker = Worker(self.acquire)
        worker.signals.result.connect(self.start2)
        self.threadpool.tryStart(worker)

    def acquire(self):
        response = self.inst.query("TEC:T?; TEC:R?")
        splitter = response.split(';')
        result = [float(splitter) for splitter in splitter]
        return result
    
    def calculate_temp(self, R):
        T1 = (1 / (self.const_c1 + (self.const_c2 * np.log(R*1000)) + (self.const_c3 * (np.log(R*1000)**3)))) - 273.15
        T2 = (1 / (self.const_a + self.const_b*np.log(R/10) + self.const_c*np.log(R/10)**2 + self.const_d*(np.log(R/10)**3))) - 273.15
        result = [T1, T2]
        return result
    
    def start2(self, fn_name, result):
        self.arrays.loc[Worker.index, self.col0] = self.time_elapsed(self.initial_time)
        self.arrays.loc[Worker.index, self.col1] = result[0]
        self.arrays.loc[Worker.index, self.col2] = self.calculate_temp(result[1])[0]
        self.arrays.loc[Worker.index, self.col3] = self.calculate_temp(result[1])[1]

        # if Worker.index > self.averaging_window.value():
        #     self.arrays.loc[:, self.col2] = (
        #         self.arrays.loc[:, self.col1]
        #         .rolling(self.averaging_window.value(), center=True)
        #         .mean()
        #     )
        # Condition so that len(array) > 2; avoid slicing errors
        if Worker.index > 0:
            self.plot(self.arrays)
            self.update_UI()
        # Loop/Stop condition
        if (
            self.arrays.loc[Worker.index, self.col0] <= self.acquisition_time.value()
            and self.stop_button_pressed == False
        ):
            self.start1()
        else:
            print('Acquisition Stopped') 
            # if self.button_pressed == "Scatter":
            # self.average_scatter = self.arrays.loc[:, self.col1].mean()
            # self.sd_scatter = self.arrays.loc[:, self.col1].std()
            #     self.scatter_indicator.setValue(self.average_scatter)
            #     self.error_scatter_indicator.setValue(self.sd_scatter)

    def plot(self, arrays):
        if Worker.index > 0:
            xdata = arrays.loc[: Worker.index, self.col0].to_numpy()
            ydata = arrays.loc[: Worker.index, self.col1].to_numpy()
            ydata2 = arrays.loc[: Worker.index, self.col2].to_numpy()
            ydata3 = arrays.loc[: Worker.index, self.col3].to_numpy()
            # plot data
            self.line_ref_xy.setData(xdata, ydata)
            self.line_ref_xy2.setData(xdata, ydata2)
            self.line_ref_xy3.setData(xdata, ydata3)
            self.region_xy.setBounds((xdata.min(), xdata.max()))
        # Rolling Average
        # if Worker.index > self.averaging_window.value():
        #     # This filtered data avoids edge effects in the rolling average
        #     filt = ~(arrays[self.col0].isnull()) & ~(arrays[self.col2].isnull())
        #     self.line_ref_xy_rolling.setData(
        #         arrays.loc[filt, self.col0].to_numpy(), 
        #         arrays.loc[filt, self.col2].to_numpy()
        #     )
        if Worker.index == 5:
            self.region_xy.setRegion((xdata.min(), xdata.max()))

    def create_plot_references(self):
        self.plot_xy.addItem(self.region_xy, ignoreBounds=True)
        self.line_ref_xy = self.plot_xy.plot(pen="k")
        self.line_ref_xy2 = self.plot_xy.plot(pen="r")
        self.line_ref_xy3 = self.plot_xy.plot(pen="b")
        # self.line_ref_xy_rolling = self.plot_xy.plot(pen="r")

        self.line_ref_xy_roi = self.plot_xy_roi.plot(pen="k")
        self.line_ref_xy_roi2 = self.plot_xy_roi.plot(pen="r")
        self.line_ref_xy_roi3 = self.plot_xy_roi.plot(pen="b")

        self.line_ref_xy_roi_fit1 = self.plot_xy_roi.plot(pen="g")
        self.line_ref_xy_roi_fit2 = self.plot_xy_roi.plot(pen="m")
        self.line_ref_xy_roi_fit3 = self.plot_xy_roi.plot(pen="c")
        # self.line_ref_xy_roi_rolling = self.plot_xy_roi.plot(pen="r")    

    def update_UI(self):
        # Get lower and upper bound of region
        self.lb, self.ub = self.region_xy.getRegion()
        self.dx = self.ub - self.lb
        filt = (self.arrays.loc[:, self.col0] >= self.lb) & (self.arrays.loc[:, self.col0] <= self.ub)
        self.line_ref_xy_roi.setData(self.arrays.loc[filt, self.col0].to_numpy(), self.arrays.loc[filt, self.col1].to_numpy())
        self.line_ref_xy_roi2.setData(self.arrays.loc[filt, self.col0].to_numpy(), self.arrays.loc[filt, self.col2].to_numpy())
        self.line_ref_xy_roi3.setData(self.arrays.loc[filt, self.col0].to_numpy(), self.arrays.loc[filt, self.col3].to_numpy())

        # if Worker.index > self.averaging_window.value():
        #     self.rolling_roi = self.arrays.loc[filt, self.col2]
        #     self.line_ref_xy_roi_rolling.setData(self.arrays.loc[filt, self.col0].to_numpy(), self.arrays.loc[filt, self.col2].to_numpy())

        #     # Calculate and show Stats
            # self.average = self.rolling_roi.mean()
        self.std_dev1 = self.arrays.loc[filt, self.col1].std()
        self.std_dev2 = self.arrays.loc[filt, self.col2].std()
        self.std_dev3 = self.arrays.loc[filt, self.col3].std()
        self.min1 = self.arrays.loc[filt, self.col1].min()
        self.min2 = self.arrays.loc[filt, self.col2].min()
        self.min3 = self.arrays.loc[filt, self.col3].min()
        self.max1 = self.arrays.loc[filt, self.col1].max()
        self.max2 = self.arrays.loc[filt, self.col2].max()
        self.max3 = self.arrays.loc[filt, self.col3].max()
        #     self.maximum = self.rolling_roi.max()
        #     self.minimum = self.rolling_roi.min()
        #     # Update Indicators
        self.error_indicator1.setValue(self.std_dev1)
        self.error_indicator2.setValue(self.std_dev2)
        self.error_indicator3.setValue(self.std_dev3)
        self.min_indicator1.setValue(self.min1)
        self.min_indicator2.setValue(self.min2)
        self.min_indicator3.setValue(self.min3)
        self.max_indicator1.setValue(self.max1)
        self.max_indicator2.setValue(self.max2)
        self.max_indicator3.setValue(self.max3)
    
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

    # Executes when window is closed
    def closeEvent(self, *args, **kwargs):
        super(QMainWindow, self).closeEvent(*args, **kwargs)
        if self.cb_pd_address.currentText() != "":
            self.inst.close()
        # if self.cb2.currentText() != "":
        # self.inst_esp.close()
        print("Good-Bye Alex!")

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
            # date_dict = {"Date":[todays_date]}
            # df_date = pd.DataFrame(date_dict)
            # print(df_date)
            # self.arrays.join(df_date)
            # print(self.arrays)
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
            self.col0, self.col1, self.col2, self.col3 = self.arrays.columns
            filt = ~(self.arrays[self.col0].isnull())
            Worker.index = self.arrays.loc[filt, self.col0].shape[0] - 1

            self.line_ref_xy.setData(
                self.arrays.loc[filt, self.col0].to_numpy(), 
                self.arrays.loc[filt, self.col1].to_numpy()
            )
            self.line_ref_xy2.setData(
                self.arrays.loc[filt, self.col0].to_numpy(), 
                self.arrays.loc[filt, self.col2].to_numpy()
            )
            self.line_ref_xy3.setData(
                self.arrays.loc[filt, self.col0].to_numpy(), 
                self.arrays.loc[filt, self.col3].to_numpy()
            )
            self.region_xy.setRegion(
                (self.arrays.loc[filt, self.col0].min(), 
                self.arrays.loc[filt, self.col0].max())
            )
            self.region_xy.setBounds(
                (self.arrays.loc[filt, self.col0].min(), 
                self.arrays.loc[filt, self.col0].max())
            )
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
    index1 = 0
    index2 = 0
    index3 = 0
    index4 = 0

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
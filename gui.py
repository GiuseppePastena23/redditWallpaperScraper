import os
import re
import sys
import PIL
import cv2
import numpy as np
from fractions import Fraction
import time
from prawcore import NotFound
from PIL import Image, UnidentifiedImageError
import requests
import praw
import configparser
import concurrent.futures
import pyautogui
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QGroupBox, QProgressBar, QCheckBox, QComboBox,
    QSpinBox, QLabel, QLineEdit, QDialog, QDialogButtonBox, QMessageBox,
    QTabWidget, QFileDialog
)
from PyQt6.QtCore import Qt, QObject, QThread, pyqtSignal
from PyQt6.QtGui import QIcon


# GLOBAL VARIABLE
config = configparser.ConfigParser()
config.read('conf.ini')

reddit = praw.Reddit(client_id=config['REDDIT']['client_id'],
                     client_secret=config['REDDIT']['client_secret'],
                     user_agent='RedditWallpaperScraper')
images_dir = "" 

# GLOBAL FUNCTIONS 
def delete_files_in_directory(directory_path):
    try:
        files = os.listdir(directory_path)
        for file in files:
            file_path = os.path.join(directory_path, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        print("All files deleted successfully.")
    except OSError:
        print("Error occurred while deleting files.")

def internet_connection():
    try:
        requests.get("https://www.google.com", timeout=1)
        return True
    except requests.ConnectionError:
        return False

def sub_exists(sub):
    exists = True
    try:
        reddit.subreddits.search_by_name(sub, exact=True)
    except NotFound:
        exists = False
    return exists
    
process_manager = []

#THREADS

class Request():
    def __init__(self, sub, images_num, sort_method, nsfw):
        self.sub = sub
        self.images_num = images_num
        self.sort_method = sort_method
        self.nsfw = nsfw

class ResWorker(QThread):
    def __init__(self, width, height, ratio, minw, minh, type):
        super().__init__()
        self.width = width
        self.height = height
        self.ratio = ratio
        self.minw = minw
        self.minh = minh
        self.type = type
        self.deleted = 0 

    def start(self):
        if(self.height != 0):
            aspect = self.calculate_aspect(self.width, self.height)

        folder_dir = images_dir
        thresh = 130.0


        # RESOLUTION CHECK
        for images in os.listdir(folder_dir):
            if (images.endswith(".png") or images.endswith(".jpg") or images.endswith(".jpeg")):
                try:
                    img = PIL.Image.open(os.path.join(folder_dir, images))
                except PIL.UnidentifiedImageError:
                    continue
                image = cv2.imread(os.path.join(folder_dir, images))
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                fm = self.variance_of_laplacian(gray)
                if(fm < thresh):
                    img.close()
                    os.remove(os.path.join(folder_dir, images))
                    continue
                wid, hgt = img.size
                if(self.ratio == True):
                        if(self.calculate_aspect(wid, hgt) != aspect or wid <= hgt or wid < self.minw or hgt < self.minh):
                            self.deleted += 1
                            img.close()
                            os.remove(os.path.join(folder_dir, images))
                            continue
                else:
                        if(wid <= hgt or wid < self.minw or hgt < self.minh):
                            self.deleted += 1
                            img.close()
                            os.remove(os.path.join(folder_dir, images))
                            continue   
                # CHECK BRIGHT OR DARK
                
                if(self.type != "both"):
                    if(self.type == "bright" and self.isbright(image) or self.type == "dark" and not(self.isbright(image))):
                        continue
                    elif(self.type == "bright" and not(self.isbright(image)) or self.type == "dark" and self.isbright(image)):
                        img.close()
                        os.remove(os.path.join(folder_dir, images))
                

    # Credits to imneonizer(https://github.com/imneonizer) for his project 'How-to-find-if-an-image-is-bright-or-dark' (https://github.com/imneonizer/How-to-find-if-an-image-is-bright-or-dark)
    def isbright(self, image, dim=100, thresh=0.3):
         # Resize image to 10x10
        image = cv2.resize(image, (dim, dim))
        # Convert color space to LAB format and extract L channel
        L, _, _ = cv2.split(cv2.cvtColor(image, cv2.COLOR_BGR2LAB))
        # Normalize L channel by dividing all pixel values with maximum pixel value
        L = L/np.max(L)
        # Return True if mean is greater than thresh else False
        return np.mean(L) > thresh
    
    def variance_of_laplacian(self, image):
        return cv2.Laplacian(image, cv2.CV_64F).var()

    def get_deleted(self):
        return self.deleted
    
    def calculate_aspect(self, width: int, height: int):
        aspect_ratio_decimal = width / height
        
        base_ratios = {
            "4/3": 4 / 3,
            "16/9": 16 / 9,
            "16/10": 16 / 10
        }
        tolerance = 0.01
        
        for base_ratio, base_ratio_decimal in base_ratios.items():
            if abs(aspect_ratio_decimal - base_ratio_decimal) < tolerance:
                return str(base_ratio)
            
class worker1(QThread):
    def __init__(self, sub_list, prog_bar, msg_label, window_instance):
        super().__init__()
        self.sub_list = sub_list 
        self.prog_bar = prog_bar
        self.window_instance = window_instance
        self.msg_label = msg_label

    def run(self):
        self.startWorker()
        
    def startWorker(self):
        for request in self.sub_list:
                    self.prog_bar.setValue(0)
                    self.msg_label.setText("Downloading images!")
                    self.worker = Worker(request.sub, request.images_num, request.sort_method, request.nsfw, self.window_instance)
                    # Connect Signals
                    self.worker.image_download.connect(self.window_instance.update_bar)
                    self.worker.finished.connect(self.window_instance.worker_finished)
                    self.worker.start()
                    self.worker.wait()

# Credits to impshum(https://github.com/impshum) for his project 'Multithreaded-Reddit-Image-Downloader'(https://github.com/impshum/Multithreaded-Reddit-Image-Downloader)
class Worker(QThread):
    # SIGNALS
    completed = pyqtSignal()
    image_download = pyqtSignal(int)

    def __init__(self, sub_name, images_num, sort_method, nsfw_toggle, window_instance):
        super().__init__()
        self.sub = sub_name
        self.limit = images_num
        self.order = sort_method
        self.nsfw = nsfw_toggle
        self.window_instance = window_instance
        self.path = f'{images_dir}'
        self.reddit = praw.Reddit(client_id=config['REDDIT']['client_id'],
                                  client_secret=config['REDDIT']['client_secret'],
                                  user_agent='Multithreaded Reddit Image Downloader v2.0 (by u/impshum)')
        self.downloaded_count = 0
        

    def run(self):
        self.startScraper()
        self.window_instance.downloaded_images = self.get_downloaded_count()
        self.completed.emit()

    def get_downloaded_count(self):
        return self.downloaded_count

    def download(self, image):
        r = requests.get(image['url'])
        with open(image['fname'], 'wb') as f:
            f.write(r.content)
            self.downloaded_count += 1
            self.image_download.emit(self.downloaded_count)

    def startScraper(self):
        images = []
        try:
            go = 0
            if self.order == 'hot':
                submissions = self.reddit.subreddit(self.sub).hot(limit=None)
            elif self.order == 'top':
                submissions = self.reddit.subreddit(self.sub).top(limit=None)
            elif self.order == 'new':
                submissions = self.reddit.subreddit(self.sub).new(limit=None)

            for submission in submissions:
                if not submission.stickied and submission.over_18 == self.nsfw \
                        and submission.url.endswith(('jpg', 'jpeg', 'png')):
                    fname = self.path + \
                        re.search('.*\w/(.*)', submission.url).group(1)
                    if not os.path.isfile(fname):
                        images.append({'url': submission.url, 'fname': fname})
                        go += 1
                        if go >= self.limit:
                            break
            if len(images):
                if not os.path.exists(self.path):
                    os.makedirs(self.path)
                with concurrent.futures.ThreadPoolExecutor() as ptolemy:
                    ptolemy.map(self.download, images)
        except Exception as e:
            print(e)
# WINDOWS
class DialogYN(QDialog):
    def __init__(self, msg):
        super().__init__()

        self.setWindowTitle("HELLO!")

        q_btn = QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No

        self.buttonBox = QDialogButtonBox(q_btn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QVBoxLayout()
        message = QLabel(msg)
        self.layout.addWidget(message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)
    
'''class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        self.file = images_dir
        self.setWindowTitle("Settings")

        layout = QHBoxLayout()

        self.dir_label = QLabel()
        self.update_label()
        self.change_dir = QPushButton("Change")
        self.change_dir.clicked.connect(self.change_directory)

        layout.addWidget(self.dir_label)
        layout.addWidget(self.change_dir)

        self.setLayout(layout)

    def change_directory(self):
        self.file = str(QFileDialog.getExistingDirectory(
            self, "Select Directory") + "/")
        self.update_label()

    def update_label(self):
        global images_dir
        images_dir = self.file
        self.dir_label.setText("dir: " + self.file)'''

class Window(QWidget):
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        self.file = images_dir

        #STYLESHEET
        self.setStyleSheet("""
        QProgressBar {
            border: 1px solid lightgray;
            border-radius: 5px;
            text-align: center;
            background-color: white;
        }
        QProgressBar::chunk {
            background-color: green;
        }
                           
        QPushButton {
            border: 1px solid #c6c6c6;
            border-radius: 2px;
            text-align: center;
            background-color: lightgray;
        }
                           
        QPushButton:hover {
            background-color: lightblue;
        }
        
        QPushButton:pressed {
            border: 2px solid lightblue;
        }
                           
        QLineEdit {
            border: 1px solid lightgray;
            border-radius: 4px;
        }
                           
        QLineEdit:hover,
        QLineEdit:focused {
            border: 2px solid #d3d3d3;
        }
                           
        QSpinBox {
            border-radius: 2px;
            border: 1px solid #c6c6c6
        }
        
        """)

        

        # Initialize tab screen
        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.tabs.resize(300, 200)
  
        # Add tabs
        self.tabs.addTab(self.tab1, "General")
        self.tabs.addTab(self.tab3, "Check Res")
        self.tabs.addTab(self.tab2, "Settings")

        self.sub_list = []
  
        # GENERAL
        # Group Box
        self.groupbox = QGroupBox("")
        self.groupbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vbox = QVBoxLayout()
        self.groupbox.setLayout(self.vbox)

        self.tab1.layout = QVBoxLayout(self)
        self.subName = QHBoxLayout(self)

        # widgets
        # Generate Button
        self.generate = QPushButton("Generate", self)
        self.generate.clicked.connect(self.start_scraper)
        self.generate.setFixedHeight(40)

        self.add_button = QPushButton("Add", self)  
        self.add_button.clicked.connect(self.add_sub)

        # Subreddit Name 
        self.inputSub = QLineEdit(self)
        self.inputSub.setFixedWidth(150)
        self.inputSub.setFixedHeight(30)
        self.subName.addWidget(self.inputSub)
        self.subName.addWidget(self.add_button)

        # Images Number 
        self.images_num = QSpinBox(self)
        self.images_num.setRange(0, 5000)
        self.images_num.setFixedWidth(60)
        self.images_num.setFixedHeight(30)
        self.images_num.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Progress Bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Nsfw Toggle
        self.nsfw = QCheckBox("nsfw", self)

        # sort_method combo 
        self.sort_method = QComboBox(self)
        self.sort_method.setFixedWidth(50)
        self.sort_method.setFixedHeight(30)
        self.sort_method.addItem('top')
        self.sort_method.addItem('hot')
        self.sort_method.addItem('new')

        # Messages Label
        self.msg_label = QLabel("Insert Data")
        self.msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.msg_label.setFixedHeight(20)
        
        # layout
        # Group Box
        self.tab1.layout.addWidget(self.progress_bar)
        self.tab1.layout.addWidget(self.msg_label)

        self.tab1.layout.addWidget(self.groupbox)
        self.vbox.addLayout(self.subName)
        self.vbox.addWidget(self.images_num)
        self.vbox.addWidget(self.sort_method)
        self.vbox.addWidget(self.nsfw)
        self.vbox.addWidget(self.generate)
        
        self.tab1.layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.tab1.setLayout(self.tab1.layout)
        

        # SETTINGS

        self.dir_layout = QVBoxLayout(self)
        self.tab2.layout = QVBoxLayout(self)
        
        # widgets 
        # Delete All Button
        self.delete_all = QPushButton("Delete all images")
        self.delete_all.clicked.connect(self.delete_images)

        # Open Dir Button
        self.openDir = QPushButton("Open Folder", self)
        self.openDir.setIcon(QIcon('folder.png'))
        self.openDir.clicked.connect(self.open_dir)
    

        # Directory Label
        self.dir_label = QLabel()
        self.update_label()
        # Change Dir Button
        self.change_dir = QPushButton("Change")
        self.change_dir.clicked.connect(self.change_directory)

        self.dir_layout.addWidget(self.dir_label)
        self.dir_layout.addWidget(self.change_dir)
        
        
        # layout
        self.tab2.layout.addWidget(self.dir_label)
        self.tab2.layout.addLayout(self.dir_layout)
        self.tab2.layout.addWidget(self.openDir)
        self.tab2.layout.addWidget(self.delete_all)

        self.tab2.setLayout(self.tab2.layout)

        # CHECK RES
        self.width_layout = QHBoxLayout(self)
        self.height_layout = QHBoxLayout(self)
        self.tab3.layout = QVBoxLayout(self)
        
        # widgets
        # Run Automatically 
        self.to_run_auto = QCheckBox("Run After Generating", self)

        # Run Button
        self.run_button= QPushButton("Run", self)
        self.run_button.clicked.connect(self.run_rescheck)
        self.run_button.setFixedHeight(40)

        # Check Aspect Ratio
        self.check_ar = QCheckBox("Check Aspect Ratio", self)

        # Use own resolution
        self.use_screenres = QCheckBox("Use Display Resolution", self)
        self.use_screenres.stateChanged.connect(self.status_changed)

        # msg label
        self.res_msglabel = QLabel("")

        # dark bright or both  
        self.type_selector = QComboBox(self)
        self.type_selector.setFixedWidth(50)
        self.type_selector.setFixedHeight(30)
        self.type_selector.addItem('both')
        self.type_selector.addItem('bright')
        self.type_selector.addItem('dark')

        size = pyautogui.size()
        # Input Width
        width = str(size[0])
        self.width_input = QLineEdit(width, self)
        self.width_label = QLabel("width:")
        self.width_layout.addWidget(self.width_label)
        self.width_layout.addWidget(self.width_input)
        
        
        # Input Height
        height = str(size[1])
        self.height_input = QLineEdit(height, self)
        self.height_label = QLabel("height:")
        self.height_layout.addWidget(self.height_label)
        self.height_layout.addWidget(self.height_input)

        # msg label
        self.msg_labelres = QLabel("a")
        self.msg_labelres.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.msg_labelres.setFixedHeight(20)


        # layout 
        
        self.tab3.layout.addWidget(self.msg_labelres)
        self.tab3.layout.addWidget(self.to_run_auto)
        self.tab3.layout.addWidget(self.check_ar)
        self.tab3.layout.addWidget(self.use_screenres)
        self.tab3.layout.addLayout(self.width_layout)
        self.tab3.layout.addLayout(self.height_layout)
        self.tab3.layout.addWidget(self.type_selector)
        self.tab3.layout.addWidget(self.run_button)
        self.tab3.setLayout(self.tab3.layout)

        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

        

    # Buttons Functions 
    def add_sub(self):
        sub = self.inputSub.text()
        images_num = self.images_num.value()
        sort_method = str(self.sort_method.currentText())
        nsfw_toggle = self.nsfw.isChecked()
        if (images_num == 0 or len(sub) == 0):
                self.msg_label.setText("Inserted Data are not valid")
                return None
        if(sub_exists(sub) == False):
            self.msg_label.setText("Subreddit name not valid")
        else:
            request = Request(sub, images_num, sort_method, nsfw_toggle)
            self.sub_list.append(request)
            self.msg_label.setText("Request Added to Queue")

    def open_dir(self):
        try:
            os.startfile(images_dir)
        except:
            self.msg_label.setText("Cannot find the requested directory")
            raise

    def delete_images(self):
        button = QMessageBox.question(self, "Confirm Deletion", "Delete All images in:\n" + images_dir + " ?")
        if button == QMessageBox.StandardButton.Yes:
            delete_files_in_directory(images_dir)
    
    def change_directory(self):
        self.file = str(QFileDialog.getExistingDirectory(
            self, "Select Directory") + "/")
        self.update_label()

    def start_scraper(self):
        if (internet_connection() and len(self.sub_list) != 0):
            # Check if there are other processes working 
            
            '''self.progress_bar.setValue(0)
            images_num = self.images_num.value()
            sub_name = str(self.inputSub.text())
            sort_method = str(self.sort_method.currentText())
            nsfw_toggle = self.nsfw.isChecked()
            

            # check if data has been entered
            if (images_num == 0 or len(sub_name) == 0):
                self.msg_label.setText("Inserted Data are not valid")
                return None
            self.progress_bar.setMaximum(images_num)

            # check if the subreddit name entered corrispond to an existent subreddit 
            if (sub_exists(sub_name) == False):
                self.msg_label.setText("Subreddit name not valid")
                return None'''
            _len = 0

            if len(images_dir) <= 3:
                self.msg_label.setText("No directory selected!")

            for request in self.sub_list:

                _len += request.images_num

            self.progress_bar.setMaximum(_len)
            
            #self.generate.setEnabled(False)

            self.worker = worker1(self.sub_list, self.progress_bar, self.msg_label, self)
            self.worker.start()
        elif(len(self.sub_list) <= 0):
            self.msg_label.setText("Add requests to generate")
        else: # Network not working 
            self.msg_label.setText("Connect To a Network And Retry!")

    # More Functions
    
    def status_changed(self, value):
        state = Qt.CheckState(value)
        if state == Qt.CheckState.Checked:
            size = pyautogui.size()
            self.width_input.setText(str(size[0]))
            self.height_input.setText(str(size[1]))
            self.width_label.setEnabled(False)
            self.width_input.setEnabled(False)
            self.height_input.setEnabled(False)
        else:
            self.width_input.setEnabled(True)
            self.height_input.setEnabled(True)


    def run_rescheck(self):
        width = int(self.width_input.text())
        height = int(self.height_input.text())
        ratio = self.check_ar.isChecked()
        _type = self.type_selector.currentText()
        minw = 1280
        minh = 720
        self.res_check = ResWorker(width, height, ratio, minw, minh, _type)
        self.res_check.start()
        self.res_check.finished.connect(self.res_checkfin)

    def res_checkfin(self):
        deleted = self.res_check.get_deleted()
        self.msg_labelres.setText("Deleted Images: " + deleted)


    def update_label(self):
        global images_dir
        images_dir = self.file
        self.dir_label.setText("dir:\n" + self.file)

    def worker_finished(self):
        self.msg_label.setText("Downloaded: " + str(self.downloaded_images) + "/" + str(self.images_num.value()))
        self.generate.setEnabled(True)
        if (self.progress_bar.value() < self.progress_bar.maximum()):
            self.progress_bar.setValue(self.progress_bar.maximum())

        self.worker.quit()
        self.worker.wait()
        
        if(self.to_run_auto.isChecked()):
            self.tabs.setCurrentIndex(1)
            self.run_rescheck()

    def update_bar(self, value):
        #self.msg_label.setText("Downloaded: " + str(value) + "/" + (self.images_num.value()))
        if(self.progress_bar.value() < self.progress_bar.maximum()):
            self.progress_bar.setValue(self.progress_bar.value() + 1)

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RedditImageScraper")
        self.setFixedSize(300, 400)
        self.tab = Window(self)
        self.setCentralWidget(self.tab)

        

       
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = App()
    window.show()
    if len(images_dir) == 0:
            window.tab.change_directory()
    sys.exit(app.exec())

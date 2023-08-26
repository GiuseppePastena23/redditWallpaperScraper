from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6 import QtCore
from PyQt6.QtCore import QObject, QThread, pyqtSignal
import sys
import pdb
import os
from fractions import Fraction
from prawcore import NotFound
import math
import PIL
from PIL import Image
from os import listdir
import argparse
import re
import requests
import praw
import configparser
import concurrent.futures
import argparse
from PIL import UnidentifiedImageError
from PyQt6.QtGui import QIcon
import pyautogui

# GLOBAL VARIABLE
config = configparser.ConfigParser()
config.read('conf.ini')

reddit = praw.Reddit(client_id=config['REDDIT']['client_id'],
                     client_secret=config['REDDIT']['client_secret'],
                     user_agent='RedditWallpaperScraper')
images_dir = "C:/Users/giuse/Desktop/redditWallpaperScraper/images/" 

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
        response = requests.get("https://www.google.com", timeout=1)
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

class resWorker(QThread):
    def __init__(self, width, height, ratio, minw, minh):
        self.width = width
        self.height = height
        self.ratio = ratio
        self.minw = minw
        self.minh = minh

    def start(self):
        deleted = 0
        if(self.height != 0):
            aspect = self.calculate_aspect(self.width, self.height)
        """self.minh = 720
        if(aspect == 7):
            self.minw = 960
        if(aspect == 25):
            self.minw = 1280"""
        folder_dir = images_dir
        for images in os.listdir(folder_dir):
            if (images.endswith(".png") or images.endswith(".jpg") or images.endswith(".jpeg")):
                try:
                    img = PIL.Image.open(os.path.join(folder_dir, images))
                except PIL.UnidentifiedImageError:
                    continue
                wid, hgt = img.size
                if(self.ratio == True):
                        if(self.calculate_aspect(wid, hgt) != aspect or wid <= hgt or wid < self.minw or hgt < self.minh):
                            deleted += 1
                            img.close()
                            os.remove(os.path.join(folder_dir, images))
                            continue
                else:
                        if(wid <= hgt or wid < self.minw or hgt < self.minh):
                            deleted += 1
                            img.close()
                            os.remove(os.path.join(folder_dir, images))
                            continue   
    
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
        
class Worker(QThread):
    # SIGNALS
    completed = pyqtSignal()
    image_download = pyqtSignal(int)

    def __init__(self, subName, imagesNum, sortMethod, nsfw_toggle, window_instance):
        super().__init__()
        self.sub = subName
        self.limit = imagesNum
        self.order = sortMethod
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
                        re.search('(?s:.*)\w/(.*)', submission.url).group(1)
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

        QBtn = QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No

        self.buttonBox = QDialogButtonBox(QBtn)
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
        self.q = Queue()

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
  
        # GENERAL
        # Group Box
        self.groupbox = QGroupBox("")
        self.groupbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vbox = QVBoxLayout()
        self.groupbox.setLayout(self.vbox)

        self.tab1.layout = QVBoxLayout(self)

        # widgets
        # Generate Button
        self.generate = QPushButton("Generate", self)
        self.generate.clicked.connect(self.start_scraper)
        self.generate.setFixedHeight(40)

        # Subreddit Name 
        self.inputSub = QLineEdit(self)
        self.inputSub.setFixedWidth(150)

        # Images Number 
        self.imagesNum = QSpinBox(self)
        self.imagesNum.setRange(0, 5000)
        self.imagesNum.setFixedWidth(60)
        self.imagesNum.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Progress Bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Nsfw Toggle
        self.nsfw = QCheckBox("nsfw", self)

        # Sort Method combo 
        self.sort_method = QComboBox(self)
        self.sort_method.setFixedWidth(50)
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
        self.vbox.addWidget(self.inputSub)
        self.vbox.addWidget(self.imagesNum)
        self.vbox.addWidget(self.sort_method)
        self.vbox.addWidget(self.nsfw)
        self.vbox.addWidget(self.generate)
        
        self.tab1.setLayout(self.tab1.layout)

        # SETTINGS
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

        # layout
        self.tab2.layout.addWidget(self.dir_label)
        self.tab2.layout.addWidget(self.change_dir)
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

        # Check Aspect Ratio
        self.check_ar = QCheckBox("Check Aspect Ratio", self)

        # Use own resolution
        self.use_screenres = QCheckBox("Use Display Resolution", self)
        self.use_screenres.stateChanged.connect(self.status_changed)

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


        # layout 
        
        self.tab3.layout.addWidget(self.to_run_auto)
        self.tab3.layout.addWidget(self.check_ar)
        self.tab3.layout.addWidget(self.use_screenres)
        self.tab3.layout.addLayout(self.width_layout)
        self.tab3.layout.addLayout(self.height_layout)
        self.tab3.layout.addWidget(self.run_button)
        self.tab3.setLayout(self.tab3.layout)

        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

    # Buttons Functions 
    def open_dir(self):
        try:
            os.startfile(images_dir)
        except:
            self.msg_label.setText("Cannot find the requested directory")

    def delete_images(self):
        button = QMessageBox.question(self, "Confirm Deletion", "Delete All images in:\n" + images_dir + " ?")
        if button == QMessageBox.StandardButton.Yes:
            delete_files_in_directory(images_dir)
    
    def change_directory(self):
        self.file = str(QFileDialog.getExistingDirectory(
            self, "Select Directory") + "/")
        self.update_label()

    def start_scraper(self):
        if (internet_connection()):
            # Check if there are other processes working 
            
            self.progress_bar.setValue(0)
            imagesNum = self.imagesNum.value()
            subName = str(self.inputSub.text())
            sortMethod = str(self.sort_method.currentText())
            nsfw_toggle = self.nsfw.isChecked()
            
            if(not self.q.isEmpty()):
                self.q.AddItem(subName)
            

            # check if data has been entered
            if (imagesNum == 0 or len(subName) == 0):
                self.msg_label.setText("Inserted Data are not valid")
                return None
            self.progress_bar.setMaximum(imagesNum)

            # check if the subreddit name entered corrispond to an existent subreddit 
            if (sub_exists(subName) == False):
                self.msg_label.setText("Subreddit name not valid")
                return None
            
            # Everything Good
            self.msg_label.setText("Downloading images...")
            #self.generate.setEnabled(False)
            self.worker = Worker(subName, imagesNum, sortMethod, nsfw_toggle, self)
            self.worker.start()
            # Connect Signals
            self.worker.image_download.connect(self.update_bar)
            self.worker.finished.connect(self.worker_finished)
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
        minw = 1280
        minh = 720
        res_check = resWorker(width, height, ratio, minw, minh)
        res_check.start()

    def update_label(self):
        global images_dir
        images_dir = self.file
        self.dir_label.setText("dir:\n" + self.file)
        self.dir_label.adjustSize()

    def worker_finished(self):
        self.msg_label.setText("Downloaded: " + str(self.downloaded_images) + "/" + str(self.imagesNum.value()))
        self.generate.setEnabled(True)
        if (self.progress_bar.value() < self.progress_bar.maximum()):
            self.progress_bar.setValue(self.progress_bar.maximum())
        if(self.to_run_auto.isChecked()):
            self.run_rescheck()

    def update_bar(self, value):
        if(self.progress_bar.value() < self.progress_bar.maximum()):
            self.progress_bar.setValue(value)

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
    sys.exit(app.exec())

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6 import QtCore
from PyQt6.QtCore import QObject, QThread, pyqtSignal
import sys
import pdb
import os
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
    
class Worker(QThread):
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
            #self.window_instance.update_bar(self.get_downloaded_count())
            
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
   
class SettingsWindow(QWidget):
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
        self.dir_label.setText("dir: " + self.file)
    
class Window(QWidget):
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        self.file = images_dir

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
  
        # FIRST TAB
        self.tab1.layout = QVBoxLayout(self)

        # WIDGETS
        # Generate Button
        self.generate = QPushButton("Generate", self)
        self.generate.clicked.connect(self.start_scraper)

        # Subreddit Name 
        self.inputSub = QLineEdit(self)

        # Images Number 
        self.imagesNum = QSpinBox(self)
        self.imagesNum.setRange(0, 5000)

        # Progress Bar
        self.current_value = 0
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Nsfw Toggle
        self.nsfw = QCheckBox("nsfw", self)

        # Sort Method combo 
        self.sort_method = QComboBox(self)
        self.sort_method.addItem('top')
        self.sort_method.addItem('hot')
        self.sort_method.addItem('new')

        # Open Dir Button
        self.openDir = QPushButton("Open Folder", self)
        self.openDir.setIcon(QIcon('folder.png'))
        self.openDir.clicked.connect(self.open_dir)

        # Messages Label
        self.msg_label = QLabel("Insert Data")
        self.msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Delete All Button
        self.delete_all = QPushButton("Delete all images")
        self.delete_all.clicked.connect(self.delete_images)

        # Layout 
        self.tab1.layout.addWidget(self.generate)
        self.tab1.layout.addWidget(self.imagesNum)
        self.tab1.layout.addWidget(self.inputSub)
        self.tab1.layout.addWidget(self.progress_bar)
        self.tab1.layout.addWidget(self.nsfw)
        self.tab1.layout.addWidget(self.sort_method)
        self.tab1.layout.addWidget(self.openDir)
        self.tab1.layout.addWidget(self.msg_label)
        self.tab1.layout.addWidget(self.delete_all)
    
        self.tab1.setLayout(self.tab1.layout)

        # SECOND TAB
        self.tab2.layout = QHBoxLayout(self)
        
        #WIDGETS
        # Directory Label
        self.dir_label = QLabel()
        self.update_label()
        # Change Dir Button
        self.change_dir = QPushButton("Change")
        self.change_dir.clicked.connect(self.change_directory)

        # Layout 
        self.tab2.layout.addWidget(self.dir_label)
        self.tab2.layout.addWidget(self.change_dir)
        self.tab2.setLayout(self.tab2.layout)

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
            self.progress_bar.setValue(0)
            imagesNum = self.imagesNum.value()
            subName = str(self.inputSub.text())
            sortMethod = str(self.sort_method.currentText())
            nsfw_toggle = self.nsfw.isChecked()

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
            self.generate.setEnabled(False)
            self.worker = Worker(subName, imagesNum, sortMethod, nsfw_toggle, self)
            self.worker.start()
            # Connect Signals
            self.worker.image_download.connect(self.update_bar)
            self.worker.finished.connect(self.worker_finished)
        else: # Network not working 
            self.msg_label.setText("Connect To a Network And Retry!")

    # More Functions

    def update_label(self):
        global images_dir
        images_dir = self.file
        self.dir_label.setText("dir: " + self.file)

    def worker_finished(self):
        self.msg_label.setText("Downloaded: " + str(self.downloaded_images) + "/" + str(self.imagesNum.value()))
        self.generate.setEnabled(True)
        if (self.progress_bar.value() < self.progress_bar.maximum()):
            self.progress_bar.setValue(self.progress_bar.maximum())

    def update_bar(self, value):
        if(self.progress_bar.value() < self.progress_bar.maximum()):
            self.progress_bar.setValue(value)

class App(QMainWindow):

    def __init__(self):
        super().__init__()
        
        
        self.setWindowTitle("RedditImageScraper")
        self.resize(350, 400)
        self.tab = Window(self)
        self.setCentralWidget(self.tab)

        # self.tab_widget = MyTabWidget(self)
        '''self.generate = QPushButton("Generate", self)
        self.generate.clicked.connect(self.button_click)

        self.inputSub = QLineEdit(self)

        self.imagesNum = QSpinBox(self)
        self.imagesNum.setRange(0, 5000)

        self.current_value = 0
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.nsfw = QCheckBox("nsfw", self)

        self.sort_method = QComboBox(self)
               

        self.sort_method.addItem('top')
        self.sort_method.addItem('hot')
        self.sort_method.addItem('new')

        self.openDir = QPushButton("Open Folder", self)
        self.openDir.setIcon(QIcon('folder.png'))
        self.openDir.clicked.connect(self.open_dir)

        self.msg_label = QLabel("Insert Data")
        self.msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.setting_btn = QPushButton("Settings")
        self.setting_btn.clicked.connect(self.open_settings)

        self.delete_all = QPushButton("Delete all images")
        self.delete_all.clicked.connect(self.delete_images)'''

        # layout.addWidget(self.tab_widget)
        '''layout.addWidget(self.setting_btn)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.msg_label)
        layout.addWidget(self.nsfw)
        layout.addWidget(self.sort_method)
        layout.addWidget(self.imagesNum)
        layout.addWidget(self.inputSub)
        layout.addWidget(self.generate)
        layout.addWidget(self.openDir)
        layout.addWidget(self.delete_all)'''
       
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())

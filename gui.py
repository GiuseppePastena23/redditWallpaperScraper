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

config = configparser.ConfigParser()
config.read('conf.ini')

reddit = praw.Reddit(client_id=config['REDDIT']['client_id'],
                     client_secret=config['REDDIT']['client_secret'],
                     user_agent='RedditWallpaperScraper')
images_dir = "C:/Users/giuse/Desktop/redditWallpaperScraper/images/" 


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


class Worker(QThread):
    def __init__(self, subName, imagesNum, sortMethod, nsfw_toggle, window_instance):
        super().__init__()
        self.subName = subName
        self.imagesNum = imagesNum
        self.sortMethod = sortMethod
        self.nsfw_toggle = nsfw_toggle
        self.window_instance = window_instance
        finished = QtCore.pyqtSignal()

    def run(self):
        scraper = redditImageScraper(
            self.subName, self.imagesNum, self.sortMethod, self.nsfw_toggle, self.window_instance)

        scraper.start()

        self.window_instance.downloaded_images = scraper.get_downloaded_count()
        self.finished.emit()


class redditImageScraper:
    def __init__(self, sub, limit, order, nsfw, window_instance):
        self.sub = sub
        self.limit = limit
        self.order = order
        self.nsfw = nsfw
        self.window_instance = window_instance
        self.path = f'{images_dir}'
        self.reddit = praw.Reddit(client_id=config['REDDIT']['client_id'],
                                  client_secret=config['REDDIT']['client_secret'],
                                  user_agent='Multithreaded Reddit Image Downloader v2.0 (by u/impshum)')
        self.downloaded_count = 0

    def get_downloaded_count(self):
        return self.downloaded_count

    def download(self, image):
        r = requests.get(image['url'])
        with open(image['fname'], 'wb') as f:
            f.write(r.content)
            #self.window_instance.update_bar(self.get_downloaded_count())
            self.downloaded_count += 1

    def start(self):
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


"""class MyTabWidget(QWidget):
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)
  
        # Initialize tab screen
        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.tabs.resize(300, 200)
  
        # Add tabs
        self.tabs.addTab(self.tab1, "General")
        self.tabs.addTab(self.tab3, "Settings")
  
        # Create first tab
        self.tab1.layout = QVBoxLayout(self)
        self.l = QLabel()
        self.l.setText("This is the first tab")
        self.tab1.layout.addWidget(self.l)
        self.tab1.setLayout(self.tab1.layout)
  
        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)"""


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

    def __init__(self):
        super().__init__()
        self.downloaded_images = 9999
        self.setWindowTitle("RedditImageScraper")

        layout = QVBoxLayout()

        # self.tab_widget = MyTabWidget(self)
        self.generate = QPushButton("Generate", self)
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
        self.delete_all.clicked.connect(self.delete_images)

        # layout.addWidget(self.tab_widget)
        layout.addWidget(self.setting_btn)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.msg_label)
        layout.addWidget(self.nsfw)
        layout.addWidget(self.sort_method)
        layout.addWidget(self.imagesNum)
        layout.addWidget(self.inputSub)
        layout.addWidget(self.generate)
        layout.addWidget(self.openDir)
        layout.addWidget(self.delete_all)

        

        self.setLayout(layout)

    def delete_images(self):
        delete_files_in_directory(images_dir)

    def open_settings(self):
        self.window = SettingsWindow()
        self.window.show()

    def button_click(self):
        if (internet_connection()):
            self.progress_bar.setValue(0)
            self.generate.setEnabled(False)
            imagesNum = self.imagesNum.value()
            subName = str(self.inputSub.text())
            sortMethod = str(self.sort_method.currentText())
            nsfw_toggle = self.nsfw.isChecked()
            if (imagesNum == 0 or len(subName) == 0):
                self.msg_label.setText("Inserted Data are not valid")
                self.generate.setEnabled(True)
                return None
            self.progress_bar.setMaximum(imagesNum)
            if (sub_exists(subName) == False):
                self.msg_label.setText("Subreddit name not valid")
                self.generate.setEnabled(True)
                return None
            self.msg_label.setText("Downloading images...")
            self.worker = Worker(subName, imagesNum, sortMethod, nsfw_toggle, self)

            
            self.worker.start()
            # downloaded_count = scraper.get_downloaded_count()
            # self.msg_label.setText("Downloaded " + str(downloaded_count) + " imag
            self.worker.finished.connect(self.worker_finished)
            
            #if self.worker_finished and self.downloaded_images < imagesNum:
            #    self.msg_label.setText("The number of images requested exceeded the available images in r/" + subName)
        else:
            self.msg_label.setText("Connect To Internet And Retry!")

    def worker_finished(self):
        self.msg_label.setText("Downloaded: " + str(self.downloaded_images) + "/" + str(self.imagesNum.value()))
        self.generate.setEnabled(True)
        if (self.progress_bar.value() < self.progress_bar.maximum()):
            self.progress_bar.setValue(self.progress_bar.maximum())

    def update_bar(self, value):
            try:
                self.progress_bar.setValue(value)
            except:
                return None

    def open_dir(self):
        try:
            os.startfile(images_dir)
        except:
            self.msg_label.setText("Cannot find the requested directory")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())

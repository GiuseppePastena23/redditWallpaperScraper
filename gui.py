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

config = configparser.ConfigParser()
config.read('conf.ini')

reddit =  praw.Reddit(client_id=config['REDDIT']['client_id'],
                                  client_secret=config['REDDIT']['client_secret'],
                                  user_agent='RedditWallpaperScraper')


def sub_exists(sub):
    exists = True
    try:
        reddit.subreddits.search_by_name(sub, exact=True)
    except NotFound:
        exists = False
    return exists

class Worker(QThread):
    def __init__(self, subName, imagesNum, sortMethod, nsfw_toggle):
        super().__init__()
        self.subName = subName
        self.imagesNum = imagesNum
        self.sortMethod = sortMethod
        self.nsfw_toggle = nsfw_toggle
        finished = QtCore.pyqtSignal()
        

    def run(self):
        scraper = redditImageScraper(self.subName, self.imagesNum, self.sortMethod, self.nsfw_toggle)
        scraper.start()
        
        self.finished.emit()

    

class redditImageScraper:
    def __init__(self, sub, limit, order, nsfw):
        self.sub = sub
        self.limit = limit
        self.order = order
        self.nsfw = nsfw
        self.path = f'images/'
        self.reddit = praw.Reddit(client_id=config['REDDIT']['client_id'],
                                  client_secret=config['REDDIT']['client_secret'],
                                  user_agent='Multithreaded Reddit Image Downloader v2.0 (by u/impshum)')
        self.downloaded_count = 0
        image_downloaded = QtCore.pyqtSignal()

    def get_downloaded_count(self):
        return self.downloaded_count

    def download(self, image):
        r = requests.get(image['url'])
        with open(image['fname'], 'wb') as f:
            f.write(r.content)
            self.image_downloaded.emit()
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
                    fname = self.path + re.search('(?s:.*)\w/(.*)', submission.url).group(1)
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
    


class Window(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("RedditImageScraper")

        layout = QVBoxLayout()
    
        self.generate = QPushButton("Generate", self)
        self.generate.clicked.connect(self.button_click)
        
        
        self.inputSub = QLineEdit(self)
        

        self.imagesNum = QSpinBox(self)
        self.imagesNum.setRange(0, 5000)

        self.current_value = 0
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        

        self.nsfw = QCheckBox("nsfw",self)
        

        self.sort_method = QComboBox(self)
        self.sort_method.addItem('top')
        self.sort_method.addItem('hot')
        self.sort_method.addItem('new')
        

        self.msg_label = QLabel("Insert Data")
        self.msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.progress_bar)
        layout.addWidget(self.msg_label)
        layout.addWidget(self.nsfw)
        layout.addWidget(self.sort_method)
        layout.addWidget(self.imagesNum)
        layout.addWidget(self.inputSub)
        layout.addWidget(self.generate)


        self.setLayout(layout)
                

    def button_click(self):
        
        imagesNum = self.imagesNum.value()
        subName = str(self.inputSub.text())
        sortMethod = str(self.sort_method.currentText())
        nsfw_toggle = self.nsfw.isChecked()
        if(imagesNum == 0 or len(subName) == 0):
            self.msg_label.setText("Inserted Data are not valid")
            return None
        self.progress_bar.setRange(0, imagesNum)
        if(sub_exists(subName) == False):
           self.msg_label.setText("Subreddit name not valid")
           return None
        self.msg_label.setText("Downloading images...")
        self.worker = Worker(subName, imagesNum, sortMethod, nsfw_toggle)
    
        self.worker.start()
        #downloaded_count = scraper.get_downloaded_count()
        #self.msg_label.setText("Downloaded " + str(downloaded_count) + " imag
        pdb.set_trace()
        self.scraper.image_downloaded.connect(self.update_bar)
        self.worker.finished.connect(self.worker_finished)
        self.update_bar()

    def worker_finished(self):
        self.msg_label.setText("Done!")

    def update_bar(self):
        self.progress_bar.setValue(self.progress_bar.value() + 50)
        
        
                
        


app = QApplication(sys.argv)
window = Window()
window.show()
sys.exit(app.exec())

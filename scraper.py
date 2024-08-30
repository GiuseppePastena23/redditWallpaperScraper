import re
import praw 
from dotenv import load_dotenv
from prawcore import NotFound
import os
import Query
import concurrent.futures
import scraper
from loguru import logger
import requests

load_dotenv()

CLIENT_ID = os.getenv('CLIENT_ID', '')
CLIENT_SECRET = os.getenv('CLIENT_SECRET', '')
reddit = praw.Reddit(client_id=CLIENT_ID,
                     client_secret=CLIENT_SECRET,
                     user_agent='RedditWallpaperScraper')

images_dir = os.getenv('DIR', 'images/')
logger.debug(f"images_dir set to: {images_dir}")

class Scraper:
    def __init__(self, sub, limit, order, nsfw=False):
        self.sub = sub
        self.limit = limit
        self.order = order
        self.nsfw = nsfw
        self.path = f'{images_dir}/{sub}/'
        self.reddit = reddit  # Assume `reddit` is initialized elsewhere
        
    
    def start(self):
        try:
            images = self.get_images() 
            if len(images):
                self.create_directory()
                self.download_images(images)
        except Exception as e:
            print(e)
    
    def get_images(self):
        images = []
        submissions = self.get_submissions()

        for submission in submissions:
            if (not submission.stickied and 
                submission.url.endswith(('jpg', 'jpeg', 'png')) and 
                submission.over_18 == self.nsfw):
                fname = self.build_file_name(submission.url)
                if not os.path.isfile(fname):
                    images.append({'url': submission.url, 'fname': fname})
        
        return images
    
    def get_submissions(self):
        submissions = []
        last_submission = None

        fetch_methods = {
            'hot': self.reddit.subreddit(self.sub).hot, 
            'top': self.reddit.subreddit(self.sub).top,
            'new': self.reddit.subreddit(self.sub).new,
        }

        fetch_method = fetch_methods.get(self.order)

        while len(submissions) < self.limit:
            new_submissions = list(fetch_method(limit=None, params={"after": last_submission}))

            if not new_submissions:
                break 

            submissions.extend(new_submissions)
            last_submission = submissions[-1].fullname 
            
            if len(submissions) >= self.limit:
                submissions = submissions[:self.limit]
                break

        return submissions
    
    def build_file_name(self, url):
        file_name = re.search(r'.*/(.*)', url).group(1)
        return os.path.join(self.path, file_name)
    
    def create_directory(self):
        if not os.path.exists(self.path):
            os.makedirs(self.path)
            
    def download_images(self, images):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(self.download, images)
            
    def download(self, image):
        r = requests.get(image['url'])
        with open(image['fname'], 'wb') as f:
            f.write(r.content)
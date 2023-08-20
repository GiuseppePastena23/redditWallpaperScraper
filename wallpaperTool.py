from prawcore import NotFound
import os
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
from alive_progress import alive_bar
import time

config = configparser.ConfigParser()
config.read('conf.ini')

reddit =  praw.Reddit(client_id=config['REDDIT']['client_id'],
                                  client_secret=config['REDDIT']['client_secret'],
                                  user_agent='RedditWallpaperScraper')

def get_yes_or_no(prompt):
    while True:
        response = input(prompt + " (Y/N): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Invalid input. Please enter 'Y' or 'N'.")

def calculate_aspect(width: int, height: int) -> str:
        def gcd(a, b):
            """The GCD (greatest common divisor) is the highest number that evenly divides both width and height."""
            return a if b == 0 else gcd(b, a % b)

        r = gcd(width, height)
        x = int(width / r)
        y = int(height / r)

        return x+y
            
class resolutionCheck:
    def __init__(self, width, height, ratio, minw, minh):
        self.width = width
        self.height = height
        self.ratio = ratio
        self.minw = minw
        self.minh = minh

    def start(self):
        deleted = 0
        if(self.height != 0):
                aspect = calculate_aspect(self.width, self.height)
        folder_dir = str(config['DIR']['folderDir'])
        for images in os.listdir(folder_dir):
            if (images.endswith(".png") or images.endswith(".jpg") or images.endswith(".jpeg")):
                try:
                    img = PIL.Image.open(os.path.join(folder_dir, images))
                except PIL.UnidentifiedImageError:
                    continue
                wid, hgt = img.size
                if(self.ratio == True):
                        if(calculate_aspect(wid, hgt) != aspect or wid <= hgt or wid < self.minw or hgt < self.minh):
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
        print('deleted images: ' + str(deleted))
        a = input("Press Enter")

class redditImageScraper:
    def __init__(self, sub, limit, order, nsfw=False):
        self.sub = sub
        self.limit = limit
        self.order = order
        self.nsfw = nsfw
        self.path = f'images/'
        self.reddit = praw.Reddit(client_id=config['REDDIT']['client_id'],
                                  client_secret=config['REDDIT']['client_secret'],
                                  user_agent='Multithreaded Reddit Image Downloader v2.0 (by u/impshum)')

    def download(self, image):
        r = requests.get(image['url'])
        with open(image['fname'], 'wb') as f:
            f.write(r.content)

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

def quitProgram():
    print("Thanks for using this program!")

def clean_up():
    os.system('cls')
    
    if(get_yes_or_no("Check Aspect Ratio?")):
       ar = True
    else:
       ar = False

    minWid = 1366
    minHgt = 768

    if(get_yes_or_no("Want to change minimun width and height?:")):
       minWid = int(input("Enter minimum width"))
       minHgt = int(input("Enter minimum height"))

    res = resolutionCheck(int(config['RESOLUTION']['width']), int(config['RESOLUTION']['height']),ar, minWid, minHgt)
    res.start()

def sort_method():
    sort_mode = int(input("Select the corresponding number:\n1.New\n2.Hot\n3.Top\n"))
    if sort_mode in range(0, 4):
        if sort_mode == 1:
            return "new"
        elif sort_mode == 2:
            return "hot"
        else:
            return "top"
    else:
        print("Number Not Valid!")
        sort_method()
        

def sub_exists(sub):
    exists = True
    try:
        reddit.subreddits.search_by_name(sub, exact=True)
    except NotFound:
        exists = False
    return exists

def main():
    # MENU
    print("Reddit Wallpaper Scraper!\n")

    # ENTER SUBREDDITS NAMES
    subreddit_list = []
    while True:
        new_subreddit = str(input("Enter subreddit name (Q to finish): "))
        if new_subreddit.upper() != 'Q':
            if sub_exists(new_subreddit):
                subreddit_list.append(new_subreddit)
            else:
                print("Subreddit name not found!")
        else:
            break

    # ENTER HOW MANY POSTS TO SCRAPE
    images_number = input("Enter how many images to download: ")

    # SORTING METHOD
    sort_mode = sort_method()

    #NSFW ON/OFF
    nsfw = False
    nsfw_mode = str(input("Find NSFW images?(y/N)"))
    if nsfw_mode == 'Y' or nsfw_mode == 'y':
        nsfw = True
    elif nsfw_mode == 'N' or nsfw_mode == 'n':
        nsfw = False
                    
    os.system('cls')
    for x in range(len(subreddit_list)):
        scraper = redditImageScraper(str(subreddit_list[x]), int(images_number), str(sort_mode), nsfw)
        scraper.start()
        
    do_clean = input("Let the program select which images can be removed?(Y/N)")
    if do_clean == 'Y' or do_clean == 'y':
        clean_up()
    elif do_clean == 'N' or do_clean == 'n':
        quitProgram()
    
    
if __name__ == '__main__':
    main()


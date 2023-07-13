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


Image.MAX_IMAGE_PIXELS = None

def calculate_aspect(width: int, height: int) -> str:
        def gcd(a, b):
            """The GCD (greatest common divisor) is the highest number that evenly divides both width and height."""
            return a if b == 0 else gcd(b, a % b)

        r = gcd(width, height)
        x = int(width / r)
        y = int(height / r)

        return x+y


class resolutionCheck:
    def __init__(self, width, height):
        self.width = width
        self.height = height


    def start(self):
        deleted = 0
        aspect = calculate_aspect(self.width, self.height)
        folder_dir = 'C:/Users/giuse/Pictures/Multithreaded-Reddit-Image-Downloader-master/images'
        for images in os.listdir(folder_dir):
            if (images.endswith(".png") or images.endswith(".jpg") or images.endswith(".jpeg")):
                try:
                    img = PIL.Image.open(images)
                except PIL.UnidentifiedImageError:
                    continue
                wid, hgt = img.size
                if(calculate_aspect(wid, hgt) != aspect):
                    deleted += 1
                    img.close()
                    os.remove(images)
                    continue
        print('deleted images: ' + str(deleted))
        a = input("Press Enter")

def main():
    parser = argparse.ArgumentParser(description='checks if the images in the folder can be used as wallpaper')
    required_args = parser.add_argument_group('required arguments')
    required_args.add_argument('-wdt', type=int, help="width", required=False)
    required_args.add_argument('-hgt', type=int, help="height", required=False)
    args = parser.parse_args()
    res = resolutionCheck(args.wdt,args.hgt)
    res.start()    


if __name__ == "__main__":
    main()

import scraper
import os
import PIL 
from PIL import Image
import cv2
import numpy as np

class ResWorker():
    def __init__(self, width, height, ratio, minw, minh, type):
        super().__init__()
        self.width = width
        self.height = height
        self.ratio = ratio
        self.minw = minw
        self.minh = minh
        self.type = type
        self.deleted = 0 

    def run(self):
        if(self.height != 0):
            aspect = self.calculate_aspect(self.width, self.height)

        folder_dir = scraper.images_dir
        thresh = 130.0


        # RESOLUTION CHECK
        for folder_name in os.listdir(folder_dir):
            folder_path = os.path.join(folder_dir, folder_name)
            if os.path.isdir(folder_path):
                for images in os.listdir(folder_path):
                    if (images.endswith(".png") or images.endswith(".jpg") or images.endswith(".jpeg")):
                        try:
                            img = PIL.Image.open(os.path.join(folder_path, images))
                        except PIL.UnidentifiedImageError:
                            continue
                        image = cv2.imread(os.path.join(folder_path, images))
                        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                        fm = self.variance_of_laplacian(gray)
                        if(fm < thresh):
                            img.close()
                            os.remove(os.path.join(folder_path, images))
                            self.deleted += 1
                            continue
                        wid, hgt = img.size
                        if(self.ratio == True):
                                if(self.calculate_aspect(wid, hgt) != aspect or wid <= hgt or wid < self.minw or hgt < self.minh):
                                    self.deleted += 1
                                    img.close()
                                    os.remove(os.path.join(folder_path, images))
                                    continue
                        else:
                                if(wid <= hgt or wid < self.minw or hgt < self.minh):
                                    self.deleted += 1
                                    img.close()
                                    os.remove(os.path.join(folder_path, images))
                                    continue   
                        # CHECK BRIGHT OR DARK
                        
                        if(self.type != "both"):
                            if(self.type == "bright" and self.isbright(image) or self.type == "dark" and not(self.isbright(image))):
                                continue
                            elif(self.type == "bright" and not(self.isbright(image)) or self.type == "dark" and self.isbright(image)):
                                img.close()
                                os.remove(os.path.join(folder_path, images))
                                self.deleted += 1
            
                

    # Credits to imneonizer(https://github.com/imneonizer) for his project 'How-to-find-if-an-image-is-bright-or-dark' (https://github.com/imneonizer/How-to-find-if-an-image-is-bright-or-dark)
    def isbright(self, image, dim=100, thresh=0.3):
        
        image = cv2.resize(image, (dim, dim))
        
        L, _, _ = cv2.split(cv2.cvtColor(image, cv2.COLOR_BGR2LAB))
       
        L = L/np.max(L)
       
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
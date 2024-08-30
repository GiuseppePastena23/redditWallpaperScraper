import itertools

class Query:
    id = itertools.count()
    
    def __init__(self, sub, images_number, sort_method, nsfw):
        self.id = next(self.id)
        self.sub = sub
        self.images_number = images_number
        self.sort_method = sort_method
        self.nsfw = nsfw
        
        
    def __str__(self):
        return f"Query {self.id}:\n r/{self.sub}; #_images = {self.images_number}; Sort = {self.sort_method}; NSFW = {self.nsfw}"
    
    
    
    
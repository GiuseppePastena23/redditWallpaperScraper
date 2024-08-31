import praw 
from dotenv import load_dotenv
from prawcore import NotFound
import os
import Query
from loguru import logger
import scraper
import concurrent.futures
import pickle as pk

load_dotenv()


logger.add("logs/log_{time}.log", level = "TRACE", rotation="100 MB")
reddit = scraper.reddit

def load_queries():
    Queries = []
    if(os.path.exists("queries.dat")):
        logger.info("Successfully loaded queries")
        with open("queries.dat", 'rb') as file:
            Queries = pk.load(file)
    else:
        logger.info("No queries.dat file found")
    
    return Queries
    

Queries = load_queries()

def is_subreddit(sub_name, exact):
    exists = True
    try:
        logger.info("Subreddit found")
        reddit.subreddits.search_by_name(sub_name, exact=exact)
    except Exception as e:
        logger.error(f"Exception details: {e.__class__.__name__}")
        exists = False
    return exists
        

def add_query(query, exact): 
    sub_name = query.sub
    images_number = query.images_number
    sort_method = query.sort_method
    nsfw = query.nsfw
    
    if(images_number <= 0) or len(sub_name) == 0:
        logger.error("Values not set correctly")
        raise ValueError(f"Set the values correctly, images_num = {images_number}, sub_name = {sub_name}")
        
    try: sub_state = is_subreddit(sub_name, exact)
    except Exception as e:
        print(str(e))
        
    if(sub_state == False):
        raise ValueError("Subreddit not Found")
    else:
        Queries.append(query)
        
def delete_query(id):
    for query in Queries:
        if query.id == id:
            Queries.remove(query)
            logger.info(f"Removed Query {query.id}")
            break
        
def save_queries():
    pk.dump(Queries, open("queries.dat", 'wb'))
    

    
        
def generate():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        
        futures = []

        for query in Queries:
            worker = scraper.Scraper(query.sub, query.images_number, query.sort_method, query.filter, query.nsfw)
            future = executor.submit(worker.start)
            futures.append(future)


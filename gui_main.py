import dearpygui.dearpygui as dpg
from dearpygui.dearpygui import set_value, get_value, get_item_children, delete_item, table_row, add_button, get_item_configuration
import main
from loguru import logger
import threading
import Query 
import resolutionChecker
import wx
import scraper


outp= wx.App(False)
screen_width, screen_height= wx.GetDisplaySize()




def update_query_table():
    clear_table("query_table")
    if len(main.Queries) <= 0:
        dpg.set_value(item="gen_info", value="Add at least 1 Query")
        return
    else:
        for query in main.Queries:
            with dpg.table_row(parent="query_table"):
                dpg.add_text(query.id)
                dpg.add_text("r/" + query.sub)
                dpg.add_text(query.images_number)
                dpg.add_text(query.sort_method)
                dpg.add_text(query.nsfw)
                dpg.add_button(label= "DEL", callback=delete_query, user_data=query.id)
    
    dpg.set_value(item="gen_info", value="Ready to Generate")
    logger.info("Updated Queries table")

def on_exit():
    logger.info("Saving queries.dat")
    main.save_queries()
    
            
def clear_table(table_tag):
    for tag in get_item_children(table_tag)[1]:
        delete_item(tag)
    logger.debug("Clearing Queries Table")

# CALLBACK FUNCTIONS

def addquery_callback():
    subreddit_name =  dpg.get_value("subreddit_input")
    exact_name = dpg.get_value("exact_name_value")
    images_num = dpg.get_value("images_num")
    sort_value = dpg.get_value("sort_value")
    nsfw_value = dpg.get_value("nsfw_value")
    query = Query.Query(subreddit_name, images_num, sort_value, nsfw_value)
    try: 
        main.add_query(query, exact_name)
        dpg.set_value(item="query_error", value="Correctly Added Query")
        logger.info(f"Query {query.id} successfully added")
        update_query_table()
    except ValueError as e:
        logger.error(e)
        dpg.set_value(item="query_error", value=str(e))
        
#TODO: multithreading
def generate_callback():
    logger.info("Generating...")
    if len(main.Queries) > 0:
        main.generate()
        
def min_res_callback():
    value = dpg.get_value("min_res_check")
    dpg.configure_item("min_wid", )
    if value:
        dpg.show_item("min_wid")
        dpg.show_item("min_hgt")
    else:
        dpg.hide_item("min_wid")
        dpg.hide_item("min_hgt")
        dpg.set_value("min_wid", value=1280)
        dpg.set_value("min_hgt", value=720)
        
def display_res_callback():
    value = dpg.get_value("use_display_res")
    dpg.configure_item("width_text", enabled=not value)
    dpg.configure_item("height_text", enabled=not value)
    if value:
        dpg.set_value("width_text", value=screen_width)
        dpg.set_value("height_text", value=screen_height)

def run_callback():
    resWorker = resolutionChecker.ResWorker(width=int(dpg.get_value("width_text")),height=int(dpg.get_value("height_text")), ratio=dpg.get_value("check_ar") , minw=int(dpg.get_value("min_wid")), minh=int(dpg.get_value("min_hgt")) , type=dpg.get_value("color_combo"))
    resWorker.run()
    logger.info("Running Resokution Check")

def open_folder_callback():
    logger.info("Opening media folder")

def delete_all_images_callback():
    logger.info("Deleting all images")

def delete_query(sender, app_data, user_data):
    main.delete_query(user_data)
    
    update_query_table()
    logger.info(f"Deleted query {user_data}")
    


dpg.create_context()
dpg.create_viewport(title='Custom Title', width=600, height=400)
dpg.setup_dearpygui()
dpg.set_exit_callback(on_exit)

sorting = ["top", "new", "hot"]
color_options = ["both", "bright", "dark"]

# Query Builder Window
with dpg.window(label="Add Query", width=300, height=200, pos=(0, 0)):
    dpg.add_input_text(label="Subreddit", tag="subreddit_input")
    dpg.add_checkbox(label="Exact name?", tag="exact_name_value")
    dpg.add_input_int(label="# Images", tag="images_num")
    dpg.add_combo(label="Sorting", items=sorting, tag="sort_value")
    dpg.add_checkbox(label="NSFW", tag="nsfw_value")
    dpg.add_button(label="Add", callback=addquery_callback)
    dpg.add_text("", tag="query_error")


# Generate Window
with dpg.window(label="Generate", width=300, height=200, pos=(0, 210)):
    
    dpg.add_text("Add query", tag="gen_info")
    with dpg.group(horizontal=True):
        dpg.add_button(label="Generate", callback=generate_callback)
        dpg.add_button(label="Stop", callback=None, enabled=False)
    with dpg.table(tag="query_table", row_background=True,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True):
        dpg.add_table_column(label="ID")
        dpg.add_table_column(label="sub_name")
        dpg.add_table_column(label="#_images")
        dpg.add_table_column(label="sort")
        dpg.add_table_column(label="nsfw")
        dpg.add_table_column(label="actions")
        
# Resolution Check Window
with dpg.window(label="Check", width=300, height=200, pos=(310, 0)):
    dpg.add_checkbox(label="Run after generating", tag="run_after_generate")
    dpg.add_checkbox(label="Check aspect ratio", tag="check_ar")
    dpg.add_checkbox(label="Use display resolution?", tag="use_display_res", callback=display_res_callback)
    dpg.add_input_text(label="Width", tag="width_text", default_value=str(screen_width))
    dpg.add_input_text(label="Height", tag="height_text", default_value=str(screen_height))
    dpg.add_combo(label="Color", items=color_options, tag="color_combo")
    dpg.add_checkbox(label="Change min resolution?", tag="min_res_check", callback=min_res_callback)
    dpg.add_input_text(label="Min Width", tag="min_wid", default_value=str(1280))
    dpg.add_input_text(label="Min Height", tag="min_hgt", default_value=str(720))
    min_res_callback()
    dpg.add_button(label="Run", callback=run_callback)

# Settings Window
with dpg.window(label="Settings", width=300, height=200, pos=(310, 210)):
    dpg.add_input_text(label="Client ID", default_value=scraper.CLIENT_ID)
    dpg.add_input_text(label="Client Secret", default_value=scraper.CLIENT_SECRET)
    dpg.add_button(label="Folder Chooser", callback=lambda: print("Folder Chooser"))
    dpg.add_button(label="Open Folder", callback=open_folder_callback)
    dpg.add_button(label="Delete All Images", callback=delete_all_images_callback)

update_query_table()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()



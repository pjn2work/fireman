import os
from dearpygui.core import add_same_line, add_text, show_logger, add_button, add_label_text, start_dearpygui, select_directory_dialog, log_debug, set_value, add_table, set_table_data
from dearpygui.simple import window
import fireman

def directory_picker(sender, data):
    select_directory_dialog(callback=apply_selected_directory)

def apply_selected_directory(sender, data):
    log_debug(data)  # so we can see what is inside of data
    folder = os.path.join(data[0], data[1]).rstrip(".").rstrip(os.sep) + os.sep

    set_value("folder", folder)

    res = fireman.list_files(folder, include_full_path_name=True, include_folders=False, include_sub_folders=True)
    tabledata = fireman.list_file_details(res, folder)
    set_table_data("Table##widget", tabledata)

show_logger()

with window("FiReMan", width=1200, height=400, x_pos=0, y_pos=0):
    add_button("Directory Selector", callback=directory_picker)

    add_text("Folder: ")
    add_same_line()
    add_label_text("##folder2", source="folder", color=[255, 255, 200])

    header = ("fpn", "folder", "rpath", "rfolder", "filename", "name", "ext", "size", "mtime", "ctime")
    add_table("Table##widget", header)
    apply_selected_directory("init", [os.getcwd(), ""])

start_dearpygui()
import os
import re
import pandas as pd
from typing import Tuple
from datetime import datetime
from pathlib import Path
from shutil import copystat, copy2
from rich import print
from rich.traceback import install
install()


HEADER = ["fpn", "folder", "rpath", "rfolder", "filename", "name", "ext", "size", "mtime", "ctime", "dst_fpn", "action"]
CSV_HEADERS = ["fpn", "dst_fpn", "action"]
ACTIONS = ("MOVE", "RENAME", "COPY", "DELETE")


def list_files(path: str = "", 
               include_full_path_name: bool = True,
               include_files: bool = True,
               include_folders: bool = True,
               include_sub_folders: bool = False,
               filename_regex_filter: str = "") -> list[str]:
    if not path:
        path = os.getcwd()
    
    if include_files and include_folders and not include_sub_folders and not filename_regex_filter:
        result = [os.path.join(path, f) for f in os.listdir(path)] if include_full_path_name else os.listdir(path)
    else:
        result = list()
        for f in os.listdir(path):
            fpn = os.path.join(path, f)

            if filename_regex_filter and os.path.isfile(fpn) and not re.search(filename_regex_filter, f):
                continue

            if (include_files and os.path.isfile(fpn)) or (include_folders and os.path.isdir(fpn)):
                result.append(fpn if include_full_path_name else f)

            if include_sub_folders and os.path.isdir(fpn):
                result += list_files(fpn,
                                include_full_path_name=include_full_path_name,
                                include_files=include_files,
                                include_folders=include_folders,
                                include_sub_folders=include_sub_folders,
                                filename_regex_filter=filename_regex_filter)

    return result


def list_folders(path: str = "", foldername_regex_filter: str = "") -> list[str]:
    folders = list_files(path=path, include_full_path_name=True, include_files=False, include_folders=True, include_sub_folders=True)
    if not foldername_regex_filter:
        return folders
    
    return [folder for folder in folders if re.search(foldername_regex_filter, folder)]


def list_file_details(list_of_fpn_files: list, relative_path: Tuple[str, int] = None) -> list[tuple]:
    if relative_path:
        if isinstance(relative_path, str):
            relative_path = len(relative_path)
    else:
        relative_path = 0

    res2 = list()
    for fpn in list_of_fpn_files:
        folder, filename = os.path.split(fpn)
        rpath = fpn[relative_path:].lstrip(os.sep)
        rfolder = folder[relative_path:].lstrip(os.sep)
        name, extension = os.path.splitext(filename)
        stat = os.stat(fpn)
        filesize = stat.st_size
        md_time = datetime.fromtimestamp(stat.st_mtime)
        cr_time = datetime.fromtimestamp(stat.st_ctime)

        attr = (fpn, folder, rpath, rfolder, filename, name, extension[1:], filesize, md_time, cr_time)
        res2.append(attr)
    return res2


def get_empty_folders_list(path: str) -> list:
    # get all files under path and save only the foldername (the occupied ones, by files)
    files = list_files(path, include_full_path_name=True, include_folders=False, include_sub_folders=True)
    files = list({os.path.dirname(file) for file in files})

    # list of all folders under same path
    folders = list_folders(path)

    # check if folders belong to files
    empty_folders = set()
    for folder in folders:
        for busy_folder in files:
            if busy_folder.startswith(folder):
                break
        else:
            empty_folders.add(folder)

    return list(empty_folders)


def execute_actions(list_of_fpn_files: list[tuple], action: str = "", callback_on_error: callable = None, is_dryrun: bool = True):
    """
    action = ("MOVE", "RENAME", "COPY", "DELETE")
    list_of_fpn_files = [(src, dst, action) or (src, dst) or "src", ...]
    callback_on_error = func(sender, data)
    """
    if not isinstance(list_of_fpn_files, list) or not isinstance(list_of_fpn_files[0], (list, tuple, str)):
        raise ValueError(f"'list_of_fpn_files' parameter must be of [(src, dst, action) or (src, dst) or 'src', ...]")

    lastfolder = src = dst = ""

    def _make_sure_folder_exists(lastfolder):
        if action != "DELETE":
            folder = os.path.dirname(dst)
            if folder != lastfolder:
                print(f"Created Folder {folder}")
                os.makedirs(folder, exist_ok=True)
                return folder
        return lastfolder

    def _execute(action, src, dst):
        if is_dryrun:
            return
        
        if action == "MOVE" or action == "RENAME":
            Path(src).rename(dst)
        elif action == "COPY":
            copy2(src, dst)
            copystat(src, dst)
        elif action == "DELETE":
            os.remove(src)

    for row in list_of_fpn_files:
        # decode vars
        if isinstance(row, str):
            src = row
        else:
            if len(row) == 3:
                src, dst, action = row
            elif len(row) == 2:
                src, dst = row
            else:
                raise ValueError(f"'list_of_fpn_files' parameter values not of valid type {type(row)}")

        try:
            lastfolder = _make_sure_folder_exists(lastfolder)
            _execute(action, src, dst)
        except Exception as e:
            if callback_on_error:
                callback_on_error(action, [src, dst, e])


def remove_folders(list_of_folders: list, callback_on_error: callable = None):
    action = "RMDIR"
    for folder in list_of_folders:
        try:
            os.rmdir(folder)
        except Exception as e:
            if callback_on_error:
                callback_on_error(action, [folder, e])


IGNORE_ERRORS = False
def callback_errors(sender, data):
    if not IGNORE_ERRORS:
        print(f"ERROR from {sender}")
        print(data)


class FiReMan:

    def __init__(self, callback_on_error: callable = None) -> None:
        super().__init__()
        self.callback_on_error = callback_on_error
        self.df = pd.DataFrame([], columns=HEADER)

    def _append_df(self, fd: list):
        df = pd.DataFrame(fd, columns=HEADER[:-2])
        self.df = self.df.append(df, ignore_index=True)
        self.df = self.df.drop_duplicates(subset=["fpn"], keep='first')

    def reset(self):
        self.df = pd.DataFrame([], columns=HEADER)
        return self

    def scan_folder(self, path: str, include_sub_folders: bool = False, filename_regex_filter: str = ""):
        files = list_files(path, include_full_path_name=True, include_folders=False, include_sub_folders=include_sub_folders, filename_regex_filter=filename_regex_filter)
        fd = list_file_details(files, path)
        self._append_df(fd)
        return self

    def generate_output(self,
                        dst_folder: str,
                        keep_source_folder_structure: bool,
                        src_regex: str = "",
                        dst_regex: str = ""):
        # rename files
        if src_regex and dst_regex:
            self.df["dst_fpn"] = self.df["filename"].replace(src_regex, dst_regex, regex=True)
        else:
            self.df["dst_fpn"] = self.df["filename"]
        
        # create destination full-path-name
        if keep_source_folder_structure:
            self.df["dst_fpn"] = dst_folder + os.sep + self.df["rfolder"] + os.sep + self.df["dst_fpn"]
        else:
            self.df["dst_fpn"] = dst_folder + os.sep + self.df["dst_fpn"]
        
        return self

    def get_output_list(self) -> list:
        if "dst_fpn" in self.df.columns:
            return self.df[["fpn", "dst_fpn"]].values.tolist()
        return []

    def get_output_list_src(self) -> list:
        return self.df["fpn"].values.tolist()

    def execute(self, action: str):
        if action not in ACTIONS:
            raise ValueError(f"Action must be one of {ACTIONS}")
        self.df["action"] = action

        # sort dataframe
        if action == "DELETE":
            self.df.sort_values(by=["fpn"], inplace=True)
            exec_list = self.get_output_list_src()
        else:
            self.df.sort_values(by=["dst_fpn"], inplace=True)
            exec_list = self.get_output_list()

        execute_actions(exec_list, action=action, callback_on_error=self.callback_on_error)

        return self

    def execute_from_csv(self, filename: str):
        df = pd.read_csv(filename)
        if df.columns != CSV_HEADERS:
            raise ValueError(f"Expected header of {filename} to have {CSV_HEADERS}")
        
        exec_list = df[CSV_HEADERS].sort_values(by=["dst_fpn"], inplace=False).fillna("", inplace=False).values.tolist()
        execute_actions(exec_list, callback_on_error=self.callback_on_error)

        return self

    def save_to_csv(self, filename: str = "fireman.csv"):
        self.df.to_csv(filename, index=False)
        return self

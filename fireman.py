import os
import re
import shutil
import pandas as pd
from typing import Tuple, List
from datetime import datetime
from rich import print
from rich.traceback import install
install()


HEADER_SOURCE_FPN = "fpn"
HEADER_TARGET_FPN = "dst_fpn"
HEADER_RELATIVE_FOLDER = "rfolder"
HEADER_IS_FILE = "is_file"
HEADER_ACTION = "action"
HEADER = [HEADER_SOURCE_FPN, "folder", "rpath", HEADER_RELATIVE_FOLDER, "filename", "name", "ext", "size", "mtime", "ctime", HEADER_IS_FILE, HEADER_TARGET_FPN, HEADER_ACTION]
CSV_HEADERS = [HEADER_SOURCE_FPN, HEADER_TARGET_FPN, HEADER_ACTION]

REGEX_RENAME_BASED_ON_FIELD = "filename"

ACTION_MOVE = "MOVE"
ACTION_RENAME = "RENAME"
ACTION_COPY = "COPY"
ACTION_DELETE = "DELETE"
ACTION_REMOVE_FOLDER = "RMDIR"
ACTION_MOVE_FOLDER = "MOVEDIR"
ACTIONS = (ACTION_MOVE, ACTION_RENAME, ACTION_COPY, ACTION_DELETE, ACTION_REMOVE_FOLDER, ACTION_MOVE_FOLDER)


def list_files(path: str = "", 
               include_full_path_name: bool = True,
               include_files: bool = True,
               include_folders: bool = True,
               include_sub_folders: bool = False,
               filename_regex_filter: str = "") -> List[str]:
    if not path:
        path = os.getcwd()
    
    if include_files and include_folders and not include_sub_folders and not filename_regex_filter:
        result = [os.path.join(path, f) for f in os.listdir(path)] if include_full_path_name else os.listdir(path)
    else:
        result = list()
        try:
            for f in os.listdir(path):
                fpn = os.path.join(path, f)
                is_match = not filename_regex_filter or re.search(filename_regex_filter, f)

                if (include_files and os.path.isfile(fpn) and is_match) or (include_folders and os.path.isdir(fpn) and is_match):
                    result.append(fpn if include_full_path_name else f)

                if include_sub_folders and os.path.isdir(fpn):
                    result += list_files(fpn,
                                    include_full_path_name=include_full_path_name,
                                    include_files=include_files,
                                    include_folders=include_folders,
                                    include_sub_folders=include_sub_folders,
                                    filename_regex_filter=filename_regex_filter)
        except Exception:
            pass

    return result


def list_folders(path: str = "",
                 foldername_regex_filter: str = "") -> List[str]:
    folders = list_files(path=path, include_full_path_name=True, include_files=False, include_folders=True, include_sub_folders=True)
    if not foldername_regex_filter:
        return folders
    
    return [folder for folder in folders if re.search(foldername_regex_filter, folder)]


def list_file_details(list_of_fpn_files: list,
                      relative_path: Tuple[str, int] = None,
                      callback_on_error: callable = None,
                      callback_on_progress: callable = None) -> List[tuple]:
    if relative_path:
        if isinstance(relative_path, str):
            relative_path = len(relative_path)
    else:
        relative_path = 0

    sender = "LIST_FILE_DETAILS"
    total = len(list_of_fpn_files)
    current = 0

    res2 = list()
    for fpn in list_of_fpn_files:
        current += 1

        try:
            folder, filename = os.path.split(fpn)
            rpath = fpn[relative_path:].lstrip(os.sep)
            rfolder = folder[relative_path:].lstrip(os.sep)
            name, extension = os.path.splitext(filename)
            is_file = os.path.isfile(fpn)
            stat = os.stat(fpn)
            filesize = stat.st_size
            md_time = datetime.fromtimestamp(stat.st_mtime)
            cr_time = datetime.fromtimestamp(stat.st_ctime)

            attr = (fpn, folder, rpath, rfolder, filename, name, extension[1:], filesize, md_time, cr_time, is_file)
            res2.append(attr)
        except Exception as e:
            filesize = -1
            if callback_on_error:
                callback_on_error(sender, [fpn, e])

        if callback_on_progress:
            callback_on_progress(sender, [total, current, fpn, filesize])

    return res2


def list_empty_folders(path: str) -> list:
    # get all files under path and save only the foldername (the occupied ones, by files)
    files = list_files(path, include_full_path_name=True, include_files=True, include_folders=False, include_sub_folders=True)
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

    empty_folders = list(empty_folders)
    empty_folders.sort(key=str.lower, reverse=True)

    return empty_folders


def execute_actions(list_of_fpn_files: List[tuple],
                    action: str = "",
                    callback_on_error: callable = None,
                    callback_on_progress: callable = None,
                    is_dryrun: bool = True):
    """
    action = ("MOVE", "RENAME", "COPY", "DELETE", "RMDIR", "MOVEDIR")
    list_of_fpn_files = [(src, dst, action) or (src, dst) or "src", ...]
    callback_on_error = func(sender, data)
    callback_on_progress = func(sender, data)
    """
    if not list_of_fpn_files:
        return
    
    if not isinstance(list_of_fpn_files, list) or not isinstance(list_of_fpn_files[0], (list, tuple, str)):
        raise ValueError(f"'list_of_fpn_files' parameter must be of [(src, dst, action) or (src, dst) or 'src', ...]")

    sender = "EXECUTE_ACTIONS"
    last_folder = src = dst = ""
    total = len(list_of_fpn_files)
    current = 0

    def _make_sure_folder_exists(lastfolder):
        if action != ACTION_DELETE:
            folder = os.path.dirname(dst)
            if folder != lastfolder:
                os.makedirs(folder, exist_ok=True)
                return folder
        return lastfolder

    def _execute(action, src, dst):
        if action == ACTION_COPY:
            shutil.copy2(src, dst)
            shutil.copystat(src, dst)
        elif action == ACTION_DELETE:
            os.remove(src)
        elif action == ACTION_REMOVE_FOLDER:
            os.rmdir(src)
        elif action in [ACTION_MOVE, ACTION_RENAME, ACTION_MOVE_FOLDER]:
            shutil.move(src, dst)

    for row in list_of_fpn_files:
        current += 1

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

        if not is_dryrun:
            try:
                last_folder = _make_sure_folder_exists(last_folder)
                _execute(action, src, dst)
            except Exception as e:
                if callback_on_error:
                    callback_on_error(sender, [action, src, dst, e])

        if callback_on_progress:
            callback_on_progress(sender, [total, current, action, src, dst])


def remove_empty_folders(path: str,
                         callback_on_error: callable = None,
                         callback_on_progress: callable = None):
    empty_folders = list_empty_folders(path)
    execute_actions(empty_folders, action=ACTION_REMOVE_FOLDER, callback_on_error=callback_on_error, callback_on_progress=callback_on_progress)


class FiReMan:

    def __init__(self, callback_on_error: callable = None, callback_on_progress: callable = None) -> None:
        super().__init__()
        self.callback_on_error = callback_on_error
        self.callback_on_progress = callback_on_progress
        self.df = pd.DataFrame([], columns=HEADER)

    def _append_df(self, fd: list):
        df = pd.DataFrame(fd, columns=HEADER[:-2])
        self.df = self.df.append(df, ignore_index=True)
        self.df = self.df.drop_duplicates(subset=[HEADER_SOURCE_FPN], keep='first')

    def _get_df_list_based_on_action(self, action: str = "") -> list:
        if action == "":
            df = self.df
        elif action in [ACTION_MOVE_FOLDER, ACTION_REMOVE_FOLDER]:
            df = self.df[self.df[HEADER_IS_FILE] == False]
        else:
            df = self.df[self.df[HEADER_IS_FILE] == True]
            df.sort_values(by=[HEADER_TARGET_FPN], inplace=True)

        if action in (ACTION_DELETE, ACTION_REMOVE_FOLDER):
            df = df[HEADER_SOURCE_FPN]
        else:
            df = df[[HEADER_SOURCE_FPN, HEADER_TARGET_FPN]]

        return df.values.tolist()

    def reset(self):
        self.df = pd.DataFrame([], columns=HEADER)
        return self

    def scan_folder(self, path: str, 
                    include_files: bool = True,
                    include_folders: bool = False,
                    include_sub_folders: bool = True,
                    filename_regex_filter: str = ""):
        files = list_files(path, include_full_path_name=True, include_files=include_files, include_folders=include_folders, include_sub_folders=include_sub_folders, filename_regex_filter=filename_regex_filter)
        fd = list_file_details(files, path, callback_on_error=self.callback_on_error, callback_on_progress=self.callback_on_progress)
        self._append_df(fd)
        return self

    def scan_empty_folders(self, path: str):
        empty_folders = list_empty_folders(path)
        fd = list_file_details(empty_folders, path, callback_on_error=self.callback_on_error, callback_on_progress=self.callback_on_progress)
        self._append_df(fd)
        return self

    def generate_output(self,
                        dst_folder: str,
                        keep_source_folder_structure: bool,
                        src_regex: str = "",
                        dst_regex: str = ""):
        # rename files
        if src_regex and dst_regex:
            self.df[HEADER_TARGET_FPN] = self.df[REGEX_RENAME_BASED_ON_FIELD].str.replace(src_regex, dst_regex, regex=True)
        else:
            self.df[HEADER_TARGET_FPN] = self.df[REGEX_RENAME_BASED_ON_FIELD]
        
        # remove ending separator
        dst_folder = dst_folder.rstrip(os.sep)

        # create destination full-path-name
        if keep_source_folder_structure:
            self.df[HEADER_TARGET_FPN] = dst_folder + os.sep + self.df[HEADER_RELATIVE_FOLDER] + os.sep + self.df[HEADER_TARGET_FPN]
            self.df[HEADER_TARGET_FPN] = self.df[HEADER_TARGET_FPN].str.replace(os.sep*2, os.sep, case=True, regex=False)
        else:
            self.df[HEADER_TARGET_FPN] = dst_folder + os.sep + self.df[HEADER_TARGET_FPN]
        
        return self

    def execute(self, action: str, is_dryrun: bool = True):
        if action not in ACTIONS:
            raise ValueError(f"Action must be one of {ACTIONS}")

        execute_actions(self._get_df_list_based_on_action(action), action=action, callback_on_error=self.callback_on_error, callback_on_progress=self.callback_on_progress, is_dryrun=is_dryrun)
        return self

    def execute_from_csv(self, filename: str, is_dryrun: bool = True):
        df = pd.read_csv(filename)
        for col_name in CSV_HEADERS:
            if col_name not in df.columns:
                raise ValueError(f"Expected header of {filename} to have {CSV_HEADERS}. Missing {col_name}")
        
        exec_list = df[CSV_HEADERS].fillna("", inplace=False).values.tolist()
        execute_actions(exec_list, callback_on_error=self.callback_on_error, callback_on_progress=self.callback_on_progress, is_dryrun=is_dryrun)

        return self

    def save_to_csv(self, filename: str = "fireman.csv"):
        self.df.to_csv(filename, index=False)
        return self

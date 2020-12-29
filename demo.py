import fireman as FRM
from rich.prompt import Prompt


IGNORE_ERRORS = False


def callback_errors(sender, data):
    global IGNORE_ERRORS
    if not IGNORE_ERRORS:
        FRM.print(f"ERROR from {sender}\n{data}")
        if Prompt.ask("Ignore next errors?", choices=["yes", "no"], default="yes") == "yes":
            IGNORE_ERRORS = True


def callback_progress(sender, data):
    #FRM.print(f"PROGRESS from {sender} - {data}")
    pass


path_src_root = r"C:\backup\GIT"
path_src = r"C:\backup\GIT\COPYfireman" #FRM.os.getcwd()
path_dst1 = r"C:\backup\GIT\copied"
path_dst2 = r"C:\backup\GIT\moved"
path_dst3 = r"C:\backup\GIT\new_move"


def copy_files1(frm):
    print("1"*50)
    frm.reset().scan_folder(path_src, include_files=True, include_folders=False, include_sub_folders=True)
    frm.generate_output(path_dst1, keep_source_folder_structure=True, src_regex=r"^(.+)$", dst_regex=r"copy_\1")
    frm.save_to_csv("1copy_files.csv").execute(FRM.ACTION_COPY, is_dryrun=False)


def move_files2(frm):
    print("2"*50)
    frm.reset().scan_folder(path_dst1, include_files=True, include_folders=False, include_sub_folders=True)
    frm.generate_output(path_dst2, keep_source_folder_structure=True, src_regex=r"^copy_(.+)$", dst_regex=r"move_\1")
    frm.save_to_csv("2move_files.csv").execute(FRM.ACTION_MOVE, is_dryrun=False)


def remove_empty_folder3(frm):
    print("3"*50)
    frm.reset().scan_empty_folders(path_dst1).save_to_csv("3remove_empty_folder.csv").execute(FRM.ACTION_REMOVE_FOLDER, is_dryrun=False)


def move_folder4(frm):
    print("4"*50)
    frm.reset().scan_folder(path_src_root, include_files=False, include_folders=True, include_sub_folders=False, filename_regex_filter="^moved$")
    frm.generate_output(path_src_root, keep_source_folder_structure=True, src_regex="^moved$", dst_regex="new_move")
    frm.save_to_csv("4move_folder.csv").execute(FRM.ACTION_MOVE_FOLDER, is_dryrun=False)


def delete_files5(frm):
    print("5"*50)
    frm.reset().scan_folder(path_dst3, include_files=True, include_folders=False, include_sub_folders=True)
    frm.save_to_csv("5delete_files.csv").execute(FRM.ACTION_DELETE, is_dryrun=False)


def remove_empty_folder6(frm):
    print("6"*50)
    frm.reset().scan_empty_folders(path_dst3).save_to_csv("6remove_empty_folder.csv").execute(FRM.ACTION_REMOVE_FOLDER, is_dryrun=False)


if __name__ == "__main__":
    frm = FRM.FiReMan(callback_on_error=callback_errors, callback_on_progress=callback_progress)
    copy_files1(frm)
    #move_files2(frm)
    #remove_empty_folder3(frm)
    #move_folder4(frm)
    #delete_files5(frm)
    #remove_empty_folder6(frm)

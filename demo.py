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
    FRM.print(f"PROGRESS from {sender} - {data}")


path_src = r"C:\backup\gdrive\LDSSA" #"/home/pedro/demo"
path_dst = "/home/pedro/apagar"


def test1():
    ef = FRM.list_empty_folders(path_src)
    efd = FRM.list_file_details(ef)
    for x in efd:
        FRM.print(x)


def test5(path = r"c:\backup\git\fireman"):    
    ef = FRM.list_files(path, include_sub_folders=True)
    efd = FRM.list_file_details(ef)
    for x in efd:
        FRM.print(x)


def test6(frm, path = r"c:\backup\git\fireman"):
    #frm.scan_folder(path, include_sub_folders=True).scan_empty_folders(path).save_to_csv()
    frm.reset().scan_empty_folders(path + r"\apagar.txt").execute(FRM.ACTION_REMOVE_FOLDER)


def test2():
    FRM.remove_empty_folders(path_src, callback_on_error=callback_errors, callback_on_progress=callback_progress)


def test3(frm):
    """Create folders based on file extension and generate CSV file"""
    frm.scan_folder(path_src, include_sub_folders=True, filename_regex_filter=r"^.+\.(py|java|md|txt)$")
    frm.generate_output(dst_folder=path_dst,
                        keep_source_folder_structure=False,
                        src_regex=r"(.+)\.(.+)$",
                        dst_regex=r"\2/code_\1.\2")
    frm.save_to_csv("demo.csv")
    frm.execute("COPY", is_dryrun=True)


def test4(frm: FRM.FiReMan):
    """Create folders based on file extension and generate CSV file"""
    frm.scan_empty_folders(path_src)
    frm.save_to_csv("demo.csv")


if __name__ == "__main__":
    frm = FRM.FiReMan(callback_on_error=callback_errors, callback_on_progress=callback_progress)
    test6(frm)
    #test4(frm)

"""
dedicated distribution builder for SuperSID
"""

import os
# import sys
import glob
import shutil
import filecmp
from zipfile import ZipFile

def get_src_files():
    """
    collect the files that are the source
    for the copy to the Program folder
    """
    src_files = []
    for root, _, filenames in os.walk('dist'):
        for filename in filenames:
            src_files.append((root, filename))
            assert os.path.isfile(os.path.join(root, filename))
    return src_files


def create_dst_folders(src_files):
    """
    create the destination folders `Program` and below
    """
    dst_folders = set()
    for src in src_files:
        dst_folders.add(os.path.join(r"..", "Program",
            f"{os.sep}".join(x for x in src[0].split(os.sep)[2:])))
    dst_folders = sorted(dst_folders)
    for dst in dst_folders:
        if not os.path.isdir(dst):
            # print(f"creating '{dst}'")
            os.makedirs(dst)


def compare_zip_files(filepath_a, filepath_b):
    """
    Verify that two zip files are equal.
    It compares the content of the zip files and the content of the files in the zip files.
    """
    result = False
    with ZipFile(filepath_a, "r") as zip_a:
        ziped_files_a = sorted(zip_a.namelist())
        with ZipFile(filepath_b, "r") as zip_b:
            ziped_files_b = sorted(zip_b.namelist())
            result = True
            if sorted(ziped_files_a) != sorted(ziped_files_b):
                print("namelist")
                result = False
            for ziped_filename in ziped_files_a:
                with zip_a.open(ziped_filename) as file_a:
                    with zip_b.open(ziped_filename) as file_b:
                        content_a = file_a.read()
                        content_b = file_b.read()
                        if content_a != content_b:
                            print(f"file content mismatch "
                                  f"'{filepath_a}{os.sep}{ziped_filename}' "
                                  f"'{filepath_b}{os.sep}{ziped_filename}'")
                            # with open("a.pyc", "wb") as f:
                                # print(f.name, len(content_a), type(content_a))
                                # f.write(content_a)
                                # f.flush()
                                # result = subprocess.run(["uncompyle6", f.name],
                                    # capture_output=True, text=True)
                                # print("stdout", result.stdout)
                                # print("stderr", result.stderr)

                            # with open("b.pyc", "wb") as f:
                                # print(f.name, len(content_b), type(content_b))
                                # f.write(content_b)
                                # f.flush()
                                # result = subprocess.run(["uncompyle6", f.name],
                                    # capture_output=True, text=True)
                                # print("stdout", result.stdout)
                                # print("stderr", result.stderr)
                            result = False
    return result


def copy_to_dst(src):
    """
    copy the files from the`'PyInstaller' to the 'Program' folder
    """
    src_file = os.path.join(src[0], src[1])
    dst_file = os.path.join(r"..", "Program",
        f"{os.sep}".join(x for x in src[0].split(os.sep)[2:]), src[1])
    if not os.path.isfile(dst_file):
        # print(f"copy '{src_file}' to '{dst_file}'")
        shutil.copy2(src_file, dst_file)
    else:
        if not filecmp.cmp(src_file, dst_file):
            if os.path.splitext(src_file)[-1].lower() == '.zip':
                if not compare_zip_files(src_file, dst_file):
                    # sys.exit(1)
                    pass
            else:
                print(f"file content mismatch '{src_file}' '{dst_file}'")
                # sys.exit(1)


def create_zip():
    """
    create the final distributabl file SuperSID.zip
    """
    cwd = os.getcwd()
    os.chdir(r"..")
    content = {
        ".": ["LICENSE", "README.md", "requirements.txt"],
        "Config": ["ftp_cmds.TXT", "supersid.cfg"],
        "Data": [],
        "docs": ["*.md"],
        "outgoing": [],
        "Private": [],
        "Program": ["*"],
        "src": ["*.*"],
    }
    with ZipFile('SuperSID.zip', 'w') as myzip:
        for folder, patterns in content.items():
            if folder not in [".", ".."]:
                myzip.write(folder)
            for pattern in patterns:
                if "*" == pattern:
                    for root, _, filenames in os.walk(folder):
                        for filename in filenames:
                            file = os.path.join(root, filename)
                            assert os.path.isfile(file)
                            # print(file)
                            myzip.write(file)
                else:
                    src_files = glob.glob(os.path.join(folder, pattern))
                    for file in src_files:
                        assert os.path.isfile(file)
                        # print(file)
                        myzip.write(file)
    os.chdir(cwd)


def main():
    """
    the main function
    """
    src_files = get_src_files()
    create_dst_folders(src_files)
    for src in src_files:
        copy_to_dst(src)
    create_zip()


if __name__ == '__main__':
    main()

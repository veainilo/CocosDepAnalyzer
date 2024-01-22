import os
import re
import pickle
import shelve
from fuzzywuzzy import process
import tkinter as tk
from tkinter import messagebox

def setValue(key, value):
    with shelve.open("my_shelf") as db:
        db[key] = value


def getValue(key):
    with shelve.open("my_shelf") as db:
        return db.get(key)


matcher = re.compile(r"[a-z\d]{8}-[a-z\d]{4}-[a-z\d]{4}-[a-z\d]{4}-[a-z\d]{12}")

dependencyMap = {}
uuidToFileName = {}
keyToUUID = {}
byDependencyMap = {}


class dependency:
    def __init__(self, uuid, uuids):
        self.uuid = uuid
        self.uuids = set(uuids)

    def __str__(self):
        return self.uuid + " " + str(self.uuids)

    def add(self, uuid):
        self.uuids.add(uuid)


def getDependency(fileName):
    uuid = None
    with open(fileName + ".meta", "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        for match in matcher.findall(content):
            uuid = match
            break

    if uuid == None:
        print("没找到文件:" + fileName)
        return

    dep = dependency(uuid, [])
    uuidToFileName[uuid] = fileName

    with open(fileName, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        for match in matcher.findall(content):
            dep.add(match)

    # print("处理文件:" + fileName)
    return dep


# 序列化到文件
import concurrent.futures


def process_file(filename):
    if filename.endswith(".meta"):
        dep = getDependency(filename[:-5])
        return dep.uuid, dep


# 分析依赖关系的方法
def getDependencies(folder):
    if os.path.isfile("./dependencies.pkl"):
        with open("./dependencies.pkl", "rb") as f:
            return pickle.load(f)

    dependencyMap = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for dirpath, dirnames, filenames in os.walk(folder):
            futures = {
                executor.submit(process_file, os.path.join(dirpath, filename)): filename
                for filename in filenames
            }

            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result is not None:
                    uuid, dep = result
                    dependencyMap[uuid] = dep

    with open("./dependencies.pkl", "wb") as f:
        pickle.dump((dependencyMap, uuidToFileName), f)

    return dependencyMap, uuidToFileName


dependencyMap = {}


def load_dependency():
    path = path_entry.get()
    setValue("path", path)
    try:
        global dependencyMap, uuidToFileName, uuidToFileName
        dependencyMap, uuidToFileName = getDependencies(path)

        # for uuid in dependencyMap.keys():
        #     keyToUUID[f"{uuid}{uuidToFileName[uuid]}"] = uuid

        for uuid, dep in dependencyMap.items():
            for depend in dep.uuids:
                if depend not in byDependencyMap:
                    byDependencyMap[depend] = []
                byDependencyMap[depend].append(uuid)

        asset_count_label["text"] = "资源数目: " + str(len(dependencyMap))
        messagebox.showinfo("Success", "Dependency loaded successfully")
    except Exception as e:
        messagebox.showinfo("Error", str(e))


def show_dependency():
    uuid = process.extractOne(uuid_entry.get(), dependencyMap.keys())[0]

    searching_uuid_label["text"] = "当前搜索: " + f"{uuid}({uuidToFileName[uuid]})"

    if uuid in dependencyMap:
        text1.delete(1.0, tk.END)
        if recursive_var.get() == 1:
            getDependencyTree(uuid, set(), 0)
            return
        dep = dependencyMap[uuid]

        dependStrList = []
        dependStrList.append(f"{uuid}({uuidToFileName[uuid]})依赖以下资源:")
        for depend in dep.uuids:
            dependStrList.append(f"\t{depend}({uuidToFileName[depend]})")
        text1.insert(tk.END, "\n".join(dependStrList))
    else:
        messagebox.showinfo("Error", "UUID not found")


def getDependencyTree(uuid, lookups, level):
    if uuid in lookups:
        return
    lookups.add(uuid)
    if uuid in dependencyMap:
        dep = dependencyMap[uuid]
        text1.insert(tk.END, "\t" * level + f"{uuid}({uuidToFileName[uuid]})")
        text1.insert(tk.END, "\n")
        for depend in dep.uuids:
            getDependencyTree(depend, lookups, level + 1)
        if dep.uuids:
            text1.insert(tk.END, "\n")
    else:
        print("没找到uuid:" + uuid)


def getByDenpendencyTree(uuid, lookups, level):
    if uuid in lookups:
        return
    lookups.add(uuid)
    if uuid in byDependencyMap:
        dep = byDependencyMap[uuid]
        text1.insert(tk.END, "\t" * level + f"{uuid}({uuidToFileName[uuid]})")
        text1.insert(tk.END, "\n")
        for depend in dep:
            getByDenpendencyTree(depend, lookups, level + 1)
        if dep:
            text1.insert(tk.END, "\n")
    elif uuid in dependencyMap:
        text1.insert(tk.END, "\t" * level + f"{uuid}({uuidToFileName[uuid]})")
        text1.insert(tk.END, "\n")
    else:
        print("没找到uuid:" + uuid)


def show_by_dependency():
    uuid = process.extractOne(uuid_entry.get(), dependencyMap.keys())[0]

    setValue("uuid", uuid)

    searching_uuid_label["text"] = "当前搜索: " + f"{uuid}({uuidToFileName[uuid]})"

    if uuid in dependencyMap:
        text1.delete(1.0, tk.END)

        if recursive_var.get() == 1:
            getByDenpendencyTree(uuid, set(), 0)
            return

        # 查找被哪些依赖
        depended_by = [k for k, v in dependencyMap.items() if uuid in v.uuids]

        depended_by_str_list = []
        depended_by_str_list.append(f"{uuid}({uuidToFileName[uuid]})被以下资源依赖:")
        for depend in depended_by:
            depended_by_str_list.append(f"\t{depend}({uuidToFileName[depend]})")
        text1.insert(tk.END, "\n".join(depended_by_str_list))
    else:
        messagebox.showinfo("Error", "UUID not found")


root = tk.Tk()

root.title("UUID Dependency Viewer")

path_label = tk.Label(root, text="输入项目资源目录:")

path_label.grid(row=0, column=0, sticky="ew")

asset_count_label = tk.Label(root, text="资源数目:")

asset_count_label.grid(row=0, column=1, sticky="ew")

path_entry = tk.Entry(root)

path_entry.grid(row=1, column=0, sticky="ew")

path_entry.insert(tk.END, getValue("path") or "")

if getValue("path"):
    load_dependency()

load_button = tk.Button(root, text="加载资源目录依赖", command=load_dependency)
load_button.grid(row=2, column=0, sticky="ew")

clean_button = tk.Button(
    root, text="清除缓存", command=lambda: os.remove("./dependencies.pkl")
)
clean_button.grid(row=2, column=1, sticky="ew")

uuid_label = tk.Label(root, text="输入UUID:")
uuid_label.grid(row=3, column=0, sticky="ew")

uuid_entry = tk.Entry(root)
uuid_entry.grid(row=4, column=0, sticky="ew")
uuid_entry.insert(tk.END, getValue("uuid") or "")

# 是否递归查找依赖
recursive_var = tk.IntVar()
recursive_var.set(0)
recursive_checkbutton = tk.Checkbutton(root, text="递归查找依赖", variable=recursive_var)
recursive_checkbutton.grid(row=4, column=1, sticky="ew")

# 使用trace方法，当uuid_var的值发生变化时，调用on_uuid_change函数

# uuid_var.trace("w", on_uuid_change)

searching_uuid_label = tk.Label(root, text="当前搜索:")

searching_uuid_label.grid(row=3, column=1, sticky="ew")

submit_button = tk.Button(root, text="显示依赖", command=show_dependency)

submit_button.grid(row=5, column=0, sticky="ew")

submit_by_dep_button = tk.Button(root, text="显示被依赖", command=show_by_dependency)
submit_by_dep_button.grid(row=5, column=1, sticky="ew")

text1 = tk.Text(root)

text1.grid(row=6, column=0, columnspan=2, sticky="nsew")

root.grid_columnconfigure(0, weight=1)

root.grid_columnconfigure(1, weight=1)

root.grid_rowconfigure(6, weight=1)

root.mainloop()

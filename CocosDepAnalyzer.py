from functools import cache
import os
import re
import pickle
import shelve
from fuzzywuzzy import process
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

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
        if uuid != self.uuid:
            self.uuids.add(uuid)


def getDependency(fileName):
    if os.path.isfile(fileName) == False:
        print("没找到文件:" + fileName)
        return

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
        if dep is None:
            return None
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

def get_selected_item():
    selected_indices = text1.curselection()
    if selected_indices:  # 如果有选中的项
        first_selected_index = selected_indices[0]
        selected_item = text1.get(first_selected_index)
        return selected_item
    else:
        return None

def show_dependency():
    uuid = process.extractOne(uuid_entry.get(), dependencyMap.keys())[0]

    searching_uuid_label["text"] = "当前搜索: " + f"{uuid}({uuidToFileName[uuid]})"

    if uuid in dependencyMap:
        # 删除Listbox中的所有项
        text1.delete(0, tk.END)
        if recursive_var.get() == 1:
            getDependencyTree(uuid, set(), 0)
            return
        dep = dependencyMap[uuid]

        text1.insert(tk.END, f"{uuid}({uuidToFileName[uuid]})依赖以下资源:")
        for depend in dep.uuids:
            text1.insert(tk.END, f"\u2003{depend}({uuidToFileName[depend]})")
    else:
        messagebox.showinfo("Error", "UUID not found")


def getDependencyTree(uuid, lookups, level):
    if uuid in lookups:
        return
    lookups.add(uuid)
    if uuid in dependencyMap:
        dep = dependencyMap[uuid]
        text1.insert(tk.END, "\u2003" * level + f"{uuid}({uuidToFileName[uuid]})")
        for depend in dep.uuids:
            getDependencyTree(depend, lookups, level + 1)       
    else:
        print("没找到uuid:" + uuid)


def getByDenpendencyTree(uuid, lookups, level):
    if uuid in lookups:
        return
    lookups.add(uuid)
    if uuid in byDependencyMap:
        dep = byDependencyMap[uuid]
        text1.insert(tk.END, "\u2003" * level + f"{uuid}({uuidToFileName[uuid]})")
        for depend in dep:
            getByDenpendencyTree(depend, lookups, level + 1)
    elif uuid in dependencyMap:
        text1.insert(tk.END, "\u2003" * level + f"{uuid}({uuidToFileName[uuid]})")
    else:
        print("没找到uuid:" + uuid)


def show_by_dependency():
    uuid = process.extractOne(uuid_entry.get(), dependencyMap.keys())[0]

    setValue("uuid", uuid)

    searching_uuid_label["text"] = "当前搜索: " + f"{uuid}({uuidToFileName[uuid]})"

    if uuid in dependencyMap:
        text1.delete(0, tk.END)

        if recursive_var.get() == 1:
            getByDenpendencyTree(uuid, set(), 0)
            return

        text1.insert(tk.END, f"{uuid}({uuidToFileName[uuid]})被以下资源依赖:")

        # 查找被哪些依赖
        depended_by = [k for k, v in dependencyMap.items() if uuid in v.uuids]
        for depend in depended_by:
            text1.insert(tk.END, f"\u2003{depend}({uuidToFileName[depend]})")
    else:
        messagebox.showinfo("Error", "UUID not found")

from functools import lru_cache

@lru_cache(maxsize=None)
def get_all_dependencies(uuid):
    if uuid not in dependencyMap:
        return set()
    dependencies = set(dependencyMap[uuid].uuids)
    for dep_uuid in list(dependencies):
        dependencies.update(get_all_dependencies(dep_uuid))
    return dependencies

def showAllRoots():
    text1.delete(0, tk.END)
    roots = []
    for uuid in dependencyMap.keys():
        if uuid not in byDependencyMap:
            roots.append(uuid)
    
    # 按照依赖数目（包括直接和间接依赖）由大到小排序
    roots.sort(key=lambda x: len(get_all_dependencies(x)), reverse=True)

    for uuid in roots:
        text1.insert(tk.END, f"{uuid}({uuidToFileName[uuid]}), 依赖资源数目: {len(get_all_dependencies(uuid))}")


def dfs(uuid, reversedDependencyMap, visited):
    if uuid in visited:
        return visited[uuid]
    visited[uuid] = 0
    if uuid in reversedDependencyMap:
        for dep_uuid in reversedDependencyMap[uuid]:
            visited[uuid] += dfs(dep_uuid, reversedDependencyMap, visited) + 1
    return visited[uuid]

def showAllLeafs():
    text1.delete(0, tk.END)
    leafs = []
    visited = {}
    reversedDependencyMap = {}

    # 反转依赖关系图
    for uuid, dep in dependencyMap.items():
        for dep_uuid in dep.uuids:
            if dep_uuid not in reversedDependencyMap:
                reversedDependencyMap[dep_uuid] = []
            reversedDependencyMap[dep_uuid].append(uuid)

    for uuid in reversedDependencyMap.keys():
        if uuid not in visited:
            dfs(uuid, reversedDependencyMap, visited)

    # 按照被依赖数目由大到小排序
    leafs = sorted(visited.keys(), key=lambda x: visited[x], reverse=True)

    for uuid in leafs:
        if uuid in uuidToFileName:
            text1.insert(tk.END, f"{uuid}({uuidToFileName[uuid]}), 被依赖资源数目: {visited[uuid]}")


if __name__ == "__main__":
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
    clean_button.grid(row=1, column=1, sticky="ew")

    show_root_button = tk.Button(
        root, text="显示所有根节点", command=lambda: showAllRoots()
    )
    show_root_button.grid(row=2, column=1, sticky="ew")

    show_leaf_button = tk.Button(
        root, text="显示所有叶子节点", command=lambda: showAllLeafs()
    )
    show_leaf_button.grid(row=2, column=2, sticky="ew")
    
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

    searching_uuid_label = tk.Label(root, text="当前搜索:")
    searching_uuid_label.grid(row=3, column=1, sticky="ew")

    submit_button = tk.Button(root, text="显示依赖", command=show_dependency)
    submit_button.grid(row=5, column=0, sticky="ew")

    submit_by_dep_button = tk.Button(root, text="显示被依赖", command=show_by_dependency)
    submit_by_dep_button.grid(row=5, column=1, sticky="ew")

    # 创建一个frame来包含文件列表和滚动条
    frame = ttk.Frame(root)
    frame.grid(row=6, column=0, columnspan=2, sticky='nsew')

    # 设置frame的列权重和行权重，使得Listbox可以自适应宽度和高度
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(6, weight=1)

    # 创建一个滚动条
    scrollbar = ttk.Scrollbar(frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # 创建一个Listbox来替换原有的Text控件
    text1 = tk.Listbox(frame, yscrollcommand=scrollbar.set)
    text1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def on_selection_change(event):
        s = get_selected_item()
        if type(s) == str:
            match = matcher.search(s)
            uuid = match.group(0)
            uuid_entry.delete(0, tk.END)
            uuid_entry.insert(tk.END, uuid)

    # 绑定<<ListboxSelect>>事件到on_selection_change函数
    text1.bind('<<ListboxSelect>>', on_selection_change)

    copy_text_button = tk.Button(
        root, text="复制文本框内容", 
        command=lambda: root.clipboard_append('\n'.join(text1.get(0, tk.END)))
    )
    copy_text_button.grid(row=1, column=2, sticky="ew")

    # 配置滚动条
    scrollbar.config(command=text1.yview)

    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)

    root.mainloop()

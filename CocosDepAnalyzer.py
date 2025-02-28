from functools import cache
import os
import re
import pickle
import shelve
from fuzzywuzzy import process
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import tkinter.font as tkfont

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
    root.title("Cocos依赖分析器")
    
    # 设置窗口最小尺寸
    root.minsize(800, 600)
    
    # 定义VS Code深色主题配色方案
    COLORS = {
        'bg': '#1E1E1E',           # VS Code 主背景色
        'frame_bg': '#252526',     # 侧边栏背景色
        'primary': '#007ACC',      # VS Code 蓝色
        'secondary': '#2D2D2D',    # 编辑器背景色
        'accent': '#0098FF',       # 高亮蓝色
        'text': '#D4D4D4',         # 主要文本色
        'text_light': '#CCCCCC',   # 次要文本色
        'border': '#3D3D3D',       # 边框颜色
        'button_hover': '#2B8BD4', # 按钮悬停色
        'selection': '#264F78',    # 选中背景色
        'list_hover': '#2A2D2E',   # 列表悬停色
        'title': '#569CD6'         # 标题文本色（VS Code 关键字蓝）
    }
    
    # 设置窗口背景色
    root.configure(bg=COLORS['bg'])
    
    # 配置主题和样式
    style = ttk.Style()
    style.theme_use('clam')
    
    # 配置全局字体
    default_font = tkfont.Font(family="Consolas", size=10)  # VS Code 默认字体
    heading_font = tkfont.Font(family="Consolas", size=11, weight='bold')
    
    # 自定义框架样式
    style.configure('Custom.TFrame', 
                   background=COLORS['bg'])
    
    style.configure('Custom.TLabelframe', 
                   background=COLORS['frame_bg'],
                   bordercolor=COLORS['border'],
                   darkcolor=COLORS['border'],
                   lightcolor=COLORS['border'])
    
    style.configure('Custom.TLabelframe.Label', 
                   background=COLORS['frame_bg'],
                   foreground=COLORS['title'],
                   font=heading_font)
    
    # 自定义按钮样式
    style.configure('Custom.TButton',
                   background=COLORS['primary'],
                   foreground=COLORS['text'],
                   padding=(10, 5),
                   font=default_font,
                   borderwidth=0)
    
    style.map('Custom.TButton',
              background=[('active', COLORS['button_hover']),
                         ('pressed', COLORS['primary'])],
              foreground=[('active', 'white')])
    
    # 自定义输入框样式
    style.configure('Custom.TEntry',
                   fieldbackground=COLORS['secondary'],
                   foreground=COLORS['text'],
                   padding=8,
                   font=default_font,
                   borderwidth=0)
    
    style.map('Custom.TEntry',
              fieldbackground=[('focus', COLORS['secondary'])],
              bordercolor=[('focus', COLORS['primary'])])
    
    # 自定义标签样式
    style.configure('Custom.TLabel',
                   background=COLORS['frame_bg'],
                   foreground=COLORS['text'],
                   font=default_font)
    
    # 自定义Checkbutton样式
    style.configure('Custom.TCheckbutton',
                   background=COLORS['frame_bg'],
                   foreground=COLORS['text'],
                   font=default_font)
    
    style.map('Custom.TCheckbutton',
              background=[('active', COLORS['frame_bg'])],
              foreground=[('active', COLORS['primary'])])
    
    # 创建主框架
    main_frame = ttk.Frame(root, style='Custom.TFrame')
    main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
    
    # 顶部框架 - 路径输入区域
    path_frame = ttk.LabelFrame(main_frame, text="项目配置", padding=15, style='Custom.TLabelframe')
    path_frame.pack(fill=tk.X, padx=5, pady=5)
    
    path_label = ttk.Label(path_frame, text="项目资源目录:", style='Custom.TLabel')
    path_label.grid(row=0, column=0, sticky="w", padx=5)
    
    path_entry = ttk.Entry(path_frame, style='Custom.TEntry')
    path_entry.grid(row=0, column=1, sticky="ew", padx=5)
    path_entry.insert(tk.END, getValue("path") or "")
    
    asset_count_label = ttk.Label(path_frame, text="资源数目:", style='Custom.TLabel')
    asset_count_label.grid(row=0, column=2, sticky="w", padx=5)
    
    button_frame = ttk.Frame(path_frame, style='Custom.TFrame')
    button_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=10)
    
    load_button = ttk.Button(button_frame, text="加载资源目录依赖", style='Custom.TButton', command=load_dependency)
    load_button.pack(side=tk.LEFT, padx=5)
    
    clean_button = ttk.Button(button_frame, text="清除缓存", style='Custom.TButton', command=lambda: os.remove("./dependencies.pkl"))
    clean_button.pack(side=tk.LEFT, padx=5)
    
    show_root_button = ttk.Button(button_frame, text="显示所有根节点", style='Custom.TButton', command=showAllRoots)
    show_root_button.pack(side=tk.LEFT, padx=5)
    
    show_leaf_button = ttk.Button(button_frame, text="显示所有叶子节点", style='Custom.TButton', command=showAllLeafs)
    show_leaf_button.pack(side=tk.LEFT, padx=5)
    
    path_frame.columnconfigure(1, weight=1)
    
    # UUID搜索框架
    search_frame = ttk.LabelFrame(main_frame, text="UUID搜索", padding=15, style='Custom.TLabelframe')
    search_frame.pack(fill=tk.X, padx=5, pady=5)
    
    uuid_label = ttk.Label(search_frame, text="输入UUID:", style='Custom.TLabel')
    uuid_label.grid(row=0, column=0, sticky="w", padx=5)
    
    uuid_entry = ttk.Entry(search_frame, style='Custom.TEntry')
    uuid_entry.grid(row=0, column=1, sticky="ew", padx=5)
    uuid_entry.insert(tk.END, getValue("uuid") or "")
    
    searching_uuid_label = ttk.Label(search_frame, text="当前搜索:", style='Custom.TLabel')
    searching_uuid_label.grid(row=0, column=2, sticky="w", padx=5)
    
    recursive_var = tk.IntVar()
    recursive_var.set(0)
    recursive_checkbutton = ttk.Checkbutton(search_frame, text="递归查找依赖", variable=recursive_var, style='Custom.TCheckbutton')
    recursive_checkbutton.grid(row=1, column=0, sticky="w", padx=5, pady=5)
    
    search_button_frame = ttk.Frame(search_frame, style='Custom.TFrame')
    search_button_frame.grid(row=1, column=1, columnspan=2, sticky="e", pady=5)
    
    submit_button = ttk.Button(search_button_frame, text="显示依赖", style='Custom.TButton', command=show_dependency)
    submit_button.pack(side=tk.LEFT, padx=5)
    
    submit_by_dep_button = ttk.Button(search_button_frame, text="显示被依赖", style='Custom.TButton', command=show_by_dependency)
    submit_by_dep_button.pack(side=tk.LEFT, padx=5)
    
    search_frame.columnconfigure(1, weight=1)
    
    # 结果显示框架
    result_frame = ttk.LabelFrame(main_frame, text="依赖关系", padding=15, style='Custom.TLabelframe')
    result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # 创建一个frame来包含文件列表和滚动条
    list_frame = ttk.Frame(result_frame, style='Custom.TFrame')
    list_frame.pack(fill=tk.BOTH, expand=True)
    
    # 创建一个滚动条
    scrollbar = ttk.Scrollbar(list_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # 创建一个Listbox
    text1 = tk.Listbox(list_frame, 
                       yscrollcommand=scrollbar.set,
                       font=default_font,
                       selectmode=tk.SINGLE,
                       activestyle='none',
                       background=COLORS['secondary'],
                       foreground=COLORS['text'],
                       selectbackground=COLORS['selection'],
                       selectforeground='white',
                       borderwidth=0,
                       highlightthickness=1,
                       highlightbackground=COLORS['border'],
                       highlightcolor=COLORS['primary'])
    text1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    # 添加Listbox的鼠标悬停效果
    def on_enter(event):
        widget = event.widget
        selection = widget.curselection()
        if selection:
            return  # 如果有选中项，不改变背景色
        item_id = widget.nearest(event.y)
        widget.selection_clear(0, tk.END)
        widget.selection_set(item_id)
        widget.itemconfig(item_id, bg=COLORS['list_hover'])

    def on_leave(event):
        widget = event.widget
        selection = widget.curselection()
        if selection:
            return  # 如果有选中项，不改变背景色
        for i in range(widget.size()):
            widget.itemconfig(i, bg=COLORS['secondary'])

    text1.bind('<Enter>', on_enter)
    text1.bind('<Leave>', on_leave)
    text1.bind('<Motion>', on_enter)
    
    # 美化滚动条
    style.configure("Custom.Vertical.TScrollbar",
                   background=COLORS['secondary'],
                   bordercolor=COLORS['border'],
                   arrowcolor=COLORS['text'],
                   troughcolor=COLORS['bg'],
                   width=10)  # VS Code风格的窄滚动条
    
    scrollbar.configure(style="Custom.Vertical.TScrollbar")
    
    def on_selection_change(event):
        s = get_selected_item()
        if type(s) == str:
            match = matcher.search(s)
            if match:
                uuid = match.group(0)
                uuid_entry.delete(0, tk.END)
                uuid_entry.insert(tk.END, uuid)
    
    # 绑定选择事件
    text1.bind('<<ListboxSelect>>', on_selection_change)
    
    # 底部工具栏
    toolbar_frame = ttk.Frame(result_frame, style='Custom.TFrame')
    toolbar_frame.pack(fill=tk.X, pady=(15,0))
    
    copy_text_button = ttk.Button(
        toolbar_frame, 
        text="复制列表内容", 
        style='Custom.TButton',
        command=lambda: root.clipboard_append('\n'.join(text1.get(0, tk.END)))
    )
    copy_text_button.pack(side=tk.RIGHT)
    
    if getValue("path"):
        load_dependency()
    
    root.mainloop()

# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
from datetime import datetime
import threading
import re
import webbrowser
from PIL import Image, ImageDraw
import pystray

class DesktopTodoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("桌面待办事项")
        self.root.geometry("400x600")
        
        # 设置窗口置顶
        self.root.attributes('-topmost', True)
        
        # 数据文件路径
        self.data_file = os.path.join(os.path.dirname(__file__), "todo_data.json")
        self.config_file = os.path.join(os.path.dirname(__file__), "todo_config.json")
        
        # 待办事项列表
        self.todos = []
        self.groups = ["默认分组"]  # 分组列表
        self.current_group = "默认分组"  # 当前选中的分组
        
        # 配置项
        self.show_completed = True
        self.auto_hide_enabled = False
        self.hide_threshold = 20  # 鼠标离开多少像素后隐藏
        self.close_to_tray = False  # 关闭时是否隐藏到托盘
        self.remember_choice = False  # 是否记住选择
        
        # 窗口状态
        self.is_hidden = False
        self.original_geometry = None
        self.tray_icon = None
        self.is_dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # 任务拖拽状态
        self.dragging_task = None
        self.drag_task_start_y = 0
        self.drag_placeholder = None
        
        # 加载数据和配置
        self.load_data()
        self.load_config()
        
        # 隐藏任务栏图标
        self.root.overrideredirect(False)  # 先保持正常模式
        
        # 创建UI
        self.create_ui()
        
        # 显示待办事项
        self.refresh_todo_list()
        
        # 绑定窗口事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind("<Configure>", self.on_window_move)
        
        # 延迟隐藏任务栏图标
        self.root.after(100, self.hide_from_taskbar)
        
        # 启动自动隐藏检查（但不自动移到边缘）
        if self.auto_hide_enabled:
            # 如果上次开启了侧边隐藏，本次启动时关闭它
            self.auto_hide_enabled = False
            self.auto_hide_var.set(False)
            self.save_config()
            # 不启动check_auto_hide
    
    def create_ui(self):
        # 标题栏
        title_frame = tk.Frame(self.root, bg="#4CAF50", height=50)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, text="📝 我的待办事项", 
                              font=("微软雅黑", 16, "bold"), 
                              bg="#4CAF50", fg="white")
        title_label.pack(pady=10)
        
        # 绑定标题栏拖动事件
        title_frame.bind("<Button-1>", self.start_drag)
        title_frame.bind("<B1-Motion>", self.on_drag)
        title_frame.bind("<ButtonRelease-1>", self.stop_drag)
        title_label.bind("<Button-1>", self.start_drag)
        title_label.bind("<B1-Motion>", self.on_drag)
        title_label.bind("<ButtonRelease-1>", self.stop_drag)
        
        # 设置栏
        settings_frame = tk.Frame(self.root, bg="#f0f0f0")
        settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 窗口置顶
        self.topmost_var = tk.BooleanVar(value=True)
        topmost_check = tk.Checkbutton(settings_frame, text="窗口置顶", 
                                      variable=self.topmost_var,
                                      command=self.toggle_topmost,
                                      font=("微软雅黑", 9),
                                      bg="#f0f0f0")
        topmost_check.pack(side=tk.LEFT)
        
        # 显示已完成
        self.show_completed_var = tk.BooleanVar(value=self.show_completed)
        show_completed_check = tk.Checkbutton(settings_frame, text="显示已完成", 
                                             variable=self.show_completed_var,
                                             command=self.toggle_show_completed,
                                             font=("微软雅黑", 9),
                                             bg="#f0f0f0")
        show_completed_check.pack(side=tk.LEFT, padx=(10, 0))
        
        # 侧边自动隐藏
        self.auto_hide_var = tk.BooleanVar(value=self.auto_hide_enabled)
        auto_hide_check = tk.Checkbutton(settings_frame, text="侧边隐藏", 
                                        variable=self.auto_hide_var,
                                        command=self.toggle_auto_hide,
                                        font=("微软雅黑", 9),
                                        bg="#f0f0f0")
        auto_hide_check.pack(side=tk.LEFT, padx=(10, 0))
        
        # 分组选择和管理
        group_frame = tk.Frame(self.root, bg="#f0f0f0")
        group_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        tk.Label(group_frame, text="分组:", font=("微软雅黑", 9), bg="#f0f0f0").pack(side=tk.LEFT)
        
        self.group_var = tk.StringVar(value=self.current_group)
        self.group_combo = ttk.Combobox(group_frame, textvariable=self.group_var, 
                                       values=self.groups, state="readonly",
                                       font=("微软雅黑", 9), width=12)
        self.group_combo.pack(side=tk.LEFT, padx=(5, 5))
        self.group_combo.bind("<<ComboboxSelected>>", self.on_group_change)
        
        tk.Button(group_frame, text="➕", command=self.add_group,
                 font=("微软雅黑", 9), bg="#4CAF50", fg="white",
                 relief=tk.FLAT, padx=5, cursor="hand2").pack(side=tk.LEFT, padx=2)
        
        tk.Button(group_frame, text="✏️", command=self.rename_group,
                 font=("微软雅黑", 9), bg="#2196F3", fg="white",
                 relief=tk.FLAT, padx=5, cursor="hand2").pack(side=tk.LEFT, padx=2)
        
        tk.Button(group_frame, text="🗑️", command=self.delete_group,
                 font=("微软雅黑", 9), bg="#f44336", fg="white",
                 relief=tk.FLAT, padx=5, cursor="hand2").pack(side=tk.LEFT, padx=2)
        
        # 输入框区域
        input_frame = tk.Frame(self.root, bg="#f0f0f0")
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.task_entry = tk.Entry(input_frame, font=("微软雅黑", 12), 
                                   relief=tk.FLAT, bd=2)
        self.task_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
        self.task_entry.bind("<Return>", lambda e: self.add_task())
        
        add_btn = tk.Button(input_frame, text="添加", 
                           command=self.add_task,
                           font=("微软雅黑", 11, "bold"),
                           bg="#4CAF50", fg="white",
                           relief=tk.FLAT, padx=15, cursor="hand2")
        add_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # 待办事项列表区域
        list_frame = tk.Frame(self.root, bg="white")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # 滚动条
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Canvas用于滚动
        self.canvas = tk.Canvas(list_frame, bg="white", 
                               yscrollcommand=scrollbar.set,
                               highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.canvas.yview)
        
        # 在Canvas中创建Frame
        self.todo_container = tk.Frame(self.canvas, bg="white")
        self.canvas_window = self.canvas.create_window((0, 0), 
                                                       window=self.todo_container, 
                                                       anchor="nw")
        
        # 绑定配置事件
        self.todo_container.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        
        # 统计信息
        self.stats_label = tk.Label(self.root, text="", 
                                   font=("微软雅黑", 10),
                                   bg="#f0f0f0", fg="#666")
        self.stats_label.pack(fill=tk.X, padx=10, pady=(0, 10))
    
    def on_frame_configure(self, event=None):
        """更新滚动区域"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def on_canvas_configure(self, event):
        """调整canvas窗口宽度"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def toggle_topmost(self):
        """切换窗口置顶状态"""
        self.root.attributes('-topmost', self.topmost_var.get())
    
    def toggle_show_completed(self):
        """切换显示已完成任务"""
        self.show_completed = self.show_completed_var.get()
        self.save_config()
        self.refresh_todo_list()
    
    def toggle_auto_hide(self):
        """切换侧边自动隐藏"""
        self.auto_hide_enabled = self.auto_hide_var.get()
        self.save_config()
        
        if self.auto_hide_enabled:
            # 移动窗口到屏幕右侧
            self.move_to_screen_edge()
            self.check_auto_hide()
        else:
            # 恢复窗口位置
            if self.is_hidden:
                self.show_window()
    
    def hide_from_taskbar(self):
        """从任务栏隐藏窗口图标"""
        try:
            # 使用Windows API隐藏任务栏图标
            import ctypes
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_APPWINDOW = 0x00040000
            
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = style & ~WS_EX_APPWINDOW
            style = style | WS_EX_TOOLWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            
            # 刷新窗口
            self.root.withdraw()
            self.root.deiconify()
        except:
            pass
    
    def start_drag(self, event):
        """开始拖动"""
        self.is_dragging = True
        self.drag_start_x = event.x_root - self.root.winfo_x()
        self.drag_start_y = event.y_root - self.root.winfo_y()
    
    def on_drag(self, event):
        """拖动中"""
        if self.is_dragging:
            x = event.x_root - self.drag_start_x
            y = event.y_root - self.drag_start_y
            self.root.geometry(f"+{x}+{y}")
    
    def stop_drag(self, event):
        """停止拖动"""
        self.is_dragging = False
        # 检查是否拖到屏幕边缘
        self.check_edge_snap()
    
    def on_window_move(self, event):
        """窗口移动事件"""
        if not self.is_dragging:
            return
        # 实时检查是否接近边缘
        self.check_edge_snap_realtime()
    
    def check_edge_snap_realtime(self):
        """实时检查边缘吸附"""
        screen_width = self.root.winfo_screenwidth()
        win_x = self.root.winfo_x()
        win_width = self.root.winfo_width()
        
        # 判断是否接近右侧边缘（50像素内）
        if win_x + win_width >= screen_width - 50:
            # 显示提示（可选）
            pass
    
    def check_edge_snap(self):
        """检查边缘吸附并自动开启/关闭侧边隐藏"""
        screen_width = self.root.winfo_screenwidth()
        win_x = self.root.winfo_x()
        win_width = self.root.winfo_width()
        
        # 判断是否拖到右侧边缘（30像素内）
        if win_x + win_width >= screen_width - 30:
            # 自动开启侧边隐藏
            if not self.auto_hide_enabled:
                self.auto_hide_var.set(True)
                self.auto_hide_enabled = True
                self.save_config()
                self.move_to_screen_edge()
                self.check_auto_hide()
        else:
            # 如果拖离边缘，关闭侧边隐藏
            if self.auto_hide_enabled:
                # 检查是否明显离开边缘（超过100像素）
                if win_x + win_width < screen_width - 100:
                    self.auto_hide_var.set(False)
                    self.auto_hide_enabled = False
                    self.save_config()
                    if self.is_hidden:
                        self.show_window()
    
    def move_to_screen_edge(self):
        """移动窗口到屏幕右侧边缘"""
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        # 保存原始位置
        if not self.original_geometry:
            self.original_geometry = self.root.geometry()
        
        # 移动到右侧边缘
        x = screen_width - window_width
        y = (self.root.winfo_screenheight() - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    def check_auto_hide(self):
        """检查是否需要自动隐藏"""
        if not self.auto_hide_enabled:
            return
        
        try:
            # 获取鼠标位置
            mouse_x = self.root.winfo_pointerx()
            mouse_y = self.root.winfo_pointery()
            
            # 获取窗口位置
            win_x = self.root.winfo_x()
            win_y = self.root.winfo_y()
            win_width = self.root.winfo_width()
            win_height = self.root.winfo_height()
            
            # 判断鼠标是否在窗口区域内
            mouse_in_window = (win_x <= mouse_x <= win_x + win_width and 
                             win_y <= mouse_y <= win_y + win_height)
            
            # 判断鼠标是否靠近屏幕右侧边缘（用于从隐藏状态展开）
            screen_width = self.root.winfo_screenwidth()
            mouse_near_edge = mouse_x >= screen_width - self.hide_threshold
            
            # 逻辑：
            # 1. 如果鼠标在窗口内，保持显示状态
            # 2. 如果鼠标不在窗口内且不靠近边缘，隐藏窗口
            # 3. 如果鼠标靠近边缘（即使不在窗口内），展开窗口
            
            if mouse_in_window:
                # 鼠标在窗口内，必须显示
                if self.is_hidden:
                    self.show_window()
            elif mouse_near_edge:
                # 鼠标靠近边缘，展开窗口
                if self.is_hidden:
                    self.show_window()
            else:
                # 鼠标既不在窗口内也不靠近边缘，隐藏窗口
                if not self.is_hidden:
                    self.hide_window()
        except:
            pass
        
        # 继续检查
        self.root.after(100, self.check_auto_hide)
    
    def hide_window(self):
        """隐藏窗口到侧边"""
        if self.is_hidden:
            return
        
        self.is_hidden = True
        screen_width = self.root.winfo_screenwidth()
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        y = self.root.winfo_y()
        
        # 保存当前窗口大小，隐藏时保持原大小，只移动位置
        # 移动到屏幕右侧，只露出5像素
        x = screen_width - 5
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    def show_window(self):
        """显示窗口"""
        if not self.is_hidden:
            return
        
        self.is_hidden = False
        screen_width = self.root.winfo_screenwidth()
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        y = self.root.winfo_y()
        
        # 完全显示窗口，保持原窗口大小
        x = screen_width - window_width
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    def add_task(self):
        """添加新任务"""
        task_text = self.task_entry.get().strip()
        if not task_text:
            messagebox.showwarning("提示", "请输入待办事项内容")
            return
        
        todo = {
            "id": datetime.now().timestamp(),
            "text": task_text,
            "completed": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "order": len([t for t in self.todos if t.get("group", "默认分组") == self.current_group]),
            "group": self.current_group  # 添加分组字段
        }
        
        self.todos.append(todo)
        self.task_entry.delete(0, tk.END)
        self.save_data()
        self.refresh_todo_list()
    
    def on_group_change(self, event=None):
        """分组切换"""
        self.current_group = self.group_var.get()
        self.save_config()
        self.refresh_todo_list()
    
    def add_group(self):
        """添加新分组"""
        dialog = tk.Toplevel(self.root)
        dialog.title("新建分组")
        dialog.geometry("300x120")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 居中显示
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text="分组名称:", font=("微软雅黑", 10)).pack(pady=(20, 5))
        entry = tk.Entry(dialog, font=("微软雅黑", 11), width=25)
        entry.pack(pady=5)
        entry.focus()
        
        def save():
            name = entry.get().strip()
            if not name:
                messagebox.showwarning("提示", "分组名称不能为空", parent=dialog)
                return
            if name in self.groups:
                messagebox.showwarning("提示", "分组名称已存在", parent=dialog)
                return
            
            self.groups.append(name)
            self.group_combo['values'] = self.groups
            self.group_var.set(name)
            self.current_group = name
            self.save_config()
            self.refresh_todo_list()
            dialog.destroy()
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="确定", command=save,
                 font=("微软雅黑", 9), bg="#4CAF50", fg="white",
                 relief=tk.FLAT, padx=15, cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="取消", command=dialog.destroy,
                 font=("微软雅黑", 9), bg="#999", fg="white",
                 relief=tk.FLAT, padx=15, cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        entry.bind("<Return>", lambda e: save())
        dialog.bind("<Escape>", lambda e: dialog.destroy())
    
    def rename_group(self):
        """重命名分组"""
        if self.current_group == "默认分组":
            messagebox.showinfo("提示", "默认分组不能重命名")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("重命名分组")
        dialog.geometry("300x120")
        dialog.transient(self.root)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text="新名称:", font=("微软雅黑", 10)).pack(pady=(20, 5))
        entry = tk.Entry(dialog, font=("微软雅黑", 11), width=25)
        entry.insert(0, self.current_group)
        entry.pack(pady=5)
        entry.focus()
        entry.select_range(0, tk.END)
        
        def save():
            new_name = entry.get().strip()
            if not new_name:
                messagebox.showwarning("提示", "分组名称不能为空", parent=dialog)
                return
            if new_name in self.groups and new_name != self.current_group:
                messagebox.showwarning("提示", "分组名称已存在", parent=dialog)
                return
            
            old_name = self.current_group
            # 更新分组列表
            idx = self.groups.index(old_name)
            self.groups[idx] = new_name
            
            # 更新所有任务的分组
            for todo in self.todos:
                if todo.get("group") == old_name:
                    todo["group"] = new_name
            
            self.current_group = new_name
            self.group_combo['values'] = self.groups
            self.group_var.set(new_name)
            self.save_data()
            self.save_config()
            self.refresh_todo_list()
            dialog.destroy()
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="确定", command=save,
                 font=("微软雅黑", 9), bg="#4CAF50", fg="white",
                 relief=tk.FLAT, padx=15, cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="取消", command=dialog.destroy,
                 font=("微软雅黑", 9), bg="#999", fg="white",
                 relief=tk.FLAT, padx=15, cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        entry.bind("<Return>", lambda e: save())
        dialog.bind("<Escape>", lambda e: dialog.destroy())
    
    def delete_group(self):
        """删除分组"""
        if self.current_group == "默认分组":
            messagebox.showinfo("提示", "默认分组不能删除")
            return
        
        # 检查分组是否有任务
        group_tasks = [t for t in self.todos if t.get("group", "默认分组") == self.current_group]
        if group_tasks:
            result = messagebox.askyesno("确认删除", 
                                        f"分组'{self.current_group}'中有{len(group_tasks)}个任务\n删除后这些任务将移到'默认分组'\n\n确定要删除吗？")
            if not result:
                return
            
            # 将任务移到默认分组
            for todo in group_tasks:
                todo["group"] = "默认分组"
        
        # 删除分组
        self.groups.remove(self.current_group)
        self.current_group = "默认分组"
        self.group_combo['values'] = self.groups
        self.group_var.set(self.current_group)
        self.save_data()
        self.save_config()
        self.refresh_todo_list()
    
    def toggle_task(self, todo_id):
        """切换任务完成状态"""
        for todo in self.todos:
            if todo["id"] == todo_id:
                todo["completed"] = not todo["completed"]
                break
        self.save_data()
        self.refresh_todo_list()
    
    def edit_task(self, todo_id):
        """编辑任务"""
        todo = None
        for t in self.todos:
            if t["id"] == todo_id:
                todo = t
                break
        
        if not todo:
            return
        
        # 创建编辑对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("编辑任务")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 根据内容自适应窗口大小
        text_lines = todo["text"].count('\n') + 1
        text_length = len(todo["text"])
        
        if text_length > 200 or text_lines > 5:
            dialog_width = 500
            dialog_height = min(400, 200 + text_lines * 20)
        else:
            dialog_width = 450
            dialog_height = 180
        
        dialog.geometry(f"{dialog_width}x{dialog_height}")
        
        # 居中显示
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # 标签
        tk.Label(dialog, text="任务内容:", font=("微软雅黑", 11)).pack(pady=(15, 5), padx=15, anchor="w")
        
        # 使用Text组件支持多行和自动换行
        text_frame = tk.Frame(dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        
        text_widget = tk.Text(text_frame, 
                             font=("微软雅黑", 11),
                             wrap=tk.WORD,
                             relief=tk.SOLID,
                             bd=1,
                             padx=5,
                             pady=5)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(text_frame, command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)
        
        text_widget.insert("1.0", todo["text"])
        text_widget.focus()
        
        def save_edit():
            new_text = text_widget.get("1.0", "end-1c").strip()
            if new_text:
                todo["text"] = new_text
                self.save_data()
                self.refresh_todo_list()
                dialog.destroy()
            else:
                messagebox.showwarning("提示", "任务内容不能为空", parent=dialog)
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=15)
        
        tk.Button(btn_frame, text="保存", command=save_edit,
                 font=("微软雅黑", 10), bg="#4CAF50", fg="white",
                 relief=tk.FLAT, padx=20, cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="取消", command=dialog.destroy,
                 font=("微软雅黑", 10), bg="#999", fg="white",
                 relief=tk.FLAT, padx=20, cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        text_widget.bind("<Control-Return>", lambda e: save_edit())
        dialog.bind("<Escape>", lambda e: dialog.destroy())
    
    def delete_task(self, todo_id):
        """删除任务"""
        self.todos = [t for t in self.todos if t["id"] != todo_id]
        for i, todo in enumerate(self.todos):
            todo["order"] = i
        self.save_data()
        self.refresh_todo_list()
    
    def move_task_up(self, todo_id):
        """向上移动任务（仅在当前分组内）"""
        # 获取当前分组的任务，按order排序
        group_todos = [t for t in self.todos if t.get("group", "默认分组") == self.current_group]
        sorted_group_todos = sorted(group_todos, key=lambda x: x.get("order", 0))
        
        # 找到当前任务的索引
        current_index = -1
        for i, todo in enumerate(sorted_group_todos):
            if todo["id"] == todo_id:
                current_index = i
                break
        
        # 如果不是第一个，与上一个交换
        if current_index > 0:
            # 交换两个任务在列表中的位置
            sorted_group_todos[current_index], sorted_group_todos[current_index - 1] = \
                sorted_group_todos[current_index - 1], sorted_group_todos[current_index]
            
            # 重新分配order值
            for i, todo in enumerate(sorted_group_todos):
                todo["order"] = i
            
            self.save_data()
            self.refresh_todo_list()
    
    def start_drag_task(self, event, item_frame, todo_id):
        """开始拖拽任务"""
        self.dragging_task = todo_id
        self.drag_task_start_y = event.y_root
        # 改变拖拽项的样式
        item_frame.config(relief=tk.RAISED, bd=2)
    
    def on_drag_task(self, event, item_frame):
        """拖拽任务中"""
        if self.dragging_task is None:
            return
        
        # 计算拖拽距离
        delta_y = event.y_root - self.drag_task_start_y
        
        # 获取所有任务项
        all_items = [w for w in self.todo_container.winfo_children() 
                     if isinstance(w, tk.Frame) and hasattr(w, 'todo_id')]
        
        if not all_items:
            return
        
        # 找到当前拖拽项的索引
        drag_index = -1
        for i, item in enumerate(all_items):
            if item.todo_id == self.dragging_task:
                drag_index = i
                break
        
        if drag_index == -1:
            return
        
        # 判断是否需要交换位置
        if delta_y > 50 and drag_index < len(all_items) - 1:
            # 向下移动
            self.swap_task_display(drag_index, drag_index + 1)
            self.drag_task_start_y = event.y_root
        elif delta_y < -50 and drag_index > 0:
            # 向上移动
            self.swap_task_display(drag_index, drag_index - 1)
            self.drag_task_start_y = event.y_root
    
    def stop_drag_task(self, event, item_frame, todo_id):
        """停止拖拽任务"""
        if self.dragging_task is None:
            return
        
        # 恢复样式
        item_frame.config(relief=tk.SOLID, bd=1)
        
        # 保存新的顺序
        self.save_task_order()
        
        self.dragging_task = None
        self.drag_task_start_y = 0
    
    def swap_task_display(self, index1, index2):
        """交换两个任务的显示位置"""
        all_items = [w for w in self.todo_container.winfo_children() 
                     if isinstance(w, tk.Frame) and hasattr(w, 'todo_id')]
        
        if index1 < 0 or index2 < 0 or index1 >= len(all_items) or index2 >= len(all_items):
            return
        
        # 获取两个任务的ID
        todo_id1 = all_items[index1].todo_id
        todo_id2 = all_items[index2].todo_id
        
        # 在数据中找到这两个任务
        group_todos = [t for t in self.todos if t.get("group", "默认分组") == self.current_group]
        sorted_group_todos = sorted(group_todos, key=lambda x: x.get("order", 0))
        
        task1 = None
        task2 = None
        for todo in sorted_group_todos:
            if todo["id"] == todo_id1:
                task1 = todo
            if todo["id"] == todo_id2:
                task2 = todo
        
        if task1 and task2:
            # 交换order值
            task1["order"], task2["order"] = task2["order"], task1["order"]
            # 立即刷新显示
            self.refresh_todo_list()
    
    def save_task_order(self):
        """保存任务顺序"""
        self.save_data()
    
    def move_task_down(self, todo_id):
        """向下移动任务（仅在当前分组内）"""
        # 获取当前分组的任务，按order排序
        group_todos = [t for t in self.todos if t.get("group", "默认分组") == self.current_group]
        sorted_group_todos = sorted(group_todos, key=lambda x: x.get("order", 0))
        
        # 找到当前任务的索引
        current_index = -1
        for i, todo in enumerate(sorted_group_todos):
            if todo["id"] == todo_id:
                current_index = i
                break
        
        # 如果不是最后一个，与下一个交换
        if current_index >= 0 and current_index < len(sorted_group_todos) - 1:
            # 交换两个任务在列表中的位置
            sorted_group_todos[current_index], sorted_group_todos[current_index + 1] = \
                sorted_group_todos[current_index + 1], sorted_group_todos[current_index]
            
            # 重新分配order值
            for i, todo in enumerate(sorted_group_todos):
                todo["order"] = i
            
            self.save_data()
            self.refresh_todo_list()
    
    def refresh_todo_list(self):
        """刷新待办事项列表显示"""
        for widget in self.todo_container.winfo_children():
            widget.destroy()
        
        # 筛选当前分组的任务
        group_todos = [t for t in self.todos if t.get("group", "默认分组") == self.current_group]
        
        if self.show_completed:
            display_todos = group_todos
        else:
            display_todos = [t for t in group_todos if not t["completed"]]
        
        if not display_todos:
            if not group_todos:
                empty_text = f"'{self.current_group}'暂无待办事项\n点击上方添加新任务"
            else:
                empty_text = "所有任务已完成！\n勾选\"显示已完成\"查看"
            empty_label = tk.Label(self.todo_container, 
                                  text=empty_text,
                                  font=("微软雅黑", 12),
                                  fg="#999", bg="white",
                                  pady=50)
            empty_label.pack()
        else:
            if display_todos and "order" not in display_todos[0]:
                for i, todo in enumerate(self.todos):
                    if "order" not in todo:
                        todo["order"] = i
            
            sorted_todos = sorted(display_todos, key=lambda x: x.get("order", 0))
            
            for i, todo in enumerate(sorted_todos):
                full_index = self.todos.index(todo)
                self.create_todo_item(todo, full_index)
        
        # 更新统计信息（只统计当前分组）
        total = len(group_todos)
        completed = sum(1 for t in group_todos if t["completed"])
        pending = total - completed
        
        if self.show_completed:
            self.stats_label.config(
                text=f"[{self.current_group}] 总计: {total} | 待完成: {pending} | 已完成: {completed}"
            )
        else:
            self.stats_label.config(
                text=f"[{self.current_group}] 待完成: {pending} | 已完成: {completed}(已隐藏)"
            )
    
    def create_todo_item(self, todo, index):
        """创建单个待办事项显示项"""
        item_frame = tk.Frame(self.todo_container, 
                             bg="#f9f9f9" if not todo["completed"] else "#e8e8e8",
                             relief=tk.SOLID, bd=1)
        item_frame.pack(fill=tk.X, padx=5, pady=3)
        
        # 保存item_frame的引用，用于拖拽
        item_frame.todo_id = todo["id"]
        
        left_frame = tk.Frame(item_frame, bg=item_frame["bg"])
        left_frame.pack(side=tk.LEFT, padx=5)
        
        drag_label = tk.Label(left_frame, text="☰", 
                             font=("微软雅黑", 12),
                             fg="#999",
                             bg=item_frame["bg"],
                             cursor="hand2")
        drag_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # 绑定拖拽事件
        drag_label.bind("<Button-1>", lambda e: self.start_drag_task(e, item_frame, todo["id"]))
        drag_label.bind("<B1-Motion>", lambda e: self.on_drag_task(e, item_frame))
        drag_label.bind("<ButtonRelease-1>", lambda e: self.stop_drag_task(e, item_frame, todo["id"]))
        
        check_var = tk.BooleanVar(value=todo["completed"])
        check_btn = tk.Checkbutton(left_frame, 
                                  variable=check_var,
                                  command=lambda: self.toggle_task(todo["id"]),
                                  bg=item_frame["bg"],
                                  cursor="hand2")
        check_btn.pack(side=tk.LEFT)
        
        text_style = ("微软雅黑", 11)
        text_fg = "#999" if todo["completed"] else "#333"
        
        text_frame = tk.Frame(item_frame, bg=item_frame["bg"])
        text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=8)
        
        # 使用Text组件支持超链接
        full_text = todo["text"]  # 保留完整文本用于超链接匹配
        display_text = full_text
        if len(display_text) > 60:
            display_text = display_text[:60] + "..."
        
        # 计算需要的高度
        lines = display_text.count('\n') + 1
        height = min(lines, 3)
        
        task_text = tk.Text(text_frame,
                           font=text_style,
                           fg=text_fg,
                           bg=item_frame["bg"],
                           wrap=tk.WORD,
                           height=height,
                           width=25,  # 限制宽度
                           relief=tk.FLAT,
                           cursor="hand2",
                           state=tk.NORMAL)
        task_text.pack(anchor="w")
        
        # 插入文本
        task_text.insert("1.0", display_text)
        
        # 查找并标记超链接（在完整文本中查找）
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = list(re.finditer(url_pattern, full_text))
        
        # 配置超链接样式
        task_text.tag_config("hyperlink", foreground="#2196F3", underline=True)
        task_text.tag_config("hyperlink_hover", foreground="#1976D2", underline=True)
        
        for match in urls:
            url = match.group()
            start_pos = match.start()
            end_pos = match.end()
            
            # 只标记在显示文本范围内的部分
            if start_pos < len(display_text):
                # 如果URL被截断，只标记显示的部分
                display_end = min(end_pos, len(display_text) - 3 if len(full_text) > 60 else len(display_text))
                
                start_idx = f"1.0+{start_pos}c"
                end_idx = f"1.0+{display_end}c"
                
                task_text.tag_add("hyperlink", start_idx, end_idx)
                # 绑定完整URL（不是截断的）
                task_text.tag_bind("hyperlink", "<Button-1>", 
                                 lambda e, u=url: webbrowser.open(u))
                task_text.tag_bind("hyperlink", "<Enter>", 
                                 lambda e: task_text.config(cursor="hand2"))
                task_text.tag_bind("hyperlink", "<Leave>", 
                                 lambda e: task_text.config(cursor="hand2"))
        
        # 禁用编辑
        task_text.config(state=tk.DISABLED)
        
        # 双击编辑
        task_text.bind("<Double-Button-1>", lambda e, tid=todo["id"]: self.edit_task(tid))
        
        if todo["completed"]:
            task_text.config(font=("微软雅黑", 11, "overstrike"))
        
        time_label = tk.Label(text_frame,
                             text=todo["created_at"],
                             font=("微软雅黑", 8),
                             fg="#aaa",
                             bg=item_frame["bg"],
                             anchor="w",
                             cursor="hand2")
        time_label.pack(anchor="w")
        time_label.bind("<Double-Button-1>", lambda e, tid=todo["id"]: self.edit_task(tid))
        
        right_frame = tk.Frame(item_frame, bg=item_frame["bg"])
        right_frame.pack(side=tk.RIGHT, padx=5)
        
        # 获取当前分组的任务列表用于排序（按order排序后的）
        group_todos = [t for t in self.todos if t.get("group", "默认分组") == self.current_group]
        sorted_group_todos = sorted(group_todos, key=lambda x: x.get("order", 0))
        
        # 通过ID查找索引
        current_index_in_group = -1
        for i, t in enumerate(sorted_group_todos):
            if t["id"] == todo["id"]:
                current_index_in_group = i
                break
        
        if current_index_in_group > 0:
            up_btn = tk.Button(right_frame, text="↑",
                              command=lambda: self.move_task_up(todo["id"]),
                              font=("微软雅黑", 10, "bold"),
                              fg="#2196F3",
                              bg=item_frame["bg"],
                              relief=tk.FLAT,
                              cursor="hand2",
                              padx=5)
            up_btn.pack(side=tk.LEFT)
        
        if current_index_in_group < len(sorted_group_todos) - 1:
            down_btn = tk.Button(right_frame, text="↓",
                                command=lambda: self.move_task_down(todo["id"]),
                                font=("微软雅黑", 10, "bold"),
                                fg="#2196F3",
                                bg=item_frame["bg"],
                                relief=tk.FLAT,
                                cursor="hand2",
                                padx=5)
            down_btn.pack(side=tk.LEFT)
        
        delete_btn = tk.Button(right_frame, 
                              text="✕",
                              command=lambda: self.delete_task(todo["id"]),
                              font=("微软雅黑", 12, "bold"),
                              fg="#f44336",
                              bg=item_frame["bg"],
                              relief=tk.FLAT,
                              cursor="hand2",
                              padx=5)
        delete_btn.pack(side=tk.LEFT, padx=(5, 0))
    
    def load_data(self):
        """从文件加载数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.todos = json.load(f)
                    # 为旧数据添加group字段
                    for todo in self.todos:
                        if "group" not in todo:
                            todo["group"] = "默认分组"
                    
                    # 为每个分组的任务初始化order值
                    groups = {}
                    for todo in self.todos:
                        group = todo.get("group", "默认分组")
                        if group not in groups:
                            groups[group] = []
                        groups[group].append(todo)
                    
                    # 为每个分组的任务分配连续的order值
                    for group, todos in groups.items():
                        for i, todo in enumerate(todos):
                            if "order" not in todo:
                                todo["order"] = i
            except Exception as e:
                print(f"加载数据失败: {e}")
                self.todos = []
        else:
            self.todos = []
    
    def save_data(self):
        """保存数据到文件"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.todos, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存数据失败: {e}")
    
    def load_config(self):
        """加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.show_completed = config.get("show_completed", True)
                    self.auto_hide_enabled = config.get("auto_hide_enabled", False)
                    self.close_to_tray = config.get("close_to_tray", False)
                    self.remember_choice = config.get("remember_choice", False)
                    self.groups = config.get("groups", ["默认分组"])
                    self.current_group = config.get("current_group", "默认分组")
                    # 确保当前分组在分组列表中
                    if self.current_group not in self.groups:
                        self.current_group = "默认分组"
            except Exception as e:
                print(f"加载配置失败: {e}")
    
    def save_config(self):
        """保存配置"""
        try:
            config = {
                "show_completed": self.show_completed,
                "auto_hide_enabled": self.auto_hide_enabled,
                "close_to_tray": self.close_to_tray,
                "remember_choice": self.remember_choice,
                "groups": self.groups,
                "current_group": self.current_group
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def create_tray_icon(self):
        """创建系统托盘图标"""
        # 创建图标图像
        image = Image.new('RGB', (64, 64), color='#4CAF50')
        draw = ImageDraw.Draw(image)
        draw.rectangle([16, 16, 48, 48], fill='white')
        draw.text((20, 18), "TODO", fill='#4CAF50')
        
        # 创建菜单
        menu = pystray.Menu(
            pystray.MenuItem("显示", self.show_from_tray, default=True),
            pystray.MenuItem("退出", self.quit_app)
        )
        
        # 创建托盘图标，设置左键点击事件
        self.tray_icon = pystray.Icon("todo_app", image, "桌面待办", menu)
        # 设置左键单击显示窗口
        self.tray_icon.on_click = self.on_tray_click
    
    def on_tray_click(self, icon, button):
        """托盘图标点击事件"""
        # 无论左键右键都显示窗口
        self.show_from_tray()
    
    def show_from_tray(self, icon=None, item=None):
        """从托盘显示窗口"""
        self.root.after(0, self._show_window_from_tray)
    
    def _show_window_from_tray(self):
        """在主线程中显示窗口"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        # 如果开启了侧边隐藏，确保窗口完全显示
        if self.auto_hide_enabled and self.is_hidden:
            self.show_window()
    
    def hide_to_tray(self):
        """隐藏到系统托盘"""
        self.root.withdraw()
        if not self.tray_icon:
            self.create_tray_icon()
            # 在新线程中运行托盘图标
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
    
    def quit_app(self, icon=None, item=None):
        """退出应用"""
        if self.tray_icon:
            self.tray_icon.stop()
        self.save_data()
        self.save_config()
        self.root.quit()
    
    def on_closing(self):
        """窗口关闭时"""
        # 如果已经记住选择，直接执行
        if self.remember_choice:
            if self.close_to_tray:
                self.hide_to_tray()
            else:
                self.quit_app()
            return
        
        # 创建自定义对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("关闭选项")
        dialog.geometry("350x200")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # 居中显示
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # 提示文本
        tk.Label(dialog, text="选择关闭方式", 
                font=("微软雅黑", 12, "bold")).pack(pady=(20, 10))
        
        # 选项框架
        option_frame = tk.Frame(dialog)
        option_frame.pack(pady=10)
        
        # 单选按钮
        close_option = tk.IntVar(value=1 if self.close_to_tray else 0)
        
        tk.Radiobutton(option_frame, text="隐藏到系统托盘（后台运行）", 
                      variable=close_option, value=1,
                      font=("微软雅黑", 10)).pack(anchor="w", pady=5)
        
        tk.Radiobutton(option_frame, text="直接退出程序", 
                      variable=close_option, value=0,
                      font=("微软雅黑", 10)).pack(anchor="w", pady=5)
        
        # 记住选择复选框
        remember_var = tk.BooleanVar(value=False)
        
        def on_remember_change():
            """勾选记住选择时立即执行"""
            if remember_var.get():
                # 保存选择
                self.close_to_tray = (close_option.get() == 1)
                self.remember_choice = True
                self.save_config()
                
                dialog.destroy()
                
                # 执行相应操作
                if self.close_to_tray:
                    self.hide_to_tray()
                else:
                    self.quit_app()
        
        tk.Checkbutton(option_frame, text="记住我的选择，下次不再询问", 
                      variable=remember_var,
                      command=on_remember_change,
                      font=("微软雅黑", 9),
                      fg="#666").pack(anchor="w", pady=(10, 0))
        
        # 按钮框架
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=20)
        
        def on_confirm():
            # 保存选择
            self.close_to_tray = (close_option.get() == 1)
            self.remember_choice = remember_var.get()
            self.save_config()
            
            dialog.destroy()
            
            # 执行相应操作
            if self.close_to_tray:
                self.hide_to_tray()
            else:
                self.quit_app()
        
        def on_cancel():
            dialog.destroy()
        
        tk.Button(btn_frame, text="确定", command=on_confirm,
                 font=("微软雅黑", 10), bg="#4CAF50", fg="white",
                 relief=tk.FLAT, padx=25, cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="取消", command=on_cancel,
                 font=("微软雅黑", 10), bg="#999", fg="white",
                 relief=tk.FLAT, padx=25, cursor="hand2").pack(side=tk.LEFT, padx=5)
        
        # 绑定回车和ESC键
        dialog.bind("<Return>", lambda e: on_confirm())
        dialog.bind("<Escape>", lambda e: on_cancel())

def main():
    root = tk.Tk()
    app = DesktopTodoApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

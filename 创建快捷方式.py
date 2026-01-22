# -*- coding: utf-8 -*-
"""
桌面待办事项 - 快捷方式创建工具
自动在桌面创建快捷方式
"""
import os
import sys

def create_shortcut():
    """创建桌面快捷方式"""
    try:
        # 获取当前脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Python路径
        python_path = r"C:\Users\黍离\AppData\Local\Programs\Python\Python313\pythonw.exe"
        
        # 主程序路径
        main_script = os.path.join(script_dir, "desktop_todo.py")
        
        # 桌面路径
        desktop = r"E:\Desktop"
        shortcut_path = os.path.join(desktop, "桌面待办.lnk")
        
        # 使用PowerShell创建快捷方式
        import subprocess
        ps_command = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{python_path}"
$Shortcut.Arguments = '"{main_script}"'
$Shortcut.WorkingDirectory = "{script_dir}"
$Shortcut.Description = "桌面待办事项"
$Shortcut.Save()
'''
        
        result = subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ 快捷方式创建成功！")
            print(f"位置：{shortcut_path}")
            print("\n现在可以双击桌面上的'桌面待办'图标启动程序了")
        else:
            print(f"❌ 创建失败：{result.stderr}")
            
    except Exception as e:
        print(f"❌ 发生错误：{e}")

if __name__ == "__main__":
    create_shortcut()
    input("\n按回车键退出...")

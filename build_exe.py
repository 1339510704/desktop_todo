# -*- coding: utf-8 -*-
"""
桌面待办事项打包脚本
使用PyInstaller将程序打包成独立的exe文件
"""
import os
import subprocess
import sys

def build_exe():
    """打包程序为exe"""
    print("开始打包桌面待办事项程序...")
    
    # PyInstaller命令
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name=桌面待办",
        "--onefile",  # 打包成单个exe文件
        "--windowed",  # 不显示控制台窗口
        "--icon=NONE",  # 暂时不设置图标
        "--add-data=使用说明.md;.",  # 包含使用说明
        "--clean",  # 清理临时文件
        "desktop_todo.py"
    ]
    
    try:
        # 执行打包
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ 打包成功！")
        print(f"\n生成的exe文件位置：{os.path.abspath('dist/桌面待办.exe')}")
        print("\n使用说明：")
        print("1. 将 dist/桌面待办.exe 发送给其他人")
        print("2. 双击exe文件即可运行，无需安装Python")
        print("3. 首次运行可能需要几秒钟启动时间")
        print("4. 数据文件会自动保存在exe所在目录")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 打包失败: {e}")
        print(f"错误信息: {e.stderr}")
    except Exception as e:
        print(f"❌ 发生错误: {e}")

if __name__ == "__main__":
    build_exe()
    input("\n按回车键退出...")

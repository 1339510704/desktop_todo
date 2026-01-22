@echo off
chcp 65001 >nul
echo ========================================
echo   桌面待办项目 - Git推送工具
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 检查Git状态...
git status
echo.

echo [2/3] 尝试推送到GitHub...
echo.
git push origin main

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   ✅ 推送成功！
    echo ========================================
    echo.
    echo 访问以下链接查看更新：
    echo https://github.com/1339510704/desktop_todo
    echo.
) else (
    echo.
    echo ========================================
    echo   ❌ 推送失败
    echo ========================================
    echo.
    echo 可能的原因：
    echo 1. 网络连接问题
    echo 2. 需要配置代理
    echo 3. 需要GitHub账号认证
    echo.
    echo 解决方案：
    echo 1. 使用GitHub Desktop（推荐）
    echo 2. 配置代理后重试
    echo 3. 查看"Git推送说明.md"获取详细帮助
    echo.
)

pause

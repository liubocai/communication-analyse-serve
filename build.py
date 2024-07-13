import sys
from PyInstaller.__main__ import run

if __name__ == '__main__':
    # 替换为你的Flask应用程序的入口文件
    entry_point = 'app.py'
    # 替换为你的Flask应用程序的名称
    app_name = 'my_flask_app'

    # 使用PyInstaller打包应用程序
    opts = [
        '--name={}'.format(app_name),
        '--onefile',
        '--windowed',
        # 添加其他PyInstaller参数，如果需要的话
    ]
    args = ['pyinstaller'] + opts + [entry_point]
    run(args)
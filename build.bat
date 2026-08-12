@echo off
REM PyInstaller を使って単一 exe を生成します。
REM 事前に仮想環境を有効にし、requirements.txt のパッケージをインストールしてください。

pyinstaller --onefile --windowed --name imgconv --icon imgconv.ico --add-data "imgconv.ico;." main.py

echo 完了: dist\imgconv.exe を生成しました。

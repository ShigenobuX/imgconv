# Windows 画像フォーマットコンバーター

Windows向けの画像変換アプリケーションです。`HEIC/HEIF` を含む多くの画像形式を `JPG`, `PNG`, `WEBP`, `BMP` に変換できます。

## セットアップ

1. Python 3.11+ をインストール
2. 仮想環境を作成し、アクティベート
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. 依存パッケージをインストール
   ```powershell
   pip install -r requirements.txt
   ```

## 使い方

- GUI を起動する:
  ```powershell
  python main.py
  ```
- CLI で変換する:
  ```powershell
  python main.py --convert-to jpg "C:\path\to\image.heic"
  ```
- 右クリックメニューを登録/解除する:
  ```powershell
  python main.py --register-menu
  python main.py --unregister-menu
  ```

## PyInstaller で EXE 化

1. `pyinstaller` をインストール

```powershell
pip install pyinstaller
```

2. `build.bat` を実行

```powershell
.\build.bat
```

3. 生成された `dist\imgconv.exe` を配布します。

  - 実行時に `imgconv.ico` を含めるため、`build.bat` は `--add-data "imgconv.ico;."` を指定しています。
  - exe化時のアイコン読み込みは `sys._MEIPASS`（PyInstallerの一時ディレクトリ）に対応しています。
  - 実行時のテーマとウィンドウサイズは `settings.json` として `C:\Users\[ユーザー名]\AppData\Local\imgconv\` に保存されます。
    - AppDataに統一されているため、ユーザーがアンインストール時に該当フォルダを削除すればクリーンアップできます。
  - 右クリックメニュー登録機能を使う場合は、ユーザー環境で `imgconv.exe --register-menu` を実行してください。

## 主な機能

- 画像のドラッグ＆ドロップ
- フォルダ内の一括読み込み
- Exif 情報保持オプション
- 画質スライダー
- リサイズ（アスペクト比保持）
- 同名ファイルの自動連番付与
- 右クリックメニュー連携
- Windows トースト通知

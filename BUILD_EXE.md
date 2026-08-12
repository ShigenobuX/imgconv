# EXE 再ビルド手順

Windows で `imgconv` を再ビルドして配布用 `exe` を生成する手順です。

## 1. 作業フォルダに移動

PowerShell を開き、プロジェクトルートに移動します。

```powershell
cd c:\work\imgconv
```

## 2. 仮想環境の作成（必要な場合）

まだ作成していない場合は、次のコマンドで作成します。

```powershell
python -m venv .venv
```

## 3. 仮想環境を有効化

PowerShell では次を実行します。

```powershell
.\.venv\Scripts\Activate.ps1
```

もし `Activate.ps1` の実行がブロックされる場合は、まず一時的に実行ポリシーを変更します。

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\.venv\Scripts\Activate.ps1
```

## 4. 依存パッケージをインストール

有効化後、必要なパッケージをインストールします。

```powershell
pip install -r requirements.txt
pip install pyinstaller
```

## 5. EXE をビルド

ビルドスクリプトを実行します。

```powershell
.\build.bat
```

生成が成功すると、次のファイルができます。

- `dist\imgconv.exe`

## 6. 結果の確認

`dist` フォルダ内に `imgconv.exe` が存在するか確認します。

## 7. 仮想環境を解除

ビルド後に仮想環境を抜けるには、次を実行します。

```powershell
deactivate
```

## 追加メモ

- `build.bat` は `imgconv.ico` を同梱してビルドするように設定されています。
- ビルドした `imgconv.exe` は、実行時のテーマとウィンドウサイズを `settings.json` に保存します。
  - **保存先:** `C:\Users\[ユーザー名]\AppData\Local\imgconv\settings.json`
  - AppDataに統一されているため、アンインストール時にこのフォルダを削除すればクリーンアップできます。
- 右クリックメニューを配布先で使う場合は、配布先環境で `imgconv.exe --register-menu` を実行します。

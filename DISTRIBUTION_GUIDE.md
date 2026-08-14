# imgconv 配布パッケージ作成手順

この手順書は、Windows 向け配布パッケージ（インストーラー）を作成する担当者向けです。
作成されるファイルは `InstallerOutput\imgconv-<バージョン>-setup.exe` です。

## 1. 事前準備

以下を用意します。

- Windows 10/11（64-bit）
- Python 3.11 以降
- Inno Setup 7（64-bit 版を推奨）

Inno Setup は公式サイトからインストールします。

<https://jrsoftware.org/isdl.php>

プロジェクトのルートフォルダーで PowerShell を開きます。

```powershell
cd C:\work\imgconv
```

初回のみ仮想環境を作成して有効化します。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

PowerShell の実行ポリシーで有効化できない場合だけ、次を実行してから再度有効化します。

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

依存パッケージと PyInstaller をインストールします。

```powershell
pip install -r requirements.txt
pip install pyinstaller
```

## 2. リリース前の確認

配布前に、次を確認します。

- `main.py` の機能変更が完了している
- `README.md` の利用方法・注意事項が最新である
- `imgconv.ico` が最新のアプリアイコンである
- [installer.iss](installer.iss) の `MyAppVersion` をリリースする版番号へ変更した

例えば 0.9.4 を配布する場合は、次の行を変更します。

```iss
#define MyAppVersion "0.9.4"
```

この版番号はインストーラーのファイル名と Windows の「インストールされているアプリ」に表示されます。

## 3. アプリ本体（EXE）の作成

次を実行します。

```powershell
.\build.bat
```

成功すると、次のファイルが生成されます。

```text
dist\imgconv.exe
```

起動確認を行います。

```powershell
.\dist\imgconv.exe
```

GUI が開き、画像の追加・変換・設定保存が正常に動作することを確認します。

## 4. インストーラーの作成

次を実行します。

```powershell
.\build_installer.bat
```

成功すると、次のファイルが生成されます。

```text
InstallerOutput\imgconv-<バージョン>-setup.exe
```

`build_installer.bat` は Inno Setup 7 の標準インストール先と、ユーザー単位のインストール先を自動検出します。

## 5. インストーラーの動作確認

配布する前に、生成したセットアップ EXE をテスト用の Windows ユーザー、仮想マシン、または未導入の環境で実行します。

確認項目は次のとおりです。

1. セットアップ画面が日本語で表示される。
2. インストールが完了し、`imgconv.exe` が起動できる。
3. スタートメニューのショートカットから起動できる。
4. 「デスクトップにショートカットを作成する」を選んだ場合だけ、デスクトップにショートカットが作成される。
5. 「右クリックメニューを登録する」を選んだ場合、画像ファイルの右クリックメニューに変換項目が現れ、変換できる。
6. アンインストール後、アプリ本体・ショートカット・右クリックメニューが削除される。

## 6. インストールされる内容

セットアップは管理者権限を要求せず、実行したユーザーの領域にインストールします。

```text
C:\Users\[ユーザー名]\AppData\Local\Programs\imgconv\
├─ imgconv.exe
├─ README.md
└─ unins000.exe などのアンインストール用ファイル
```

スタートメニューには `imgconv` のショートカットが作成されます。デスクトップショートカットと右クリックメニューは、セットアップ時に選択した場合のみ追加されます。

アプリが作成するユーザー設定は、次の場所に保存されます。

```text
C:\Users\[ユーザー名]\AppData\Local\imgconv\settings.json
```

この設定ファイルはアンインストール後も残るため、再インストール時に設定を引き継げます。完全に削除したい場合は、アンインストール後に `AppData\Local\imgconv` フォルダーを手動で削除してください。

## 7. 配布

動作確認済みの `InstallerOutput\imgconv-<バージョン>-setup.exe` だけを配布します。`dist\imgconv.exe` は開発用の中間成果物であり、通常は配布しません。

配布ページやメールには、少なくとも次を記載します。

- 対応 OS: Windows 10/11（64-bit）
- インストーラーのファイル名とバージョン
- 初回起動方法（スタートメニューの `imgconv`）
- 右クリックメニューはセットアップ時に任意で有効化できること
- アンインストール方法（Windows の「インストールされているアプリ」から `imgconv` を選択）

## 8. よくある問題

### `dist\imgconv.exe was not found` と表示される

先に `build.bat` を実行してください。成功後に `dist\imgconv.exe` が存在することを確認してから、`build_installer.bat` を実行します。

### `Inno Setup 7 was not found` と表示される

Inno Setup 7 をインストールし直してください。標準以外の場所へ導入している場合は、[build_installer.bat](build_installer.bat) の `ISCC` のパスをその環境に合わせて追加します。

### Windows が実行時に警告を表示する

コード署名していない新しい配布ファイルでは、Microsoft Defender SmartScreen などが警告を表示する場合があります。正式配布では、信頼できる認証局のコードサイニング証明書による署名を検討してください。

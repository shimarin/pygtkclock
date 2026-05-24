# pygtkclock

Python + GTK4 製のアナログ時計アプリケーションです。  
Windows 用の [dotnetclock](https://github.com/shimarin/dotnetclock) と同じ見た目を Linux (GTK4) 上で再現しています。

## 機能

- 半透明の円形文字盤（ダーク系）
- 時針・分針・秒針（滑らかなアニメーション、50ms 更新）
- 日付表示（例: `4月21日(月)`）― 土曜は青、日曜は赤
- ウィンドウ枠なし・背景透明
- 左ドラッグで移動
- 右下グリップのドラッグでリサイズ（最小 150px）
- 右クリックメニューで終了
- **時報機能**（オプション）― 毎正時に音声ファイルを時刻の回数分再生

## 依存

| パッケージ | 用途 |
|---|---|
| Python 3 | ランタイム |
| GTK4 (`gi` / PyGObject) | UI・描画 |
| Cairo (`pycairo`) | 時計描画 |
| GStreamer 1.0 (`gi` 経由) | 時報音声再生 |

Gentoo の場合:

```
dev-python/pygobject
dev-python/pycairo
media-libs/gstreamer
media-plugins/gst-plugins-good   # OGG/Vorbis 再生に必要
```

## 使い方

```bash
python3 clock.py
```

ランチャー（`.desktop`）からの起動を主に想定しているため、コマンドライン引数は取りません。
時報音声はデータディレクトリから自動検出します（下記）。

## ビルド / インストール

zipapp によりシステム Python 前提の単一実行ファイル (`build/pygtkclock`) を作り、
GNU 流の `make install` でインストールします（`blueprint-compiler` は不要、Cairo 直描画のため）。

```bash
# ビルドのみ
make                              # -> build/pygtkclock（単一実行ファイル）

# 一般ユーザー（root 不要、~/.local に入る）
make install                      # -> ~/.local/{bin,share/...}

# システム全体
sudo make install                # -> /usr/local/{bin,share/...}
sudo make install PREFIX=/usr     # -> /usr/{bin,share/...}

# パッケージビルド（ebuild の src_install 等）
make install DESTDIR="${D}" PREFIX=/usr

# アンインストール / クリーン
make uninstall
make clean
```

インストールされるもの:

- 実行ファイル `pygtkclock`（`$(PREFIX)/bin`）
- `.desktop` ランチャー（app_id = `com.walbrix.analogclock`）
- アイコン `clock.png`（`hicolor` の 128px、`dotnetclock/app.ico` 由来。表示サイズはシェルがオートスケール）
- 時報音声 `chime.*`（任意。リポジトリ直下に置いてあれば `$(PREFIX)/share/pygtkclock/` へ）

`~/.local/bin` が PATH に無い場合は通しておいてください。

### 時報の仕様

- 音声ファイルは **データディレクトリの `pygtkclock/chime.<拡張子>` を自動検出**する。
  探索順は XDG に従い、ユーザー → システムの順:
  - `~/.local/share/pygtkclock/chime.*`（`$XDG_DATA_HOME`）
  - `/usr/local/share/pygtkclock/chime.*`、`/usr/share/pygtkclock/chime.*`（`$XDG_DATA_DIRS`）
- 拡張子は `ogg oga opus flac wav mp3 m4a aac aiff aif wma` を優先順に探す
  （実際に鳴らせるかは GStreamer のプラグイン次第。OGG Vorbis 推奨）
- ファイルが見つからなければ**無音**で動作する
- 毎正時に `hour % 12`（または 12）回鳴らす（例: 3時→3回、12時→12回）
- 各打鐘は **2秒間隔**で発火（前の音の終了を待たない）
- **22:00〜04:59 は無音**（深夜・早朝の静粛時間）


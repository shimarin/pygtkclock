# pygtkclock - GTK4 アナログ時計
#
# 使い方:
#   make                              # build/pygtkclock を組み立てる
#   make install                      # 一般ユーザー -> ~/.local / root -> /usr/local
#   sudo make install PREFIX=/usr     # システム全体 (/usr)
#   make install DESTDIR=stage PREFIX=/usr   # ステージング (ebuild 等)
#   make uninstall
#   make clean

APP_ID   := com.walbrix.analogclock
BIN_NAME := pygtkclock

BUILD := build
PKG   := $(BUILD)/pkg
EXE   := $(BUILD)/$(BIN_NAME)

# アイコンは 128px の clock.png 1枚のみ。表示サイズはデスクトップシェルのオートスケールに任せる
ICON_SIZE := 128

# uid によって既定の PREFIX を切り替える
ifeq ($(shell id -u),0)
  PREFIX ?= /usr/local
else
  PREFIX ?= $(HOME)/.local
endif

DESTDIR ?=
BINDIR  := $(PREFIX)/bin
DATADIR := $(PREFIX)/share
APPSDIR := $(DATADIR)/applications
ICONROOT := $(DATADIR)/icons/hicolor
ICONDIR := $(ICONROOT)/$(ICON_SIZE)x$(ICON_SIZE)/apps
PKGDATADIR := $(DATADIR)/$(BIN_NAME)

.PHONY: all install uninstall clean

all: $(EXE)

# zipapp で単一実行ファイルを組み立てる。
# このアプリは clock.py 単体（Blueprint UI なし）なので __main__.py に置くだけ。
$(EXE): clock.py
	@rm -rf $(PKG)
	@mkdir -p $(PKG)
	cp clock.py $(PKG)/__main__.py
	python3 -m zipapp $(PKG) -o $(EXE) -p '/usr/bin/env python3'
	@chmod +x $(EXE)

install: all
	install -d $(DESTDIR)$(BINDIR) $(DESTDIR)$(APPSDIR) $(DESTDIR)$(ICONDIR)
	install -m 0755 $(EXE) $(DESTDIR)$(BINDIR)/$(BIN_NAME)
	install -m 0644 clock.png $(DESTDIR)$(ICONDIR)/$(APP_ID).png
	sed -e 's|@BIN@|$(BINDIR)/$(BIN_NAME)|g' \
	    -e 's|@ICON@|$(APP_ID)|g' \
	    -e 's|@APPID@|$(APP_ID)|g' \
	    $(BIN_NAME).desktop.in > $(DESTDIR)$(APPSDIR)/$(APP_ID).desktop
	@chmod 0644 $(DESTDIR)$(APPSDIR)/$(APP_ID).desktop
	@# 時報音声 chime.* がリポジトリ直下にあればデータディレクトリへ入れる（任意）
	@for f in chime.*; do \
	  [ -e "$$f" ] || continue ; \
	  install -d $(DESTDIR)$(PKGDATADIR) ; \
	  install -m 0644 "$$f" $(DESTDIR)$(PKGDATADIR)/$$f ; \
	  echo "  chime $$f -> $(DESTDIR)$(PKGDATADIR)/$$f" ; \
	done
ifeq ($(DESTDIR),)
	-update-desktop-database $(APPSDIR) 2>/dev/null || true
	-gtk-update-icon-cache -t -f $(ICONROOT) 2>/dev/null || true
endif

uninstall:
	rm -f $(DESTDIR)$(BINDIR)/$(BIN_NAME)
	rm -f $(DESTDIR)$(APPSDIR)/$(APP_ID).desktop
	rm -f $(DESTDIR)$(ICONDIR)/$(APP_ID).png
	rm -f $(DESTDIR)$(PKGDATADIR)/chime.*
	-rmdir $(DESTDIR)$(PKGDATADIR) 2>/dev/null || true
ifeq ($(DESTDIR),)
	-update-desktop-database $(APPSDIR) 2>/dev/null || true
	-gtk-update-icon-cache -t -f $(ICONROOT) 2>/dev/null || true
endif

clean:
	rm -rf $(BUILD)

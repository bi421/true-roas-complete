# TrueROAS Audit Validator Build Automation

APP_NAME := TrueROAS-Audit-Validator
ENTRY_POINT := src/trueroas/workers/verify_csv_gui.py
WORKERS_DIR := src/trueroas/workers
ASSETS_DIR := assets

# OS Detection for Path Separators and Icons
ifeq ($(OS),Windows_NT)
	SEP := ;
	ICON_FILE := app_icon.ico
else
	SEP := :
	ICON_FILE := app_icon.icns
endif

ICON_PATH := $(ASSETS_DIR)/$(ICON_FILE)

.PHONY: build clean

build:
	@echo "Building TrueROAS Audit Validator..."
	pyinstaller --noconsole --onefile \
		--collect-all tkinterdnd2 \
		--name "$(APP_NAME)" \
		--paths "$(WORKERS_DIR)" \
		--add-data "$(ICON_PATH)$(SEP)." \
		--icon "$(ICON_PATH)" \
		$(ENTRY_POINT)

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build dist *.spec
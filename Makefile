# 聖靈故事（HS Story）— 測試用 Makefile
#
# 慣用流程：
#   make install                     # 一次裝好 backend / web / app 依賴
#   make test                        # 跑所有測試（pytest + flutter test）
#
#   終端機 A：  make backend          # 起本機後端（預設 8000，web 代理也指這裡）
#   終端機 B：  make emulator         # 開 Android 模擬器（Pixel_10）
#   終端機 B：  make app              # App 連「本機後端」跑（需先 make backend）
#   或        make app-prod          # App 連「線上後端」跑（不用起本機後端）
#
# 可覆寫的變數：
#   make backend BACKEND_PORT=8010
#   make app DEVICE=emulator-5554 BACKEND_PORT=8010

APP_DIR      := app
WEB_DIR      := web
BACKEND_PORT ?= 8000
EMULATOR     ?= hs_test
DEVICE       ?= emulator-5554
ADB          ?= $(HOME)/Library/Android/sdk/platform-tools/adb
# Android 模擬器連「本機」要用 10.0.2.2（不是 localhost）
API_BASE_URL ?= http://10.0.2.2:$(BACKEND_PORT)

.DEFAULT_GOAL := help

# ---- 說明 ----------------------------------------------------------------
.PHONY: help
help: ## 顯示這份說明
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

# ---- 安裝依賴 ------------------------------------------------------------
.PHONY: install install-backend install-web install-app
install: install-backend install-web install-app ## 裝好 backend + web + app 依賴

install-backend: ## uv sync（backend 依賴）
	uv sync

install-web: ## npm install（web 依賴）
	cd $(WEB_DIR) && npm install

install-app: ## flutter pub get（app 依賴）
	cd $(APP_DIR) && flutter pub get

# ---- 手動測試：起服務 ----------------------------------------------------
.PHONY: backend web
backend: ## 起本機後端（uvicorn --reload，埠 = BACKEND_PORT）
	uv run uvicorn backend.app:app --port $(BACKEND_PORT) --reload

web: ## 起 web 開發伺服器（http://localhost:5173，/api 代理到 8000）
	cd $(WEB_DIR) && npm run dev

# ---- 手動測試：模擬器 + App ----------------------------------------------
.PHONY: emulator wait-boot devices app app-prod
emulator: ## 啟動 Android 模擬器並等到開機完成（EMULATOR，預設 hs_test）
	flutter emulators --launch $(EMULATOR)
	@$(MAKE) --no-print-directory wait-boot

wait-boot: ## 等模擬器開機完成（boot_completed=1）才返回，避免安裝撞開機競速
	@echo ">> 等模擬器開機…"; $(ADB) wait-for-device; \
	until [ "$$($(ADB) shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; do sleep 2; done; \
	echo ">> 模擬器已就緒（boot_completed=1）"

devices: ## 列出 flutter 可見裝置
	flutter devices

app: ## App 連「本機後端」跑（先 make backend、make emulator）
	@echo ">> 連 $(API_BASE_URL)（需先 make backend）"
	cd $(APP_DIR) && flutter run -d $(DEVICE) --dart-define=API_BASE_URL=$(API_BASE_URL)

app-prod: ## App 連「線上後端」跑（用 config.dart 預設網址，不用起本機後端）
	cd $(APP_DIR) && flutter run -d $(DEVICE)

# ---- 自動化測試 ----------------------------------------------------------
.PHONY: test test-backend test-app analyze
test: test-backend test-app ## 跑所有測試（pytest + flutter test）

test-backend: ## 後端測試（pytest）
	uv run pytest -q

test-app: ## App 測試（flutter test）
	cd $(APP_DIR) && flutter test

analyze: ## 靜態檢查（flutter analyze）
	cd $(APP_DIR) && flutter analyze

# ---- 其他 ----------------------------------------------------------------
.PHONY: build-web doctor
build-web: ## 打包前端（web/dist，改由後端一併提供）
	cd $(WEB_DIR) && npm run build

doctor: ## flutter doctor（診斷工具鏈）
	flutter doctor

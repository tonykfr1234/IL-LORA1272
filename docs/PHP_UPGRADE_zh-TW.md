# PHP 閘道安裝與升級

本分支的 PHP 網頁環境已改用 **PHP 8.4.27 + mysqli**，搭配 **MariaDB 11.4.13**。兩個官方 Docker 映像均固定版本與 manifest digest；PHP 版本包含 CVE-2026-109618、CVE-2026-109619 的官方修補。日後有新安全版本，仍需更新映像版本／digest、重建並重新測試。

## 新安裝

需要 Git、Python 3，以及可執行 Linux 容器的 Docker Engine／Docker Desktop（含 Docker Compose v2）。在儲存庫根目錄執行：

```sh
python scripts/init_env.py
docker compose up --build -d --wait
docker compose ps
docker compose exec web php -v
```

`init_env.py` 會產生互不相同的隨機資料庫密碼與 API key，存在本機 `.env`；檔案已存在時會拒絕覆蓋。不會將密碼印出或寫入映像。若自行設定，可複製 `.env.example` 為 `.env`，填入三個不同的隨機值；`IOT_API_KEY` 至少 32 個字元。保護 `.env` 的檔案權限，勿上傳 GitHub。

- 主儀表板：<http://127.0.0.1:8080/>
- CES 儀表板：<http://127.0.0.1:8080/ces/>
- 主 API：<http://127.0.0.1:8080/AjaxIoT.php?action=list>
- CES API：<http://127.0.0.1:8080/ces/AjaxIoT.php?action=list>

兩個儀表板共用 `loragateway.IoTTable`。新資料庫以 InnoDB／utf8mb4 建立空表，不自動灌入 2017 年的示範資料。API 自動產生的時間使用 UTC；匯入的舊時間值不會自動轉換，遷移時請確認原始資料的時區。

網頁只綁定 `127.0.0.1`，資料庫不開放主機端連接埠。讀取 API 沒有登入限制，因此不應直接將此示範服務公開到網際網路。若要讓其他裝置使用，需自行配置有身分驗證及 HTTPS 的反向代理，並限制可連線的來源。此更新沒有替你建立公開網站。

## API 與 LoRa 採集程式

`list` 保留既有 jTable JSON 格式；`insertByAPIKey`、`insert`、`create`、`update`、`delete` 都需要與伺服器一致的 API key，優先使用 `X-API-Key` HTTP header。舊版 `APIKey` 輸入仍可相容，但不要把 key 放進網址、書籤或截圖。

Python HTTP gateway 範例改以環境變數設定：

| 變數 | 用途 |
| --- | --- |
| `IOT_API_KEY` | 與本機 `.env` 相同的 key；採集程式不會自動讀取 Compose `.env` |
| `IOT_API_URL` | 預設 `http://127.0.0.1:8080/AjaxIoT.php`；CES 可設為 `/ces/AjaxIoT.php` |

範例改用 POST 與 `X-API-Key` header 傳送資料；遠端連線請使用 HTTPS。LoRa USB／串列埠與部分硬體函式庫仍是舊 Python 2 範例，**這次沒有宣稱完成硬體或 Python 3 的全面移植**。需要實體模組才能驗證收發與頻率設定。Web 容器不會自動啟動採集程式或綁定 USB 裝置。

自行管理 PHP／資料庫時，使用以下環境變數，並確認真正處理 HTTP 請求的 PHP 已修補；另一個 CLI 的 `php -v` 不能取代 Apache／FPM 的版本確認。

| 變數 | 設定 |
| --- | --- |
| `DB_HOST` | Compose 中為 `db`；獨立執行預設 `127.0.0.1` |
| `DB_PORT` | `3306` |
| `DB_NAME` | `loragateway` |
| `DB_USER`、`DB_PASSWORD` | 必填；使用應用程式專用帳號 |
| `DB_TABLE` | 預設 `IoTTable` |
| `IOT_API_KEY` | 至少 32 個字元的私密隨機值 |

## 既有資料遷移

1. 停止寫入與 LoRa 採集，備份舊資料庫、環境設定及目前程式。舊表可能是 MyISAM，備份期間需停止寫入或正確鎖表。
2. 在獨立測試資料庫／volume 匯入 SQL 備份，勿直接掛載舊 MariaDB 的資料目錄到新版本。保留所有原始欄位與 `Id`。若新環境已有初始化的空表，應先由管理者核對其確實沒有資料，再處理匯入時同名表的衝突；本專案不自動刪除資料表。
3. 在匯入完成的目標資料庫執行 `deploy/migrate.sql`。它將 `IoTTable` 轉為 InnoDB／utf8mb4，保留資料、主鍵及自動編號。自訂 `DB_TABLE` 時先修改 SQL 中的表名。此操作會重建表，預留磁碟空間。
4. 檢查筆數、最新資料、中文字元與儀表板，再切換採集程式到新 API，使用新產生的 key。原先寫在舊範例內的共用密碼／key 不再有效。
5. 保留可還原的 SQL 備份；回復時使用備份與獨立環境，不要把新 MariaDB volume 直接交給舊版啟動。

`deploy/schema.sql` 只在全新資料庫 volume 第一次啟動時執行；更新容器不會替現有資料表執行遷移。`docker compose down` 保留資料。**不要執行 `docker compose down -v`，除非確定要刪除該專案全部資料庫資料。**

## 驗證與更新

GitHub Actions 會建置固定版本的 PHP／MariaDB 容器，檢查 PHP 語法並針對可丟棄的資料庫執行 HTTP 整合測試。測試涵蓋兩套 API、增刪改查、API key、輸入驗證、資料保留與舊資料匯入。

`tests/integration.py` 是會寫入及刪除測試資料的工具，只能對可丟棄的測試資料庫執行。設定環境變數 `IOT_API_KEY` 後，測試命令形式如下：

```sh
python tests/integration.py --base-url http://127.0.0.1:18080 --disposable-db
```

上例假設你已在獨立測試專案與 volume 開啟 `18080` 連接埠；不要指向有真實資料的 `8080` 正式環境。密碼與 key 不需要放在命令列參數中。

更新版本前，先備份並在測試環境執行同樣驗證，再重新建立服務：

```sh
docker compose build --pull
docker compose up -d --wait
docker compose exec web php -v
```

單純執行 `docker compose pull` 不會更新固定 digest，也不會重新建置自訂的 web 映像。需要先修改版本／digest。舊 `MakeiFrogLabLoRaDocker.txt`、`RuniFrogLabLoRaDocker.txt` 與啟動腳本已改為指向本流程。

## 官方來源

- [PHP 2026-10-21 安全公告](https://www.php.net/archive/2026.php#2026-10-21-5)
- [Docker 官方 PHP 映像](https://hub.docker.com/_/php)
- [MariaDB 11.4.13 維護版本公告](https://mariadb.org/mariadb-server-12-3-11-8-11-4-and-10-11-q3-2026-maintenance-releases-and-goodbye-10-6/)

映像標籤與 manifest digest 於 2026-10-22 從 Docker 官方 registry 核對。

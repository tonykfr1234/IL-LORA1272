#  IL-LORA1272 is for ifroglab  LoRa module development sample code and tools.

## PHP 閘道更新（2026-10-22）

本分支的網頁範例已升級到 **PHP 8.4.27 + mysqli**，包含 CVE-2026-109618、CVE-2026-109619 修補，搭配 **MariaDB 11.4.13**。主閘道與 CES 示範都使用同一套更新後的 API；舊資料庫密碼與共用 API key 已移除，寫入操作需要私密 key。

在儲存庫根目錄執行（需 Python 3、Docker Compose v2）：

```sh
python scripts/init_env.py
docker compose up --build -d --wait
```

開啟 <http://127.0.0.1:8080/>，CES 頁面位於 <http://127.0.0.1:8080/ces/>。設定存於不會上傳的 `.env`。資料庫保留在 Docker volume，預設不對外開放；需要實體 LoRa 模組才能驗證硬體收發。

**已有資料時，請先備份並依 [PHP 安裝／遷移說明](docs/PHP_UPGRADE_zh-TW.md) 處理。** 測試工具只能指向可丟棄的資料庫，不能用在正式資料。下方保留原始硬體介紹。

IL-LORA1272 is ifroglab product, please see http://www.ifroglab.com/?p=7086

iFrogLab  Lora 868/900/915 MHz SX1272 module compatible

<h2>Features:</h2>

*. Frequency Range: 868/900/915MHz.<br>
*. Modulation: FSK/GFSK/MSK/LoRa.<br>
*. SPI Data Interface Sensitivity: -137dBm.<br>
*. Output Power: +20dBm Data Rate: <300 kbps 127dB dynamic Range RSSI Excellent blocking immunity Preamble detection Automatic RF sense and CAD monitor Built-in bit synchronizer for clock recovery Packet engine up to 256 bytes with CRC.<br>
*. Working Temperature: -40°C ~+80°C Build-in temperature sensor.<br>
*. Standby current: ≤ 1uA.<br>
*. Supply voltage: 1.8~3.6V.<br>



<h2>Descrption:</h2>

iL-LORA1272 is a type of low cost RF front-end transceiver module based on SX1272 from Semtech Corporation. It keeps the advantages of RFIC SX1272 but simplifies the circuit design. The high sensitivity (-137dBm) in LoRa modulation and 20dBm high power output make the module suitable for low range and low data rate applications.

iL-LORA1272 module consists of RFIC SX1272 and include powerful MCU, thin SMD crystal and antenna matching circuit. The antenna port is well matched to standard 50 Ohm impedance. Users don’t need to spend time in RF circuit design and choose suitable antennas for different applications. iL-LORA1272 operates at 1.8~3.6V with extra low standby current which makes it suitable for battery powered-up applications. Because iL-LORA1272 is purely hardware module and it adopts ±10ppm crystal which the resolution of it places a important role in calculating spreading factor, bandwidth, etc.

In addition, We’er add powerful MCU to help Users that don’t needs to read the datasheet of SX1272, you just go through UART to control this module and will easy to use the module in the best performance.


<img src="http://www.ifroglab.com/wp-content/uploads/2016/07/IMG_0532.jpg" alt="LoRa" style="width:304px;height:304px;">

 [http://www.ifroglab.com/wp-content/uploads/2016/07/IMG_0532.jpg]




<h2>Where to buy?</h2>
http://www.ifroglab.com/?product=il-lora1272-超遠端資料傳遞模組




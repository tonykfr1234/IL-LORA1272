# www.ifroglab.com
# -*- coding: utf8 -*-
# coding=UTF-8
# * iFrogLab IL-LORA1272  www.ifroglab.com
# *
# * 功能,             USB to TTL , IFROGLAB LORA
# * 電源VDD,          3.3V       ,Pin 3
# * 接地GND,          GND        ,Pin 1
# * 接收反應Host_IRQ,  null       , Pin 2
# * UART,             RX         ,UART_RX  Pin 7
# * UART,             TX         ,UART_TX  Pin 8

import time
import os
import getopt
import sys

# 檢查碼計算
def Fun_CRC(data):
    crc=0
    for i in data:
        crc=crc^i
    return crc

# BEGIN HTTP API ADAPTER (Python 2.7 / Python 3 compatible)
import json
import os
try:
    import httplib as http_client
    from urlparse import urlsplit
    from urllib import urlencode
except ImportError:
    import http.client as http_client
    from urllib.parse import urlsplit, urlencode


def _api_settings():
    api_key = os.environ.get("IOT_API_KEY", "")
    if len(api_key) < 32 or any(ord(ch) < 33 or ord(ch) > 126 for ch in api_key):
        raise RuntimeError("Set IOT_API_KEY to the server's 32+ character ASCII key before starting the radio.")
    try:
        endpoint = urlsplit(os.environ.get("IOT_API_URL", "http://127.0.0.1:8080/AjaxIoT.php"))
        if (endpoint.scheme not in ("http", "https") or not endpoint.hostname
                or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment):
            raise ValueError("Invalid endpoint")
        port = endpoint.port
        if port is not None and not 1 <= port <= 65535:
            raise ValueError("Invalid port")
        if any(ord(ch) < 33 or ord(ch) > 126 for ch in endpoint.netloc + endpoint.path):
            raise ValueError("Invalid endpoint characters")
    except ValueError:
        raise RuntimeError("IOT_API_URL must be an HTTP(S) endpoint without credentials, query, or fragment.")
    return endpoint, api_key


def Fun_HTTPPost(fields):
    endpoint, api_key = _api_settings()
    connection = None
    try:
        connection_type = http_client.HTTPSConnection if endpoint.scheme == "https" else http_client.HTTPConnection
        connection = connection_type(endpoint.hostname, endpoint.port, timeout=10)
        connection.request("POST", endpoint.path or "/", urlencode(fields), {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "X-API-Key": api_key,
        })
        response = connection.getresponse()
        body = response.read()
        if not 200 <= response.status < 300:
            raise RuntimeError("Gateway API returned HTTP %d." % response.status)
        try:
            result = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeError):
            raise RuntimeError("Gateway API returned invalid JSON.")
        if not isinstance(result, dict) or result.get("Result") != "OK":
            raise RuntimeError("Gateway API did not accept the sensor record.")
        return result
    finally:
        if connection is not None:
            connection.close()
# END HTTP API ADAPTER


def main(argv):
    inputfile = ''
    outputfile = ''
    try:
      opts, args = getopt.getopt(argv,"hi:o:",["ifile=","ofile="])
    except getopt.GetoptError:
      #print 'ap-01-lora-gateway-2-read-httpGet.py -i <frequency>  '
      #sys.exit(2)
      print("LoRa Fregency is 915.00")
      Fun_main("915.00")
    for opt, arg in opts:
      if opt == '-h':
         print 'ap-01-lora-gateway-2-read-httpGet.py -i 920.00  '
         sys.exit()
      elif opt in ("-i", "--ifile"):
         inputfile = arg
    if inputfile=="":
        inputfile="915.00"     
    print 'LoRa Fregency is ', inputfile
    Fun_main(inputfile)



def Fun_main(frequency):
    _api_settings()  # Validate credentials before importing/initializing the radio.
    import ifroglab
    float_frequency = float(frequency)
    print(frequency)
    LoRa = ifroglab.LoRa()

    # 打開Port
    print("Open Port, FunLora_init()")
    ser=LoRa.FunLora_init()

    #讀取F/W版本及Chip ID
    print("Get Firmware Version, FunLora_0_GetChipID()")
    LoRa.FunLora_0_GetChipID()

    # 重置 & 初始化
    print("Init, FunLora_1_Init()")
    LoRa.FunLora_1_Init()


    # 讀取設定狀態
    print("\n[4]:FunLora_2_ReadSetup");
    LoRa.FunLora_2_ReadSetup();

    # 設定寫入和頻段
    print("\n[7]:FunLora_3_TX")
    LoRa.FunLora_3_TX2(float_frequency);

    #寫入資料：通知大家，Gateway 啟動了
    print("\n[10]:FunLora_5_write16bytesArray")
    LoRa.FunLora_5_write16bytesArray("D:iFL,G:S");

    # 設定讀取和頻段
    print("\n[7]:FunLora_3_RX")
    LoRa.FunLora_3_RX2(float_frequency);

    #讀取資料
    print("\n[8]:FunLora_6_read")
    try:
        while True:
            # IDs2=UpdatePoints(value,IDs2)  # 請整到實際的工作秒數
            # ptint(t1)
            data=LoRa.FunLora_6_read();
            #  print(data)
            len1=len(data)
            #print(len1)
            if len1>4:      
                HexString=LoRa.FunArrayToHexStringKeepPureData(data)
                mqtt=" mosquitto_pub -d -t ifroglab/mqtt  -m '%s' -h 'iot.eclipse.org' "%(HexString);
                # mqtt=" mosquitto_pub -d -t ifroglab/mqtt  -m '%s' -h test.mosquitto.org"%(HexString);
                # mqtt=" mosquitto_pub -d -t ifroglab/mqtt  -m '%d "%(data); 
                print(mqtt)
                print os.popen(mqtt).read()
                for t1 in range(0,len1-3):                                                                                                                                                      
                    #print("data[%s]=%s,  Hex->%s"%(t1,data[t1+3],data[t1+3].encode('hex')))
                    x1=(int(data[t1+3].encode('hex'),16))
                    Fun_HTTPPost({"action": "insertByAPIKey", "KeyName": str(t1),
                                  "Data": x1, "Datatype": "1"})
            time.sleep(5)     
            #break;
            #time.sleep(10)
    except:
        print("quit")

        
    
    # 關閉
    LoRa.FunLora_close() 
    ser.close()
    print("cose port.")


# Start Main Program
#Fun_main()

if __name__ == "__main__":
   main(sys.argv[1:])





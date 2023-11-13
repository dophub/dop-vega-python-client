
import sys
import os
import time
import requests
import sqlite3
from dotenv import load_dotenv
import pystray
from PIL import Image
import threading
from datetime import datetime, timedelta


load_dotenv()
exit_program = False
API_URL = os.getenv("API_URL")
REMOTE_API_URL = str(os.getenv("REMOTE_API_URL"))

api_key = os.getenv("REMOTE_API_KEY")
secret_key = os.getenv("REMOTE_API_SECRET")


GLOBAL_REMOTE_TOKEN = ""
GLOBAL_TOKEN = ""


class LocalLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        self.today_log_file = os.path.join(self.log_dir, f"{datetime.now().date()}.log")

    def get_log_file(self):
        self.today_log_file = os.path.join(self.log_dir, f"{datetime.now().date()}.log")
        return self.today_log_file

    def log(self, message):
        try:
            # self.get_log_file()
            self.today_log_file = os.path.join(self.log_dir, f"{datetime.now().date()}.log")
            with open(self.today_log_file, "a") as log_file:
                log_file.write(f"{datetime.now()} --> {message}\n")
        except:
            print("Log dosyası oluşturulamadı.")

logger = LocalLogger()
def remote_login():
    global GLOBAL_REMOTE_TOKEN
    global api_key
    global secret_key

    try:
        login_endpoint = f"{REMOTE_API_URL}/publicapi/auth/login"
        response = requests.post(
            login_endpoint, json={"apikey": api_key, "secretkey": secret_key}
        )
        if response.status_code in (200, 201):
            GLOBAL_REMOTE_TOKEN = response.json()["access_token"]
        else:
            raise Exception("Product API Login işlemi başarısız oldu.")
    except:
        logger.log('[ERROR] REMOTE LOGIN BAŞARISIZ')
        raise Exception('REMOTE LOgin Başarısız')


def local_login():
    global GLOBAL_TOKEN

    login_endpoint = f"{API_URL}/sefim/auth/login"
    username = os.getenv("APIUSER")
    password = os.getenv("PASSWORD")

    try:
        response = requests.post(
            login_endpoint, json={"username": username, "password": password}
        )
        print(response.status_code)

        if response.status_code == 200:
            GLOBAL_TOKEN = response.json()["token"]
        else:
            logger.log(f"Login işlemi başarısız oldu: {response.status_code}")
            raise Exception("Login işlemi başarısız oldu.")
    except:
        logger.log('[ERROR] VEGA LOGIN BAŞARISIZ')
        raise Exception('VEGA Login Başarısız')


def close_local_order(bill_id: int, amount: float, table_name: str, customer_name: str):
    """
    bill_id, amount, table_name, customer_name,
    """
    try:
        headers = {"Authorization": f"Bearer {GLOBAL_TOKEN}"}
        local_api_url = f"{API_URL}/sefim/forex/create-payment"
        prepared_data = {
            "TableNo": table_name,
            "CashPayment": 0,
            "CreditPayment": 0,
            "TicketPayment": 0,
            "OnlinePayment": amount,
            "Discount": 0,
            "Debit": 0,
            "CustomerName": customer_name,
            "PaymentTime": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "ReceivedByUserName": "TIMEFOOD",
            "HeaderId": bill_id,
            "DiscountReason": "",
            "PersonName": "",
            "InvoiceNo": "",
            "IdentificationNo": "",
            "OnlineOdeme": "",
            "Description": "",
            "KrediKarti": "",
            "YemekKarti": "",
            "Deliverer": "",
            "PaymentDetails": [
                {
                    "PaymentType": "Online",
                    "PaymentMethod": "Online",
                    "Amount": amount,
                    "PaymentTime": datetime.now().strftime("%Y-%m-%d %H:%M:00"),
                }
            ],
        }

        print("??" * 5)
        print(prepared_data)
        print("??" * 5)

        response = requests.post(local_api_url, json=prepared_data, headers=headers)
        logger.log(f"---> Order Data Response: {response.status_code}")
        if response.status_code != 200:
            logger.log(f"Masa Kapatılamadı: {response.status_code}")
    except:
        logger.log(f"VEGAYADA SİPARİŞ KAPATILAMADI: {table_name}")
        raise Exception('Vegaya Sipariş Yazılamadı')



def send_orders_to_local_api(orders):
    # try:
    # print(len(orders), "---------")
    headers = {"Authorization": f"Bearer {GLOBAL_TOKEN}"}
    local_api_url = f"{API_URL}/sefim/forex/create-order-table"

    order_data = []

    for order in orders:
        # print(order)
        is_sync = True if order.get("is_sync", False) is False and order.get("service_status_id","")=="IN_COMPLETE" else False
        multiply = -1 if order.get("service_status_id","")=="CANCEL2" else 1
        logger.log(f"is_sync: {is_sync}")
        logger.log(f"Cancel: {multiply}")
        product_items = []
        for item in order.get("orders", [])[0].get("items", []):
            local_product_code = item.get("local_product_code", "")
            local_product_name = item.get("local_product_name", "")
            if local_product_code is None or local_product_code == "":
                logger.log(f"None Error:local_product_name: {local_product_code} - {local_product_name}")
                continue
            logger.log(f"local_product_name: {local_product_code} - {local_product_name}")
            item_price = float(item.get("item_price", 0))
            count = item.get("count", 0)
            local_options = item.get("local_options", [])
            choice1Id = -1
            choice2Id = -1
            code = ""
            code2 = ""
            if local_options is not None and len(local_options) > 0:
                for lo in local_options:
                    integration_additional_data = lo.get(
                        "integration_additional_data", {}
                    )
                    if lo.get("group_code") == "SC1":
                        choice1Id = integration_additional_data.get("choice1id", -1)
                        choice2Id = integration_additional_data.get("choice2id", -1)
                        code = integration_additional_data.get("code", "")
                    elif lo.get("group_code", "") == "SC2":
                        code2 = integration_additional_data.get("code", "")

            _local_product_name:str =f"{local_product_name}.{code}"
            _local_product_name = _local_product_name.rstrip(".")
            items_model = {
                "ProductName": _local_product_name,
                "ProductId": int(local_product_code),
                "Choice1Id": choice1Id if choice1Id > 0 else -1,
                "Choice2Id": choice2Id if choice2Id > 0 else -1,
                "Options": code2,
                "Price": multiply * item_price,
                "Quantity": multiply * count,
                "Comment": item.get("item_note", "") if is_sync is False else "DİKKAT: Sipariş Hazırlandı!",
                "OrginalPrice": 0,
            }
            product_items.append(items_model)

        table_name_str = order.get("special_table_name", "-") if is_sync is False else "!-HAZIRLANDI"
        if multiply == -1:
            table_name_str = "İPTAL EDİLDİ"

        prepared_data = {
            "PhoneNumber": order.get("mobile_phone", ""),
            "Price": multiply * float(order.get("service_total_amount", 0)),
            "TableNumber": table_name_str,
            "Address": "",
            "CustomerName": order.get("first_name", "")
            + " "
            + order.get("lastname", ""),
            "OrderNo": str(order.get("service_id", "")),
            "CreatedByUserName": "TIMEFOOD",
            "Discount": 0,
            "PaymentDetail": "",
            "UserName": "TIMEFOOD",
            "Bill": product_items,
            "ComputerName": "",
            "service_id": order.get("service_id"),
            "CustomerNote": order.get("service_notes", ""),
        }
        order_data.append(prepared_data)
        if multiply == -1:
            logger.log(f"{order.get('special_table_name','-')} - İptal Edildi")
        if is_sync is True:
            logger.log(f"{order.get('special_table_name','-')} - Manuel Hazırlandı")

    # print("-" * 55)
    # print(order_data)
    # print("-" * 55)
    # print(local_api_url)

    try:
        for od in order_data:
            print(od)
            response = requests.post(local_api_url, json=od, headers=headers)
            print(f"[LOCAL]---> Local Order Data Response: {response.status_code}")
            logger.log(f"[PAST LOCAL] --> {od.get('OrderNo','')} - {od.get('TableNumber','')} - Local Response: {response.status_code}")
            if response.status_code != 200:
                print(f"Error sending API: {response.status_code}")
            else:
                _data = response.json()
                # save_orders(od, _data.get("BillHeaderId", 0))
                # Siparişi kapatma
                close_local_order(
                    _data.get("BillHeaderId", 0),
                    od.get("Price", 0),
                    od.get("TableNumber"),
                    od.get("CustomerName"),
                )
                complete_sync(od.get("service_id"))
    except Exception as e:
        logger.log("- VEGA aktarımı yapılamadı")
        raise Exception('Vega Aktarımı Yapılamadı')

    # except Exception as err:
    #     print(err)
    #     pass


def complete_sync(service_id):
    """
    ilgili servis için senkronizasyonu tamamlandı olarak işaretler
    """
    try:
        headers = {"Authorization": f"Bearer {GLOBAL_REMOTE_TOKEN}"}
        api_endpoint = f"{REMOTE_API_URL}/publicapi/product/sync-complete/{service_id}"
        # print(f"--> api_endpoint: {api_endpoint}")
        response = requests.get(api_endpoint, headers=headers)
        # print(f"--> response: {response.status_code}")
        logger.log(f"[COMPLETE REMOTE] --> {service_id} - Local Response: {response.status_code}")
        return response.status_code == 200
    except Exception as err:
        logger.log(f"[ERROR] Senkronizayon tamamlanamadı--> {service_id} - {err}")
        raise Exception('Senkronizasyon Tamamlanamadı')


def fetch_orders(last_service_id):
    """
    Sipairşim API dan orderlar çekilir.
    """
    try:
        # print(f"---{GLOBAL_REMOTE_TOKEN}")
        headers = {"Authorization": f"Bearer {GLOBAL_REMOTE_TOKEN}"}
        data = {"last_service_id": last_service_id}
        api_endpoint = f"{REMOTE_API_URL}/publicapi/product/table-orders"
        # print(f"--> api_endpoint: {api_endpoint}")
        response = requests.post(api_endpoint, json=data, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get("data", [])
        else:
            logger.log(f"Error fetching orders from siparisim api: {response.status_code}")
            return None
    except Exception as err:
        logger.log(
            f" REQUEST EXCEPTION: Siparisim sunucuna bağlantı sağlanamadı. Tekrar denenecek"
        )
        logger.log(err)
        return None


def process_orders(orders):
    global API_URL
    global REMOTE_API_URL
    global GLOBAL_TOKEN
    global GLOBAL_REMOTE_TOKEN

    headers = {"Authorization": f"Bearer {GLOBAL_TOKEN}"}
    remote_headers = {"Authorization": f"Bearer {GLOBAL_REMOTE_TOKEN}"}

    for order in orders:
        service_id = order[0]
        bill_id = order[1]
        print(f"Giden Bill Id: {bill_id}")

        get_order_url = f"{API_URL}/sefim/forex/get-Order"
        response = requests.get(
            get_order_url, headers=headers, json={"billHeaderId": bill_id}
        )

        if response.status_code == 200:
            print(response.json(), "**" * 23)
            data = response.json()
            data = data.get("data")[0]
            if data["BillState"] == 1:
                accept_order_url = (
                    f"{REMOTE_API_URL}/publicapi/product/accept-table/{service_id}"
                )
                response = requests.get(accept_order_url, headers=remote_headers)
                print(f"Remote APi Response: {response.status_code} {REMOTE_API_URL}")
                if response.status_code != 200:
                   print(f"Error accepting order {bill_id}: {response.status_code}")
        else:
            print(
                f"Error fetching order {bill_id} from local API: {response.status_code}"
            )


VER = 24
def main():

    print(f"V{VER} - ###########-----------")
    logger.log("")
    logger.log(f"V{VER} - Başladı...")
    remote_login()

# delete_all_orders()
# reset_last_value()
# unprocessed_orders = fetch_unprocessed_orders()
# process_orders(unprocessed_orders)
# last_service_id = get_last_service_id()

    while True:
        try:
            orders = fetch_orders(0)
            if orders:
                logger.log(f"Merkezden {len(orders)} adet sipariş alındı.")
                local_login()
                send_orders_to_local_api(orders)
                logger.log("\n")
                # max_service_id = max(order["service_id"] for order in orders)
                # update_last_service_id(max_service_id)
            # print_orders()
            time.sleep(10)
        except Exception as err:
            logger.log(f"GLOBAL [ERROR] V{VER} 120 sn sonra tekrar başlayacak --> {err}")
            time.sleep(120)
            remote_login()

def on_activate(icon, item):
    pass


def exit_action(icon, item):
    logger.log('Program Kapatıldı.')
    icon.stop()
    # global exit_program
    # exit_program = True
    # sys.exit(0)



def create_icon(main_func):
    # İkon görüntüsü
    image = Image.open("sip.png")
    menu = (
        pystray.MenuItem("Çıkış", exit_action),
    )
    icon = pystray.Icon("name", image, "Siparişim-VEGA", ())
    def start_main_func(icon, main_func):
        icon.visible = True
        main_func()
        # icon.stop()
    icon.run(
        setup=lambda icon: threading.Thread(
            target=start_main_func, args=(icon, main_func)
        ).start()
    )


if __name__ == "__main__":
    logger.log('Program Başlatıldı')
    # create_icon(main)
    main();

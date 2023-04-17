import sys
import ctypes
import os
import time
import requests
import sqlite3
from dotenv import load_dotenv
import pystray
from PIL import Image
import threading
from datetime import date

load_dotenv()
exit_program = False
API_URL = os.getenv("API_URL")
REMOTE_API_URL = str(os.getenv("REMOTE_API_URL"))

api_key = os.getenv("REMOTE_API_KEY")
secret_key = os.getenv("REMOTE_API_SECRET")

GLOBAL_REMOTE_TOKEN = ""
GLOBAL_TOKEN = ""


def remote_login():
    global GLOBAL_REMOTE_TOKEN
    global api_key
    global secret_key

    login_endpoint = f"{REMOTE_API_URL}/publicapi/auth/login"
    print(login_endpoint)
    print({"apikey": api_key, "secretkey": secret_key})

    response = requests.post(login_endpoint, json={
                             "apikey": api_key, "secretkey": secret_key})

    if response.status_code in (200, 201):
        GLOBAL_REMOTE_TOKEN = response.json()["access_token"]
    else:
        raise Exception("Product API Login işlemi başarısız oldu.")


def local_login():
    global GLOBAL_TOKEN

    login_endpoint = f"{API_URL}/sefim/auth/login"
    username = os.getenv("APIUSER")
    password = os.getenv("PASSWORD")

    print(f"login endpoint {login_endpoint}")
    print(f"user: {username}")

    try:
        response = requests.post(login_endpoint, json={
                                 "username": username, "password": password})
        print(response.status_code)

        if response.status_code == 200:
            GLOBAL_TOKEN = response.json()["token"]
        else:
            raise Exception("Login işlemi başarısız oldu.")
    except:
        pass


def create_tables():
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS last_value (last_service_id INTEGER)")
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS orders (service_id INTEGER, bill_id INTEGER, order_status INTEGER)")

    conn.commit()
    conn.close()


def delete_all_orders():
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM orders")
    conn.commit()

    print("All records deleted from local orders table.")
    conn.close()


def reset_last_value():
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()

    cursor.execute("UPDATE last_value SET last_service_id = 0")
    conn.commit()

    print("Local last_value reset to 0.")
    conn.close()


def get_last_service_id():
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()

    cursor.execute("SELECT last_service_id FROM last_value")
    last_service_id = cursor.fetchone()

    if last_service_id is None:
        cursor.execute("INSERT INTO last_value (last_service_id) VALUES (0)")
        conn.commit()
        last_service_id = 0
    else:
        last_service_id = last_service_id[0]

    conn.close()
    return last_service_id


def update_last_service_id(new_last_service_id):
    print(f"----- LastService Id: {new_last_service_id}")
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()

    cursor.execute("UPDATE last_value SET last_service_id = ?",
                   (new_last_service_id,))
    conn.commit()
    conn.close()


def save_orders(order, bill_id):
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()

    print('---', order, '*'*22)
    cursor.execute("INSERT INTO orders (service_id, bill_id, order_status) VALUES (?, ?,0)",
                   (order["service_id"], bill_id,))

    conn.commit()
    conn.close()


def close_local_order(bill_id: int,amount:float, table_name: str, customer_name: str ):
    """
    bill_id, amount, table_name, customer_name,
    """
    try:
        headers = {"Authorization": f"Bearer {GLOBAL_TOKEN}"}
        local_api_url = f"{API_URL}/sefim/forex/create-payment"
        prepared_data = {
            "TableNo":table_name,
            "CashPayment":0,
            "CreditPayment":0,
            "TicketPayment":0,
            "OnlinePayment":amount,
            "Discount":0,
            "Debit":0,
            "CustomerName":customer_name,
            "PaymentTime": date.today().strftime("%Y-%m-%d %H:%M"),
            "ReceivedByUserName":"",
            "HeaderId":bill_id,
            "DiscountReason":"",
            "PersonName":"",
            "InvoiceNo":"",
            "IdentificationNo":"",
            "OnlineOdeme":"",
            "Description":"",
            "KrediKarti":"",
            "YemekKarti":"",
            "Deliverer":"",
            "PaymentDetails":[
                {
                    "PaymentType":"Online",
                    "PaymentMethod":"Online",
                    "Amount":amount,
                    "PaymentTime":date.today().strftime("%Y-%m-%d %H:%M")
                }
            ]
        }

        print(prepared_data)

        response = requests.post(local_api_url, json=prepared_data, headers=headers)
        print(f"---> Order Data Response: {response.status_code}")
        if response.status_code != 200:
            print(f"Masa Kapatılamadı: {response.status_code}")
    except:
        pass


def send_orders_to_local_api(orders):
    try:
        print(len(orders), "---------")
        headers = {"Authorization": f"Bearer {GLOBAL_TOKEN}"}
        local_api_url = f"{API_URL}/sefim/forex/create-order-table"

        order_data = []

        for order in orders:
            product_items = []
            for item in order.get("orders", [])[0].get("items", []):
                local_product_code = item.get("local_product_code", "")
                local_product_name = item.get("local_product_name", "")
                item_price = item.get("item_price", 0)
                count = item.get("count", [])
                local_options = item.get("local_options", [])
                choice1Id = 0
                choice2Id = 0
                code = ""
                code2 = ""
                for lo in local_options:
                    integration_additional_data = lo.get(
                        "integration_additional_data", {})
                    if lo.get("group_code") == "SC1":
                        choice1Id = integration_additional_data.get(
                            "choice1id", 0)
                        choice2Id = integration_additional_data.get(
                            "choice2id", 0)
                        code = integration_additional_data.get("code", "")
                    elif lo.get("group_code", "") == "SC2":
                        code2 = integration_additional_data.get("code", "")

                product_items.append(
                    {
                        "ProductName": f"{local_product_name}.{code}",
                        "ProductId": int(local_product_code),
                        "Choice1Id": choice1Id,
                        "Choice2Id": choice2Id,
                        "Options": code2,
                        "Price": item_price,
                        "Quantity": count,
                        "Comment": "",
                        "OrginalPrice": 0
                    })

            prepared_data = {
                "PhoneNumber": order.get("mobile_phone", ""),
                "TableNumber": order.get("first_name", "") + order.get("last_name", ""),
                "Address": "",
                "CustomerName": order.get("first_name", "") + " " + order.get("last_name", ""),
                "OrderNo": "",
                "CreatedByUserName": "Siparisim+",
                "Discount": 0,
                "PaymentDetail": "",
                "UserName": "Siparisim+",
                            "Bill": product_items,
                            "ComputerName": "",
                            "service_id": order.get("service_id"),
                            "CustomerNote": order.get("orders")[0].get("order_note", "")
            }
            order_data.append(prepared_data)

        print("-"*55)
        print(order_data)
        print("-"*55)
        print(local_api_url)

        for od in order_data:
            response = requests.post(local_api_url, json=od, headers=headers)
            print(f"---> Order Data Response: {response.status_code}")
            if response.status_code != 200:
                print(f"Error sending API: {response.status_code}")
            else:
                _data = response.json()
                # save_orders(od, _data.get("BillHeaderId", 0))
                close_local_order(_data.get("BillHeaderId", 0), od.get("Price",0), od.get("TableNumber"), od.get("CustomerName"))

    except Exception as err:
        print(err)
        pass


def fetch_orders(last_service_id):
    """
    Sipairşim API dan orderlar çekilir.
    """
    print(f"---{GLOBAL_REMOTE_TOKEN}")
    headers = {"Authorization": f"Bearer {GLOBAL_REMOTE_TOKEN}"}
    data = {"last_service_id": last_service_id}
    api_endpoint = f"{REMOTE_API_URL}/publicapi/product/table-orders"
    print(f"--> api_endpoint: {api_endpoint}")
    response = requests.post(api_endpoint, json=data, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data.get("data", [])
    else:
        print(f"Error fetching orders: {response.status_code}")
        return None


def print_orders():
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders WHERE order_status = 0")
    orders = cursor.fetchall()

    print("Local orders table contents:")
    for order in orders:
        print(
            f"service_id: {order[0]},bill_id: {order[1]} ,order_status: {order[2]}")

    conn.close()


def update_order_status(service_id, order_status):
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE orders SET order_status = ? WHERE service_id = ?", (order_status, service_id))
    conn.commit()

    conn.close()


def fetch_unprocessed_orders():
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders WHERE order_status = 0")
    unprocessed_orders = cursor.fetchall()

    conn.close()

    return unprocessed_orders


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
        response = requests.get(get_order_url, headers=headers, json={
                                "billHeaderId": bill_id})

        if response.status_code == 200:
            print(response.json(), '**'*23)
            data = response.json()
            data = data.get("data")[0]
            if data["BillState"] == 1:
                accept_order_url = f"{REMOTE_API_URL}/publicapi/product/accept-table/{service_id}"
                response = requests.get(
                    accept_order_url, headers=remote_headers)
                print(
                    f"Remote APi Response: {response.status_code} {REMOTE_API_URL}")
                if response.status_code != 200:
                    print(
                        f"Error accepting order {bill_id}: {response.status_code}")
                else:
                    update_order_status(service_id, 1)
        else:
            print(
                f"Error fetching order {bill_id} from local API: {response.status_code}")


mutex_name = "dop_vega_order_matcher"


def main():

    remote_login()
    create_tables()

    # delete_all_orders()
    # reset_last_value()
    global exit_program

    while not exit_program:

        unprocessed_orders = fetch_unprocessed_orders()
        process_orders(unprocessed_orders)

        last_service_id = get_last_service_id()
        print("###########----------->", last_service_id, "------")
        orders = fetch_orders(last_service_id)

        if orders:
            local_login()
            send_orders_to_local_api(orders)
            max_service_id = max(order["service_id"] for order in orders)
            update_last_service_id(max_service_id)

        print_orders()

        time.sleep(10)


def on_activate(icon, item):
    pass


def exit_action(icon, item):
    icon.stop()
    global exit_program
    exit_program = True


def create_icon(main_func):
    # İkon görüntüsü
    image = Image.open("sip.png")

    menu = (
        pystray.MenuItem("Uygulama", on_activate),
        pystray.MenuItem("Çıkış", exit_action)
    )

    icon = pystray.Icon("name", image, "Siparişim", menu)

    def start_main_func(icon, main_func):
        icon.visible = True
        main_func()
        # icon.stop()

    icon.run(setup=lambda icon: threading.Thread(
        target=start_main_func, args=(icon, main_func)).start())


if __name__ == "__main__":
    create_icon(main)

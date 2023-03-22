import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL")
REMOTE_URL = "https://integrationv2.siparisim.app/product"
REMOTE_TOKEN = os.getenv("REMOTE_TOKEN")

global_token = ""

def login():
    global global_token

    login_endpoint = f"{API_URL}/sefim/auth/login"
    username = os.getenv("APIUSER")
    password = os.getenv("PASSWORD")

    print(f"login endpoint {login_endpoint}")
    print(f"user: {username}")
    print(f"psw: {password}")

    response = requests.post(login_endpoint, json={"username": username, "password": password})
    print(response.status_code)
    
    if response.status_code == 200:
        global_token = response.json()["token"]
    else:
        raise Exception("Login işlemi başarısız oldu.")

def get_product_list():
    global global_token

    product_list_endpoint = f"{API_URL}/sefim/product/get-all"
    headers = {"Authorization": f"Bearer {global_token}"}
    response = requests.get(product_list_endpoint, headers=headers)

    if response.status_code == 200:
        return response.json().get("allItems", [])
    elif response.status_code == 500:
        print("Yeniden giriş yapılıyor...")
        login()
        return get_product_list()
    else:
        raise Exception("Ürün listesi alınamadı.")

def post_product_to_remote(token, product):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(REMOTE_URL, json=product, headers=headers)

    if response.status_code == 200:
        print(f"Ürün başarıyla gönderildi: {product['ProductName']}")
    else:
        print(f"Ürün gönderimi başarısız oldu: {product['ProductName']}")

def main():
    login()
    products = get_product_list()
    print(f"{len(products)} adet ürün bulundu...")

    for product in products:
        post_product_to_remote(REMOTE_TOKEN, product)

if __name__ == "__main__":
    main()

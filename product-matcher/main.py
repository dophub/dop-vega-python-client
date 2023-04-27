import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL")

global_token = ""
global_remote_token = ""

api_key = os.getenv("REMOTE_API_KEY")
secret_key = os.getenv("REMOTE_API_SECRET")
REMOTE_API_URL = str(os.getenv("REMOTE_API_URL"))


def remote_login():
    global global_remote_token
    global api_key
    global secret_key

    login_endpoint = f"{REMOTE_API_URL}/publicapi/auth/login"
    print(login_endpoint)
    print({"apikey": api_key, "secretkey": secret_key})

    response = requests.post(login_endpoint, json={
                             "apikey": api_key, "secretkey": secret_key})
    print(response.status_code)

    if response.status_code in (200, 201):
        global_remote_token = response.json()["access_token"]
    else:
        raise Exception("Product API Login işlemi başarısız oldu.")


def login():
    global global_token

    login_endpoint = f"{API_URL}/sefim/auth/login"
    username = os.getenv("APIUSER")
    password = os.getenv("PASSWORD")

    print(f"login endpoint {login_endpoint}")
    print(f"user: {username}")

    response = requests.post(login_endpoint, json={
                             "username": username, "password": password})
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


def prepare_product(product):
    """
        1- Ürünlerin choice1s ve choice2s değerleri birleştirilecek
        choice1s:
    {
        "Id": 14549,
        "ProductId": 10205,
        "Name": "BRASIL SANTOS",
        "Price": 0,
        "Aktarildi": true,
        "IsSynced": null,
        "IsUpdated": null
    }

        choice2s:
        {
          "Id": 10267,
          "ProductId": 10205,
          "Choice1Id": 14549,
          "Name": "KUPA(330ML)",
          "Price": 0,
          "Aktarildi": true,
          "IsSynced": null,
          "IsUpdated": null
      }


      Çıktı: 

      {
       "name": "BRASIL SANTOS KUPA(330ML)",
       "price": 0 + 0,
       addition_data: {choice1Id:14549, choise2Id:10267, code:"BRASIL SANTOS.KUPA(250ML)"}
      }


    """
    option1 = []
    option2 = []
    if len(product.get("choice2s", [])) > 0:
        for choice2s in product.get("choice2s"):
            choice1 = filter(lambda item: item.get("Id") == choice2s.get(
                "Choice1Id"), product.get("choice1s"))
            choice1 = list(choice1)
            if choice1:
                choice1 = choice1[0]
                name = f"{choice1['Name']} {choice2s['Name']}"
                code = f"{choice1['Name']}.{choice2s['Name']}"
                price = choice1['Price'] + choice2s['Price']
                additional_data = {
                    "choice1id": choice1['Id'], "choice2id": choice2s['Id'], "code": code, "price": price}
                option1.append({"name": name, "price": price,
                               "additional_data": additional_data})
    else:
        # Choice2 yok direkt seçenekler choice1
        for choice1 in product.get("choice1s"):
            name = f"{choice1['Name']}"
            code = f"{choice1['Name']}"
            price = choice1['Price']
            additional_data = {
                "choice1id": choice1['Id'], "choice2id": 0, "code": code, "price": price}
            option1.append({"name": name, "price": price,
                           "additional_data": additional_data})

    for option in product.get("options", []):
        option2.append({"name": option.get("Name"), "price": 0, "additional_data": {
                       "code": option.get("Name", ""), "choice1id": 0, "choice2id": 0, "price": 0}})

    options = []
    productPrice = product.get("Price", 0)

    if (len(option1) > 0):
        option1.sort(key=getPrice)
        if product.get("Price", 0) == 0 and len(option1) > 0 and option1[0].get("price", 0) > 0:
            basePrice = option1[0].get("price")
            productPrice = basePrice
            for op in option1:
                op["price"] = op["price"] - basePrice
        options.append({"group_name": "Seçenek 1",
                       "id": "SC1", "options": option1})
    if (len(option2) > 0):
        option2.sort(key=getPrice)
        options.append({"group_name": "Seçenek2",
                       "id": "SC2", "options": option2})

    return {"id": product.get("Id"), "name": product.get("ProductName"), "category": product.get("ProductGroup"), "code": product.get("ProductCode", ""), "price": productPrice, "vat": product.get("VatRate", 8),
            "options": options}


def getPrice(optionVal):
    return optionVal.get("price")


def post_product_to_remote(token, product):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{REMOTE_API_URL}/publicapi/product", json=product, headers=headers)
    print(product['name'], ':', response.status_code)

    if response.status_code != 200:
        print(f"Ürün gönderimi başarısız oldu: {product['name']}")


def post_product_deactivate_to_remote(token, product_id: str):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{REMOTE_API_URL}/publicapi/product/deactivate/{product_id}", headers=headers)
    print(f"Deactivating : {product_id}", response.status_code)

    if response.status_code != 200:
        print(f"Ürün deactivate başarısız oldu: {product_id}")


def read_demo_file():
    f = open('data.json')
    data = json.load(f)
    return data


def main():
    global global_remote_token
    remote_login()
    login()
    print("***"*50)
    print(f"Global Token: {global_remote_token}")
    print("*"*20, "-ÜRÜNLER VEGADAN ÇEKİLİYOR-", "*"*20)

    products = get_product_list()
    total_products: int = len(products)
    # products = read_demo_file()
    print(f"Toplam Ürün Sayısı:{total_products} adet ürün bulundu...")

    # temp_json = ""
    count = 0

    print("*"*20, "ÜRÜNLER ÇEKİLDİ - SUNUCUYA AKTARILIYOR", "*"*20)

    for product in products:
        count += 1
        if product.get("ProductGroup", "$")[0:1] != "$":
            prepared_product = prepare_product(product)
            # temp_json += "," + json.dumps(prepared_product)
            post_product_to_remote(global_remote_token, prepared_product)
            print(f"{count}/{total_products}")
        else:
            # print(f"Ürün grubu $ ile başlıyor. Ürün pasif yapılıyor: {product.get('ProductName')}")
            product_id: int = product.get("Id")
            post_product_deactivate_to_remote(
                global_remote_token, str(product_id))

    print(f"-->Toplam Aktarılan: {count}")

    # f = open("temp.json","w")
    # f.write("[" + temp_json[1:] + "]")


if __name__ == "__main__":
    main()

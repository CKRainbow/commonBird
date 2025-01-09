import requests
import config
import json


def query_species(specie):
    url = f"https://api.ebird.org/v2/ref/taxonomy/ebird?species={specie}&locale=zh_SIM&fmt=json"
    payload = {}
    headers = {"X-eBirdApiToken": config.token}
    response = requests.request("GET", url, headers=headers, data=payload)
    res = response.text
    return json.loads(res)


def get_species(specie):
    url = f"https://api.ebird.org/v2/ref/taxon/forms/{specie}"
    payload = {}
    headers = {"X-eBirdApiToken": config.token}
    response = requests.request("GET", url, headers=headers, data=payload)
    res = response.text
    return eval(res)


def get_spplist(regionCode):
    url = f"https://api.ebird.org/v2/product/spplist/{regionCode}"
    payload = {}
    headers = {"X-eBirdApiToken": config.token}
    response = requests.request("GET", url, headers=headers, data=payload)
    res = response.text
    return eval(res)

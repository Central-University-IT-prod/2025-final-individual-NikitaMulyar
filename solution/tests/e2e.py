import pytest
import requests
import uuid
import random
import string


BASE_URL = "http://REDACTED:8080"


@pytest.fixture(autouse=True)
def reset_state():
    pass


def test_client_management():
    # Создание клиента
    client_id = str(uuid.uuid4())
    response = requests.post(
        f"{BASE_URL}/clients/bulk",
        json=[{
            "client_id": client_id,
            "login": "".join(random.choices(string.ascii_uppercase + string.digits, k=10)),
            "age": 25,
            "location": "Moscow",
            "gender": "MALE"
        }]
    )
    assert response.status_code == 201

    # Получение клиента
    response = requests.get(f"{BASE_URL}/clients/{client_id}")
    assert response.status_code == 200
    assert response.json()["client_id"] == client_id


def test_advertiser_management():
    # Создание рекламодателя
    advertiser_id = str(uuid.uuid4())
    response = requests.post(
        f"{BASE_URL}/advertisers/bulk",
        json=[{
            "advertiser_id": advertiser_id,
            "name": "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
        }]
    )
    assert response.status_code == 201

    # Получение рекламодателя
    response = requests.get(f"{BASE_URL}/advertisers/{advertiser_id}")
    assert response.status_code == 200
    assert response.json()["advertiser_id"] == advertiser_id


def test_campaign_lifecycle():
    advertiser_id = str(uuid.uuid4())
    client_id = str(uuid.uuid4())

    # Создание рекламодателя и клиента
    requests.post(f"{BASE_URL}/advertisers/bulk",
                  json=[{"advertiser_id": advertiser_id,
                         "name": "".join(random.choices(string.ascii_uppercase + string.digits, k=10))}])
    requests.post(f"{BASE_URL}/clients/bulk",
                  json=[{"client_id": client_id,
                         "login": "".join(random.choices(string.ascii_uppercase + string.digits, k=10)),
                         "age": 30, "location": "Moscow", "gender": "FEMALE"}])

    # Создание кампании
    campaign_data = {
        "impressions_limit": 100,
        "clicks_limit": 10,
        "cost_per_impression": 0.5,
        "cost_per_click": 5.0,
        "ad_title": "Test Ad",
        "ad_text": "Buy this!",
        "start_date": 2,
        "end_date": 3,
        "targeting": {
            "gender": "FEMALE",
            "age_from": 20,
            "age_to": 40,
            "location": "Moscow"
        }
    }
    response = requests.post(
        f"{BASE_URL}/advertisers/{advertiser_id}/campaigns",
        json=campaign_data
    )
    assert response.status_code == 201
    campaign_id = response.json()["campaign_id"]

    # Проверка получения кампании
    response = requests.get(f"{BASE_URL}/advertisers/{advertiser_id}/campaigns/{campaign_id}")
    assert response.status_code == 200
    assert response.json()["ad_title"] == "Test Ad"


def test_ad_display_and_click():
    # Настройка данных
    client_id = str(uuid.uuid4())
    advertiser_id = str(uuid.uuid4())

    # Создание тестовых данных (клиент, рекламодатель, кампания, ML-скор)
    requests.post(f"{BASE_URL}/clients/bulk",
                  json=[{"client_id": client_id,
                         "login": "".join(random.choices(string.ascii_uppercase + string.digits, k=10)),
                         "age": 25, "location": "Moscow", "gender": "MALE"}])
    requests.post(f"{BASE_URL}/advertisers/bulk", json=[{"advertiser_id": advertiser_id, "name": "A"}])
    requests.post(
        f"{BASE_URL}/advertisers/{advertiser_id}/campaigns",
        json={
            "impressions_limit": 100,
            "clicks_limit": 10,
            "cost_per_impression": 0.5,
            "cost_per_click": 5.0,
            "ad_title": "Test",
            "ad_text": "Text",
            "start_date": 2,
            "end_date": 3,
            "targeting": {"gender": "MALE"}
        }
    )
    requests.post(f"{BASE_URL}/ml-scores", json={"client_id": client_id, "advertiser_id": advertiser_id, "score": 100})

    # Установка текущего дня
    requests.post(f"{BASE_URL}/time/advance", json={"current_date": 2})

    # Запрос объявления
    response = requests.get(f"{BASE_URL}/ads?client_id={client_id}")
    assert response.status_code == 200
    ad_id = response.json()["ad_id"]

    # Фиксация клика
    response = requests.post(
        f"{BASE_URL}/ads/{ad_id}/click",
        json={"client_id": client_id}
    )
    assert response.status_code == 204

    # Проверка статистики
    response = requests.get(f"{BASE_URL}/stats/campaigns/{ad_id}")
    assert response.status_code == 200
    assert response.json()["clicks_count"] == 1

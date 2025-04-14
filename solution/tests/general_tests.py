import random
import string

import pytest
import requests
import uuid


BASE_URL = "http://REDACTED:8080"


# Фикстуры для создания тестовых данных
@pytest.fixture
def client_id():
    return str(uuid.uuid4())


@pytest.fixture
def advertiser_id():
    return str(uuid.uuid4())


@pytest.fixture
def campaign_id():
    return str(uuid.uuid4())


@pytest.fixture
def test_client(client_id):
    client_data = {
        "client_id": client_id,
        "login": "".join(random.choices(string.ascii_uppercase + string.digits, k=10)),
        "age": random.randint(1, 100),
        "location": "Moscow",
        "gender": "MALE"
    }
    response = requests.post(f"{BASE_URL}/clients/bulk", json=[client_data])
    assert response.status_code == 201
    return client_id


@pytest.fixture
def test_advertiser(advertiser_id):
    advertiser_data = {
        "advertiser_id": advertiser_id,
        "name": "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
    }
    response = requests.post(f"{BASE_URL}/advertisers/bulk", json=[advertiser_data])
    assert response.status_code == 201
    return advertiser_id


@pytest.fixture
def test_campaign(test_advertiser, campaign_id):
    campaign_data = {
        "impressions_limit": 1000,
        "clicks_limit": 100,
        "cost_per_impression": 0.5,
        "cost_per_click": 5.0,
        "ad_title": "Test Campaign",
        "ad_text": "Test Ad Text",
        "start_date": 2,
        "end_date": 7,
        "targeting": {
            "gender": "MALE",
            "age_from": 20,
            "age_to": 30,
            "location": "Moscow"
        }
    }
    response = requests.post(
        f"{BASE_URL}/advertisers/{test_advertiser}/campaigns",
        json=campaign_data
    )
    assert response.status_code == 201
    return response.json()["campaign_id"]


# Тесты для клиентов и рекламодателей
def test_get_client(test_client):
    response = requests.get(f"{BASE_URL}/clients/{test_client}")
    assert response.status_code == 200
    assert response.json()["client_id"] == test_client


def test_get_advertiser(test_advertiser):
    response = requests.get(f"{BASE_URL}/advertisers/{test_advertiser}")
    assert response.status_code == 200
    assert response.json()["advertiser_id"] == test_advertiser


# Тесты для ML-скор
def test_upsert_ml_score(test_client, test_advertiser):
    ml_score = {
        "client_id": test_client,
        "advertiser_id": test_advertiser,
        "score": 150
    }
    response = requests.post(f"{BASE_URL}/ml-scores", json=ml_score)
    assert response.status_code == 200


# Тесты для кампаний
def test_get_campaign(test_advertiser, test_campaign):
    response = requests.get(
        f"{BASE_URL}/advertisers/{test_advertiser}/campaigns/{test_campaign}"
    )
    assert response.status_code == 200
    assert response.json()["campaign_id"] == test_campaign


# Тесты для показа рекламы
def test_get_ad(test_client):
    # Устанавливаем текущий день в диапазон кампании
    requests.post(f"{BASE_URL}/time/advance", json={"current_date": 1})

    response = requests.get(
        f"{BASE_URL}/ads?client_id={test_client}"
    )
    assert response.status_code in [200, 404]  # 404 если нет подходящих кампаний


# Тесты для статистики
def test_get_campaign_stats(test_campaign):
    response = requests.get(f"{BASE_URL}/stats/campaigns/{test_campaign}")
    assert response.status_code == 200
    assert "impressions_count" in response.json()


# Тесты управления временем
def test_advance_time():
    new_date = {"current_date": 2}
    response = requests.post(f"{BASE_URL}/time/advance", json=new_date)
    assert response.status_code == 200
    assert response.json()["current_date"] == 2


# Тесты обработки ошибок
def test_nonexistent_client():
    fake_id = str(uuid.uuid4())
    response = requests.get(f"{BASE_URL}/clients/{fake_id}")
    assert response.status_code == 404


def test_invalid_campaign_creation(test_advertiser):
    invalid_data = {"invalid_field": "value"}
    response = requests.post(
        f"{BASE_URL}/advertisers/{test_advertiser}/campaigns",
        json=invalid_data
    )
    assert response.status_code == 422

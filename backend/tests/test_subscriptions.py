"""Интеграционные тесты биллинга/подписок: автосоздание trial при регистрации,
GET/PATCH /api/subscriptions/me, применение лимита машин и статуса expired при
создании Vehicle/Driver."""

from tests.conftest import register_and_login


def create_vehicle(client, auth_headers, plate_number="А000АА00"):
    return client.post(
        "/api/vehicles",
        json={"plate_number": plate_number, "brand_model": "КамАЗ"},
        headers=auth_headers,
    )


def create_driver(client, auth_headers, full_name="Иван Петров"):
    return client.post("/api/drivers", json={"full_name": full_name}, headers=auth_headers)


def test_registration_creates_trial_subscription(client, auth_headers):
    resp = client.get("/api/subscriptions/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "starter"
    assert data["status"] == "trial"
    assert data["vehicles_limit"] == 3
    assert data["vehicles_used"] == 0
    assert data["price"] == 0
    assert data["next_billing_date"] is None


def test_get_subscription_counts_existing_vehicles(client, auth_headers):
    create_vehicle(client, auth_headers, plate_number="А000АА00")
    create_vehicle(client, auth_headers, plate_number="В111ВВ00")

    resp = client.get("/api/subscriptions/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["vehicles_used"] == 2


def test_subscription_me_isolated_by_organization(client, fake_sms, auth_headers):
    create_vehicle(client, auth_headers)

    other_tokens = register_and_login(client, fake_sms, phone="+79990000020")
    other_headers = {"Authorization": f"Bearer {other_tokens['access_token']}"}

    resp = client.get("/api/subscriptions/me", headers=other_headers)
    assert resp.status_code == 200
    # У другой организации своя свежая trial-подписка, машина первой
    # организации не должна на неё влиять.
    assert resp.json()["vehicles_used"] == 0


def test_patch_subscription_updates_plan_and_limit(client, auth_headers):
    resp = client.patch(
        "/api/subscriptions/me",
        json={"plan": "pro", "vehicles_limit": 10, "status": "active", "price": 1990},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "pro"
    assert data["vehicles_limit"] == 10
    assert data["status"] == "active"
    assert data["price"] == 1990


def test_patch_subscription_cannot_lower_limit_below_current_usage(client, auth_headers):
    create_vehicle(client, auth_headers, plate_number="А000АА00")
    create_vehicle(client, auth_headers, plate_number="В111ВВ00")

    resp = client.patch(
        "/api/subscriptions/me",
        json={"vehicles_limit": 1},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_patch_subscription_isolated_by_organization(client, fake_sms, auth_headers):
    other_tokens = register_and_login(client, fake_sms, phone="+79990000021")
    other_headers = {"Authorization": f"Bearer {other_tokens['access_token']}"}

    client.patch(
        "/api/subscriptions/me",
        json={"plan": "fleet"},
        headers=other_headers,
    )

    resp = client.get("/api/subscriptions/me", headers=auth_headers)
    assert resp.status_code == 200
    # Апгрейд другой организации не должен затронуть первую.
    assert resp.json()["plan"] == "starter"


def test_create_vehicles_up_to_limit_succeeds(client, auth_headers):
    # Дефолтный trial-лимит — 3.
    for plate in ["А000АА00", "В111ВВ00", "С222СС00"]:
        resp = create_vehicle(client, auth_headers, plate_number=plate)
        assert resp.status_code == 201


def test_create_vehicle_over_limit_is_blocked(client, auth_headers):
    for plate in ["А000АА00", "В111ВВ00", "С222СС00"]:
        assert create_vehicle(client, auth_headers, plate_number=plate).status_code == 201

    resp = create_vehicle(client, auth_headers, plate_number="К333КК00")
    assert resp.status_code == 402


def test_expired_subscription_blocks_vehicle_and_driver_creation(client, auth_headers):
    resp = client.patch("/api/subscriptions/me", json={"status": "expired"}, headers=auth_headers)
    assert resp.status_code == 200

    assert create_vehicle(client, auth_headers).status_code == 402
    assert create_driver(client, auth_headers).status_code == 402


def test_upgrading_plan_lifts_limit_block(client, auth_headers):
    for plate in ["А000АА00", "В111ВВ00", "С222СС00"]:
        assert create_vehicle(client, auth_headers, plate_number=plate).status_code == 201
    assert create_vehicle(client, auth_headers, plate_number="К333КК00").status_code == 402

    resp = client.patch("/api/subscriptions/me", json={"vehicles_limit": 10}, headers=auth_headers)
    assert resp.status_code == 200

    resp = create_vehicle(client, auth_headers, plate_number="К333КК00")
    assert resp.status_code == 201

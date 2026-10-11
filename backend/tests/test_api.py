"""Інтеграційні тести REST API ModaLine Shop."""


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_register_login_and_me(client):
    r = client.post(
        "/api/auth/register", json={"email": "Olena@ModaLine.ua", "password": "Secret123", "full_name": "Олена"}
    )
    assert r.status_code == 201 and r.json()["role"] == "manager"
    assert (
        client.post(
            "/api/auth/register", json={"email": "olena@modaline.ua", "password": "Secret123", "full_name": "Дубль"}
        ).status_code
        == 409
    )
    bad = client.post("/api/auth/login", json={"email": "olena@modaline.ua", "password": "wrong-pass"})
    assert bad.status_code == 401
    tok = client.post("/api/auth/login", json={"email": "olena@modaline.ua", "password": "Secret123"}).json()[
        "access_token"
    ]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert me.status_code == 200 and me.json()["email"] == "olena@modaline.ua"


def test_protected_routes_require_token(client):
    assert client.get("/api/customers").status_code == 401
    assert client.post("/api/products", json={}).status_code == 401
    assert client.get("/api/orders", headers={"Authorization": "Bearer invalid.token"}).status_code == 401


def test_product_crud(client, auth, product):
    p = product(sku="TS-BAS-M-WH", price=399, stock=10, name="Футболка базова", category="Футболки", size="M")
    assert client.get(f"/api/products/{p['id']}").json()["name"] == "Футболка базова"
    upd = client.put(f"/api/products/{p['id']}", json={"price": 449, "stock": 7}, headers=auth)
    assert upd.status_code == 200 and upd.json()["price"] == 449 and upd.json()["stock"] == 7
    dup = client.post(
        "/api/products",
        json={**{k: p[k] for k in ("sku", "name", "category", "size", "color")}, "price": 1, "stock": 1},
        headers=auth,
    )
    assert dup.status_code == 409
    assert (
        client.post(
            "/api/products",
            json={"sku": "X1", "name": "Bad", "category": "C", "size": "M", "color": "c", "price": -5, "stock": 1},
            headers=auth,
        ).status_code
        == 422
    )
    assert client.delete(f"/api/products/{p['id']}", headers=auth).status_code == 204
    assert client.get(f"/api/products/{p['id']}").status_code == 404


def test_products_filters_and_pagination(client, product):
    for i in range(5):
        product(sku=f"TS-{i}", price=300 + i * 100, stock=i, name=f"Футболка {i}", category="Футболки")
    product(sku="HD-1", price=1290, stock=3, category="Худі")
    r = client.get(
        "/api/products", params={"category": "Футболки", "in_stock": True, "sort": "-price", "page": 1, "limit": 2}
    ).json()
    assert r["total"] == 4 and [x["sku"] for x in r["items"]] == ["TS-4", "TS-3"]
    assert client.get("/api/products", params={"search": "худі"}).json()["total"] == 1
    assert client.get("/api/products", params={"min_price": 500, "max_price": 700}).json()["total"] == 3


def test_order_creation_total_and_stock(client, auth, product, customer):
    a = product(sku="SKU-A", price=1290, stock=5)
    b = product(sku="SKU-B", price=399, stock=10)
    r = client.post(
        "/api/orders",
        json={
            "customer_id": customer["id"],
            "items": [{"product_id": a["id"], "quantity": 2}, {"product_id": b["id"], "quantity": 3}],
        },
        headers=auth,
    )
    assert r.status_code == 201
    order = r.json()
    assert order["total"] == 2 * 1290 + 3 * 399 and order["status"] == "new" and len(order["items"]) == 2
    assert client.get(f"/api/products/{a['id']}").json()["stock"] == 3
    assert client.get(f"/api/products/{b['id']}").json()["stock"] == 7


def test_order_insufficient_stock_rolls_back(client, auth, product, customer):
    a = product(sku="SKU-A", stock=5)
    b = product(sku="SKU-B", stock=1)
    r = client.post(
        "/api/orders",
        json={
            "customer_id": customer["id"],
            "items": [{"product_id": a["id"], "quantity": 2}, {"product_id": b["id"], "quantity": 4}],
        },
        headers=auth,
    )
    assert r.status_code == 409 and "Недостатньо" in r.json()["detail"]
    assert client.get(f"/api/products/{a['id']}").json()["stock"] == 5
    assert client.get("/api/orders", headers=auth).json()["total"] == 0


def test_payment_marks_order_paid_and_status_flow(client, auth, product, customer):
    a = product(sku="SKU-A", price=1000, stock=5)
    oid = client.post(
        "/api/orders",
        json={"customer_id": customer["id"], "items": [{"product_id": a["id"], "quantity": 1}]},
        headers=auth,
    ).json()["id"]
    assert client.put(f"/api/orders/{oid}", json={"status": "shipped"}, headers=auth).status_code == 400
    assert client.put(f"/api/orders/{oid}", json={"status": "paid"}, headers=auth).status_code == 400
    p = client.post("/api/payments", json={"order_id": oid, "amount": 1000, "method": "card"}, headers=auth)
    assert p.status_code == 201 and p.json()["status"] == "success"
    order = client.get(f"/api/orders/{oid}", headers=auth).json()
    assert order["status"] == "paid" and order["paid"] == 1000
    assert client.put(f"/api/orders/{oid}", json={"status": "shipped"}, headers=auth).json()["status"] == "shipped"


def test_cancel_order_restores_stock(client, auth, product, customer):
    a = product(sku="SKU-A", stock=5)
    oid = client.post(
        "/api/orders",
        json={"customer_id": customer["id"], "items": [{"product_id": a["id"], "quantity": 3}]},
        headers=auth,
    ).json()["id"]
    assert client.get(f"/api/products/{a['id']}").json()["stock"] == 2
    assert client.put(f"/api/orders/{oid}", json={"status": "cancelled"}, headers=auth).json()["status"] == "cancelled"
    assert client.get(f"/api/products/{a['id']}").json()["stock"] == 5
    assert (
        client.post("/api/payments", json={"order_id": oid, "amount": 10, "method": "cash"}, headers=auth).status_code
        == 400
    )


def test_customers_crud_and_conflicts(client, auth, customer, product):
    assert (
        client.post(
            "/api/customers", json={"full_name": "Дубль", "email": "IRYNA@example.com"}, headers=auth
        ).status_code
        == 409
    )
    r = client.get("/api/customers", params={"search": "петренко"}, headers=auth).json()
    assert r["total"] == 1 and r["items"][0]["orders_count"] == 0
    a = product(sku="SKU-A", stock=2)
    client.post(
        "/api/orders",
        json={"customer_id": customer["id"], "items": [{"product_id": a["id"], "quantity": 1}]},
        headers=auth,
    )
    assert client.delete(f"/api/customers/{customer['id']}", headers=auth).status_code == 409
    assert (
        client.put(f"/api/customers/{customer['id']}", json={"city": "Ірпінь"}, headers=auth).json()["city"] == "Ірпінь"
    )

-- 001: початкова схема БД «ModaLine Shop» (PostgreSQL 16)
CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    email         VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(100) NOT NULL,
    role          VARCHAR(20)  NOT NULL DEFAULT 'manager' CONSTRAINT users_role_check CHECK (role IN ('admin','manager')),
    created_at    TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE TABLE customers (
    id         SERIAL PRIMARY KEY,
    full_name  VARCHAR(100) NOT NULL,
    email      VARCHAR(120) NOT NULL UNIQUE,
    phone      VARCHAR(20),
    city       VARCHAR(60),
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE products (
    id          SERIAL PRIMARY KEY,
    sku         VARCHAR(30)  NOT NULL UNIQUE,
    name        VARCHAR(150) NOT NULL,
    category    VARCHAR(60)  NOT NULL,
    size        VARCHAR(5)   NOT NULL CHECK (size IN ('XS','S','M','L','XL','XXL')),
    color       VARCHAR(30)  NOT NULL,
    price       NUMERIC(10,2) NOT NULL CONSTRAINT products_price_check CHECK (price > 0),
    stock       INT NOT NULL DEFAULT 0 CONSTRAINT products_stock_check CHECK (stock >= 0),
    description TEXT,
    created_at  TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE orders (
    id          SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(id),
    status      VARCHAR(20) NOT NULL DEFAULT 'new'
                CONSTRAINT orders_status_check CHECK (status IN ('new','paid','shipped','completed','cancelled')),
    total       NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (total >= 0),
    comment     TEXT,
    created_by  INT REFERENCES users(id),
    created_at  TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE order_items (
    id         SERIAL PRIMARY KEY,
    order_id   INT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INT NOT NULL REFERENCES products(id),
    quantity   INT NOT NULL CONSTRAINT order_items_quantity_check CHECK (quantity > 0),
    unit_price NUMERIC(10,2) NOT NULL CHECK (unit_price > 0)
);

CREATE TABLE payments (
    id         SERIAL PRIMARY KEY,
    order_id   INT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    amount     NUMERIC(10,2) NOT NULL CONSTRAINT payments_amount_check CHECK (amount > 0),
    method     VARCHAR(20) NOT NULL CONSTRAINT payments_method_check CHECK (method IN ('card','cash','transfer')),
    status     VARCHAR(20) NOT NULL DEFAULT 'pending' CONSTRAINT payments_status_check CHECK (status IN ('pending','success','failed')),
    paid_at    TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_payments_order ON payments(order_id);

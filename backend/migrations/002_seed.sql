-- 002: початкові (демонстраційні) дані
-- Облікові записи: admin@modaline.ua / Admin123!   manager@modaline.ua / Manager123!
INSERT INTO users (email, password_hash, full_name, role) VALUES
 ('admin@modaline.ua',   '$2b$10$sEXrQBKhxxRLM7UQ2Pm3ku/xsX164VlPaqd3NX9opbactoiCNvOB.', 'Андрій Мельник', 'admin'),
 ('manager@modaline.ua', '$2b$10$igBRtueQLwDiU1yWwtn4X.XuUwP8Yb6OSStK2qcn3uk/w5HruQz9S', 'Олена Коваль',   'manager');

INSERT INTO customers (full_name, email, phone, city, created_at) VALUES
 ('Ірина Петренко',  'iryna.p@gmail.com',   '+380671234567', 'Київ',    now() - interval '40 days'),
 ('Максим Гнатюк',   'max.hn@ukr.net',      '+380502223344', 'Львів',   now() - interval '35 days'),
 ('Олена Савчук',    'o.savchuk@gmail.com', '+380935551212', 'Ірпінь',  now() - interval '20 days'),
 ('Тарас Кравець',   'taras.k@gmail.com',   '+380974044040', 'Буча',    now() - interval '18 days'),
 ('Софія Литвин',    'sofia.l@ukr.net',     '+380660102030', 'Київ',    now() - interval '12 days'),
 ('Дмитро Олійник',  'd.oliynyk@gmail.com', '+380637778899', 'Одеса',   now() - interval '7 days'),
 ('Анна Шевчук',     'anna.sh@gmail.com',   '+380683216598', 'Харків',  now() - interval '3 days');

INSERT INTO products (sku, name, category, size, color, price, stock, description) VALUES
 ('TS-BAS-S-WH', 'Футболка базова',        'Футболки', 'S',  'білий',     399.00, 12, 'Бавовна 100 %'),
 ('TS-BAS-M-WH', 'Футболка базова',        'Футболки', 'M',  'білий',     399.00, 18, 'Бавовна 100 %'),
 ('TS-BAS-L-BK', 'Футболка базова',        'Футболки', 'L',  'чорний',    399.00,  9, 'Бавовна 100 %'),
 ('TS-POL-L-BL', 'Футболка поло',          'Футболки', 'L',  'синій',     690.00,  6, 'Піке'),
 ('HD-BAS-M-GR', 'Худі оверсайз «Basic»',  'Худі',     'M',  'сірий',    1290.00,  7, 'Футер з начосом'),
 ('HD-BAS-L-GR', 'Худі оверсайз «Basic»',  'Худі',     'L',  'сірий',    1290.00,  4, 'Футер з начосом'),
 ('HD-ZIP-XL-BK','Худі на блискавці',      'Худі',     'XL', 'чорний',   1490.00,  2, 'Футер, металева блискавка'),
 ('SW-BAS-M-BE', 'Світшот',                'Худі',     'M',  'бежевий',   990.00, 10, 'Футер'),
 ('JN-SLM-S-BL', 'Джинси slim',            'Джинси',   'S',  'синій',    1550.00,  8, 'Денім зі стрейчем'),
 ('JN-SLM-M-BL', 'Джинси slim',            'Джинси',   'M',  'синій',    1550.00,  3, 'Денім зі стрейчем'),
 ('JN-MOM-M-LB', 'Джинси mom fit',         'Джинси',   'M',  'блакитний',1690.00,  5, 'Висока посадка'),
 ('DR-MID-S-FL', 'Сукня міді',             'Сукні',    'S',  'квітковий',1890.00,  2, 'Віскоза'),
 ('DR-MID-M-FL', 'Сукня міді',             'Сукні',    'M',  'квітковий',1890.00,  4, 'Віскоза'),
 ('JK-DEN-M-BL', 'Куртка джинсова',        'Верхній одяг','M','синій',   2390.00,  3, 'Денім'),
 ('CT-WOL-L-GR', 'Пальто вовняне',         'Верхній одяг','L','сірий',   4890.00,  1, 'Вовна 60 %'),
 ('AC-SCF-UN-BG','Шарф трикотажний',       'Аксесуари','M',  'бежевий',   450.00,  0, 'Акрил');

INSERT INTO orders (customer_id, status, total, comment, created_by, created_at) VALUES
 (1, 'completed', 2886.00, NULL,                    2, now() - interval '30 days'),
 (2, 'shipped',   1550.00, 'Доставка у відділення №5', 2, now() - interval '6 days'),
 (3, 'new',       1890.00, 'Передзвонити після 18:00', 2, now() - interval '2 days'),
 (5, 'paid',      2280.00, NULL,                    1, now() - interval '1 day'),
 (4, 'cancelled',  690.00, 'Клієнт передумав',       2, now() - interval '10 days'),
 (6, 'new',        399.00, NULL,                    2, now() - interval '3 hours');

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
 (1, 5, 1, 1290.00), (1, 2, 2, 399.00), (1, 3, 1, 399.00), (1, 1, 1, 399.00),
 (2, 9, 1, 1550.00),
 (3, 13, 1, 1890.00),
 (4, 8, 1, 990.00), (4, 6, 1, 1290.00),
 (5, 4, 1, 690.00),
 (6, 1, 1, 399.00);

INSERT INTO payments (order_id, amount, method, status, paid_at, created_at) VALUES
 (1, 2886.00, 'card',     'success', now() - interval '30 days', now() - interval '30 days'),
 (2, 1550.00, 'card',     'success', now() - interval '6 days',  now() - interval '6 days'),
 (4, 2280.00, 'transfer', 'success', now() - interval '1 day',   now() - interval '1 day'),
 (3, 1890.00, 'card',     'failed',  NULL,                       now() - interval '2 days');

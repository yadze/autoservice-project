CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    price INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    service_id INTEGER REFERENCES services(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO services (title, description, price) VALUES
('Ремонт тормозной системы', 'Замена колодок, дисков, ремонт суппортов', 3000),
('Замена ГРМ', 'Замена ремня/цепи ГРМ, роликов, помпы', 5000),
('Комплексное ТО', 'Полное техническое обслуживание по регламенту', 8000)
ON CONFLICT (title) DO UPDATE SET
    price = EXCLUDED.price,
    description = EXCLUDED.description;

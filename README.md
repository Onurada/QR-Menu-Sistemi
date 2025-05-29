Flask ile çalışan bu projeyi kullanmak için main.py dosyasını çalıştırmanız yeterli olacaktır.

Database oluşturma kodları;

-- 1) Database oluştur ve ona bağlan
-- (PostgreSQL'de superuser yetkisiyle)
CREATE DATABASE qrdb;
\c qrdb;

-- 2) Extension’lar (isteğe bağlı, örn. UUID için)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 3) users tablosu
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(150) NOT NULL UNIQUE,
  email    VARCHAR(150) NOT NULL UNIQUE,
  password_hash VARCHAR(256) NOT NULL
);

-- 4) qr_requests tablosu
CREATE TABLE qr_requests (
  id SERIAL PRIMARY KEY,
  user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  data        TEXT    NOT NULL,
  filename    VARCHAR(200) NOT NULL,
  created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 5) menu_items tablosu
CREATE TABLE menu_items (
  id          SERIAL PRIMARY KEY,
  user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name        VARCHAR(100) NOT NULL,
  price       REAL         NOT NULL,
  description VARCHAR(200),
  image_url   VARCHAR(300)
);

-- 6) İzinleri kontrol et (opsiyonel)
// GRANT ALL PRIVILEGES ON DATABASE qrdb TO your_username;
// GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO your_username;

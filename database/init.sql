-- Базовая схема БД для мегалабы (под SQLAlchemy-модели в backend/app/models/*)

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT false,
    can_view_dashboard BOOLEAN DEFAULT false
);

CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    device_uid VARCHAR(100) UNIQUE NOT NULL,
    device_type VARCHAR(50) NOT NULL,
    description VARCHAR(255),
    catalog_info TEXT,
    owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    location VARCHAR(255),
    status VARCHAR(50) DEFAULT 'registered',
    device_secret VARCHAR(255) NOT NULL
);

CREATE INDEX idx_devices_device_uid ON devices(device_uid);
CREATE INDEX idx_devices_status ON devices(status);

CREATE TABLE sensor_data (
    id SERIAL PRIMARY KEY,
    device_uid VARCHAR(100) NOT NULL,
    sensor_type VARCHAR(50),
    value FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sensor_data_device_uid ON sensor_data(device_uid);
CREATE INDEX idx_sensor_data_created_at ON sensor_data(created_at);

CREATE TABLE actuators (
    id SERIAL PRIMARY KEY,
    device_uid VARCHAR(100) UNIQUE NOT NULL,
    actuator_type VARCHAR(50) NOT NULL,
    state VARCHAR(20) DEFAULT 'OFF',
    control_mode VARCHAR(20) DEFAULT 'AUTO'
);

CREATE TABLE automation_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    sensor_type VARCHAR(50) NOT NULL,
    condition VARCHAR(10) NOT NULL,
    threshold VARCHAR(50) NOT NULL,
    actuator_type VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL
);
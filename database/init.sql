CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    device_uid VARCHAR(100) UNIQUE,
    type VARCHAR(50),
    name VARCHAR(100),
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sensor_data (
    id SERIAL PRIMARY KEY,
    device_uid VARCHAR(100),
    value FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
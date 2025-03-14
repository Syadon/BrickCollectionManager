CREATE TABLE IF NOT EXISTS colors (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    rgb TEXT NOT NULL,
    type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS parts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category INTEGER NOT NULL,
    altid TEXT,
    FOREIGN KEY(category) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS colors_parts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codename INTEGER NOT NULL,
    color_id INTEGER NOT NULL, 
    part_id TEXT NOT NULL,
    UNIQUE (codename, part_id, color_id),
    FOREIGN KEY(color_id) REFERENCES colors(id),
    FOREIGN KEY(part_id) REFERENCES parts(id)
);

CREATE TABLE IF NOT EXISTS containers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS parts_collection (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item INTEGER NOT NULL,
    count INTEGER NOT NULL,
    container_id INTEGER NOT NULL,
    FOREIGN KEY(item) REFERENCES color_parts(id),
    FOREIGN KEY(container_id) REFERENCES containers(id)
);
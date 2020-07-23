CREATE TABLE magic_castles(
    hostname TEXT PRIMARY KEY NOT NULL,
    cluster_name TEXT NOT NULL,
    domain TEXT NOT NULL,
    status TEXT NOT NULL,
    plan_type TEXT NOT NULL
)
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from config import Config

db_pool = SimpleConnectionPool(
    minconn=1,
    maxconn=5,
    user=Config.DB_USER,
    password=Config.DB_PASSWORD,
    host=Config.DB_HOST,
    port=Config.DB_PORT,
    database=Config.DB_NAME
)

def get_db():
    return db_pool.getconn()

def put_db(conn):
    db_pool.putconn(conn)

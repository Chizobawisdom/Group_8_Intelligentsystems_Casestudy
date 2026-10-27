import os
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine


def get_engine() -> Engine:
    # URL.create handles special characters in passwords safely
    url = URL.create(
        "mysql+pymysql",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "3306")),
        database=os.environ["DB_NAME"],
    )
    return create_engine(url, pool_pre_ping=True)
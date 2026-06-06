import os
from dotenv import load_dotenv

load_dotenv()

def get_db_config() -> dict[str, str | int]:
    """Get PostgreSQL connection configuration from environment.
    
    Returns:
        Dictionary with database connection parameters:
        - host: PostgreSQL host (default: localhost)
        - port: PostgreSQL port (default: 5432)
        - dbname: Database name (default: pet_dog)
        - user: Database user (default: admin)
        - password: Database password (default: admin1234)
    """
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": os.getenv("POSTGRES_DB", "pet_dog"),
        "user": os.getenv("POSTGRES_USER", "admin"),
        "password": os.getenv("POSTGRES_PASSWORD", "admin1234"),
    }

def get_db_connection_string() -> str:
    """LangChain PGVector가 사용할 PostgreSQL 연결 문자열을 만든다.

    - docker-compose.yml 기본값과 맞춘다.
    - 팀 Docker 설정 기본값:
      - DB: pet_dog
      - USER: admin
      - PASSWORD: admin1234
    """
    config = get_db_config()
    
    return f"postgresql+psycopg://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['dbname']}"
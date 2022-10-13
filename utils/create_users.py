from config import DB_CONNECTION_STRING
from sqlalchemy import MetaData, Table, create_engine, insert



def main():
    mo = MetaData()
    engine = create_engine(DB_CONNECTION_STRING)

    users = Table('users', mo, autoload_with=engine)



    # with engine.connect() as conn:



if __name__ == '__main__':
    main()

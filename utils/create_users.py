from config import db_connection_string
from sqlalchemy import MetaData, Table, create_engine, insert



def main():
    mo = MetaData()
    engine = create_engine(db_connection_string)

    users = Table('users', mo, autoload_with=engine)



    # with engine.connect() as conn:



if __name__ == '__main__':
    main()

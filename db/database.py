import mysql.connector
from mysql.connector import pooling


class MysqlDatabase:

    __pool = None

    def __init__(
        self,
        host="127.0.0.1",
        user="root",
        password="",
        database="mydb",
        port=3306,
        pool_name="mypool",
        pool_size=5
    ):

        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.pool_name = pool_name
        self.pool_size = pool_size

    def connect(self):

        if MysqlDatabase.__pool is None:

            MysqlDatabase.__pool = pooling.MySQLConnectionPool(
                pool_name=self.pool_name,
                pool_size=self.pool_size,
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port
            )

            print("Pool criado!")

        return MysqlDatabase.__pool

    def get_connection(self):

        pool = self.connect()

        return pool.get_connection()
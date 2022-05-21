import sys
import os
import mysql.connector
import json
from datetime import datetime


def insert_device_state(params):
    mydb = connect_database()
    with mydb.cursor() as mycursor:
        sql = "INSERT INTO device_state (room, type, value, date) VALUES (%s,%s,%s,%s)"
        print(sql, file= sys.stderr)
        values = (
            params["room"],
            params["type"],
            params["value"],
            datetime.now()
        )
        mycursor.execute(sql, values)
        mydb.commit()
        return mycursor

def connect_database():
    mydb = mysql.connector.connect(
        host = os.getenv('DB_HOST'),
        user = os.getenv('DB_USER'),
        password = os.getenv('DB_PASSWORD'),
        database = os.getenv('DB_NAME')
    )
    return mydb

def get_device_state():
    mydb = connect_database()
    r = []
    with mydb.cursor() as mycursor:
        mycursor.execute("SELECT * FROM device_state ORDER BY date ASC")
        myresult = mycursor.fetchall()
        for id, room, type, value, date in myresult:

            r.append({
                "room":room,
                "type": type,
                "value":value,
                "date":str(date)
            })
        mydb.commit()

    return json.dumps(r, sort_keys=True)

import numpy as np
import sys
import psycopg2

dbname = "mtgrid_uc"

def db_connection(dbname):
    try:
        global conn
        conn = psycopg2.connect("dbname='" + dbname + "' user='' host='localhost' password=''")
        print("DB: " + dbname + " connected.")
        return(conn)
    except:
        print("I am unable to connect to the database. STOP.")
        sys.exit(0)


def clean():

    conn = psycopg2.connect("dbname='" + dbname + "' user='' host='10.12.0.10' password=''")
    cursor = conn.cursor()
    np.set_printoptions(suppress=True)
    cursor.execute("ALTER TABLE mtgrid_uc.etpmu SET (\"blocks.read_only_allow_delete\" = null);")
    cursor.execute("ALTER TABLE mtgrid_uc.etrtds SET (\"blocks.read_only_allow_delete\" = null);")
    cursor.execute("DELETE FROM mtgrid_uc.etpmu; DELETE FROM mtgrid_uc.etrtds;");


clean()

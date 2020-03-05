# During discovery add device data into a sqlite db, which can be used by connector.
# Each time any data is needed, search the db.
#
# 1. Storing the whole json data in memory is not scalable.
# 2. Its cleaner. Updates to data wont need app restart.
# 3. There might be disk read overheads, but since the db is small, the OS will cache most of it.
#
# DB structure:
# main DEVICE_TABLE: device_id, description, jci_name, name, addr, max_apdu, vendor_id
#      contains high level devices and their data
#
# <device_id>_OBJ_TABLE: uuid, instance, object_type, desc, jci_name, sensor_type, units
#      contains objects within device and their data


import json
from pdb import set_trace as bp
from contextlib import contextmanager

import sqlite3


@contextmanager
def cursor_to_commit(db):
    try:
        conn = sqlite3.connect(db)
        c = conn.cursor()
        yield c
        conn.commit
    finally:
        pass

class SqliteWrapper():
    """ The main wrapper through which data can be read/written.
        Input/Output is a dictionary with column name as key and entry as value.
    """
    def __init__(self, db_name):
        """ provide the db from which data needs to be read from """

        self.db = db_name
        conn = sqlite3.connect(self.db)

        if not self.does_table_exist("device_table"):
            c = conn.cursor()
            c.execute("CREATE TABLE device_table ( version varchar(255)," +
                                               "device_id int, " +
                                               "description varchar(255), " +
                                               "jci_name varchar(255), " +
                                               "name varchar(255), " +
                                               "ip_addr varchar(12), " +
                                               "max_apdu int, "+
                                               "uuid str, "+
                                               "vendor_id int);"
                                               )
            conn.commit()

        if not self.does_table_exist('uuid_table'):
            c = conn.cursor()
            c.execute("CREATE TABLE uuid_table (uuid, nae_id int, instance int)")
            conn.commit()

    def does_table_exist(self, name):
        conn = sqlite3.connect(self.db)
        c = conn.cursor()
        for tbl in c.execute("SELECT name FROM sqlite_master"):
            if tbl[0] == name:
                return True

        return False

    def write_device_properties(self, device, version='v1'):
        conn = sqlite3.connect(self.db)
        c = conn.cursor()

        c.execute(("DELETE FROM device_table WHERE device_id=?"), (device["device_id"],))
        conn.commit()

        c.execute(("INSERT INTO device_table (version, device_id, description, jci_name ,name ,ip_addr ,max_apdu, vendor_id) " +
                    "VALUES (?, ?, ? ,?, ?, ?, ?, ?);"),
                    (version,
                     device["device_id"],
                     device["description"],
                     device["jci_name"],
                     device["name"],
                     device["addr"],
                     device["max_apdu"],
                     device["vendor_id"]
                    )
                )
        conn.commit()

        table_name = 'table_%s_%s'%(device["device_id"], version)
        if self.does_table_exist((table_name)):
            #flush the old data and read it afresh
            c.execute("DROP TABLE "+ table_name);
            conn.commit()

        c.execute(("CREATE TABLE "+ table_name + " ( uuid varchar(36), " +
                                                     "device_ref int, " +
                                                     "instance int, " +
                                                     "object_type int, " +
                                                     "description varchar(255), " +
                                                     "jci_name varchar(255), " +
                                                     "sensor_type varchar(255), " +
                                                     "unit varchar(255) " +
                                                     ");"))
        conn.commit()

    def read_device_properties(self, device_id, version='v1'):
        conn = sqlite3.connect(self.db)
        c = conn.cursor()
        table_name = 'table_%s_%s'%(str(device_id), version)
        res = c.execute("SELECT * FROM device_table WHERE device_id=?", (device_id,)).fetchone()
        table_name = 'table_%s_%s'%(str(device_id), version)
        objects =[]
        for obj in c.execute("SELECT instance FROM "+table_name):
            objects.append(obj[0])


        return {"version"    : res[0],
                "device_id"  : res[1],
                "description": res[2],
                "jci_name"   : res[3],
                "name"       : res[4],
                "addr"       : res[5],
                "max_apdu"   : res[6],
                "vendor_id"  : res[7],
                "objects"    : objects
               }

    def read_obj_properties(self, uuid=None, device_id=None, instance=None, version='v1'):
        if uuid is None and (instance is None or device_id is None):
            raise Exception("Provide atleast one of uuid and instance")

        conn = sqlite3.connect(self.db)
        c = conn.cursor()

        device_id = int(device_id)
        instance = int(instance)

        if device_id is None: # get device_id from uuid
            res =  c.execute("SELECT * from uuid_table WHERE uuid=\""+uuid+"\";").fetchone()
            device_id = res[1]
            instance = res[2]

        table_name = 'table_%s_%s'%(str(device_id), version)
        res = c.execute("SELECT * FROM " + table_name + " WHERE instance=?", (instance,)).fetchone()

        return {"uuid":        res[0],
                "device_ref":   res[1],
                "instance":    res[2],
                "object_type": res[3],
                "description": res[4],
                "jci_name":    res[5],
                "sensor_type": res[6],
                "unit":        res[7] }

    def write_obj_properties(self, props, version='v1'):
        table_name = 'table_%s_%s'%(str(props["device_ref"]), version)

        if not self.does_table_exist(table_name):
            raise Exception("Table %s does not exist" %table_name)

        conn = sqlite3.connect(self.db)
        c = conn.cursor()

        # remove old entry and add a new one.
        c.execute(("DELETE FROM "+ table_name + " WHERE device_ref=? AND instance=?;"),
                    (int(props["device_ref"]), props["instance"]))
        conn.commit()

        c.execute(("INSERT INTO "+ table_name + "(uuid ,device_ref, instance, object_type, "
                                              + "description, jci_name ,sensor_type ,unit) "
                    + "VALUES (? ,? ,? ,? ,? ,? ,? ,?);" ),
                    ( props["uuid"],
                      props["device_ref"],
                      props["instance"],
                      props["object_type"],
                      props["description"],
                      props["jci_name"],
                      props["sensor_type"],
                      props["unit"]
                    )
                )
        conn.commit()

    def update_dev_property(self, dev_id, prop, val, version='v1'):
        table_name = 'device_table'

        if not self.does_table_exist(table_name):
            raise Exception("Table %s does not exist" %table_name)

        conn = sqlite3.connect(self.db)
        c = conn.cursor()

        qstr = f"UPDATE {table_name} \n" + f"SET {prop} = {val}\n" + f"WHERE device_id= {dev_id}"

        c.execute(f"UPDATE {table_name} \n" +
                  f'SET {prop} = "{val}"\n' +
                  f"WHERE device_id= {dev_id}"
                  )
        conn.commit()



    def update_obj_property(self, dev_id, obj_instance, prop, val, version='v1'):
        table_name = 'table_%s_%s'%(str(dev_id), version)

        if not self.does_table_exist(table_name):
            raise Exception("Table %s does not exist" %table_name)

        conn = sqlite3.connect(self.db)
        c = conn.cursor()

        c.execute(f"UPDATE {table_name}\n" +
                  f"SET {prop} = '{val}'\n" +
                  f"WHERE instance = {obj_instance}"
                  )
        conn.commit()


    def find_dev_uuid(self, dev_id):
        qstr = f"""
        select uuid
        from device_table
        where
        device_id = {dev_id}
        """
        with cursor_to_commit(self.db) as cursor:
            res = cursor.execute(qstr)
        row = res.fetchone()
        return row[0]

    def find_obj_uuid(self, dev_id: str, instance: str, version: str='v1'):
        table_name = 'table_%s_%s'%(str(dev_id), version)
        qstr = f"""
        select uuid
        from {table_name}
        where
        instance = {instance}
        """
        with cursor_to_commit(self.db) as cursor:
            res = cursor.execute(qstr)
        row = res.fetchone()
        return row[0]

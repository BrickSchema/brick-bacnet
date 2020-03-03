#import dataservice_pb2 as dsrpc_data
#import dataservice_pb2_grpc  as dsrpc_mtd
#
#class ActuationServer(dsrpc_mtd.DataserviceServicer):
#    def viewSensorData(self, sensorId, context):
#        value = 123
#        return dsrpc_data.sensorData(uuid=sensorId.uuid, datapoint=str(value))
#
#    def recvSensorData(self, requestList, context):
#        for sensor_data in requestList.list:
#            print(sensor_data.uuid, sensor_data.datapoint)
#
#        # Log the write into a Database, see ActionLog
#        return dsrpc_data.sendStatus(numOfFailures=0)

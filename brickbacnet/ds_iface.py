""" Interface to interact with the dataservice.
    Inherit the class and Overload the necessary Methods

"""

class DsSensorObj():
    """ inherit & overload it. add infomation that represents the sensor for the Dataservice.
    """

class DsSensorData():
    """ inherit & overload it.
        represents data or MetaData read from the data service
    """


class DsIface(object):

    def put_timeseries_data(self, datapoints):
        """ Push a batch of datapoints.
            Overload if a more efficient way to PUT exists.
            Default is to call put_timeseries_datapoint() for each sensor, datapoint pair
        """
        raise NotImplementedError('Method not implemented!')

    def get_timeseries_metadata(self, sensor):
        """ get the current data for the sensor
            sensor current sensor metadata data
        """
        raise NotImplementedError('Method not implemented!')

    def get_timeseries_data(self, sensor):
        """ get the current data for the sensor
            sensor current sensor data
        """
        raise NotImplementedError('Method not implemented!')


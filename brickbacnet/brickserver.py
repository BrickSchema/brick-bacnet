import requests
from collections import defaultdict

from pdb import set_trace as bp

from .ds_iface import DsIface



class BrickServer(DsIface):
    def __init__(self, hostname, jwt_token, srcid_uuid_map={}):
        self.hostname = hostname
        self.api_url = hostname + '/brickapi/v1'
        self.ts_url = hostname + '/brickapi/v1/data/timeseries'
        self.ttl_upload_url = hostname + '/brickapi/v1/entities/upload'
        self.jwt_token = jwt_token
        self.default_headers = {
            'Authorization': 'Bearer ' + self.jwt_token
        }
        self.srcid_uuid_map = srcid_uuid_map
        self.type_map = {
            'analogInput': 'number',
            'analogValue': 'number',
            'analogOutput': 'number',
            'binaryOutput': 'number',
            'binaryInput': 'number',
            'binaryValue': 'number',
            'multiStateOutput': 'number',
            'multiStateInput': 'number',
            'multiStateValue': 'number',
        }

    def _update_token(self, jwt_token):
        self.jwt_token = jwt_token

        self.default_headers['Authorization'] = 'Bearer ' + self.jwt_token

    def _get(self, url, headers={}, params={}):
        headers = headers.update(self.default_headers)
        resp = requests.get(url, headers=headers, params=params)
        return resp

    def _post(self, url, **kwargs):
        if 'headers' in kwargs:
            kwargs['headers'].update(self.default_headers)
        else:
            kwargs['headers'] = self.default_headers
        resp = requests.post(url, **kwargs)
        return resp


    def register_graph(self, g):
        serialized = g.serialize(format='turtle')
        headers = {'Content-Type': 'text/turtle'}
        #resp = self._post(self.ttl_upload_url,
        #                  data=serialized,
        #                  headers=headers,
        #                  )
        #assert resp.status_code == 200

    def _authorize_headers(self, headers={}):
        headers.update(self.default_headers)
        return headers

    def get_uuid(self, src_id):
        return src_id #TODO: Implement this

    def put_timeseries_data(self, datapoints):

        object_types = set([datapoint['object_type'] for datapoint in datapoints])
        datapoints_per_type = defaultdict(list)
        for dp in datapoints:
            datapoints_per_type[self.type_map[dp['object_type']]].append(
                [self.get_uuid(dp['src_id']), dp['timestamp'], dp['value']]
            )
        datapoints_per_type = dict(datapoints_per_type)
        data_per_type = {
        }
        for data_type, dps in datapoints_per_type.items():
            body = {
                'columns': ['uuid', 'timestamp'] + [data_type],
                'data': dps
            }
            resp = self._post(self.ts_url, json=body)

    def get_timeseries_metadata(self, sensor):
        raise NotImplementedError('Method not implemented!')

    def get_timeseries_data(self, sensor):
        raise NotImplementedError('Method not implemented!')


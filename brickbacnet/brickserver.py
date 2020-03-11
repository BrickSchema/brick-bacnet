import requests
import time
from collections import defaultdict

from pdb import set_trace as bp

from rdflib import Namespace

from .ds_iface import DsIface
from .namespaces import BRICK_NS_TEMPLATE, BACNET



class BrickServer(DsIface):
    def __init__(self, hostname: str,
                 jwt_token: str,
                 brick_version: str,
                 srcid_uuid_map: dict={},
                 ):
        self.brick_version = brick_version
        self.BRICK = Namespace(BRICK_NS_TEMPLATE.format(version=self.brick_version))
        self.hostname = hostname
        self.api_url = hostname + '/brickapi/v1'
        self.ts_url = hostname + '/brickapi/v1/data/timeseries'
        self.entities_url = hostname + '/brickapi/v1/entities'
        self.sparql_url = hostname + '/brickapi/v1/rawqueries/sparql'
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
        resp = self._post(self.ttl_upload_url,
                          data=serialized,
                          headers=headers,
                          )
        assert resp.status_code == 200

    def _authorize_headers(self, headers={}):
        headers.update(self.default_headers)
        return headers

    def get_uuid(self, src_id):
        return src_id #TODO: Implement this

    def put_timeseries_data(self, datapoints):

        object_types = set([datapoint['object_type'] for datapoint in datapoints])
        datapoints_per_type = defaultdict(list)
        for dp in datapoints:
            obj_type = self.type_map.get(dp['object_type'], None)
            if not obj_type:
                continue
            datapoints_per_type[obj_type].append([dp['uuid'], dp['timestamp'], dp['value']])
        datapoints_per_type = dict(datapoints_per_type)
        data_per_type = {
        }
        t0 = time.time()
        for data_type, dps in datapoints_per_type.items():
            body = {
                'columns': ['uuid', 'timestamp'] + [data_type],
                'data': dps
            }
            resp = self._post(self.ts_url, json=body)
        t1 = time.time()
        print('post took: {0} seconds'.format(t1 - t0))

    def get_timeseries_metadata(self, sensor):
        raise NotImplementedError('Method not implemented!')

    def get_timeseries_data(self, sensor):
        raise NotImplementedError('Method not implemented!')

    def create_entity(self, entity_type):
        body = {
            entity_type: 1,
        }
        headers = self._authorize_headers()
        resp = self._post(self.entities_url,
                          json=body,
                          headers=headers,
                          )
        assert resp.status_code == 200
        return resp.json()[entity_type][0]

    def query_entities(self, props):
        qstr = """
        prefix bacnet: <{BACNET}>
        prefix brick: <{BRICK}>
        prefix xsd: <http://www.w3.org/2001/XMLSchema#>
        select ?entity where {{
        """.format(BRICK=self.BRICK, BACNET=BACNET)

        for prop, val in props.items():
            if prop == 'device_ref':
                qstr += f"""
?dev brick:hasPoint ?entity.
?dev bacnet:device_id "{val}"^^xsd:integer.
"""
            else:
                if isinstance(val, int):
                    val = f'"{val}"^^xsd:integer'
                elif isinstance(val, str):
                    val = f'"{val}"'
                else:
                    raise Exception('Not implemented')

                qstr += f'?entity bacnet:{prop} {val}.\n'
        qstr += '\n}'
        headers = self._authorize_headers({'Content-Type': 'application/sparql-query'})
        resp = self._post(self.sparql_url,
                          data=qstr,
                          headers=headers,
                          )
        assert resp.status_code == 200
        entity_ids = [row['entity']['value'] for row in resp.json()['results']['bindings']]
        return entity_ids



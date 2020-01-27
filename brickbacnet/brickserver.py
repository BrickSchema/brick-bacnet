import requests

from pdb import set_trace as bp


class BrickServer(object):
    def __init__(self, hostname, jwt_token):
        self.hostname = hostname
        self.jwt_token = jwt_token
        self.default_headers = {
            'Authorization': 'Bearer ' + self.jwt_token
        }

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
        resp = self._post(self.hostname + '/brickapi/v1/entities/upload',
                          data=serialized,
                          headers=headers,
                          )
        assert resp.status_code == 200



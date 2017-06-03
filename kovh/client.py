from ovh import Client as OVHClient
from ovh.config import config


class Client(OVHClient):

    def __init__(self, project=None, region=None, sshkey=None, flavor=None, **kwargs):
        super().__init__(**kwargs)

        if project is None:
            project = config.get('kovhernetes', 'project')
        self._project = project

        if region is None:
            region = config.get('kovhernetes', 'region')
        self._region = region

        if sshkey is None:
            sshkey = config.get('kovhernetes', 'sshkey')
        self._sshkey = sshkey

        if flavor is None:
            flavor = config.get('kovhernetes', 'flavor')
        self._flavor = flavor

    def missing_params(self, params):
        config = {
            'project': self._project,
            'region': self._region,
            'sshkey': self._sshkey,
            'flavor': self._flavor
        }

        empty = []
        for p, v in config.items():
            if v is None:
                empty.append(p)

        return set(empty).intersection(params)

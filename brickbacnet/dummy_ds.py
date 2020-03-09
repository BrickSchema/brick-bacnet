from uuid import uuid4 as gen_uuid

from .ds_iface import DsIface
from .namespaces import UUID

class DummyDs(DsIface):

    def create_entity(self, entity_type):
        return str(gen_uuid())

    def query_entities(self, props):
        return []

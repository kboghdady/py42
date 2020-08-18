from py42.services import BaseService


class KeyValueStoreClient(BaseService):
    def __init__(self, connection):
        super(KeyValueStoreClient, self).__init__(connection)

    def get_stored_value(self, key):
        uri = u"/v1/{}".format(key)
        # this request doesn't expect json, unlike most.
        headers = {"Accept": "*/*"}
        return self._connection.get(uri, headers=headers)
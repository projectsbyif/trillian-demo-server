import json
import grpc

from collections import OrderedDict

import trillian_log_api_pb2
import trillian_log_api_pb2_grpc
import trillian_admin_api_pb2
import trillian_admin_api_pb2_grpc
import trillian_pb2
import crypto.sigpb.sigpb_pb2
import google.protobuf.duration_pb2
import crypto.keyspb.keyspb_pb2


class TrillianAdminClient():
    """
    Calls the gRPC endpoints defined in:
    https://github.com/google/trillian/blob/master/trillian_admin_api.proto
    """

    def __init__(self, host, port):
        self.__channel = grpc.insecure_channel('{}:{}'.format(host, port))
        self.__stub = trillian_admin_api_pb2_grpc.TrillianAdminStub(
            self.__channel)

    def logs(self):
        """
        Gets a ListTreeResponse:
        https://github.com/google/trillian/blob/master/trillian_admin_api.proto

        Then returns an iterable of Tree objects from:
        https://github.com/google/trillian/blob/master/trillian.proto
        """
        request = trillian_admin_api_pb2.ListTreesRequest()

        # TODO: filter out maps

        return self.__stub.ListTrees(request).tree

    def get_public_key(self, log_id):
        request = trillian_admin_api_pb2.GetTreeRequest(tree_id=log_id)

        return self.__stub.GetTree(request)

    def create_log(self, display_name, description):
        request = trillian_admin_api_pb2.CreateTreeRequest(
            tree=trillian_pb2.Tree(
                tree_state=trillian_pb2.ACTIVE,
                tree_type=trillian_pb2.LOG,
                hash_strategy=trillian_pb2.RFC6962_SHA256,
                hash_algorithm=crypto.sigpb.sigpb_pb2.DigitallySigned.SHA256,
                signature_algorithm=crypto.sigpb.sigpb_pb2.DigitallySigned
                                     .ECDSA,
                display_name=display_name,
                description=description,
                max_root_duration=google.protobuf.duration_pb2.Duration(
                    seconds=600
                )
                # TODO: think about this value
            ),
            key_spec=crypto.keyspb.keyspb_pb2.Specification(
                ecdsa_params=crypto.keyspb.keyspb_pb2.Specification.ECDSA(
                    curve=crypto.keyspb.keyspb_pb2.Specification.ECDSA
                           .DEFAULT_CURVE
                )
            )
        )

        return self.__stub.CreateTree(request)

    def delete_log(self, log_id):
        request = trillian_admin_api_pb2.DeleteTreeRequest(
            tree_id=log_id
        )

        return self.__stub.DeleteTree(request)

    def get_log(self, log_id):
        request = trillian_admin_api_pb2.GetTreeRequest(
            tree_id=log_id
        )

        return self.__stub.GetTree(request)


class TrillianLogClient():
    MAX_LEAVES_PER_REQUEST = 1024

    def __init__(self, host, port, log_id):
        self.__channel = grpc.insecure_channel('{}:{}'.format(host, port))
        self.__stub = trillian_log_api_pb2_grpc.TrillianLogStub(self.__channel)
        self.__log_id = log_id

    def init_log(self):
        request = trillian_log_api_pb2.InitLogRequest(
            log_id=self.__log_id,
            charge_to=trillian_log_api_pb2.ChargeTo()
        )

        return self.__stub.InitLog(request)

    def queue_entry_dictionary(self, dictionary):
        """
        Store a Python dictionary
        """
        normaliser = DictToBinaryNormaliser(dictionary)

        return self.queue_entry_binary(normaliser.normalise())

    def queue_entry_binary(self, data):
        leaf = trillian_log_api_pb2.LogLeaf(leaf_value=data)

        request = trillian_log_api_pb2.QueueLeafRequest(
            log_id=self.__log_id,
            leaf=leaf
        )
        return self.__stub.QueueLeaf(request)

    def get_recent_leaves(self, number_of_leaves):
        tree_size = self.get_tree_size()

        indexes = list(range(
            tree_size - 1,
            max(0, tree_size - 1 - number_of_leaves),
            -1
        ))

        if not indexes:
            return []

        print("Requesting indexes {}".format(indexes))

        request = trillian_log_api_pb2.GetLeavesByIndexRequest(
            log_id=self.__log_id,
        )
        request.leaf_index.extend(indexes)

        response = self.__stub.GetLeavesByIndex(request)
        return response.leaves

    def get_leaves(self, start, end):
        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError('`start` and `end` must be integers')

        if start < 0 or end < 0:
            raise ValueError('`start` and `end` must be greater than zero')

        if start >= end:
            raise ValueError('`end` must be greater than `start`')

        tree_size = self.get_tree_size()

        if not start < tree_size:
            raise ValueError(
                'start ({}) must be < tree_size ({})'.format(
                    start, tree_size
                )
            )

        end = min(start + self.MAX_LEAVES_PER_REQUEST, end)

        indexes = list(
            range(start, min(end, tree_size))
        )

        if not indexes:
            return []

        print("Requesting indexes {}".format(indexes))

        request = trillian_log_api_pb2.GetLeavesByIndexRequest(
            log_id=self.__log_id,
        )
        request.leaf_index.extend(indexes)

        response = self.__stub.GetLeavesByIndex(request)

        return sorted(
            response.leaves,
            key=lambda l: l.leaf_index
        )

    def get_leaves_by_range(self, start_index, count):
        return self.get_leaves(start_index, start_index + count)

    def get_consistency_proof(self, first_tree_size, second_tree_size):
        if first_tree_size <= 0:
            raise ValueError('`first_tree_size` must be > 0')

        if first_tree_size > second_tree_size:
            raise ValueError('`first_tree_size` must be < `second_tree_size`')

        request = trillian_log_api_pb2.GetConsistencyProofRequest(
            log_id=self.__log_id,
            first_tree_size=first_tree_size,
            second_tree_size=second_tree_size,
        )
        response = self.__stub.GetConsistencyProof(request)
        return response

    def get_tree_size(self):
        return self.get_signed_log_root().tree_size

    def get_signed_log_root(self):
        request = trillian_log_api_pb2.GetLatestSignedLogRootRequest(
            log_id=self.__log_id,
        )

        response = self.__stub.GetLatestSignedLogRoot(request)
        return response.signed_log_root


class DictToBinaryNormaliser():
    def __init__(self, dictionary):
        self.__dictionary = dictionary

    def normalise(self):
        self.validate_is_dictionary()
        self.validate_not_empty()
        self.stringify_numbers()
        self.order_by_keys()

        return self.encode_to_json()

    def validate_is_dictionary(self):
        pass

    def validate_not_empty(self):
        pass

    def stringify_numbers(self):
        self.__dictionary = {k: str(v) for k, v in self.__dictionary.items()}

    def order_by_keys(self):
        self.__dictionary = OrderedDict(
            sorted(self.__dictionary.items(), key=lambda x: x[0], reverse=True)
        )

    def encode_to_json(self):
        return json.dumps(self.__dictionary, indent=0).encode('utf-8')

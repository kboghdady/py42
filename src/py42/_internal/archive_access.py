import posixpath
import time
from collections import namedtuple

from py42.exceptions import Py42ArchiveFileNotFoundError


FileSelection = namedtuple(u"FileSelection", u"path_set, num_files, num_dirs, size")


class FileType(object):
    DIRECTORY = u"directory"
    FILE = u"file"


class ArchiveAccessorManager(object):
    def __init__(self, archive_client, storage_client_factory):
        self._archive_client = archive_client
        self._storage_client_factory = storage_client_factory

    def get_archive_accessor(
        self,
        device_guid,
        destination_guid=None,
        private_password=None,
        encryption_key=None,
    ):
        client = self._storage_client_factory.from_device_guid(
            device_guid, destination_guid=destination_guid
        )
        decryption_keys = self._get_decryption_keys(
            device_guid, private_password, encryption_key
        )
        session_id = self._create_restore_session(
            client.archive, device_guid, **decryption_keys
        )
        restore_job_manager = create_restore_job_manager(
            client.archive, device_guid, session_id
        )
        return ArchiveAccessor(
            device_guid, session_id, client.archive, restore_job_manager
        )

    def _get_decryption_keys(self, device_guid, private_password, encryption_key):
        decryption_keys = {}
        if encryption_key:
            decryption_keys[u"encryption_key"] = encryption_key
        else:
            data_key_token = (
                self._get_data_key_token(device_guid) if not encryption_key else None
            )
            if data_key_token:
                decryption_keys[u"data_key_token"] = data_key_token

            if private_password:
                decryption_keys[u"private_password"] = private_password
        return decryption_keys

    def _get_data_key_token(self, device_guid):
        return self._archive_client.get_data_key_token(device_guid)[u"dataKeyToken"]

    @staticmethod
    def _create_restore_session(storage_archive_client, device_guid, **kwargs):
        response = storage_archive_client.create_restore_session(device_guid, **kwargs)
        return response[u"webRestoreSessionId"]


def _create_file_selections(file_paths, metadata_list, file_sizes):
    file_selections = []
    for i in range(0, len(file_paths)):
        metadata = metadata_list[i]
        size_info = file_sizes[i]
        path_set = {
            u"type": metadata[u"type"],
            u"path": metadata[u"path"],
            u"selected": True,
        }
        selection = FileSelection(
            path_set, size_info[u"numFiles"], size_info[u"numDirs"], size_info[u"size"],
        )
        file_selections.append(selection)

    return file_selections


def _get_default_file_size_info(file_ids):
    return [{u"numFiles": 1, u"numDirs": 1, u"size": 1} for _ in file_ids]


class ArchiveAccessor(object):

    DEFAULT_DIRECTORY_DOWNLOAD_NAME = u"download"
    JOB_POLLING_INTERVAL = 1

    def __init__(
        self,
        device_guid,
        archive_session_id,
        storage_archive_client,
        restore_job_manager,
    ):
        self._device_guid = device_guid
        self._archive_session_id = archive_session_id
        self._storage_archive_client = storage_archive_client
        self._restore_job_manager = restore_job_manager

    def stream_from_backup(self, file_paths, ignore_size_calc=False):
        if not isinstance(file_paths, (list, tuple)):
            file_paths = [file_paths]
        file_paths = [fp.replace("\\", "/") for fp in file_paths]
        metadata_list = self._get_restore_metadata(file_paths)
        file_ids = [md[u"id"] for md in metadata_list]
        file_sizes = (
            self._get_file_size_info(file_ids)
            if not ignore_size_calc
            else _get_default_file_size_info(file_ids)
        )
        file_selections = _create_file_selections(file_paths, metadata_list, file_sizes)
        return self._restore_job_manager.get_stream(file_selections)

    def _get_restore_metadata(self, file_paths):
        metadata_list = []
        for path in file_paths:
            metadata = self._get_file_via_walking_tree(path)
            metadata_list_entry = {
                u"id": metadata[u"id"],
                u"path": metadata[u"path"],
                u"type": metadata[u"type"],
            }
            metadata_list.append(metadata_list_entry)
        return metadata_list

    def _get_file_via_walking_tree(self, file_path):
        path_parts = file_path.split(u"/")
        path_root = path_parts[0] + u"/"

        response = self._get_children(node_id=None)
        for root in response:
            if root[u"path"].lower() == path_root.lower():
                return self._walk_tree(response, root, path_parts[1:])

        raise Py42ArchiveFileNotFoundError(response, self._device_guid, file_path)

    def _walk_tree(self, response, current_node, remaining_path_components):
        if not remaining_path_components or not remaining_path_components[0]:
            return current_node

        children = self._get_children(node_id=current_node[u"id"])
        current_node_path = current_node[u"path"]
        target_child_path = posixpath.join(
            current_node_path, remaining_path_components[0]
        )

        for child in children:
            if child[u"path"].lower() == target_child_path.lower():
                return self._walk_tree(response, child, remaining_path_components[1:])

        raise Py42ArchiveFileNotFoundError(
            response, self._device_guid, target_child_path
        )

    def _get_children(self, node_id=None):
        return self._storage_archive_client.get_file_path_metadata(
            self._archive_session_id,
            self._device_guid,
            file_id=node_id,
            show_deleted=True,
        )

    def _get_file_size_info(self, file_ids):
        file_sizes = []
        for file_id in file_ids:
            size_data = self._storage_archive_client.get_file_size(
                self._device_guid, file_id
            )
            file_size_entry = {
                u"numFiles": size_data[u"numFiles"],
                u"numDirs": size_data[u"numDirs"],
                u"size": size_data[u"size"],
            }
            file_sizes.append(file_size_entry)
        return file_sizes


class RestoreJobManager(object):
    JOB_POLLING_INTERVAL_SECONDS = 1

    def __init__(
        self,
        storage_archive_client,
        device_guid,
        archive_session_id,
        job_polling_interval=JOB_POLLING_INTERVAL_SECONDS,
    ):
        self._storage_archive_client = storage_archive_client
        self._device_guid = device_guid
        self._archive_session_id = archive_session_id
        self._job_polling_interval = job_polling_interval

    def get_stream(self, file_selections):
        response = self._start_restore(file_selections)
        job_id = response["jobId"]

        while not self.is_job_complete(job_id):
            time.sleep(self._job_polling_interval)

        return self._get_stream(job_id)

    def is_job_complete(self, job_id):
        response = self._storage_archive_client.get_restore_status(job_id)
        return self._get_completion_status(response)

    def _start_restore(self, file_selection):
        num_files = sum([fs.num_files for fs in file_selection])
        num_dirs = sum([fs.num_dirs for fs in file_selection])
        size = sum([fs.size for fs in file_selection])
        zip_result = _check_for_multiple_files(file_selection) or None
        return self._storage_archive_client.start_restore(
            guid=self._device_guid,
            web_restore_session_id=self._archive_session_id,
            path_set=[fs.path_set for fs in file_selection],
            num_files=num_files,
            num_dirs=num_dirs,
            size=size,
            zip_result=zip_result,
            show_deleted=True,
        )

    @staticmethod
    def _get_completion_status(response):
        return response[u"done"]

    def _get_stream(self, job_id):
        response = self._storage_archive_client.stream_restore_result(job_id)
        return response


def create_restore_job_manager(storage_archive_client, device_guid, archive_session_id):
    return RestoreJobManager(storage_archive_client, device_guid, archive_session_id)


def _check_for_multiple_files(file_selection):
    if not file_selection:
        return False
    if len(file_selection) > 1:
        return True

    # Only one file selected
    selection = file_selection[0]
    return selection.path_set[u"type"].lower() == u"directory"

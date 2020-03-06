import pytest

from py42._internal.session import Py42Session
from py42._internal.session_factory import SessionFactory
from py42._internal.clients import (
    administration,
    archive,
    devices,
    legal_hold,
    orgs,
    security,
    users,
)
from py42._internal.modules import (
    archive as arch_mod,
    employee_case_management as ecm_mod,
    security as sec_mod,
)
from py42._internal.dependency_containers import SDKDependencies
from py42._internal.client_factories import StorageClientFactory
from py42._internal.user_context import UserContext

from py42.sdk import SDK

HOST_ADDRESS = "https://example.com"
TEST_USERNAME = "test-username"
TEST_PASSWORD = "test-password"


class TestSDK(object):
    @pytest.fixture
    def py42_session(self, mocker, successful_response):
        mock_session = mocker.MagicMock(spec=Py42Session)
        mock_session.get.return_value = successful_response
        return mock_session

    @pytest.fixture
    def mock_session_factory(self, mocker, py42_session):
        mock_session_factory = mocker.MagicMock(spec=SessionFactory)
        mock_session_factory.create_jwt_session.return_value = py42_session
        return mock_session_factory

    def test_has_administation_client_set(self, mock_session_factory, success_requests_session):
        deps = SDKDependencies(HOST_ADDRESS, mock_session_factory, success_requests_session)
        sdk = SDK(deps)
        assert type(sdk.administration) == administration.AdministrationClient

    def test_has_archive_module_set(self, mock_session_factory, success_requests_session):
        deps = SDKDependencies(HOST_ADDRESS, mock_session_factory, success_requests_session)
        sdk = SDK(deps)
        assert type(sdk.archive) == arch_mod.ArchiveModule

    def test_has_device_client_set(self, mock_session_factory, success_requests_session):
        deps = SDKDependencies(HOST_ADDRESS, mock_session_factory, success_requests_session)
        sdk = SDK(deps)
        assert type(sdk.devices) == devices.DeviceClient

    def test_has_employee_case_management_module_set(
        self, mock_session_factory, success_requests_session
    ):
        deps = SDKDependencies(HOST_ADDRESS, mock_session_factory, success_requests_session)
        sdk = SDK(deps)
        assert type(sdk.employee_case_management) == ecm_mod.EmployeeCaseManagementModule

    def test_has_legal_hold_client_set(self, mock_session_factory, success_requests_session):
        deps = SDKDependencies(HOST_ADDRESS, mock_session_factory, success_requests_session)
        sdk = SDK(deps)
        assert type(sdk.legal_hold) == legal_hold.LegalHoldClient

    def test_has_org_client_set(self, mock_session_factory, success_requests_session):
        deps = SDKDependencies(HOST_ADDRESS, mock_session_factory, success_requests_session)
        sdk = SDK(deps)
        assert type(sdk.orgs) == orgs.OrgClient

    def test_has_security_module_set(self, mock_session_factory, success_requests_session):
        deps = SDKDependencies(HOST_ADDRESS, mock_session_factory, success_requests_session)
        sdk = SDK(deps)
        assert type(sdk.security) == sec_mod.SecurityModule

    def test_has_user_client_set(self, mock_session_factory, success_requests_session):
        deps = SDKDependencies(HOST_ADDRESS, mock_session_factory, success_requests_session)
        sdk = SDK(deps)
        assert type(sdk.users) == users.UserClient

    def test_has_storage_client_factory_set(self, mock_session_factory, success_requests_session):
        deps = SDKDependencies(HOST_ADDRESS, mock_session_factory, success_requests_session)
        sdk = SDK(deps)
        assert type(sdk.storage) == StorageClientFactory

    def test_has_user_context_set(self, mock_session_factory, success_requests_session):
        deps = SDKDependencies(HOST_ADDRESS, mock_session_factory, success_requests_session)
        sdk = SDK(deps)
        assert type(sdk.user_context) == UserContext
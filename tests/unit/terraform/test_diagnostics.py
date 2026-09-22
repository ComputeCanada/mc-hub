import json
import pytest

from mchub.models.terraform.diagnostics import extract_diagnostics, is_timeout


PROVISIONER = '''Error: file provisioner error
with module.openstack.module.provision.terraform_data.deploy_puppetserver_files["mgmt1"]
on .terraform/modules/openstack/common/provision/main.tf line 99:
  provisioner "file" {
timeout - last error: Error connecting to bastion: ssh: handshake failed: ssh: unable to authenticate'''


def test_plain_provisioner_timeout_preserves_context():
    diagnostic = extract_diagnostics('node1: Creation complete\n' + PROVISIONER)
    assert diagnostic == PROVISIONER
    assert is_timeout(diagnostic)


def test_resize_error_is_not_a_timeout():
    diagnostic = extract_diagnostics("Error: Error waiting for instance to resize: unexpected state 'ACTIVE', wanted target 'VERIFY_RESIZE'.")
    assert not is_timeout(diagnostic)


def test_boxed_errors_keep_only_diagnostics():
    log = '\x1b[31m╷\n│ Error: timed out\n│\n│ with node1\n╵\x1b[0m\nnode2: Still creating...\n╷\n│ Error: another error\n╵'
    assert extract_diagnostics(log) == 'Error: timed out\n\nwith node1\n\nError: another error'


def test_structured_diagnostics_exclude_warnings_and_keep_source():
    warning = {'diagnostic': {'severity': 'warning', 'summary': 'timeout'}}
    error = {'diagnostic': {'severity': 'error', 'summary': 'file provisioner error',
             'detail': 'timeout - last error: SSH handshake failed', 'address': 'node1',
             'range': {'filename': 'main.tf', 'start': {'line': 99}},
             'snippet': {'code': 'provisioner "file" {'}}}
    result = extract_diagnostics('\n'.join(map(json.dumps, [warning, error])))
    assert result == 'Error: file provisioner error\ntimeout - last error: SSH handshake failed\nwith node1\non main.tf line 99\nprovisioner "file" {'
    assert is_timeout(result)


@pytest.mark.parametrize('log', ['', 'node1: Creating...', '{"type":"apply_progress"}'])
def test_no_diagnostic(log):
    assert extract_diagnostics(log) == ''


def test_timeout_setting_in_source_is_not_a_reported_timeout():
    assert not is_timeout('Error: Invalid value\non timeout.tf line 12:\ntimeout = 300')

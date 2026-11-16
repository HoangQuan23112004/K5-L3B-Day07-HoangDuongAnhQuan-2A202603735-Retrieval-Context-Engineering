import socket
import ssl
import unittest
import urllib.error
from unittest.mock import patch

from src.rag.providers import Provider, connection_detail


class NetworkErrorTests(unittest.TestCase):
    def test_classifies_network_errors_without_raw_secret_values(self):
        cases = [
            (socket.gaierror(11001, 'private-host'), 'DNS lookup failed'),
            (ssl.SSLCertVerificationError(1, 'private-certificate'), 'TLS certificate verification failed'),
            (TimeoutError('private-address'), 'connection timed out'),
            (ConnectionResetError('private-address'), 'connection reset'),
            ('Tunnel connection failed: 407 private-password', 'proxy authentication required'),
        ]
        for reason, expected in cases:
            detail = connection_detail(urllib.error.URLError(reason))
            self.assertIn(expected, detail)
            self.assertNotIn('private-', detail)

    def test_provider_reports_dns_cause(self):
        provider = Provider('ollama')
        provider.max_retries = 0
        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError(socket.gaierror(11001, 'private-host'))):
            with self.assertRaisesRegex(ConnectionError, 'DNS lookup failed'):
                provider.post('/api/chat', {'model': 'test-only'})

    def test_temporary_dns_error_is_retried_and_recorded(self):
        import io
        provider = Provider('ollama')
        provider.request_interval = 0
        with patch('urllib.request.urlopen', side_effect=[urllib.error.URLError(socket.gaierror(11001, 'private-host')), io.StringIO('{}')]), patch('time.sleep'):
            self.assertEqual(provider.post('/api/chat', {'model': 'test-only'}), {})
        self.assertEqual(provider.calls[0]['status'], 'network_error')
        self.assertTrue(provider.calls[0]['will_retry'])

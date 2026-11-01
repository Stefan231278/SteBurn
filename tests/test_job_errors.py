import unittest
from steburn.core.job_errors import remedy
from steburn.devices.grbl import GrblSession
from test_streaming import device

class JobErrorTests(unittest.TestCase):
    def test_offline_recommends_port_scan_and_connect_homing(self):
        hint=remedy('Kein Gerät verbunden.',GrblSession())
        self.assertIn('Ports suchen',hint); self.assertIn('Verbinden + Referenzfahrt',hint)
    def test_reference_fault_recommends_home_without_reconnect(self):
        self.assertIn('→ Neu referenzieren.',remedy('Controller-Neustart: reale Position unbekannt. Neu referenzieren.',device()))
    def test_position_error_recommends_geometry_correction(self):
        self.assertIn('Position und Größe',remedy('Ziel außerhalb des vorläufigen Innenbereichs',device()))
    def test_timeout_recommends_connection_recovery(self):
        self.assertIn('USB und Stromversorgung',remedy('Kein frischer Controllerstatus',device()))
    def test_firmware_requirements_are_not_automatically_modified(self):
        self.assertIn('nicht automatisch',remedy('$32=1 erforderlich',device()))

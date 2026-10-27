"""omarchy · pc widget: CPU and RAM readers (Linux /proc, macOS Mach ticks + vm_stat)."""
import subprocess
import sys
import unittest
from unittest import mock

import helpers  # noqa: F401  (hermetic env + sys.path)
from omarchy_link import stats

VM_STAT = """Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                                     4839.
Pages active:                                 163137.
Pages inactive:                               162248.
Pages wired down:                             442858.
Pages purgeable:                                  20.
"Translation faults":                    77603136123.
Anonymous pages:                              232657.
Pages occupied by compressor:                 234586.
"""


def fake_run(argv, **kw):
    out = {"vm_stat": VM_STAT, "sysctl": "17179869184\n"}[argv[0]]
    return subprocess.CompletedProcess(argv, 0, out, "")


class Stats(unittest.TestCase):
    def setUp(self):
        stats._last_cpu = None

    def test_cpu_is_a_delta(self):
        ticks = iter([(900, 1000), (1200, 2000), (1200, 2000)])
        with mock.patch.object(stats, "_cpu_ticks", lambda: next(ticks)):
            self.assertIsNone(stats.cpu_percent())     # first sample: nothing to compare with
            self.assertEqual(stats.cpu_percent(), 70)  # 300 idle of 1000 ticks
            self.assertIsNone(stats.cpu_percent())     # no ticks passed

    def test_cpu_counter_wrap_is_skipped(self):
        ticks = iter([(900, 4_000_000_000), (10, 100)])
        with mock.patch.object(stats, "_cpu_ticks", lambda: next(ticks)):
            stats.cpu_percent()
            self.assertIsNone(stats.cpu_percent())

    def test_macos_ram_from_vm_stat(self):
        # Activity Monitor's "Memory Used": wired + compressor + anonymous - purgeable, over hw.memsize.
        with mock.patch.object(sys, "platform", "darwin"), mock.patch.object(stats.subprocess, "run", fake_run):
            used = (442858 + 234586 + 232657 - 20) * 16384
            self.assertEqual(stats.ram_percent(), round(100 * used / 17179869184))

    def test_macos_ram_unknown_format(self):
        bad = lambda argv, **kw: subprocess.CompletedProcess(argv, 0, "nothing useful\n", "")
        with mock.patch.object(sys, "platform", "darwin"), mock.patch.object(stats.subprocess, "run", bad):
            self.assertIsNone(stats.ram_percent())

    @unittest.skipUnless(sys.platform == "darwin", "macOS only")
    def test_macos_real_readers(self):
        self.assertIsNone(stats.cpu_percent())
        subprocess.run(["sleep", "0.3"])
        cpu, ram = stats.cpu_percent(), stats.ram_percent()
        self.assertTrue(cpu is None or 0 <= cpu <= 100, cpu)
        self.assertTrue(0 < ram <= 100, ram)


if __name__ == "__main__":
    unittest.main()

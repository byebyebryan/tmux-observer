"""Capacity accounting must include processes created by the Mesh reader thread."""

import importlib.machinery
import importlib.util
import os
import selectors
import signal
import subprocess
import sys
import unittest
from pathlib import Path


class CapacityAccountingTests(unittest.TestCase):
    def test_process_tree_counts_child_spawned_from_non_main_thread(self):
        loader = importlib.machinery.SourceFileLoader(
            "capacity_accounting_test",
            str(Path(__file__).resolve().parents[1] / "scripts/accept-installed-capacity"),
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        program = """
import subprocess,sys,threading
def worker():
    child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'])
    try:
        print(child.pid,flush=True)
        sys.stdin.readline()
    finally:
        child.terminate()
        child.wait(timeout=5)
thread=threading.Thread(target=worker)
thread.start()
thread.join()
"""
        process = subprocess.Popen(
            [sys.executable, "-u", "-c", program],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                self.assertTrue(selector.select(5), "owned thread did not report its child")
            child = int(process.stdout.readline())
            rows = module.process_tree(process.pid)
            self.assertIn(process.pid, {row["pid"] for row in rows})
            self.assertIn(child, {row["pid"] for row in rows})
            self.assertTrue(all(row["rssBytes"] > 0 for row in rows))
        finally:
            try:
                process.communicate("close\n", timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main()

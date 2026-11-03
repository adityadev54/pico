import importlib.util,subprocess,sys,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pico_test_session',ROOT/'scripts/run_test_session.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class PrivateRuntimePackage(unittest.TestCase):
    def test_packaged_server_imports_teaching_without_source_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp)/'runtime.zip';module.package_runtime(archive)
            dest=Path(tmp)/'isolated';dest.mkdir()
            with zipfile.ZipFile(archive) as z:z.extractall(dest)
            # Isolated Python prevents accidentally finding agents in the checkout.
            result=subprocess.run([sys.executable,'-I','-c',f'import sys;sys.path.insert(0,{str(dest)!r});from server.skills.model import complete;assert callable(complete)'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

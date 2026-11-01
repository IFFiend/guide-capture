import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("guide",ROOT/"scripts/guide.py")
guide=importlib.util.module_from_spec(spec)
spec.loader.exec_module(guide)

class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)

    def write(self, data, name="input.json"):
        path = self.work / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def guide_input(self):
        image = self.work/"secret.png"
        Image.new("RGB",(300,200),"white").save(image)
        return {"title":"Guide", "audience":"Operators", "prerequisites":"Demo account", "steps":[
            {"id":"one","action":"Open settings", "expected":"Settings appear", "observed":"Supplied screenshot shows settings", "screenshot":str(image), "redact":[[10,10,80,40]]}]}

    def test_guide_redaction_is_baked_and_original_not_shipped(self):
        data = self.guide_input()
        result = guide.build(self.write(data), self.work/"out")
        with Image.open(self.work/"out/images/step-01.png") as image:
            self.assertEqual(image.getpixel((20,20)),(23,43,40))
            self.assertEqual(image.getpixel((100,100)),(255,255,255))
        self.assertFalse((self.work/"out/secret.png").exists())
        self.assertEqual(result["behavioral_verification"],"not_performed_by_builder")
        self.assertEqual(result["items"][0]["origin"],"user-supplied")
        self.assertIn("images/step-01.png",(self.work/"out/guide.md").read_text())

    def test_guide_requires_note_for_claimed_live_observation(self):
        data = self.guide_input()
        data["steps"][0]["origin"] = "agent-observed"
        with self.assertRaises(guide.GuideError):
            guide.build(self.write(data),self.work/"out")

    def test_guide_rejects_out_of_frame_redaction(self):
        data = self.guide_input()
        data["steps"][0]["redact"] = [[-1,0,50,50]]
        with self.assertRaises(guide.GuideError):
            guide.build(self.write(data),self.work/"out")

    def test_guide_html_does_not_execute_untrusted_prose(self):
        data = self.guide_input()
        data["title"] = "<script>alert(1)</script>"
        guide.build(self.write(data), self.work/"out")
        self.assertNotIn("<script>",(self.work/"out/index.html").read_text())

    def test_nonobject_input_is_rejected(self):
        with self.assertRaises(guide.GuideError):
            guide.build(self.write([]),self.work/"out")

if __name__=="__main__":
    unittest.main()

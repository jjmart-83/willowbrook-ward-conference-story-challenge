"""Verify archive round trips, integrity checks, and safe restoration paths."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, HERE.parent / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


archive_tool = load_module("archive_source_media")
restore_tool = load_module("restore_source_media")


class SourceArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="conference-source-test-")
        self.root = Path(self.temporary.name).resolve()
        self.source = self.root / "source"
        self.folder = self.source / "talks" / "Example Speaker \u00a6 October 2026"
        self.folder.mkdir(parents=True)
        (self.folder / "talk.mp4").write_bytes(b"example video bytes")
        (self.folder / "talk.English.srt").write_bytes(b"1\r\n00:00:00,000 --> 00:00:01,000\r\nA caption.\r\n")
        self.cache = self.root / "archives"
        self.cache.mkdir()
        self.zip_path = self.cache / "source-example.zip"
        files = archive_tool.create_archive(self.folder, self.zip_path, self.source)
        self.talk = {"id": "example", "files": files, "archive": {
            "assetName": self.zip_path.name, "bytes": self.zip_path.stat().st_size,
            "sha256": archive_tool.sha256(self.zip_path), "url": "https://example.invalid/not-needed.zip"}}
        self.destination = self.root / "restored"

    def tearDown(self):
        self.temporary.cleanup()

    def test_round_trip_preserves_bytes_paths_and_timestamps(self):
        restore_tool.restore_talk(self.talk, self.destination, self.cache)
        for record in self.talk["files"]:
            restored = self.destination / record["path"]
            self.assertEqual(restored.read_bytes(), (self.source / record["path"]).read_bytes())
            self.assertEqual(restored.stat().st_mtime_ns, record["mtimeNs"])
        restore_tool.restore_talk(self.talk, self.destination, self.cache, verify_only=True)

    def test_matching_caption_in_a_clone_is_kept(self):
        caption = next(record for record in self.talk["files"] if record["path"].endswith(".srt"))
        target = self.destination / caption["path"]
        target.parent.mkdir(parents=True)
        target.write_bytes((self.source / caption["path"]).read_bytes())
        restore_tool.restore_talk(self.talk, self.destination, self.cache)
        self.assertEqual(archive_tool.sha256(target), caption["sha256"])

    def test_different_existing_file_is_not_overwritten(self):
        target = self.destination / self.talk["files"][0]["path"]
        target.parent.mkdir(parents=True)
        target.write_bytes(b"local edit")
        with self.assertRaisesRegex(ValueError, "Existing file differs"):
            restore_tool.restore_talk(self.talk, self.destination, self.cache)
        self.assertEqual(target.read_bytes(), b"local edit")

    def test_corrupt_archive_is_rejected_before_extraction(self):
        self.zip_path.write_bytes(b"corrupt archive")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            restore_tool.restore_talk(self.talk, self.destination, self.cache)
        self.assertFalse(self.destination.exists())

    def test_paths_cannot_escape_talks(self):
        for relative in ["../outside", "talks/../outside", "/talks/absolute", "C:/outside", "talks\\..\\outside"]:
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                restore_tool.destination_for(self.destination, relative)

    def test_verify_only_reports_missing_files(self):
        with self.assertRaises(FileNotFoundError):
            restore_tool.restore_talk(self.talk, self.destination, self.cache, verify_only=True)


if __name__ == "__main__":
    unittest.main()

"""Tests of the form's behaviour. They open the real window, so they are
skipped where no display is available."""

import os
import sys
import tempfile
import tkinter as tk
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import remind

IMAGE_METADATA = {"System Name": "LSM 980", "Objective Model": "Plan-Apochromat 63x/1.4"}


class FormTest(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest(f"no display: {e}")
        self.addCleanup(self.root.destroy)

        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)

        # Message boxes wait for a click, and the real readers need image files.
        for patch in (
            mock.patch.object(remind, "messagebox"),
            mock.patch.object(remind, "application_folder", return_value=self.folder.name),
            mock.patch.dict(remind.IMAGE_READERS, {
                ".czi": ("CZI", lambda path: dict(IMAGE_METADATA), remind.metadata_to_form_fields),
            }),
        ):
            patch.start()
            self.addCleanup(patch.stop)

        self.app = remind.REMBIGUI(self.root)

    def write_file(self, name, text):
        path = os.path.join(self.folder.name, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def field(self, label):
        return dict(self.app.field_values())[label]

    def test_clear_form_removes_image_metadata_from_the_next_readme(self):
        self.app.load_image_file("first_experiment.czi")
        self.assertIn("LSM 980", self.app.readme_text())

        self.app.clear_form()

        self.assertNotIn("LSM 980", self.app.readme_text())
        self.assertNotIn("Extracted Image Metadata", self.app.readme_text())

    def test_loading_a_readme_replaces_image_metadata(self):
        self.app.load_image_file("first_experiment.czi")
        path = self.write_file("second_ReadME.txt", "Experiment name: Second\n")

        self.app.parse_readme_file(path)

        self.assertNotIn("Extracted Image Metadata", self.app.readme_text())

    def test_clear_form_returns_to_the_template(self):
        path = self.write_file("Confocal5_ReadME_template.txt",
                               "Storage Location: \\\\server\\Confocal5\\\n"
                               "Microscope name: Confocal 5\n"
                               "\n# Extracted Image Metadata\nSystem Name: LSM 880\n")
        self.app.select_and_load_template()  # the only template loads unasked
        self.assertEqual(self.app.template_path, path)
        # Metadata left in a template belongs to some earlier experiment.
        self.assertNotIn("Extracted Image Metadata", self.app.readme_text())

        self.app.set_field("Storage Location", "somewhere else")
        self.app.set_field("Experiment name", "Previous user's experiment")
        self.app.clear_form()

        self.assertEqual(self.field("Storage Location"), "\\\\server\\Confocal5\\")
        self.assertEqual(self.field("Microscope name"), "Confocal 5")
        self.assertEqual(self.field("Experiment name"), "")

    def test_image_file_does_not_replace_the_template_microscope_name(self):
        self.app.load_image_file("image.czi")
        self.assertEqual(self.field("Microscope name"), "LSM 980")

        self.app.load_template(self.write_file("Confocal5_ReadME_template.txt",
                                               "Microscope name: Confocal 5\n"))
        self.app.load_image_file("image.czi")

        self.assertEqual(self.field("Microscope name"), "Confocal 5")
        self.assertEqual(self.field("Objective"), "Plan-Apochromat 63x/1.4")


if __name__ == "__main__":
    unittest.main()

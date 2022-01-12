import unittest
import components.repository as repo
import logging

class RepoTests(unittest.TestCase):

    def repo_should_load(self):
        self.assertIsNone(repo.read_component(0))

if __name__ == "__main__":
    logging.basicConfig(
        filename="repo.log", filemode="w", level=logging.INFO
    )
    unittest.main()

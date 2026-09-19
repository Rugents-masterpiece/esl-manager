import unittest


class ApplicationContractTests(unittest.TestCase):
    def test_application_factory_exists(self):
        from esl_web.server import create_server

        self.assertTrue(callable(create_server))


if __name__ == "__main__":
    unittest.main()

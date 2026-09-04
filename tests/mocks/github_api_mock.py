class GithubStorageMock:
    def get_magic_castle_versions(self):
        return ["14.1.2", "14.0.0"]

    def create_repo(self, *args, **kwargs):
        return "MOCK_ORG/MOCK_REPO"

    def write(self, *args, **kwargs):
        return "MOCK_SHA"

    def archive_repo(self, *args, **kwargs):
        return None

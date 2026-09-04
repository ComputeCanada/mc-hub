class GithubStorageMock:
    def create_repo(self, *args, **kwargs):
        return "MOCK_ORG/MOCK_REPO"

    def write(self, *args, **kwargs):
        return "MOCK_SHA"

    def archive_repo(self, *args, **kwargs):
        return None

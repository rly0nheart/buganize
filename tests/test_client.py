import pytest
import pytest_asyncio

from buganize.api.client import Buganize
from buganize.api.models import (
    Comment,
    Issue,
    IssueUpdatesResult,
    Priority,
    SearchResult,
    Status,
)


@pytest_asyncio.fixture
async def client():
    async with Buganize() as buganizer:
        yield buganizer


class TestSearch:
    async def test_returns_search_result(self, client):
        result = await client.search("status:open", page_size=5)

        assert isinstance(result, SearchResult)
        assert result.total_count > 0
        assert len(result.issues) > 0
        assert len(result.issues) <= 5

    async def test_issues_have_basic_fields(self, client):
        result = await client.search("status:open", page_size=3)

        for issue in result.issues:
            assert isinstance(issue, Issue)
            assert isinstance(issue.id, int)
            assert issue.id > 0
            assert isinstance(issue.title, str)
            assert len(issue.title) > 0
            assert isinstance(issue.status, Status)
            assert isinstance(issue.priority, Priority)

    async def test_pagination_token_present(self, client):
        result = await client.search("status:open", page_size=1)

        assert result.has_more is True
        assert result.next_page_token is not None
        assert isinstance(result.next_page_token, str)

    async def test_query_filters_work(self, client):
        result = await client.search("component:Blink", page_size=3)

        assert isinstance(result, SearchResult)
        assert result.total_count > 0
        assert len(result.issues) > 0


class TestGetIssue:
    async def test_returns_issue(self, client):
        # First find an issue ID from search
        search = await client.search("status:open", page_size=1)
        issue_id = search.issues[0].id

        issue = await client.issues(issue_ids=[issue_id])

        assert isinstance(issue[0], Issue)
        assert issue[0].id == issue_id

    async def test_issue_has_all_basic_fields(self, client):
        search = await client.search("status:open", page_size=1)
        issue = await client.issues(issue_ids=[search.issues[0].id])

        assert isinstance(issue[0].id, int)
        assert isinstance(issue[0].title, str)
        assert len(issue[0].title) > 0
        assert isinstance(issue[0].status, Status)
        assert isinstance(issue[0].priority, Priority)
        assert issue[0].created_at is not None
        assert issue[0].modified_at is not None
        assert issue[0].url == f"https://issuetracker.google.com/issues/{issue[0].id}"

    async def test_issue_has_reporter(self, client):
        search = await client.search("status:open", page_size=1)
        issue = await client.issues(issue_ids=[search.issues[0].id])

        assert issue[0].reporter is not None
        assert "@" in issue[0].reporter

    async def test_timestamps_are_sane(self, client):
        search = await client.search("status:open", page_size=1)
        issue = await client.issues(issue_ids=[search.issues[0].id])

        assert issue[0].created_at.year >= 2008  # Chromium tracker existed since ~2008
        assert issue[0].modified_at >= issue[0].created_at


class TestBatchGetIssues:
    async def test_returns_all_requested_issues(self, client):
        # Get some issue IDs first
        search = await client.search("status:open", page_size=3)
        ids = [i.id for i in search.issues]

        issues = await client.issues(ids)

        assert len(issues) == len(ids)
        returned_ids = {i.id for i in issues}
        assert returned_ids == set(ids)

    async def test_batch_issues_have_basic_fields(self, client):
        search = await client.search("status:open", page_size=2)
        ids = [i.id for i in search.issues]

        issues = await client.issues(ids)

        for issue in issues:
            assert isinstance(issue, Issue)
            assert issue.id > 0
            assert len(issue.title) > 0
            assert isinstance(issue.status, Status)
            assert isinstance(issue.priority, Priority)


class TestGetIssueUpdates:
    async def test_returns_updates_result(self, client):
        # Find an issue that has comments
        search = await client.search("status:fixed", page_size=5)
        # Pick one with comments
        target = None
        for issue in search.issues:
            if issue.comment_count > 0:
                target = issue
                break
        if target is None:
            pytest.skip("No issue with comments found in search results")

        result = await client.issue_updates(target.id)

        assert isinstance(result, IssueUpdatesResult)
        assert result.total_count > 0
        assert len(result.updates) > 0

    async def test_updates_have_authors_and_timestamps(self, client):
        search = await client.search("status:fixed", page_size=5)
        target = next((i for i in search.issues if i.comment_count > 0), None)
        if target is None:
            pytest.skip("No issue with comments found")

        result = await client.issue_updates(target.id)

        for update in result.updates:
            assert update.issue_id == target.id
            assert update.author is not None
            assert update.timestamp is not None


class TestGetComments:
    async def test_returns_comments_in_chronological_order(self, client):
        search = await client.search("status:fixed", page_size=10)
        candidates = [i for i in search.issues if i.comment_count >= 2]
        if not candidates:
            pytest.skip("No issue with 2+ comments found")

        # Skip internal issues (all comments have empty bodies)
        for candidate in candidates:
            comments = await client.comments(candidate.id)
            if any(c.body for c in comments):
                break
            assert isinstance(candidate.title, str)
        else:
            pytest.skip("All candidate issues are internal (redacted comments)")

        assert len(comments) >= 2
        for comment in comments:
            assert isinstance(comment, Comment)
            assert comment.issue_id == candidate.id
            assert isinstance(comment.comment_number, int)
            assert comment.comment_number >= 1

        # Verify chronological order
        for i in range(len(comments) - 1):
            if comments[i].timestamp and comments[i + 1].timestamp:
                assert comments[i].timestamp <= comments[i + 1].timestamp

    async def test_comments_have_content(self, client):
        search = await client.search("status:fixed", page_size=10)
        candidates = [i for i in search.issues if i.comment_count > 0]
        if not candidates:
            pytest.skip("No issue with comments found")

        for candidate in candidates:
            comments = await client.comments(candidate.id)
            if any(c.body for c in comments):
                break
            assert isinstance(candidate.title, str)
        else:
            pytest.skip("All candidate issues are internal (redacted comments)")

        assert len(comments) > 0
        has_body = any(len(comment.body) > 0 for comment in comments)
        assert has_body

    async def test_comment_authors_are_emails(self, client):
        search = await client.search("status:fixed", page_size=10)
        candidates = [i for i in search.issues if i.comment_count > 0]
        if not candidates:
            pytest.skip("No issue with comments found")

        for candidate in candidates:
            comments = await client.comments(candidate.id)
            if any(c.body for c in comments):
                break
            assert isinstance(candidate.title, str)
        else:
            pytest.skip("All candidate issues are internal (redacted comments)")

        for comment in comments:
            if comment.author:
                assert "@" in comment.author

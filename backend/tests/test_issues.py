from datetime import datetime, timedelta, timezone

from backend.models import SupportIssue
from backend.services import is_overdue_high_priority


def test_create_defaults_trims_and_generates_id_timestamp(client):
    body = {"client_name": " ABC ", "issue_title": " Title ", "description": " Details "}
    first = client.post("/api/issues", json=body)
    second = client.post("/api/issues", json=body)
    assert first.status_code == 201
    issue = first.json()
    assert issue["issue_id"] != second.json()["issue_id"]
    assert issue["client_name"] == "ABC"
    assert issue["priority"] == "Medium" and issue["status"] == "Open"
    assert datetime.fromisoformat(issue["date_time_reported"].replace("Z", "+00:00")).tzinfo
    assert issue["is_overdue_high_priority"] is False


def test_create_rejects_empty_invalid_and_missing_fields(client):
    assert client.post("/api/issues", json={}).status_code == 422
    assert client.post("/api/issues", json={"client_name": " ", "issue_title": "x", "description": "x"}).status_code == 422
    payload = {"client_name": "a", "issue_title": "b", "description": "c", "priority": "Urgent"}
    assert client.post("/api/issues", json=payload).status_code == 422
    payload["priority"] = "Low"
    payload["status"] = "Pending"
    assert client.post("/api/issues", json=payload).status_code == 422


def test_list_pagination_get_and_not_found(client, create_issue):
    a = create_issue(issue_title="One")
    create_issue(issue_title="Two")
    assert len(client.get("/api/issues").json()) == 2
    assert len(client.get("/api/issues?skip=1&limit=1").json()) == 1
    assert client.get(f"/api/issues/{a['issue_id']}").json()["issue_title"] == "One"
    assert client.get("/api/issues/999").status_code == 404
    assert client.get("/api/issues?limit=101").status_code == 422


def test_update_status_delete_and_missing(client, create_issue):
    original = create_issue(priority="High", assigned_engineer="Casey Engineer")
    issue_id = original["issue_id"]
    updated = client.put(f"/api/issues/{issue_id}", json={
        "client_name": "Changed", "issue_title": "Changed title", "description": "Changed",
        "assigned_engineer": "Casey Engineer", "priority": "Low", "status": "Open",
    }).json()
    assert updated["client_name"] == "Changed"
    assert updated["issue_id"] == issue_id
    assert updated["date_time_reported"] == original["date_time_reported"]
    changed = client.patch(f"/api/issues/{issue_id}/status", json={"status": "Resolved"}).json()
    assert changed["status"] == "Resolved"
    assert changed["issue_title"] == "Changed title"
    assert client.patch(f"/api/issues/{issue_id}/status", json={"status": "Bad"}).status_code == 422
    assert client.put("/api/issues/999", json={
        "client_name": "a", "issue_title": "b", "description": "c", "priority": "Low", "status": "Open"
    }).status_code == 404
    assert client.delete(f"/api/issues/{issue_id}").status_code == 204
    assert client.get(f"/api/issues/{issue_id}").status_code == 404
    assert client.delete("/api/issues/999").status_code == 404


def test_engineer_assignment_filter_and_resolution_rule(client, create_issue):
    unassigned = create_issue(issue_title="Needs ownership")
    assert unassigned["assigned_engineer"] is None
    blocked = client.patch(
        f"/api/issues/{unassigned['issue_id']}/status", json={"status": "Resolved"}
    )
    assert blocked.status_code == 422

    assigned = create_issue(
        issue_title="Assigned request", assigned_engineer="  Alex Engineer  "
    )
    assert assigned["assigned_engineer"] == "Alex Engineer"
    result = client.get("/api/issues?assigned_engineer=alex%20engineer")
    assert [issue["issue_id"] for issue in result.json()] == [assigned["issue_id"]]
    result = client.get("/api/issues/filter?assigned_engineer=Alex%20Engineer")
    assert len(result.json()) == 1

    resolved = client.patch(
        f"/api/issues/{assigned['issue_id']}/status", json={"status": "Resolved"}
    )
    assert resolved.status_code == 200
    assert resolved.json()["assigned_engineer"] == "Alex Engineer"

    invalid_create = client.post("/api/issues", json={
        "client_name": "Client", "issue_title": "No owner", "description": "Details",
        "status": "Resolved",
    })
    assert invalid_create.status_code == 422

    invalid_update = client.put(f"/api/issues/{assigned['issue_id']}", json={
        "client_name": "Client", "issue_title": "Updated", "description": "Details",
        "assigned_engineer": None, "priority": "Low", "status": "Resolved",
    })
    assert invalid_update.status_code == 422


def test_search_and_filters(client, create_issue):
    create_issue(client_name="Acme Account", issue_title="Billing", priority="High")
    create_issue(client_name="Other", issue_title="account failure", priority="High", status="Resolved", assigned_engineer="Riley")
    create_issue(client_name="Other", issue_title="Network", priority="Low")
    assert len(client.get("/api/issues/search?q= ACCOUNT ").json()) == 2
    assert len(client.get("/api/issues/search?q=billing").json()) == 1
    assert len(client.get("/api/issues/filter?priority=High&status=Resolved").json()) == 1
    assert len(client.get("/api/issues?q=account&priority=High&status=Open").json()) == 1
    assert client.get("/api/issues/search?q=%20%20").status_code == 422
    assert client.get("/api/issues/filter?priority=Urgent").status_code == 422
    assert client.get("/api/issues/search?q=absent").json() == []


def test_overdue_boundary_and_endpoint_and_stats(client, create_issue, monkeypatch):
    # Exercise the shared business rule at boundaries without relying on wall-clock timing.
    now = datetime.now(timezone.utc)
    def item(priority="High", status="Open", age=25):
        return SupportIssue(priority=priority, status=status, date_time_reported=now - timedelta(hours=age))
    assert is_overdue_high_priority(item(), now)
    assert is_overdue_high_priority(item(status="In Progress"), now)
    assert not is_overdue_high_priority(item(status="Resolved"), now)
    assert not is_overdue_high_priority(item(priority="Medium"), now)
    assert not is_overdue_high_priority(item(priority="Low"), now)
    assert not is_overdue_high_priority(item(age=23), now)
    assert not is_overdue_high_priority(item(age=24), now)

    oldest = create_issue(priority="High", status="Open")
    create_issue(priority="High", status="In Progress")
    create_issue(priority="High", status="Resolved", assigned_engineer="Jordan")
    create_issue(priority="Medium", status="Open")
    stats = client.get("/api/issues/stats").json()
    assert stats["total_issues"] == 4
    assert stats["open_issues"] == 2
    assert stats["in_progress_issues"] == 1
    assert stats["resolved_issues"] == 1
    assert stats["high_priority_issues"] == 3
    assert stats["overdue_high_priority_issues"] == 0
    assert client.get("/api/issues/overdue").json() == []

    # Advancing the shared clock makes the same stored issue overdue without changing its row.
    future = now + timedelta(hours=26)
    monkeypatch.setattr("backend.crud.utc_now", lambda: future)
    monkeypatch.setattr("backend.services.utc_now", lambda: future)
    fetched = client.get(f"/api/issues/{oldest['issue_id']}").json()
    assert fetched["is_overdue_high_priority"] is True
    assert len(client.get("/api/issues/overdue").json()) == 2
    assert client.get("/api/issues/stats").json()["overdue_high_priority_issues"] == 2

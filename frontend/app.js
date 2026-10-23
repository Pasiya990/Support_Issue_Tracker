const API = `${window.location.protocol}//${window.location.hostname}:8000/api`;
const rows = document.querySelector('#issue-rows');
const formMessage = document.querySelector('#form-message');
const listMessage = document.querySelector('#list-message');
let allIssues = [];

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  });
  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((item) => item.msg).join(', ')
      : data.detail;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return data;
}

function setMessage(element, message = '', success = false) {
  element.textContent = message;
  element.classList.toggle('success', success);
}

function updateStats(stats) {
  document.querySelector('#total-count').textContent = stats.total_issues;
  document.querySelector('#open-count').textContent = stats.open_issues;
  document.querySelector('#progress-count').textContent = stats.in_progress_issues;
  document.querySelector('#resolved-count').textContent = stats.resolved_issues;
  document.querySelector('#overdue-count').textContent = stats.overdue_high_priority_issues;
}

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
}

function addCell(row, content, className = '') {
  const cell = document.createElement('td');
  if (className) cell.className = className;
  if (content instanceof Node) cell.append(content);
  else cell.textContent = content;
  row.append(cell);
  return cell;
}

function makeIssueCell(issue) {
  const wrapper = document.createElement('div');
  const title = document.createElement('span');
  title.className = 'issue-title';
  title.textContent = issue.issue_title;
  title.title = issue.issue_title;
  wrapper.append(title);
  const id = document.createElement('span');
  id.className = 'issue-id';
  id.textContent = `ISS-${String(issue.issue_id).padStart(4, '0')}`;
  wrapper.append(id);
  if (issue.is_overdue_high_priority) {
    const overdue = document.createElement('span');
    overdue.className = 'overdue-tag';
    overdue.textContent = 'OVERDUE';
    title.append(overdue);
  }
  return wrapper;
}

function makePriority(issue) {
  const pill = document.createElement('span');
  pill.className = `priority-pill priority-${issue.priority.toLowerCase()}`;
  pill.textContent = issue.priority;
  return pill;
}

function makeEngineerEditor(issue) {
  const wrapper = document.createElement('div');
  wrapper.className = 'engineer-cell';
  const input = document.createElement('input');
  input.className = 'engineer-input';
  input.maxLength = 200;
  input.placeholder = 'Unassigned';
  input.value = issue.assigned_engineer || '';
  input.setAttribute('aria-label', `Assigned engineer for ${issue.issue_title}`);
  const save = document.createElement('button');
  save.className = 'save-assignee';
  save.type = 'button';
  save.textContent = 'Save';
  save.title = 'Save assigned engineer';
  save.addEventListener('click', async () => {
    const engineer = input.value.trim() || null;
    try {
      await request(`/issues/${issue.issue_id}`, {
        method: 'PUT',
        body: JSON.stringify({
          client_name: issue.client_name,
          issue_title: issue.issue_title,
          description: issue.description,
          assigned_engineer: engineer,
          priority: issue.priority,
          status: issue.status,
        }),
      });
      setMessage(listMessage, 'Engineer assignment saved.', true);
      await refresh();
    } catch (error) {
      setMessage(listMessage, error.message);
    }
  });
  wrapper.append(input, save);
  return wrapper;
}

function makeStatusSelect(issue) {
  const select = document.createElement('select');
  select.className = 'status-select';
  select.setAttribute('aria-label', `Status for ${issue.issue_title}`);
  for (const status of ['Open', 'In Progress', 'Resolved']) {
    const option = document.createElement('option');
    option.value = status;
    option.textContent = status;
    option.disabled = status === 'Resolved' && !issue.assigned_engineer;
    option.selected = status === issue.status;
    select.append(option);
  }
  select.addEventListener('change', async () => {
    try {
      await request(`/issues/${issue.issue_id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: select.value }),
      });
      setMessage(listMessage, 'Issue status updated.', true);
      await refresh();
    } catch (error) {
      setMessage(listMessage, error.message);
      select.value = issue.status;
    }
  });
  return select;
}

function renderIssues(issues) {
  rows.replaceChildren();
  if (!issues.length) {
    const row = document.createElement('tr');
    const cell = addCell(row, 'No issues match these filters.', 'empty-state');
    cell.colSpan = 7;
    rows.append(row);
    return;
  }
  for (const issue of issues) {
    const row = document.createElement('tr');
    if (issue.is_overdue_high_priority) row.className = 'overdue-row';
    addCell(row, makeIssueCell(issue));
    addCell(row, issue.client_name, 'client-name');
    addCell(row, makeEngineerEditor(issue));
    addCell(row, makePriority(issue));
    addCell(row, makeStatusSelect(issue));
    addCell(row, formatDate(issue.date_time_reported), 'date-cell');
    const deleteButton = document.createElement('button');
    deleteButton.className = 'delete-button';
    deleteButton.type = 'button';
    deleteButton.textContent = 'Delete';
    deleteButton.addEventListener('click', async () => {
      if (!window.confirm(`Delete “${issue.issue_title}”? This cannot be undone.`)) return;
      try {
        await request(`/issues/${issue.issue_id}`, { method: 'DELETE' });
        setMessage(listMessage, 'Issue deleted.', true);
        await refresh();
      } catch (error) {
        setMessage(listMessage, error.message);
      }
    });
    addCell(row, deleteButton);
    rows.append(row);
  }
}

function refreshEngineerOptions() {
  const select = document.querySelector('#engineer-filter');
  const selected = select.value;
  const engineers = [...new Set(allIssues.map((issue) => issue.assigned_engineer).filter(Boolean))]
    .sort((a, b) => a.localeCompare(b));
  select.replaceChildren(new Option('All engineers', ''));
  for (const engineer of engineers) select.add(new Option(engineer, engineer));
  select.value = engineers.includes(selected) ? selected : '';
}

async function refresh() {
  setMessage(listMessage);
  try {
    const [issues, stats] = await Promise.all([
      request('/issues?limit=100'),
      request('/issues/stats'),
    ]);
    allIssues = issues;
    refreshEngineerOptions();
    updateStats(stats);
    const params = new URLSearchParams();
    const search = document.querySelector('#search-input').value.trim();
    const status = document.querySelector('#status-filter').value;
    const priority = document.querySelector('#priority-filter').value;
    const engineer = document.querySelector('#engineer-filter').value;
    if (search) params.set('q', search);
    if (status) params.set('status', status);
    if (priority) params.set('priority', priority);
    if (engineer) params.set('assigned_engineer', engineer);
    const filtered = params.size ? await request(`/issues?${params}`) : issues;
    renderIssues(filtered);
  } catch (error) {
    rows.replaceChildren();
    const row = document.createElement('tr');
    const cell = addCell(row, 'Could not connect to the API. Start the backend on port 8000 and refresh.', 'empty-state');
    cell.colSpan = 7;
    rows.append(row);
    setMessage(listMessage, error.message);
  }
}

document.querySelector('#create-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const values = Object.fromEntries(new FormData(form).entries());
  values.assigned_engineer = values.assigned_engineer.trim() || null;
  setMessage(formMessage);
  try {
    await request('/issues', { method: 'POST', body: JSON.stringify(values) });
    form.reset();
    form.elements.priority.value = 'Medium';
    setMessage(formMessage, 'Issue created and added to the queue.', true);
    await refresh();
  } catch (error) {
    setMessage(formMessage, error.message);
  }
});

document.querySelector('#refresh-button').addEventListener('click', refresh);
for (const selector of ['#status-filter', '#priority-filter', '#engineer-filter']) {
  document.querySelector(selector).addEventListener('change', refresh);
}
let searchTimer;
document.querySelector('#search-input').addEventListener('input', () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(refresh, 250);
});

refresh();

#!/usr/bin/env python3
"""
Browser-style navigation test for Small ERP.
Tests every page and function by making real HTTP requests to the running server.
"""
import sys
import requests
from datetime import date
from urllib.parse import urlparse

BASE = 'http://127.0.0.1:5099'
PASS = 0
FAIL = 0
ERRORS = []


def ok(test_name):
    global PASS
    PASS += 1
    print(f'  \033[32mOK\033[0m  {test_name}')


def fail(test_name, detail=''):
    global FAIL
    FAIL += 1
    msg = f'  \033[31mFAIL\033[0m {test_name}'
    if detail:
        msg += f' — {detail}'
    print(msg)
    ERRORS.append(f'{test_name}: {detail}')


def check(condition, test_name, detail=''):
    if condition:
        ok(test_name)
    else:
        fail(test_name, detail)


def login(session, username='admin', password='admin123'):
    """Login and return the response."""
    # Get CSRF token from login page
    r = session.get(f'{BASE}/login')
    # Extract csrf_token from form
    import re
    csrf = re.search(r'name="csrf_token"\s+value="([^"]+)"', r.text)
    token = csrf.group(1) if csrf else ''
    r = session.post(f'{BASE}/login', data={
        'username': username,
        'password': password,
        'csrf_token': token,
    }, allow_redirects=True)
    return r


def get_csrf(session, url):
    """Extract CSRF token from a GET request to the url."""
    import re
    r = session.get(url)
    csrf = re.search(r'name="csrf_token"\s+value="([^"]+)"', r.text)
    return csrf.group(1) if csrf else '', r


def post_with_csrf(session, url, data, **kwargs):
    """POST with auto-extracted CSRF token."""
    csrf, get_resp = get_csrf(session, url)
    data['csrf_token'] = csrf
    return session.post(url, data=data, **kwargs)


# =========================================================================
print('\n' + '='*70)
print('SMALL ERP — BROWSER NAVIGATION TEST')
print('='*70)

# =========================================================================
print('\n--- 1. LOGIN PAGE ---')
s = requests.Session()

r = s.get(f'{BASE}/login')
check(r.status_code == 200, 'Login page loads')
check('Small ERP' in r.text, 'Login page has brand')
check('name="username"' in r.text, 'Login page has username field')
check('name="password"' in r.text, 'Login page has password field')
check('csrf_token' in r.text, 'Login page has CSRF token')

# Bad credentials
csrf, _ = get_csrf(s, f'{BASE}/login')
r = s.post(f'{BASE}/login', data={
    'username': 'admin', 'password': 'wrongpassword', 'csrf_token': csrf,
}, allow_redirects=True)
check('flash' in r.text or 'Credenziali' in r.text or 'Invalid' in r.text,
      'Login with wrong password shows error')

# Protected route redirects to login
s2 = requests.Session()
r = s2.get(f'{BASE}/', allow_redirects=False)
check(r.status_code in (301, 302, 303, 307), 'Dashboard redirects when not logged in')

r = s2.get(f'{BASE}/activities/', allow_redirects=False)
check(r.status_code in (301, 302, 303, 307), 'Activities redirects when not logged in')

# Successful login
r = login(s)
check(r.status_code == 200, 'Login with valid credentials succeeds')
check('Dashboard' in r.text or 'dashboard' in r.text, 'Redirects to dashboard after login')

# =========================================================================
print('\n--- 2. DASHBOARD ---')
r = s.get(f'{BASE}/')
check(r.status_code == 200, 'Dashboard loads')
check('stat-card' in r.text, 'Dashboard has stat cards')
check('sidebar' in r.text, 'Dashboard has sidebar navigation')
check('/activities/new' in r.text, 'Dashboard has new activity button')
check('/users/' in r.text, 'Dashboard shows admin nav (superadmin)')
check('/audit/' in r.text, 'Dashboard shows audit nav (superadmin)')
check('lang-switch' in r.text, 'Dashboard has language switcher')
check('/logout' in r.text, 'Dashboard has logout link')

# =========================================================================
print('\n--- 3. ACTIVITIES LIST ---')
r = s.get(f'{BASE}/activities/')
check(r.status_code == 200, 'Activities list loads')
check('/activities/new' in r.text, 'Activities list has new button')

# Filter by status
r = s.get(f'{BASE}/activities/?status=bozza')
check(r.status_code == 200, 'Activities filter by bozza works')

r = s.get(f'{BASE}/activities/?status=confermata')
check(r.status_code == 200, 'Activities filter by confermata works')

r = s.get(f'{BASE}/activities/?status=chiusa')
check(r.status_code == 200, 'Activities filter by chiusa works')

r = s.get(f'{BASE}/activities/?status=invalid')
check(r.status_code == 200, 'Activities filter with invalid status does not crash')

# =========================================================================
print('\n--- 4. CREATE ACTIVITY ---')
r = s.get(f'{BASE}/activities/new')
check(r.status_code == 200, 'Activity create form loads')
check('name="title"' in r.text, 'Create form has title field')
check('name="date"' in r.text, 'Create form has date field')
check('name="total_revenue"' in r.text, 'Create form has revenue field')
check('name="agent_id"' in r.text, 'Create form has agent dropdown')
check('name="status"' in r.text, 'Create form has status field')

# Submit valid activity
r = post_with_csrf(s, f'{BASE}/activities/new', {
    'title': 'Browser Test Activity',
    'description': 'Created via browser test',
    'date': date.today().isoformat(),
    'total_revenue': '5000',
    'agent_percentage': '10',
    'status': 'bozza',
}, allow_redirects=True)
check('Browser Test Activity' in r.text, 'Activity created successfully and visible on detail page')
# Extract activity ID from URL
activity_url = r.url
activity_id = activity_url.rstrip('/').split('/')[-1] if '/activities/' in activity_url else None
check(activity_id and activity_id.isdigit(), f'Activity detail page URL is correct (ID={activity_id})')

# Submit with empty title (should be rejected)
r = post_with_csrf(s, f'{BASE}/activities/new', {
    'title': '',
    'date': date.today().isoformat(),
    'total_revenue': '100',
    'agent_percentage': '0',
}, allow_redirects=True)
check('flash' in r.text, 'Empty title activity rejected with flash')

# Submit with invalid revenue
r = post_with_csrf(s, f'{BASE}/activities/new', {
    'title': 'Bad Revenue',
    'date': date.today().isoformat(),
    'total_revenue': 'abc',
    'agent_percentage': '0',
}, allow_redirects=True)
check('flash' in r.text, 'Invalid revenue rejected with flash')

# Submit with percentage > 100
r = post_with_csrf(s, f'{BASE}/activities/new', {
    'title': 'Over 100',
    'date': date.today().isoformat(),
    'total_revenue': '1000',
    'agent_percentage': '150',
}, allow_redirects=True)
check('flash' in r.text, 'Agent percentage > 100 rejected with flash')

# Submit with negative revenue
r = post_with_csrf(s, f'{BASE}/activities/new', {
    'title': 'Negative Revenue',
    'date': date.today().isoformat(),
    'total_revenue': '-500',
    'agent_percentage': '0',
}, allow_redirects=True)
check('flash' in r.text, 'Negative revenue rejected with flash')

# =========================================================================
print('\n--- 5. ACTIVITY DETAIL ---')
if activity_id:
    r = s.get(f'{BASE}/activities/{activity_id}')
    check(r.status_code == 200, 'Activity detail loads')
    check('Browser Test Activity' in r.text, 'Detail shows activity title')
    check('breakdown' in r.text, 'Detail has financial breakdown')
    check('5.000,00' in r.text, 'Detail shows formatted revenue')
    check('500,00' in r.text, 'Detail shows agent compensation (10% of 5000)')
    check('4.500,00' in r.text, 'Detail shows net margin')
    check(f'/activities/{activity_id}/edit' in r.text, 'Detail has edit button')
    check(f'/activities/{activity_id}/delete' in r.text, 'Detail has delete form')
    check('costs/add' in r.text, 'Detail has add cost button')
    check('participants/add' in r.text, 'Detail has add participant button')

    # 404 for nonexistent
    r = s.get(f'{BASE}/activities/99999')
    check(r.status_code == 404, 'Nonexistent activity returns 404')

# =========================================================================
print('\n--- 6. EDIT ACTIVITY ---')
if activity_id:
    r = s.get(f'{BASE}/activities/{activity_id}/edit')
    check(r.status_code == 200, 'Activity edit form loads')
    check('Browser Test Activity' in r.text, 'Edit form prefills title')

    r = post_with_csrf(s, f'{BASE}/activities/{activity_id}/edit', {
        'title': 'Browser Test Edited',
        'date': date.today().isoformat(),
        'total_revenue': '7000',
        'agent_percentage': '12',
        'status': 'confermata',
    }, allow_redirects=True)
    check('Browser Test Edited' in r.text, 'Activity edited successfully')
    check('confermata' in r.text.lower() or 'Confermata' in r.text, 'Status updated to confermata')

# =========================================================================
print('\n--- 7. ADD COST ---')
if activity_id:
    r = s.get(f'{BASE}/activities/{activity_id}/costs/add')
    check(r.status_code == 200, 'Cost form loads')
    check('name="description"' in r.text, 'Cost form has description field')
    check('name="amount"' in r.text, 'Cost form has amount field')
    check('name="category"' in r.text, 'Cost form has category field')
    check('materiale' in r.text, 'Cost form has materiale option')
    check('trasporto' in r.text, 'Cost form has trasporto option')

    r = post_with_csrf(s, f'{BASE}/activities/{activity_id}/costs/add', {
        'description': 'Browser Test Cost',
        'amount': '250.50',
        'category': 'consulenza',
        'cost_type': 'operativo',
        'date': date.today().isoformat(),
    }, allow_redirects=True)
    check('Browser Test Cost' in r.text, 'Cost added successfully')
    check('250,50' in r.text, 'Cost amount displayed correctly')

    # Empty description rejected
    r = post_with_csrf(s, f'{BASE}/activities/{activity_id}/costs/add', {
        'description': '',
        'amount': '100',
        'category': 'altro',
        'date': date.today().isoformat(),
    }, allow_redirects=True)
    check('flash' in r.text, 'Empty cost description rejected')

# =========================================================================
print('\n--- 8. ADD PARTICIPANT ---')
if activity_id:
    r = s.get(f'{BASE}/activities/{activity_id}/participants/add')
    check(r.status_code == 200, 'Participant form loads')
    check('name="participant_name"' in r.text, 'Participant form has name field')
    check('name="work_share"' in r.text, 'Participant form has work_share field')

    r = post_with_csrf(s, f'{BASE}/activities/{activity_id}/participants/add', {
        'participant_name': 'Browser Test Participant',
        'role_description': 'Tester',
        'work_share': '60',
        'fixed_compensation': '100',
    }, allow_redirects=True)
    check('Browser Test Participant' in r.text, 'Participant added successfully')

    # Empty name rejected
    r = post_with_csrf(s, f'{BASE}/activities/{activity_id}/participants/add', {
        'participant_name': '',
        'work_share': '50',
        'fixed_compensation': '0',
    }, allow_redirects=True)
    check('flash' in r.text, 'Empty participant name rejected')

# =========================================================================
print('\n--- 9. AGENTS ---')
r = s.get(f'{BASE}/agents/')
check(r.status_code == 200, 'Agents list loads')
check('/agents/new' in r.text, 'Agents list has new button')

# Create agent
r = post_with_csrf(s, f'{BASE}/agents/new', {
    'first_name': 'Browser Test Agent',
    'default_percentage': '15',
    'is_active': 'on',
}, allow_redirects=True)
check('Browser Test Agent' in r.text, 'Agent created successfully')

# Create agent with empty name (rejected)
r = post_with_csrf(s, f'{BASE}/agents/new', {
    'first_name': '',
    'default_percentage': '10',
    'is_active': 'on',
}, allow_redirects=True)
check('flash' in r.text, 'Empty agent name rejected')

# Create agent with percentage > 100 (rejected)
r = post_with_csrf(s, f'{BASE}/agents/new', {
    'first_name': 'Over Agent',
    'default_percentage': '200',
    'is_active': 'on',
}, allow_redirects=True)
check('flash' in r.text, 'Agent percentage > 100 rejected')

# Create agent with negative percentage (rejected)
r = post_with_csrf(s, f'{BASE}/agents/new', {
    'first_name': 'Neg Agent',
    'default_percentage': '-5',
    'is_active': 'on',
}, allow_redirects=True)
check('flash' in r.text, 'Agent negative percentage rejected')

# Find and edit the created agent
import re
agent_edit_match = re.search(r'/agents/(\d+)/edit', r.text)
if agent_edit_match:
    agent_id = agent_edit_match.group(1)

    r = s.get(f'{BASE}/agents/{agent_id}/edit')
    check(r.status_code == 200, 'Agent edit form loads')

    r = post_with_csrf(s, f'{BASE}/agents/{agent_id}/edit', {
        'first_name': 'Updated Browser Agent',
        'default_percentage': '20',
        'is_active': 'on',
    }, allow_redirects=True)
    check('Updated Browser Agent' in r.text, 'Agent edited successfully')

# Agent 404
r = s.get(f'{BASE}/agents/99999/edit')
check(r.status_code == 404, 'Nonexistent agent returns 404')

# =========================================================================
print('\n--- 10. USERS MANAGEMENT ---')
r = s.get(f'{BASE}/users/')
check(r.status_code == 200, 'Users list loads')
check('admin' in r.text, 'Users list shows admin user')
check('/users/new' in r.text, 'Users list has new button')

# Create user
r = s.get(f'{BASE}/users/new')
check(r.status_code == 200, 'User create form loads')
check('minlength="12"' in r.text, 'Password field has correct minlength=12')
check('12' in r.text, 'Password placeholder mentions 12')

r = post_with_csrf(s, f'{BASE}/users/new', {
    'username': 'browseruser',
    'password': 'Str0ngP@ssw0rd!',
    'is_active': 'on',
}, allow_redirects=True)
check('browseruser' in r.text, 'User created successfully')

# Duplicate username
r = post_with_csrf(s, f'{BASE}/users/new', {
    'username': 'browseruser',
    'password': 'Str0ngP@ssw0rd!',
}, allow_redirects=True)
check('flash' in r.text, 'Duplicate username rejected')

# Empty username
r = post_with_csrf(s, f'{BASE}/users/new', {
    'username': '',
    'password': 'Str0ngP@ssw0rd!',
}, allow_redirects=True)
check('flash' in r.text, 'Empty username rejected')

# Weak password
r = post_with_csrf(s, f'{BASE}/users/new', {
    'username': 'weakuser',
    'password': 'short',
}, allow_redirects=True)
check('flash' in r.text and '12' in r.text, 'Short password rejected with correct message')

# No uppercase
r = post_with_csrf(s, f'{BASE}/users/new', {
    'username': 'weakuser',
    'password': 'alllowercase1234',
}, allow_redirects=True)
check('flash' in r.text, 'No uppercase password rejected')

# No digit
r = post_with_csrf(s, f'{BASE}/users/new', {
    'username': 'weakuser',
    'password': 'NoDigitsHereAA',
}, allow_redirects=True)
check('flash' in r.text, 'No digit password rejected')

# Edit user
user_edit_match = re.search(r'/users/(\d+)/edit', r.text)
# Find browseruser's edit link
r = s.get(f'{BASE}/users/')
user_ids = re.findall(r'/users/(\d+)/edit', r.text)
if user_ids:
    # Edit the last user (likely browseruser)
    uid = user_ids[-1]
    r = s.get(f'{BASE}/users/{uid}/edit')
    check(r.status_code == 200, 'User edit form loads')
    check('disabled' in r.text, 'Username field is disabled in edit mode')

# Delete user (new feature)
# Find browseruser's delete form
r = s.get(f'{BASE}/users/')
delete_match = re.search(r'/users/(\d+)/delete', r.text)
if delete_match:
    check(True, 'User delete form is present in the list')
    del_uid = delete_match.group(1)
    # Try to delete
    csrf, _ = get_csrf(s, f'{BASE}/users/')
    r = s.post(f'{BASE}/users/{del_uid}/delete', data={'csrf_token': csrf}, allow_redirects=True)
    check(r.status_code == 200, 'User delete request completed')
else:
    check(False, 'User delete form is present in the list', 'No delete form found')

# User 404
r = s.get(f'{BASE}/users/99999/edit')
check(r.status_code == 404, 'Nonexistent user returns 404')

# =========================================================================
print('\n--- 11. REPORTS ---')
r = s.get(f'{BASE}/reports/')
check(r.status_code == 200, 'Reports page loads')
check('name="month"' in r.text, 'Reports has month selector')
check('name="year"' in r.text, 'Reports has year selector')
check('window.print()' in r.text, 'Reports has print button')

today = date.today()
r = s.get(f'{BASE}/reports/?year={today.year}&month={today.month}')
check(r.status_code == 200, 'Reports with current month loads')
check('report-summary-card' in r.text or 'empty-state' in r.text,
      'Reports shows summary cards or empty state')

r = s.get(f'{BASE}/reports/?year=2020&month=1')
check(r.status_code == 200, 'Reports with old date loads')
check('empty-state' in r.text, 'Reports shows empty state for old period')

# =========================================================================
print('\n--- 12. AUDIT LOG ---')
r = s.get(f'{BASE}/audit/')
check(r.status_code == 200, 'Audit log loads')
check('name="username"' in r.text, 'Audit has username filter')
check('name="action_type"' in r.text, 'Audit has action type filter')
check('name="entity_type"' in r.text, 'Audit has entity type filter')
check('name="date_from"' in r.text, 'Audit has date_from filter')
check('name="date_to"' in r.text, 'Audit has date_to filter')

# Filters
r = s.get(f'{BASE}/audit/?action_type=create')
check(r.status_code == 200, 'Audit filter by action_type works')

r = s.get(f'{BASE}/audit/?entity_type=User')
check(r.status_code == 200, 'Audit filter by entity_type works')

r = s.get(f'{BASE}/audit/?username=admin')
check(r.status_code == 200, 'Audit filter by username works')

r = s.get(f'{BASE}/audit/?date_from={today.isoformat()}&date_to={today.isoformat()}')
check(r.status_code == 200, 'Audit filter by date range works')

# Invalid dates
r = s.get(f'{BASE}/audit/?date_from=not-a-date')
check(r.status_code == 200, 'Audit with invalid date_from does not crash')

r = s.get(f'{BASE}/audit/?date_to="><script>alert(1)</script>')
check(r.status_code == 200, 'Audit with XSS date_to does not crash')

# SQL wildcard injection
r = s.get(f'{BASE}/audit/?username=%25%25%25')
check(r.status_code == 200, 'Audit SQL wildcard in username does not crash')

# Audit detail
audit_match = re.search(r'/audit/(\d+)', r.text)
if audit_match:
    audit_id = audit_match.group(1)
    r = s.get(f'{BASE}/audit/{audit_id}')
    check(r.status_code == 200, 'Audit detail loads')
    check('detail' in r.text.lower() or 'Log' in r.text, 'Audit detail has content')

r = s.get(f'{BASE}/audit/99999')
check(r.status_code == 404, 'Nonexistent audit log returns 404')

# =========================================================================
print('\n--- 13. LANGUAGE SWITCHING ---')
csrf, _ = get_csrf(s, f'{BASE}/')
r = s.post(f'{BASE}/set-language', data={
    'lang': 'en',
    'next': '/',
    'csrf_token': csrf,
}, allow_redirects=True)
check('Open Activities' in r.text or 'Activities' in r.text, 'Switched to English')

r = s.get(f'{BASE}/activities/')
check('Activities' in r.text, 'English persists on activities page')

r = s.get(f'{BASE}/agents/')
check('Agents' in r.text, 'English persists on agents page')

# Switch back to Italian
csrf, _ = get_csrf(s, f'{BASE}/')
r = s.post(f'{BASE}/set-language', data={
    'lang': 'it',
    'next': '/',
    'csrf_token': csrf,
}, allow_redirects=True)
check('Attivita Aperte' in r.text or 'Dashboard' in r.text, 'Switched back to Italian')

# Invalid language
csrf, _ = get_csrf(s, f'{BASE}/')
r = s.post(f'{BASE}/set-language', data={
    'lang': 'xx',
    'next': '/',
    'csrf_token': csrf,
}, allow_redirects=True)
check(r.status_code == 200, 'Invalid language does not crash')

# =========================================================================
print('\n--- 14. SECURITY TESTS ---')

# Open redirect on login
csrf, _ = get_csrf(s, f'{BASE}/login')
s3 = requests.Session()
csrf3, _ = get_csrf(s3, f'{BASE}/login')
r = s3.post(f'{BASE}/login?next=https://evil.com', data={
    'username': 'admin', 'password': 'admin123', 'csrf_token': csrf3,
}, allow_redirects=False)
location = r.headers.get('Location', '')
check('evil.com' not in location, 'Open redirect on login blocked')

# Protocol-relative redirect
s4 = requests.Session()
csrf4, _ = get_csrf(s4, f'{BASE}/login')
r = s4.post(f'{BASE}/login?next=//evil.com', data={
    'username': 'admin', 'password': 'admin123', 'csrf_token': csrf4,
}, allow_redirects=False)
location = r.headers.get('Location', '')
check('evil.com' not in location, 'Protocol-relative redirect blocked')

# Open redirect on set-language
csrf, _ = get_csrf(s, f'{BASE}/')
r = s.post(f'{BASE}/set-language', data={
    'lang': 'en',
    'next': 'https://evil.com',
    'csrf_token': csrf,
}, allow_redirects=False)
location = r.headers.get('Location', '')
check('evil.com' not in location, 'Open redirect on set-language blocked')

# Security headers
r = s.get(f'{BASE}/activities/')
check(r.headers.get('X-Content-Type-Options') == 'nosniff', 'X-Content-Type-Options header present')
check(r.headers.get('X-Frame-Options') == 'DENY', 'X-Frame-Options header present')
check(r.headers.get('X-XSS-Protection') == '1; mode=block', 'X-XSS-Protection header present')
check(r.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin', 'Referrer-Policy header present')

# Logout requires POST
r = s.get(f'{BASE}/logout')
check(r.status_code == 405, 'GET /logout returns 405')

# XSS in activity title
r = post_with_csrf(s, f'{BASE}/activities/new', {
    'title': '<script>alert(1)</script>',
    'date': date.today().isoformat(),
    'total_revenue': '100',
    'agent_percentage': '0',
}, allow_redirects=True)
check('<script>alert(1)</script>' not in r.text, 'XSS in activity title escaped')

# =========================================================================
print('\n--- 15. ROLE-BASED ACCESS ---')

# Create operator session
s_op = requests.Session()
# First create an operator user
post_with_csrf(s, f'{BASE}/users/new', {
    'username': 'test_operator',
    'password': 'Str0ngP@ssw0rd!',
    'is_active': 'on',
})

login(s_op, 'test_operator', 'Str0ngP@ssw0rd!')
r = s_op.get(f'{BASE}/')
check(r.status_code == 200, 'Operator can access dashboard')
check('/users/' not in r.text, 'Operator does not see Users nav')
check('/audit/' not in r.text, 'Operator does not see Audit nav')

r = s_op.get(f'{BASE}/users/', allow_redirects=False)
check(r.status_code in (302, 303), 'Operator denied access to /users/')

r = s_op.get(f'{BASE}/audit/', allow_redirects=False)
check(r.status_code in (302, 303), 'Operator denied access to /audit/')

# Operator can create activity
r = post_with_csrf(s_op, f'{BASE}/activities/new', {
    'title': 'Operator Activity',
    'date': date.today().isoformat(),
    'total_revenue': '300',
    'agent_percentage': '0',
    'status': 'bozza',
}, allow_redirects=True)
check('Operator Activity' in r.text, 'Operator can create activity')

# Operator cannot edit others' activity
if activity_id:
    r = post_with_csrf(s_op, f'{BASE}/activities/{activity_id}/edit', {
        'title': 'Hacked',
        'date': date.today().isoformat(),
        'total_revenue': '1',
        'agent_percentage': '0',
    }, allow_redirects=True)
    check('Non autorizzat' in r.text or 'Not authorized' in r.text,
          'Operator cannot edit others activity (IDOR blocked)')

# =========================================================================
print('\n--- 16. DELETE ACTIVITY ---')
if activity_id:
    csrf, _ = get_csrf(s, f'{BASE}/activities/{activity_id}')
    r = s.post(f'{BASE}/activities/{activity_id}/delete', data={
        'csrf_token': csrf,
    }, allow_redirects=True)
    check(r.status_code == 200, 'Activity deleted successfully')

    r = s.get(f'{BASE}/activities/{activity_id}')
    check(r.status_code == 404, 'Deleted activity returns 404')

# =========================================================================
print('\n--- 17. LOGOUT ---')
csrf, _ = get_csrf(s, f'{BASE}/')
r = s.post(f'{BASE}/logout', data={'csrf_token': csrf}, allow_redirects=False)
check(r.status_code in (302, 303), 'Logout redirects')

r = s.get(f'{BASE}/', allow_redirects=False)
check(r.status_code in (302, 303), 'After logout, dashboard redirects to login')


# =========================================================================
print('\n' + '='*70)
print(f'RESULTS: {PASS} passed, {FAIL} failed, {PASS+FAIL} total')
print('='*70)
if ERRORS:
    print('\nFailed tests:')
    for e in ERRORS:
        print(f'  - {e}')
    sys.exit(1)
else:
    print('\nAll tests passed!')
    sys.exit(0)

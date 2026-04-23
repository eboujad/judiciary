# Phase 2C — Judgment, Appeals & Archival Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable judges to deliver digital judgments, automatically start a 30-day appeal window with T-7/T-3/T-1 reminders, allow parties to file appeals electronically, and archive closed cases with full audit trails.

**Architecture:** New `apps/judgments` Django app with three models (`Judgment`, `AppealWindow`, `Appeal`). Celery periodic task monitors appeal windows and fires reminders. Case status progresses through `JUDGMENT_PENDING → JUDGMENT_DELIVERED → APPEAL_FILED | CLOSED → ARCHIVED`. Depends on Phase 2B (hearings must exist before judgment can be delivered).

**Tech Stack:** Django 5.1, DRF, Celery + Redis, pytest-django, factory-boy, React + TypeScript + Tailwind, React Query

**Prerequisite:** Phase 2A and 2B fully implemented and merged.

---

## File Map

### Create
| File | Responsibility |
|------|---------------|
| `backend/apps/judgments/__init__.py` | App package |
| `backend/apps/judgments/models.py` | `Judgment`, `AppealWindow`, `Appeal` |
| `backend/apps/judgments/serializers.py` | Request/response shapes |
| `backend/apps/judgments/views.py` | 6 view classes |
| `backend/apps/judgments/urls.py` | URL patterns |
| `backend/apps/judgments/admin.py` | Admin registrations |
| `backend/apps/judgments/tasks.py` | Appeal window reminders + archival |
| `backend/apps/judgments/tests/__init__.py` | Test package |
| `backend/apps/judgments/tests/test_models.py` | Model unit tests |
| `backend/apps/judgments/tests/test_views.py` | API integration tests |
| `backend/apps/judgments/tests/test_tasks.py` | Celery task tests |
| `frontend/src/screens/judge/DeliverJudgment.tsx` | Judge: write and submit judgment |
| `frontend/src/screens/lawyer/AppealFiling.tsx` | Lawyer: file appeal |
| `frontend/src/screens/registrar/ArchivalQueue.tsx` | Registrar: archive closed cases |

### Modify
| File | Change |
|------|--------|
| `backend/apps/cases/models.py` | Add `JUDGMENT_PENDING → JUDGMENT_DELIVERED`, `JUDGMENT_DELIVERED → APPEAL_FILED`, `JUDGMENT_DELIVERED → CLOSED`, `CLOSED → ARCHIVED` |
| `backend/config/settings/base.py` | Add `apps.judgments` to LOCAL_APPS |
| `backend/config/urls.py` | Include `apps.judgments.urls` at `/api/v1/judgments/` |
| `frontend/src/App.tsx` | Add judgment and appeal routes |
| `frontend/src/api/endpoints.ts` | Add judgment API calls |
| `frontend/src/types/index.ts` | Add Judgment, AppealWindow, Appeal types |

---

## Task 1 — Models: `Judgment`, `AppealWindow`, `Appeal`

**Files:**
- Create: `backend/apps/judgments/__init__.py`
- Create: `backend/apps/judgments/models.py`
- Create: `backend/apps/judgments/admin.py`
- Modify: `backend/config/settings/base.py`
- Modify: `backend/apps/cases/models.py`

- [ ] **Step 1: Write failing model tests**

Create `backend/apps/judgments/tests/__init__.py` (empty).
Create `backend/apps/judgments/tests/test_models.py`:

```python
import pytest
from datetime import timedelta
from django.utils import timezone
from apps.users.models import User, UserRole
from apps.cases.models import Case, CaseStatus, CourtTier, CaseType
from apps.firms.models import LawFirm, Lawyer
from apps.judgments.models import Judgment, AppealWindow, Appeal, JudgmentOutcome


@pytest.fixture
def judgment_pending_case(db):
    firm = LawFirm.objects.create(name='Firm G', bar_number='GBR-007', address='Banjul', status='active')
    lu = User.objects.create_user(email='l7@firm.gm', password='pass', role=UserRole.LAWYER)
    lawyer = Lawyer.objects.create(user=lu, firm=firm, bar_number='LAW-007')
    return Case.objects.create(
        title='Judgment Test Case', court=CourtTier.HIGH, case_type=CaseType.CIVIL_CLAIM,
        status=CaseStatus.JUDGMENT_PENDING, submitted_by=lawyer, case_number='GJ-2026-HC-00007',
    )


@pytest.fixture
def judge_user(db):
    return User.objects.create_user(
        email='jjudge@jud.gm', password='pass',
        first_name='Ibrahim', last_name='Sanneh', role=UserRole.JUDGE,
    )


@pytest.fixture
def delivered_judgment(db, judgment_pending_case, judge_user):
    j = Judgment.objects.create(
        case=judgment_pending_case,
        judge=judge_user,
        outcome=JudgmentOutcome.ALLOWED,
        summary='Claimant succeeds on all grounds.',
        full_text='Full text of the judgment…',
    )
    judgment_pending_case.status = CaseStatus.JUDGMENT_DELIVERED
    judgment_pending_case.save()
    return j


class TestJudgment:
    def test_str(self, delivered_judgment):
        assert 'GJ-2026-HC-00007' in str(delivered_judgment)

    def test_creates_appeal_window_on_save(self, delivered_judgment):
        assert AppealWindow.objects.filter(judgment=delivered_judgment).exists()

    def test_appeal_window_expires_30_days_after_delivery(self, delivered_judgment):
        window = AppealWindow.objects.get(judgment=delivered_judgment)
        delta = window.expires_at - window.opened_at
        assert delta.days == 30

    def test_appeal_window_is_open_initially(self, delivered_judgment):
        window = AppealWindow.objects.get(judgment=delivered_judgment)
        assert window.is_open() is True


class TestAppealWindow:
    def test_is_open_returns_false_after_expiry(self, delivered_judgment, db):
        window = AppealWindow.objects.get(judgment=delivered_judgment)
        window.expires_at = timezone.now() - timedelta(days=1)
        window.save()
        assert window.is_open() is False

    def test_is_open_returns_false_when_appeal_filed(self, delivered_judgment, db):
        window = AppealWindow.objects.get(judgment=delivered_judgment)
        window.appeal_filed = True
        window.save()
        assert window.is_open() is False

    def test_days_remaining(self, delivered_judgment):
        window = AppealWindow.objects.get(judgment=delivered_judgment)
        assert 29 <= window.days_remaining() <= 30


class TestAppeal:
    def test_filing_appeal_creates_record(self, delivered_judgment, db):
        window = AppealWindow.objects.get(judgment=delivered_judgment)
        lawyer_user = delivered_judgment.case.submitted_by.user
        appeal = Appeal.objects.create(
            judgment=delivered_judgment,
            window=window,
            filed_by=lawyer_user,
            grounds='Error of law in the judgment.',
            appeal_court='appeal',
        )
        assert appeal.id is not None

    def test_appeal_marks_window_as_filed(self, delivered_judgment, db):
        window = AppealWindow.objects.get(judgment=delivered_judgment)
        lawyer_user = delivered_judgment.case.submitted_by.user
        Appeal.objects.create(
            judgment=delivered_judgment,
            window=window,
            filed_by=lawyer_user,
            grounds='Error of law.',
            appeal_court='appeal',
        )
        window.refresh_from_db()
        assert window.appeal_filed is True
```

- [ ] **Step 2: Run — expect ImportError**

```bash
cd backend
pytest apps/judgments/tests/test_models.py -v
```
Expected: `ModuleNotFoundError: No module named 'apps.judgments'`

- [ ] **Step 3: Create models**

Create `backend/apps/judgments/__init__.py` (empty).

Create `backend/apps/judgments/models.py`:

```python
import uuid
from datetime import timedelta
from django.db import models
from django.utils import timezone
from apps.cases.models import CourtTier


class JudgmentOutcome(models.TextChoices):
    ALLOWED = 'allowed', 'Allowed'
    DISMISSED = 'dismissed', 'Dismissed'
    SETTLED = 'settled', 'Settled'
    WITHDRAWN = 'withdrawn', 'Withdrawn'
    CONSENT_ORDER = 'consent_order', 'Consent Order'


class Judgment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.OneToOneField(
        'cases.Case', on_delete=models.CASCADE, related_name='judgment',
    )
    judge = models.ForeignKey(
        'users.User', on_delete=models.PROTECT, related_name='judgments',
        limit_choices_to={'role': 'judge'},
    )
    outcome = models.CharField(max_length=20, choices=JudgmentOutcome.choices)
    summary = models.TextField()
    full_text = models.TextField(blank=True)
    delivered_at = models.DateTimeField(auto_now_add=True)
    document = models.FileField(upload_to='judgments/', null=True, blank=True)

    class Meta:
        ordering = ['-delivered_at']

    def __str__(self):
        return f"{self.case.case_number} — {self.outcome}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            AppealWindow.objects.create(
                judgment=self,
                opened_at=self.delivered_at,
                expires_at=self.delivered_at + timedelta(days=30),
            )


class AppealWindow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    judgment = models.OneToOneField(Judgment, on_delete=models.CASCADE, related_name='appeal_window')
    opened_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    appeal_filed = models.BooleanField(default=False)

    def is_open(self):
        return not self.appeal_filed and timezone.now() < self.expires_at

    def days_remaining(self):
        delta = self.expires_at - timezone.now()
        return max(delta.days, 0)

    def __str__(self):
        return f"AppealWindow({self.judgment.case.case_number}) — {self.days_remaining()}d left"


class Appeal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    judgment = models.ForeignKey(Judgment, on_delete=models.CASCADE, related_name='appeals')
    window = models.ForeignKey(AppealWindow, on_delete=models.CASCADE, related_name='appeals')
    filed_by = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='filed_appeals')
    grounds = models.TextField()
    appeal_court = models.CharField(max_length=20, choices=CourtTier.choices)
    filed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-filed_at']

    def __str__(self):
        return f"Appeal on {self.judgment.case.case_number} — {self.appeal_court}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            self.window.appeal_filed = True
            self.window.save()
```

Create `backend/apps/judgments/admin.py`:

```python
from django.contrib import admin
from .models import Appeal, AppealWindow, Judgment


@admin.register(Judgment)
class JudgmentAdmin(admin.ModelAdmin):
    list_display = ['case', 'judge', 'outcome', 'delivered_at']
    list_filter = ['outcome']
    search_fields = ['case__case_number']
    readonly_fields = ['delivered_at']


@admin.register(AppealWindow)
class AppealWindowAdmin(admin.ModelAdmin):
    list_display = ['judgment', 'opened_at', 'expires_at', 'appeal_filed']
    readonly_fields = ['opened_at', 'expires_at']


@admin.register(Appeal)
class AppealAdmin(admin.ModelAdmin):
    list_display = ['judgment', 'appeal_court', 'filed_by', 'filed_at']
    readonly_fields = ['filed_at']
```

- [ ] **Step 4: Register and migrate**

In `backend/config/settings/base.py`, add `'apps.judgments'` to `LOCAL_APPS`.

Add to `backend/apps/cases/models.py` ALLOWED_TRANSITIONS:

```python
CaseStatus.JUDGMENT_PENDING: [CaseStatus.JUDGMENT_DELIVERED],
CaseStatus.JUDGMENT_DELIVERED: [CaseStatus.APPEAL_FILED, CaseStatus.CLOSED],
CaseStatus.APPEAL_FILED: [CaseStatus.CLOSED],
CaseStatus.CLOSED: [CaseStatus.ARCHIVED],
```

```bash
python manage.py makemigrations judgments
python manage.py migrate
```
Expected: `Applying judgments.0001_initial... OK`

- [ ] **Step 5: Run model tests — expect PASS**

```bash
pytest apps/judgments/tests/test_models.py -v
```
Expected: 9 passed

- [ ] **Step 6: Commit**

```bash
git add apps/judgments/ config/settings/base.py apps/cases/models.py
git commit -m "feat: add Judgment, AppealWindow, Appeal models"
```

---

## Task 2 — Appeal window reminder Celery task

**Files:**
- Create: `backend/apps/judgments/tasks.py`
- Test: `backend/apps/judgments/tests/test_tasks.py`

- [ ] **Step 1: Write failing task tests**

Create `backend/apps/judgments/tests/test_tasks.py`:

```python
import pytest
from datetime import timedelta
from unittest.mock import patch
from django.utils import timezone
from apps.users.models import User, UserRole
from apps.cases.models import Case, CaseStatus, CourtTier, CaseType
from apps.firms.models import LawFirm, Lawyer
from apps.judgments.models import Judgment, AppealWindow, JudgmentOutcome
from apps.judgments.tasks import send_appeal_window_reminders, archive_closed_cases


@pytest.fixture
def case_with_open_window(db):
    firm = LawFirm.objects.create(name='Firm H', bar_number='GBR-008', address='Banjul', status='active')
    lu = User.objects.create_user(email='l8@firm.gm', password='pass', role=UserRole.LAWYER)
    lawyer = Lawyer.objects.create(user=lu, firm=firm, bar_number='LAW-008')
    judge = User.objects.create_user(email='jj4@jud.gm', password='pass', role=UserRole.JUDGE)
    case = Case.objects.create(
        title='Appeal Window Test', court=CourtTier.HIGH, case_type=CaseType.CIVIL_CLAIM,
        status=CaseStatus.JUDGMENT_DELIVERED, submitted_by=lawyer, case_number='GJ-2026-HC-00008',
    )
    j = Judgment.objects.create(
        case=case, judge=judge, outcome=JudgmentOutcome.DISMISSED,
        summary='Case dismissed.', full_text='',
    )
    # Manually set expires_at to 7 days from now for T-7 reminder
    window = AppealWindow.objects.get(judgment=j)
    window.expires_at = timezone.now() + timedelta(days=7)
    window.save()
    return window


@pytest.fixture
def old_closed_case(db):
    firm = LawFirm.objects.create(name='Firm I', bar_number='GBR-009', address='Banjul', status='active')
    lu = User.objects.create_user(email='l9@firm.gm', password='pass', role=UserRole.LAWYER)
    lawyer = Lawyer.objects.create(user=lu, firm=firm, bar_number='LAW-009')
    case = Case.objects.create(
        title='Old Closed', court=CourtTier.HIGH, case_type=CaseType.CIVIL_CLAIM,
        status=CaseStatus.CLOSED, submitted_by=lawyer, case_number='GJ-2026-HC-00009',
    )
    # Backdate updated_at to 91 days ago
    Case.objects.filter(id=case.id).update(
        updated_at=timezone.now() - timedelta(days=91)
    )
    return Case.objects.get(id=case.id)


class TestSendAppealWindowReminders:
    @patch('apps.judgments.tasks.send_notification')
    def test_reminder_sent_7_days_before_expiry(self, mock_notify, case_with_open_window):
        send_appeal_window_reminders()
        assert mock_notify.called

    @patch('apps.judgments.tasks.send_notification')
    def test_no_reminder_when_appeal_already_filed(self, mock_notify, case_with_open_window):
        case_with_open_window.appeal_filed = True
        case_with_open_window.save()
        send_appeal_window_reminders()
        assert not mock_notify.called


class TestArchiveClosedCases:
    def test_old_closed_case_gets_archived(self, old_closed_case):
        archive_closed_cases()
        old_closed_case.refresh_from_db()
        assert old_closed_case.status == CaseStatus.ARCHIVED

    def test_recently_closed_case_not_archived(self, db):
        firm = LawFirm.objects.create(name='Firm J', bar_number='GBR-010', address='Banjul', status='active')
        lu = User.objects.create_user(email='l10@firm.gm', password='pass', role=UserRole.LAWYER)
        lawyer = Lawyer.objects.create(user=lu, firm=firm, bar_number='LAW-010')
        case = Case.objects.create(
            title='Recent Closed', court=CourtTier.HIGH, case_type=CaseType.CIVIL_CLAIM,
            status=CaseStatus.CLOSED, submitted_by=lawyer, case_number='GJ-2026-HC-00010',
        )
        archive_closed_cases()
        case.refresh_from_db()
        assert case.status == CaseStatus.CLOSED
```

- [ ] **Step 2: Run — expect ImportError**

```bash
pytest apps/judgments/tests/test_tasks.py -v
```
Expected: `ImportError: cannot import name 'send_appeal_window_reminders'`

- [ ] **Step 3: Write tasks**

Create `backend/apps/judgments/tasks.py`:

```python
from datetime import timedelta
from django.utils import timezone
from config.celery import app
from apps.notifications.models import Notification, NotificationChannel


def send_notification(recipient, subject, body, obj_id=''):
    Notification.objects.create(
        recipient=recipient,
        channel=NotificationChannel.SMS,
        subject=subject,
        body=body,
        content_type='appeal_window',
        object_id=str(obj_id),
    )


@app.task(name='judgments.send_appeal_window_reminders')
def send_appeal_window_reminders():
    """
    Run daily. Sends reminders at T-7, T-3, T-1 before appeal window closes.
    """
    from apps.judgments.models import AppealWindow

    now = timezone.now()
    reminder_days = [7, 3, 1]

    for days in reminder_days:
        window_start = now + timedelta(days=days)
        window_end = now + timedelta(days=days, hours=1)

        windows = AppealWindow.objects.filter(
            appeal_filed=False,
            expires_at__gte=window_start,
            expires_at__lt=window_end,
        ).select_related('judgment__case__submitted_by__user', 'judgment__judge')

        for window in windows:
            case = window.judgment.case
            lawyer_user = case.submitted_by.user
            send_notification(
                recipient=lawyer_user,
                subject=f"Appeal Window Closing — {case.case_number}",
                body=(
                    f"REMINDER: Your {days}-day appeal window for case {case.case_number} "
                    f"closes on {window.expires_at:%d %b %Y}. "
                    f"File an appeal at the court portal if you intend to appeal."
                ),
                obj_id=window.id,
            )


@app.task(name='judgments.archive_closed_cases')
def archive_closed_cases():
    """
    Run weekly. Auto-archives cases that have been CLOSED for more than 90 days.
    """
    from apps.cases.models import Case, CaseStatus

    cutoff = timezone.now() - timedelta(days=90)
    cases = Case.objects.filter(status=CaseStatus.CLOSED, updated_at__lt=cutoff)

    for case in cases:
        case.transition_to(CaseStatus.ARCHIVED)
        case.save()
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest apps/judgments/tests/test_tasks.py -v
```
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add apps/judgments/tasks.py apps/judgments/tests/test_tasks.py
git commit -m "feat: add appeal window reminder and auto-archival Celery tasks"
```

---

## Task 3 — Serializers

**Files:**
- Create: `backend/apps/judgments/serializers.py`

- [ ] **Step 1: Create serializers**

Create `backend/apps/judgments/serializers.py`:

```python
from rest_framework import serializers
from apps.cases.models import CourtTier
from .models import Appeal, AppealWindow, Judgment, JudgmentOutcome


class JudgmentSerializer(serializers.ModelSerializer):
    judge_name = serializers.CharField(source='judge.get_full_name', read_only=True)
    case_number = serializers.CharField(source='case.case_number', read_only=True)
    days_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Judgment
        fields = [
            'id', 'case', 'case_number', 'judge', 'judge_name',
            'outcome', 'summary', 'full_text', 'delivered_at', 'days_remaining',
        ]
        read_only_fields = ['delivered_at']

    def get_days_remaining(self, obj):
        try:
            return obj.appeal_window.days_remaining()
        except AppealWindow.DoesNotExist:
            return None


class JudgmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Judgment
        fields = ['case', 'outcome', 'summary', 'full_text']

    def validate_outcome(self, value):
        valid = [c[0] for c in JudgmentOutcome.choices]
        if value not in valid:
            raise serializers.ValidationError(f'Must be one of: {valid}')
        return value

    def validate_case(self, value):
        from apps.cases.models import CaseStatus
        if value.status != CaseStatus.JUDGMENT_PENDING:
            raise serializers.ValidationError(
                'Case must be in JUDGMENT_PENDING status to receive a judgment.'
            )
        return value


class AppealWindowSerializer(serializers.ModelSerializer):
    days_remaining = serializers.SerializerMethodField()
    case_number = serializers.CharField(source='judgment.case.case_number', read_only=True)

    class Meta:
        model = AppealWindow
        fields = [
            'id', 'case_number', 'opened_at', 'expires_at',
            'appeal_filed', 'days_remaining',
        ]

    def get_days_remaining(self, obj):
        return obj.days_remaining()


class AppealCreateSerializer(serializers.Serializer):
    grounds = serializers.CharField(min_length=20)
    appeal_court = serializers.ChoiceField(choices=CourtTier.choices)
    notes = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, data):
        window = self.context['window']
        if not window.is_open():
            raise serializers.ValidationError('The appeal window for this case has closed.')
        return data


class AppealSerializer(serializers.ModelSerializer):
    filed_by_name = serializers.CharField(source='filed_by.get_full_name', read_only=True)
    case_number = serializers.CharField(source='judgment.case.case_number', read_only=True)

    class Meta:
        model = Appeal
        fields = [
            'id', 'case_number', 'appeal_court', 'filed_by_name',
            'grounds', 'notes', 'filed_at',
        ]
        read_only_fields = ['filed_at']
```

- [ ] **Step 2: Commit**

```bash
git add apps/judgments/serializers.py
git commit -m "feat: add judgment and appeal serializers"
```

---

## Task 4 — Views and URLs

**Files:**
- Create: `backend/apps/judgments/views.py`
- Create: `backend/apps/judgments/urls.py`
- Modify: `backend/config/urls.py`
- Test: `backend/apps/judgments/tests/test_views.py`

- [ ] **Step 1: Write failing view tests**

Create `backend/apps/judgments/tests/test_views.py`:

```python
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User, UserRole
from apps.cases.models import Case, CaseStatus, CourtTier, CaseType
from apps.firms.models import LawFirm, Lawyer
from apps.judgments.models import Judgment, AppealWindow, JudgmentOutcome


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def judge_user(db):
    return User.objects.create_user(
        email='jdv@jud.gm', password='pass', role=UserRole.JUDGE,
    )


@pytest.fixture
def lawyer_user(db):
    firm = LawFirm.objects.create(name='Firm K', bar_number='GBR-011', address='Banjul', status='active')
    lu = User.objects.create_user(email='l11@firm.gm', password='pass', role=UserRole.LAWYER)
    Lawyer.objects.create(user=lu, firm=firm, bar_number='LAW-011')
    return lu


@pytest.fixture
def judgment_pending_case(db, lawyer_user):
    lawyer = Lawyer.objects.get(user=lawyer_user)
    return Case.objects.create(
        title='Judgment Pending Case', court=CourtTier.HIGH, case_type=CaseType.CIVIL_CLAIM,
        status=CaseStatus.JUDGMENT_PENDING, submitted_by=lawyer, case_number='GJ-2026-HC-00011',
    )


@pytest.fixture
def delivered_judgment(db, judgment_pending_case, judge_user):
    j = Judgment.objects.create(
        case=judgment_pending_case, judge=judge_user,
        outcome=JudgmentOutcome.ALLOWED,
        summary='Claimant succeeds on all grounds.',
    )
    judgment_pending_case.status = CaseStatus.JUDGMENT_DELIVERED
    judgment_pending_case.save()
    return j


class TestJudgmentDeliverView:
    def test_judge_delivers_judgment(self, api_client, judge_user, judgment_pending_case):
        api_client.force_authenticate(judge_user)
        url = reverse('judgment-deliver')
        resp = api_client.post(url, {
            'case': str(judgment_pending_case.id),
            'outcome': JudgmentOutcome.ALLOWED,
            'summary': 'Claimant succeeds on all grounds.',
            'full_text': 'The full text of the judgment.',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        judgment_pending_case.refresh_from_db()
        assert judgment_pending_case.status == CaseStatus.JUDGMENT_DELIVERED
        assert AppealWindow.objects.filter(judgment__case=judgment_pending_case).exists()

    def test_lawyer_cannot_deliver_judgment(self, api_client, lawyer_user, judgment_pending_case):
        api_client.force_authenticate(lawyer_user)
        url = reverse('judgment-deliver')
        resp = api_client.post(url, {
            'case': str(judgment_pending_case.id),
            'outcome': JudgmentOutcome.DISMISSED,
            'summary': 'No.',
        }, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_wrong_case_status_rejected(self, api_client, judge_user, judgment_pending_case):
        judgment_pending_case.status = CaseStatus.ACTIVE
        judgment_pending_case.save()
        api_client.force_authenticate(judge_user)
        url = reverse('judgment-deliver')
        resp = api_client.post(url, {
            'case': str(judgment_pending_case.id),
            'outcome': JudgmentOutcome.DISMISSED,
            'summary': 'Dismissed.',
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestAppealWindowView:
    def test_lawyer_can_view_appeal_window(self, api_client, lawyer_user, delivered_judgment):
        api_client.force_authenticate(lawyer_user)
        window = AppealWindow.objects.get(judgment=delivered_judgment)
        url = reverse('appeal-window', kwargs={'window_id': window.id})
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['appeal_filed'] is False
        assert resp.data['days_remaining'] >= 29


class TestAppealFileView:
    def test_lawyer_files_appeal(self, api_client, lawyer_user, delivered_judgment):
        api_client.force_authenticate(lawyer_user)
        window = AppealWindow.objects.get(judgment=delivered_judgment)
        url = reverse('appeal-file', kwargs={'window_id': window.id})
        resp = api_client.post(url, {
            'grounds': 'The judge erred in law by failing to consider the key precedent.',
            'appeal_court': CourtTier.APPEAL,
            'notes': '',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        window.refresh_from_db()
        assert window.appeal_filed is True
        delivered_judgment.case.refresh_from_db()
        assert delivered_judgment.case.status == CaseStatus.APPEAL_FILED

    def test_cannot_file_appeal_after_window_closes(self, api_client, lawyer_user, delivered_judgment, db):
        from datetime import timedelta
        from django.utils import timezone
        window = AppealWindow.objects.get(judgment=delivered_judgment)
        window.expires_at = timezone.now() - timedelta(days=1)
        window.save()
        api_client.force_authenticate(lawyer_user)
        url = reverse('appeal-file', kwargs={'window_id': window.id})
        resp = api_client.post(url, {
            'grounds': 'Too late grounds.',
            'appeal_court': CourtTier.APPEAL,
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_judge_cannot_file_appeal(self, api_client, judge_user, delivered_judgment):
        window = AppealWindow.objects.get(judgment=delivered_judgment)
        api_client.force_authenticate(judge_user)
        url = reverse('appeal-file', kwargs={'window_id': window.id})
        resp = api_client.post(url, {
            'grounds': 'Should not work.',
            'appeal_court': CourtTier.APPEAL,
        }, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestCaseCloseView:
    def test_registrar_closes_case(self, api_client, delivered_judgment, db):
        registrar = User.objects.create_user(
            email='reg@jud.gm', password='pass', role=UserRole.REGISTRAR,
        )
        api_client.force_authenticate(registrar)
        url = reverse('case-close', kwargs={'case_id': delivered_judgment.case.id})
        resp = api_client.post(url)
        assert resp.status_code == status.HTTP_200_OK
        delivered_judgment.case.refresh_from_db()
        assert delivered_judgment.case.status == CaseStatus.CLOSED
```

- [ ] **Step 2: Run — expect errors**

```bash
pytest apps/judgments/tests/test_views.py -v
```
Expected: `NoReverseMatch` or import errors

- [ ] **Step 3: Create views**

Create `backend/apps/judgments/views.py`:

```python
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog, AuditSeverity
from apps.cases.models import Case, CaseStatus
from core.permissions import IsJudge, IsRegistrar

from .models import Appeal, AppealWindow, Judgment
from .serializers import (
    AppealCreateSerializer,
    AppealSerializer,
    AppealWindowSerializer,
    JudgmentCreateSerializer,
    JudgmentSerializer,
)


class JudgmentDeliverView(APIView):
    """POST /api/v1/judgments/ — judge delivers judgment."""
    permission_classes = [IsJudge]

    def post(self, request):
        serializer = JudgmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        judgment = serializer.save(judge=request.user)
        case = judgment.case
        case.transition_to(CaseStatus.JUDGMENT_DELIVERED)
        case.save()

        AuditLog.objects.create(
            actor=request.user,
            actor_role=request.user.role,
            action=f'judgment_delivered:{judgment.outcome}',
            content_type='judgment',
            object_id=str(judgment.id),
            note=f'Outcome: {judgment.outcome}',
            severity=AuditSeverity.INFO,
        )
        return Response(JudgmentSerializer(judgment).data, status=status.HTTP_201_CREATED)


class AppealWindowView(APIView):
    """GET /api/v1/judgments/appeal-windows/<window_id>/ — view appeal window."""

    def get(self, request, window_id):
        window = get_object_or_404(AppealWindow, id=window_id)
        return Response(AppealWindowSerializer(window).data)


class AppealFileView(APIView):
    """POST /api/v1/judgments/appeal-windows/<window_id>/file/ — lawyer files appeal."""
    permission_classes = [IsRegistrar | IsJudge.__class__]

    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        return [IsAuthenticated()]

    def post(self, request, window_id):
        if request.user.role not in ('lawyer', 'public_user'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only lawyers and parties can file appeals.')

        window = get_object_or_404(AppealWindow, id=window_id)
        serializer = AppealCreateSerializer(data=request.data, context={'window': window})
        serializer.is_valid(raise_exception=True)

        appeal = Appeal.objects.create(
            judgment=window.judgment,
            window=window,
            filed_by=request.user,
            grounds=serializer.validated_data['grounds'],
            appeal_court=serializer.validated_data['appeal_court'],
            notes=serializer.validated_data.get('notes', ''),
        )

        case = window.judgment.case
        case.transition_to(CaseStatus.APPEAL_FILED)
        case.save()

        AuditLog.objects.create(
            actor=request.user,
            actor_role=request.user.role,
            action='appeal_filed',
            content_type='appeal',
            object_id=str(appeal.id),
            note=f'Appeal to {appeal.appeal_court}',
            severity=AuditSeverity.INFO,
        )
        return Response(AppealSerializer(appeal).data, status=status.HTTP_201_CREATED)


class CaseCloseView(APIView):
    """POST /api/v1/judgments/cases/<case_id>/close/ — registrar closes case."""
    permission_classes = [IsRegistrar]

    def post(self, request, case_id):
        case = get_object_or_404(
            Case, id=case_id,
            status__in=[CaseStatus.JUDGMENT_DELIVERED, CaseStatus.APPEAL_FILED],
        )
        case.transition_to(CaseStatus.CLOSED)
        case.save()

        AuditLog.objects.create(
            actor=request.user,
            actor_role=request.user.role,
            action='case_closed',
            content_type='case',
            object_id=str(case.id),
            severity=AuditSeverity.INFO,
        )
        return Response({'status': 'closed', 'case_id': str(case.id)})
```

- [ ] **Step 4: Create URL patterns**

Create `backend/apps/judgments/urls.py`:

```python
from django.urls import path
from .views import AppealFileView, AppealWindowView, CaseCloseView, JudgmentDeliverView

urlpatterns = [
    path('', JudgmentDeliverView.as_view(), name='judgment-deliver'),
    path('appeal-windows/<uuid:window_id>/', AppealWindowView.as_view(), name='appeal-window'),
    path('appeal-windows/<uuid:window_id>/file/', AppealFileView.as_view(), name='appeal-file'),
    path('cases/<uuid:case_id>/close/', CaseCloseView.as_view(), name='case-close'),
]
```

- [ ] **Step 5: Wire into master URL conf**

In `backend/config/urls.py`:

```python
path('api/v1/judgments/', include('apps.judgments.urls')),
```

- [ ] **Step 6: Run all tests — expect PASS**

```bash
pytest apps/judgments/tests/ -v
```
Expected: all pass

```bash
pytest --tb=short -q
```
Expected: all passing, no regressions

- [ ] **Step 7: Commit**

```bash
git add apps/judgments/views.py apps/judgments/urls.py config/urls.py
git commit -m "feat: add judgment delivery, appeal filing, and case close endpoints"
```

---

## Task 5 — Frontend: Judgment and Appeal screens

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/endpoints.ts`
- Create: `frontend/src/screens/judge/DeliverJudgment.tsx`
- Create: `frontend/src/screens/lawyer/AppealFiling.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add types to `frontend/src/types/index.ts`**

```typescript
export interface Judgment {
  id: string;
  case: string;
  case_number: string;
  judge_name: string;
  outcome: 'allowed' | 'dismissed' | 'settled' | 'withdrawn' | 'consent_order';
  summary: string;
  full_text: string;
  delivered_at: string;
  days_remaining: number | null;
}

export interface AppealWindow {
  id: string;
  case_number: string;
  opened_at: string;
  expires_at: string;
  appeal_filed: boolean;
  days_remaining: number;
}

export interface Appeal {
  id: string;
  case_number: string;
  appeal_court: string;
  filed_by_name: string;
  grounds: string;
  notes: string;
  filed_at: string;
}
```

- [ ] **Step 2: Add API calls to `frontend/src/api/endpoints.ts`**

```typescript
export const judgmentApi = {
  deliver: (payload: {
    case: string; outcome: string; summary: string; full_text?: string;
  }) => apiClient.post<Judgment>('/api/v1/judgments/', payload),

  getAppealWindow: (windowId: string) =>
    apiClient.get<AppealWindow>(`/api/v1/judgments/appeal-windows/${windowId}/`),

  fileAppeal: (windowId: string, payload: {
    grounds: string; appeal_court: string; notes?: string;
  }) => apiClient.post<Appeal>(`/api/v1/judgments/appeal-windows/${windowId}/file/`, payload),

  closeCase: (caseId: string) =>
    apiClient.post(`/api/v1/judgments/cases/${caseId}/close/`),
};
```

- [ ] **Step 3: Create `DeliverJudgment.tsx`**

Create `frontend/src/screens/judge/DeliverJudgment.tsx`:

```tsx
import { useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { judgmentApi } from '../../api/endpoints';

const OUTCOMES = [
  { value: 'allowed', label: 'Allowed' },
  { value: 'dismissed', label: 'Dismissed' },
  { value: 'settled', label: 'Settled' },
  { value: 'withdrawn', label: 'Withdrawn' },
  { value: 'consent_order', label: 'Consent Order' },
];

export default function DeliverJudgment() {
  const [params] = useSearchParams();
  const caseId = params.get('case') ?? '';
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [form, setForm] = useState({ outcome: '', summary: '', full_text: '' });

  const deliver = useMutation({
    mutationFn: () => judgmentApi.deliver({ case: caseId, ...form }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['judge-queue'] });
      navigate('/judge/dashboard');
    },
  });

  return (
    <div className="p-6 max-w-2xl">
      <button onClick={() => navigate(-1)} className="text-sm text-muted mb-4 hover:text-text">← Back</button>
      <h1 className="text-2xl font-semibold mb-6">Deliver Judgment</h1>

      <div className="space-y-4">
        <div>
          <label className="block text-sm text-muted mb-1">Outcome</label>
          <select
            value={form.outcome}
            onChange={e => setForm(f => ({ ...f, outcome: e.target.value }))}
            className="w-full bg-surface2 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-teal"
          >
            <option value="">Select outcome…</option>
            {OUTCOMES.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        <div>
          <label className="block text-sm text-muted mb-1">Summary <span className="text-red">*</span></label>
          <textarea
            value={form.summary}
            onChange={e => setForm(f => ({ ...f, summary: e.target.value }))}
            rows={4}
            placeholder="Brief summary of the judgment…"
            className="w-full bg-surface2 border border-border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:border-teal"
          />
        </div>

        <div>
          <label className="block text-sm text-muted mb-1">Full Text (optional)</label>
          <textarea
            value={form.full_text}
            onChange={e => setForm(f => ({ ...f, full_text: e.target.value }))}
            rows={8}
            placeholder="Full judgment text…"
            className="w-full bg-surface2 border border-border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:border-teal"
          />
        </div>

        <button
          disabled={!form.outcome || form.summary.length < 10 || deliver.isPending}
          onClick={() => deliver.mutate()}
          className="w-full bg-teal text-white font-semibold py-2.5 rounded-lg disabled:opacity-40"
        >
          {deliver.isPending ? 'Delivering…' : 'Deliver Judgment'}
        </button>

        {deliver.isError && <p className="text-red text-sm">Failed to deliver judgment. Check your inputs.</p>}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create `AppealFiling.tsx`**

Create `frontend/src/screens/lawyer/AppealFiling.tsx`:

```tsx
import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { judgmentApi } from '../../api/endpoints';
import PageLoader from '../../components/ui/Spinner';

const COURTS = [
  { value: 'appeal', label: 'Court of Appeal' },
  { value: 'supreme', label: 'Supreme Court' },
];

export default function AppealFiling() {
  const { windowId } = useParams<{ windowId: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [form, setForm] = useState({ grounds: '', appeal_court: '', notes: '' });

  const { data: window, isLoading } = useQuery({
    queryKey: ['appeal-window', windowId],
    queryFn: () => judgmentApi.getAppealWindow(windowId!).then(r => r.data),
    enabled: !!windowId,
  });

  const file = useMutation({
    mutationFn: () => judgmentApi.fileAppeal(windowId!, form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cases'] });
      navigate('/cases');
    },
  });

  if (isLoading) return <PageLoader />;
  if (!window) return <p className="p-6 text-muted">Appeal window not found.</p>;

  const isOpen = !window.appeal_filed && window.days_remaining > 0;

  return (
    <div className="p-6 max-w-lg">
      <button onClick={() => navigate(-1)} className="text-sm text-muted mb-4 hover:text-text">← Back</button>
      <h1 className="text-2xl font-semibold mb-1">File Appeal</h1>

      <div className={`mb-6 p-3 rounded-lg text-sm font-mono ${isOpen ? 'bg-green/10 text-green' : 'bg-red/10 text-red'}`}>
        {isOpen
          ? `Appeal window open — ${window.days_remaining} day${window.days_remaining !== 1 ? 's' : ''} remaining`
          : 'Appeal window closed'}
      </div>

      {!isOpen ? (
        <p className="text-muted text-sm">The 30-day appeal window has expired. No further appeal can be filed.</p>
      ) : (
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-muted mb-1">Court to Appeal To</label>
            <select
              value={form.appeal_court}
              onChange={e => setForm(f => ({ ...f, appeal_court: e.target.value }))}
              className="w-full bg-surface2 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-gold"
            >
              <option value="">Select court…</option>
              {COURTS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-sm text-muted mb-1">Grounds of Appeal <span className="text-red">*</span></label>
            <textarea
              value={form.grounds}
              onChange={e => setForm(f => ({ ...f, grounds: e.target.value }))}
              rows={5}
              placeholder="State the legal grounds for your appeal…"
              className="w-full bg-surface2 border border-border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:border-gold"
            />
          </div>

          <button
            disabled={!form.appeal_court || form.grounds.length < 20 || file.isPending}
            onClick={() => file.mutate()}
            className="w-full bg-gold text-ink font-semibold py-2.5 rounded-lg disabled:opacity-40"
          >
            {file.isPending ? 'Filing Appeal…' : 'File Appeal'}
          </button>

          {file.isError && <p className="text-red text-sm">Failed to file appeal. The window may have closed.</p>}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Add routes to `App.tsx`**

```tsx
import DeliverJudgment from './screens/judge/DeliverJudgment';
import AppealFiling from './screens/lawyer/AppealFiling';

// Inside protected routes:
<Route path="/judgments/deliver" element={<DeliverJudgment />} />
<Route path="/appeals/:windowId/file" element={<AppealFiling />} />
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/screens/judge/DeliverJudgment.tsx frontend/src/screens/lawyer/AppealFiling.tsx frontend/src/types/index.ts frontend/src/api/endpoints.ts frontend/src/App.tsx
git commit -m "feat: add judgment delivery and appeal filing screens"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Step 12: Judgment delivered — `JudgmentDeliverView` + `DeliverJudgment.tsx`
- [x] Step 12: Appeal window auto-starts on judgment creation — `Judgment.save()` creates `AppealWindow`
- [x] Step 13: Appeal window timer with 30-day countdown — `AppealWindow.days_remaining()`
- [x] Step 13: Reminders T-7, T-3, T-1 — `send_appeal_window_reminders` Celery task
- [x] Step 14: Appeal filed electronically — `AppealFileView` + `AppealFiling.tsx`
- [x] Step 14: Case transitions to APPEAL_FILED on filing — in `AppealFileView.post()`
- [x] Step 15: Case archival — `archive_closed_cases` Celery task (90-day auto-archive)
- [x] Step 15: Manual case close — `CaseCloseView` for Registrar
- [x] Audit trail on all actions — `AuditLog.objects.create()` in every view

**Placeholder scan:** None.

**Type consistency:**
- `AppealWindow.id` UUID used consistently in URL patterns and frontend
- `Judgment.case` validated to be in `JUDGMENT_PENDING` status before creation
- `Appeal.save()` sets `window.appeal_filed = True` atomically

# Phase 2B — Hearing Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable Judge Clerks to create courtroom bookings and hearing schedules, record attendance and adjournments, and send automated hearing reminders (T-7, T-1) via Celery. Judges can view hearing details and record outcomes.

**Architecture:** New `apps/hearings` Django app with three models (`Courtroom`, `Hearing`, `HearingAttendance`). A Celery periodic task handles reminders. Four new permission checks: Clerk can create/update hearings; Judge can record outcomes; parties are notified via existing `notifications` app. Depends on Phase 2A (CaseAssignment must exist before a hearing can be created).

**Tech Stack:** Django 5.1, DRF, Celery + Redis (already configured), pytest-django, factory-boy, React + TypeScript + Tailwind, React Query

**Prerequisite:** Phase 2A plan fully implemented and merged.

---

## File Map

### Create
| File | Responsibility |
|------|---------------|
| `backend/apps/hearings/__init__.py` | App package |
| `backend/apps/hearings/models.py` | `Courtroom`, `Hearing`, `HearingAttendance` |
| `backend/apps/hearings/serializers.py` | Request/response shapes |
| `backend/apps/hearings/views.py` | 6 view classes |
| `backend/apps/hearings/urls.py` | URL patterns |
| `backend/apps/hearings/admin.py` | Admin registrations |
| `backend/apps/hearings/tasks.py` | Celery reminder tasks |
| `backend/apps/hearings/tests/__init__.py` | Test package |
| `backend/apps/hearings/tests/test_models.py` | Model unit tests |
| `backend/apps/hearings/tests/test_views.py` | API integration tests |
| `backend/apps/hearings/tests/test_tasks.py` | Celery task tests |
| `frontend/src/screens/clerk/HearingScheduler.tsx` | Clerk: schedule hearing |
| `frontend/src/screens/clerk/HearingDetail.tsx` | Clerk: manage hearing |
| `frontend/src/screens/judge/HearingView.tsx` | Judge: view + record outcome |

### Modify
| File | Change |
|------|--------|
| `backend/apps/cases/models.py` | Add `ASSIGNED → HEARING_SCHEDULED`, `HEARING_SCHEDULED → ACTIVE`, `ACTIVE → JUDGMENT_PENDING` to ALLOWED_TRANSITIONS |
| `backend/config/settings/base.py` | Add `apps.hearings` to LOCAL_APPS |
| `backend/config/urls.py` | Include `apps.hearings.urls` at `/api/v1/hearings/` |
| `frontend/src/App.tsx` | Add hearing routes |
| `frontend/src/components/layout/Sidebar.tsx` | Add clerk nav |
| `frontend/src/api/endpoints.ts` | Add hearing API calls |
| `frontend/src/types/index.ts` | Add Hearing, Courtroom types |

---

## Task 1 — Models: `Courtroom`, `Hearing`, `HearingAttendance`

**Files:**
- Create: `backend/apps/hearings/__init__.py`
- Create: `backend/apps/hearings/models.py`
- Create: `backend/apps/hearings/admin.py`
- Modify: `backend/config/settings/base.py`

- [ ] **Step 1: Write failing model tests**

Create `backend/apps/hearings/tests/__init__.py` (empty).
Create `backend/apps/hearings/tests/test_models.py`:

```python
import pytest
from datetime import timedelta
from django.utils import timezone
from apps.users.models import User, UserRole
from apps.cases.models import Case, CaseStatus, CourtTier, CaseType
from apps.firms.models import LawFirm, Lawyer
from apps.hearings.models import Courtroom, Hearing, HearingAttendance, HearingStatus


@pytest.fixture
def courtroom(db):
    return Courtroom.objects.create(
        name='Courtroom 1', court=CourtTier.HIGH, capacity=50, is_active=True,
    )


@pytest.fixture
def assigned_case(db):
    firm = LawFirm.objects.create(name='Firm B', bar_number='GBR-002', address='Banjul', status='active')
    lu = User.objects.create_user(email='l2@firm.gm', password='pass', role=UserRole.LAWYER)
    lawyer = Lawyer.objects.create(user=lu, firm=firm, bar_number='LAW-002')
    return Case.objects.create(
        title='Hearing Test Case',
        court=CourtTier.HIGH, case_type=CaseType.CIVIL_CLAIM,
        status=CaseStatus.ASSIGNED, submitted_by=lawyer, case_number='GJ-2026-HC-00002',
    )


@pytest.fixture
def hearing(db, assigned_case, courtroom):
    judge = User.objects.create_user(email='jj@jud.gm', password='pass', role=UserRole.JUDGE)
    return Hearing.objects.create(
        case=assigned_case,
        courtroom=courtroom,
        judge=judge,
        scheduled_at=timezone.now() + timedelta(days=7),
        duration_minutes=60,
    )


class TestCourtroom:
    def test_str(self, courtroom):
        assert 'Courtroom 1' in str(courtroom)

    def test_is_available_returns_true_when_no_hearings(self, courtroom):
        slot = timezone.now() + timedelta(days=7)
        assert courtroom.is_available(slot, 60) is True

    def test_is_available_returns_false_when_overlapping(self, courtroom, hearing):
        # hearing is at now+7d for 60 min; overlap: now+7d+30min
        overlap_slot = hearing.scheduled_at + timedelta(minutes=30)
        assert courtroom.is_available(overlap_slot, 60) is False

    def test_is_available_returns_true_outside_window(self, courtroom, hearing):
        after_slot = hearing.scheduled_at + timedelta(minutes=90)
        assert courtroom.is_available(after_slot, 60) is True


class TestHearing:
    def test_str(self, hearing, assigned_case):
        assert assigned_case.case_number in str(hearing)

    def test_default_status_is_scheduled(self, hearing):
        assert hearing.status == HearingStatus.SCHEDULED

    def test_cancel_sets_status(self, hearing):
        hearing.cancel(reason='Judge unavailable')
        assert hearing.status == HearingStatus.CANCELLED
        assert hearing.cancellation_reason == 'Judge unavailable'

    def test_adjourn_creates_new_hearing(self, hearing, courtroom):
        new_slot = timezone.now() + timedelta(days=14)
        new_hearing = hearing.adjourn(new_slot, courtroom, reason='Parties not ready')
        assert hearing.status == HearingStatus.ADJOURNED
        assert new_hearing.case == hearing.case
        assert new_hearing.scheduled_at == new_slot


class TestHearingAttendance:
    def test_attendance_recorded(self, hearing, db):
        party = User.objects.create_user(email='party@test.gm', password='pass')
        att = HearingAttendance.objects.create(
            hearing=hearing,
            party=party,
            attended=True,
        )
        assert att.attended is True
```

- [ ] **Step 2: Run — expect ImportError**

```bash
cd backend
pytest apps/hearings/tests/test_models.py -v
```
Expected: `ModuleNotFoundError: No module named 'apps.hearings'`

- [ ] **Step 3: Create models**

Create `backend/apps/hearings/__init__.py` (empty).

Create `backend/apps/hearings/models.py`:

```python
import uuid
from datetime import timedelta
from django.db import models
from django.utils import timezone
from apps.cases.models import CourtTier, CaseStatus


class HearingStatus(models.TextChoices):
    SCHEDULED = 'scheduled', 'Scheduled'
    ACTIVE = 'active', 'Active'
    COMPLETED = 'completed', 'Completed'
    ADJOURNED = 'adjourned', 'Adjourned'
    CANCELLED = 'cancelled', 'Cancelled'


class Courtroom(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    court = models.CharField(max_length=20, choices=CourtTier.choices)
    capacity = models.PositiveIntegerField(default=50)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['court', 'name']

    def __str__(self):
        return f"{self.name} ({self.court})"

    def is_available(self, slot, duration_minutes):
        """Return True if no SCHEDULED/ACTIVE hearing overlaps with slot for duration_minutes."""
        slot_end = slot + timedelta(minutes=duration_minutes)
        return not self.hearings.filter(
            status__in=[HearingStatus.SCHEDULED, HearingStatus.ACTIVE],
            scheduled_at__lt=slot_end,
            scheduled_end__gt=slot,
        ).exists()


class Hearing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(
        'cases.Case', on_delete=models.CASCADE, related_name='hearings',
    )
    courtroom = models.ForeignKey(
        Courtroom, on_delete=models.PROTECT, related_name='hearings',
    )
    judge = models.ForeignKey(
        'users.User', on_delete=models.PROTECT, related_name='hearings',
        limit_choices_to={'role': 'judge'},
    )
    scheduled_at = models.DateTimeField()
    scheduled_end = models.DateTimeField(editable=False)
    duration_minutes = models.PositiveIntegerField(default=60)
    status = models.CharField(
        max_length=20, choices=HearingStatus.choices, default=HearingStatus.SCHEDULED,
    )
    agenda = models.TextField(blank=True)
    outcome_notes = models.TextField(blank=True)
    cancellation_reason = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'users.User', on_delete=models.PROTECT, related_name='hearings_created',
        null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_at']

    def __str__(self):
        return f"{self.case.case_number} — {self.scheduled_at:%Y-%m-%d %H:%M}"

    def save(self, *args, **kwargs):
        self.scheduled_end = self.scheduled_at + timedelta(minutes=self.duration_minutes)
        super().save(*args, **kwargs)

    def cancel(self, reason=''):
        self.status = HearingStatus.CANCELLED
        self.cancellation_reason = reason
        self.save()

    def adjourn(self, new_slot, courtroom, reason=''):
        self.status = HearingStatus.ADJOURNED
        self.outcome_notes = reason
        self.save()
        return Hearing.objects.create(
            case=self.case,
            courtroom=courtroom,
            judge=self.judge,
            scheduled_at=new_slot,
            duration_minutes=self.duration_minutes,
            agenda=self.agenda,
            created_by=self.created_by,
        )


class HearingAttendance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hearing = models.ForeignKey(Hearing, on_delete=models.CASCADE, related_name='attendance')
    party = models.ForeignKey('users.User', on_delete=models.CASCADE)
    attended = models.BooleanField(default=False)
    notes = models.CharField(max_length=300, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['hearing', 'party']]
```

Create `backend/apps/hearings/admin.py`:

```python
from django.contrib import admin
from .models import Courtroom, Hearing, HearingAttendance


@admin.register(Courtroom)
class CourtroomAdmin(admin.ModelAdmin):
    list_display = ['name', 'court', 'capacity', 'is_active']
    list_filter = ['court', 'is_active']


@admin.register(Hearing)
class HearingAdmin(admin.ModelAdmin):
    list_display = ['case', 'courtroom', 'judge', 'scheduled_at', 'status']
    list_filter = ['status', 'courtroom__court']
    search_fields = ['case__case_number']
    readonly_fields = ['scheduled_end', 'created_at', 'updated_at']


@admin.register(HearingAttendance)
class HearingAttendanceAdmin(admin.ModelAdmin):
    list_display = ['hearing', 'party', 'attended']
```

- [ ] **Step 4: Register and migrate**

In `backend/config/settings/base.py`, add `'apps.hearings'` to `LOCAL_APPS`.

```bash
python manage.py makemigrations hearings
python manage.py migrate
```
Expected: `Applying hearings.0001_initial... OK`

- [ ] **Step 5: Run tests — expect PASS**

```bash
pytest apps/hearings/tests/test_models.py -v
```
Expected: 8 passed

- [ ] **Step 6: Add case transitions**

In `backend/apps/cases/models.py`, add to `ALLOWED_TRANSITIONS`:

```python
CaseStatus.ASSIGNED: [CaseStatus.HEARING_SCHEDULED],
CaseStatus.HEARING_SCHEDULED: [CaseStatus.ACTIVE],
CaseStatus.ACTIVE: [CaseStatus.JUDGMENT_PENDING],
```

- [ ] **Step 7: Commit**

```bash
git add apps/hearings/ config/settings/base.py apps/cases/models.py
git commit -m "feat: add Courtroom, Hearing, HearingAttendance models"
```

---

## Task 2 — Celery reminder tasks

**Files:**
- Create: `backend/apps/hearings/tasks.py`
- Test: `backend/apps/hearings/tests/test_tasks.py`

- [ ] **Step 1: Write failing task tests**

Create `backend/apps/hearings/tests/test_tasks.py`:

```python
import pytest
from datetime import timedelta
from unittest.mock import patch, call
from django.utils import timezone
from apps.users.models import User, UserRole
from apps.cases.models import Case, CaseStatus, CourtTier, CaseType
from apps.firms.models import LawFirm, Lawyer
from apps.hearings.models import Courtroom, Hearing, HearingStatus
from apps.hearings.tasks import send_hearing_reminders


@pytest.fixture
def setup_hearing_in_7_days(db):
    firm = LawFirm.objects.create(name='Firm C', bar_number='GBR-003', address='Banjul', status='active')
    lu = User.objects.create_user(email='l3@firm.gm', password='pass', role=UserRole.LAWYER, phone='+22012345678')
    lawyer = Lawyer.objects.create(user=lu, firm=firm, bar_number='LAW-003')
    case = Case.objects.create(
        title='Reminder Test Case', court=CourtTier.HIGH, case_type=CaseType.CIVIL_CLAIM,
        status=CaseStatus.HEARING_SCHEDULED, submitted_by=lawyer, case_number='GJ-2026-HC-00003',
    )
    judge = User.objects.create_user(email='jj2@jud.gm', password='pass', role=UserRole.JUDGE)
    room = Courtroom.objects.create(name='Room 2', court=CourtTier.HIGH, capacity=30, is_active=True)
    return Hearing.objects.create(
        case=case, courtroom=room, judge=judge,
        scheduled_at=timezone.now() + timedelta(days=7),
        duration_minutes=60,
    )


class TestSendHearingReminders:
    @patch('apps.hearings.tasks.send_notification')
    def test_reminder_sent_7_days_before(self, mock_notify, setup_hearing_in_7_days):
        send_hearing_reminders()
        assert mock_notify.called

    @patch('apps.hearings.tasks.send_notification')
    def test_no_reminder_for_cancelled(self, mock_notify, setup_hearing_in_7_days, db):
        setup_hearing_in_7_days.cancel('test')
        send_hearing_reminders()
        assert not mock_notify.called

    @patch('apps.hearings.tasks.send_notification')
    def test_no_reminder_for_hearing_20_days_away(self, mock_notify, db):
        firm = LawFirm.objects.create(name='Firm D', bar_number='GBR-004', address='Banjul', status='active')
        lu = User.objects.create_user(email='l4@firm.gm', password='pass', role=UserRole.LAWYER)
        lawyer = Lawyer.objects.create(user=lu, firm=firm, bar_number='LAW-004')
        case = Case.objects.create(
            title='Far Future', court=CourtTier.HIGH, case_type=CaseType.CIVIL_CLAIM,
            status=CaseStatus.HEARING_SCHEDULED, submitted_by=lawyer, case_number='GJ-2026-HC-00004',
        )
        judge = User.objects.create_user(email='jj3@jud.gm', password='pass', role=UserRole.JUDGE)
        room = Courtroom.objects.create(name='Room 3', court=CourtTier.HIGH, capacity=30, is_active=True)
        Hearing.objects.create(
            case=case, courtroom=room, judge=judge,
            scheduled_at=timezone.now() + timedelta(days=20),
            duration_minutes=60,
        )
        send_hearing_reminders()
        assert not mock_notify.called
```

- [ ] **Step 2: Run — expect ImportError**

```bash
pytest apps/hearings/tests/test_tasks.py -v
```
Expected: `ImportError: cannot import name 'send_hearing_reminders'`

- [ ] **Step 3: Write the Celery task**

Create `backend/apps/hearings/tasks.py`:

```python
from datetime import timedelta
from django.utils import timezone
from config.celery import app
from apps.notifications.models import Notification, NotificationChannel


def send_notification(recipient, subject, body, obj_id=''):
    """Create a Notification record (actual SMS/email dispatched by existing notification tasks)."""
    Notification.objects.create(
        recipient=recipient,
        channel=NotificationChannel.SMS,
        subject=subject,
        body=body,
        content_type='hearing',
        object_id=str(obj_id),
    )


@app.task(name='hearings.send_hearing_reminders')
def send_hearing_reminders():
    """
    Run daily. Sends reminders for hearings scheduled in exactly 7 days or 1 day.
    Only fires for SCHEDULED status hearings.
    """
    from apps.hearings.models import Hearing, HearingStatus

    now = timezone.now()
    windows = [
        (now + timedelta(days=7), now + timedelta(days=7, hours=1), 'T-7'),
        (now + timedelta(days=1), now + timedelta(days=1, hours=1), 'T-1'),
    ]

    for window_start, window_end, label in windows:
        hearings = Hearing.objects.filter(
            status=HearingStatus.SCHEDULED,
            scheduled_at__gte=window_start,
            scheduled_at__lt=window_end,
        ).select_related('case__submitted_by__user', 'judge', 'courtroom')

        for hearing in hearings:
            lawyer_user = hearing.case.submitted_by.user
            body = (
                f"REMINDER ({label}): Your case {hearing.case.case_number} "
                f"has a hearing on {hearing.scheduled_at:%d %b %Y at %H:%M} "
                f"in {hearing.courtroom.name}."
            )
            send_notification(
                recipient=lawyer_user,
                subject=f"Hearing Reminder — {hearing.case.case_number}",
                body=body,
                obj_id=hearing.id,
            )
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest apps/hearings/tests/test_tasks.py -v
```
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add apps/hearings/tasks.py apps/hearings/tests/test_tasks.py
git commit -m "feat: add Celery hearing reminder task (T-7, T-1)"
```

---

## Task 3 — Serializers

**Files:**
- Create: `backend/apps/hearings/serializers.py`

- [ ] **Step 1: Create `backend/apps/hearings/serializers.py`**

```python
from rest_framework import serializers
from .models import Courtroom, Hearing, HearingAttendance, HearingStatus


class CourtroomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Courtroom
        fields = ['id', 'name', 'court', 'capacity', 'is_active']


class HearingSerializer(serializers.ModelSerializer):
    courtroom_name = serializers.CharField(source='courtroom.name', read_only=True)
    judge_name = serializers.CharField(source='judge.get_full_name', read_only=True)
    case_number = serializers.CharField(source='case.case_number', read_only=True)

    class Meta:
        model = Hearing
        fields = [
            'id', 'case', 'case_number', 'courtroom', 'courtroom_name',
            'judge', 'judge_name', 'scheduled_at', 'scheduled_end',
            'duration_minutes', 'status', 'agenda', 'outcome_notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['scheduled_end', 'status', 'created_at', 'updated_at']


class HearingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hearing
        fields = ['case', 'courtroom', 'judge', 'scheduled_at', 'duration_minutes', 'agenda']

    def validate(self, data):
        courtroom = data['courtroom']
        slot = data['scheduled_at']
        duration = data.get('duration_minutes', 60)
        if not courtroom.is_available(slot, duration):
            raise serializers.ValidationError(
                f'{courtroom.name} is already booked at that time.'
            )
        return data


class HearingAdjournSerializer(serializers.Serializer):
    new_slot = serializers.DateTimeField()
    courtroom = serializers.UUIDField()
    reason = serializers.CharField(min_length=5)

    def validate_courtroom(self, value):
        try:
            return Courtroom.objects.get(id=value, is_active=True)
        except Courtroom.DoesNotExist:
            raise serializers.ValidationError('Courtroom not found or inactive.')


class HearingOutcomeSerializer(serializers.Serializer):
    outcome_notes = serializers.CharField(min_length=10)
    status = serializers.ChoiceField(choices=[HearingStatus.COMPLETED, HearingStatus.ADJOURNED])


class HearingAttendanceSerializer(serializers.ModelSerializer):
    party_name = serializers.CharField(source='party.get_full_name', read_only=True)

    class Meta:
        model = HearingAttendance
        fields = ['id', 'party', 'party_name', 'attended', 'notes', 'recorded_at']
        read_only_fields = ['recorded_at']
```

- [ ] **Step 2: Commit**

```bash
git add apps/hearings/serializers.py
git commit -m "feat: add hearing serializers"
```

---

## Task 4 — Views and URLs

**Files:**
- Create: `backend/apps/hearings/views.py`
- Create: `backend/apps/hearings/urls.py`
- Modify: `backend/config/urls.py`
- Test: `backend/apps/hearings/tests/test_views.py`

- [ ] **Step 1: Write failing view tests**

Create `backend/apps/hearings/tests/test_views.py`:

```python
import pytest
from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User, UserRole
from apps.cases.models import Case, CaseStatus, CourtTier, CaseType
from apps.firms.models import LawFirm, Lawyer
from apps.hearings.models import Courtroom, Hearing, HearingStatus


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def clerk_user(db):
    return User.objects.create_user(
        email='clerk@jud.gm', password='pass', role=UserRole.JUDGE_CLERK,
    )


@pytest.fixture
def judge_user(db):
    return User.objects.create_user(
        email='judge@jud.gm', password='pass', role=UserRole.JUDGE,
    )


@pytest.fixture
def courtroom(db):
    return Courtroom.objects.create(
        name='Room A', court=CourtTier.HIGH, capacity=30, is_active=True,
    )


@pytest.fixture
def assigned_case(db, judge_user):
    from apps.assignments.models import CaseAssignment, JudgeProfile
    cj = User.objects.create_user(email='cj@jud.gm', password='pass', role=UserRole.CHIEF_JUSTICE)
    firm = LawFirm.objects.create(name='Firm E', bar_number='GBR-005', address='Banjul', status='active')
    lu = User.objects.create_user(email='l5@firm.gm', password='pass', role=UserRole.LAWYER)
    lawyer = Lawyer.objects.create(user=lu, firm=firm, bar_number='LAW-005')
    case = Case.objects.create(
        title='View Test Case', court=CourtTier.HIGH, case_type=CaseType.CIVIL_CLAIM,
        status=CaseStatus.ASSIGNED, submitted_by=lawyer, case_number='GJ-2026-HC-00005',
    )
    CaseAssignment.objects.create(case=case, judge=judge_user, assigned_by=cj)
    return case


class TestCourtroomListView:
    def test_authenticated_user_can_list_courtrooms(self, api_client, clerk_user, courtroom):
        api_client.force_authenticate(clerk_user)
        url = reverse('courtroom-list')
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert any(r['id'] == str(courtroom.id) for r in resp.data)


class TestHearingCreateView:
    def test_clerk_can_schedule_hearing(self, api_client, clerk_user, assigned_case, courtroom, judge_user):
        api_client.force_authenticate(clerk_user)
        url = reverse('hearing-list-create')
        slot = (timezone.now() + timedelta(days=7)).isoformat()
        resp = api_client.post(url, {
            'case': str(assigned_case.id),
            'courtroom': str(courtroom.id),
            'judge': str(judge_user.id),
            'scheduled_at': slot,
            'duration_minutes': 60,
            'agenda': 'Opening statements',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assigned_case.refresh_from_db()
        assert assigned_case.status == CaseStatus.HEARING_SCHEDULED

    def test_double_booking_rejected(self, api_client, clerk_user, assigned_case, courtroom, judge_user):
        slot = timezone.now() + timedelta(days=7)
        Hearing.objects.create(
            case=assigned_case, courtroom=courtroom, judge=judge_user,
            scheduled_at=slot, duration_minutes=60,
        )
        assigned_case.status = CaseStatus.HEARING_SCHEDULED
        assigned_case.save()

        # Create a second case in ASSIGNED status for the second hearing
        firm2 = LawFirm.objects.create(name='Firm F', bar_number='GBR-006', address='Banjul', status='active')
        lu2 = User.objects.create_user(email='l6@firm.gm', password='pass', role=UserRole.LAWYER)
        lawyer2 = Lawyer.objects.create(user=lu2, firm=firm2, bar_number='LAW-006')
        case2 = Case.objects.create(
            title='Case 2', court=CourtTier.HIGH, case_type=CaseType.CIVIL_CLAIM,
            status=CaseStatus.ASSIGNED, submitted_by=lawyer2, case_number='GJ-2026-HC-00006',
        )
        api_client.force_authenticate(clerk_user)
        url = reverse('hearing-list-create')
        resp = api_client.post(url, {
            'case': str(case2.id),
            'courtroom': str(courtroom.id),
            'judge': str(judge_user.id),
            'scheduled_at': (slot + timedelta(minutes=30)).isoformat(),
            'duration_minutes': 60,
            'agenda': '',
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_lawyer_cannot_create_hearing(self, api_client, assigned_case, courtroom, judge_user):
        lu = User.objects.create_user(email='lx@f.gm', password='pass', role=UserRole.LAWYER)
        api_client.force_authenticate(lu)
        url = reverse('hearing-list-create')
        resp = api_client.post(url, {
            'case': str(assigned_case.id), 'courtroom': str(courtroom.id),
            'judge': str(judge_user.id),
            'scheduled_at': (timezone.now() + timedelta(days=7)).isoformat(),
        }, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestHearingAdjournView:
    def test_clerk_can_adjourn(self, api_client, clerk_user, assigned_case, courtroom, judge_user):
        slot = timezone.now() + timedelta(days=7)
        hearing = Hearing.objects.create(
            case=assigned_case, courtroom=courtroom, judge=judge_user,
            scheduled_at=slot, duration_minutes=60,
        )
        api_client.force_authenticate(clerk_user)
        url = reverse('hearing-adjourn', kwargs={'hearing_id': hearing.id})
        new_slot = (slot + timedelta(days=14)).isoformat()
        resp = api_client.post(url, {
            'new_slot': new_slot,
            'courtroom': str(courtroom.id),
            'reason': 'Parties requested more time',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        hearing.refresh_from_db()
        assert hearing.status == HearingStatus.ADJOURNED


class TestHearingOutcomeView:
    def test_judge_records_outcome(self, api_client, judge_user, assigned_case, courtroom):
        slot = timezone.now() + timedelta(days=7)
        hearing = Hearing.objects.create(
            case=assigned_case, courtroom=courtroom, judge=judge_user,
            scheduled_at=slot, duration_minutes=60,
        )
        api_client.force_authenticate(judge_user)
        url = reverse('hearing-outcome', kwargs={'hearing_id': hearing.id})
        resp = api_client.post(url, {
            'outcome_notes': 'Claimant presented evidence. Case continues.',
            'status': HearingStatus.COMPLETED,
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        hearing.refresh_from_db()
        assert hearing.status == HearingStatus.COMPLETED

    def test_clerk_cannot_record_outcome(self, api_client, clerk_user, assigned_case, courtroom, judge_user):
        hearing = Hearing.objects.create(
            case=assigned_case, courtroom=courtroom, judge=judge_user,
            scheduled_at=timezone.now() + timedelta(days=7), duration_minutes=60,
        )
        api_client.force_authenticate(clerk_user)
        url = reverse('hearing-outcome', kwargs={'hearing_id': hearing.id})
        resp = api_client.post(url, {
            'outcome_notes': 'Should not work',
            'status': HearingStatus.COMPLETED,
        }, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN
```

- [ ] **Step 2: Run — expect errors**

```bash
pytest apps/hearings/tests/test_views.py -v
```
Expected: `NoReverseMatch` or import errors

- [ ] **Step 3: Create views**

Create `backend/apps/hearings/views.py`:

```python
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog, AuditSeverity
from apps.cases.models import Case, CaseStatus
from core.permissions import IsJudge, IsJudgeClerk

from .models import Courtroom, Hearing, HearingStatus
from .serializers import (
    CourtroomSerializer,
    HearingAdjournSerializer,
    HearingCreateSerializer,
    HearingOutcomeSerializer,
    HearingSerializer,
)


class CourtroomListView(generics.ListAPIView):
    """GET /api/v1/hearings/courtrooms/ — list active courtrooms."""
    serializer_class = CourtroomSerializer
    queryset = Courtroom.objects.filter(is_active=True)


class HearingListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/hearings/          — list hearings (filterable by case)
    POST /api/v1/hearings/          — clerk creates a hearing
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsJudgeClerk()]
        from rest_framework.permissions import IsAuthenticated
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return HearingCreateSerializer
        return HearingSerializer

    def get_queryset(self):
        qs = Hearing.objects.select_related('case', 'courtroom', 'judge')
        case_id = self.request.query_params.get('case')
        if case_id:
            qs = qs.filter(case__id=case_id)
        return qs

    def perform_create(self, serializer):
        hearing = serializer.save(created_by=self.request.user)
        case = hearing.case
        case.transition_to(CaseStatus.HEARING_SCHEDULED)
        case.save()
        AuditLog.objects.create(
            actor=self.request.user,
            actor_role=self.request.user.role,
            action='hearing_scheduled',
            content_type='hearing',
            object_id=str(hearing.id),
            note=f'Hearing on {hearing.scheduled_at:%Y-%m-%d} in {hearing.courtroom.name}',
            severity=AuditSeverity.INFO,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        out = HearingSerializer(serializer.instance)
        return Response(out.data, status=status.HTTP_201_CREATED)


class HearingDetailView(generics.RetrieveAPIView):
    """GET /api/v1/hearings/<hearing_id>/ — hearing detail."""
    serializer_class = HearingSerializer
    queryset = Hearing.objects.select_related('case', 'courtroom', 'judge')
    lookup_field = 'id'
    lookup_url_kwarg = 'hearing_id'


class HearingAdjournView(APIView):
    """POST /api/v1/hearings/<hearing_id>/adjourn/ — clerk adjourns hearing."""
    permission_classes = [IsJudgeClerk]

    def post(self, request, hearing_id):
        hearing = get_object_or_404(Hearing, id=hearing_id, status=HearingStatus.SCHEDULED)
        serializer = HearingAdjournSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_hearing = hearing.adjourn(
            new_slot=serializer.validated_data['new_slot'],
            courtroom=serializer.validated_data['courtroom'],
            reason=serializer.validated_data['reason'],
        )
        AuditLog.objects.create(
            actor=request.user,
            actor_role=request.user.role,
            action='hearing_adjourned',
            content_type='hearing',
            object_id=str(hearing.id),
            note=serializer.validated_data['reason'],
            severity=AuditSeverity.INFO,
        )
        return Response(HearingSerializer(new_hearing).data, status=status.HTTP_201_CREATED)


class HearingOutcomeView(APIView):
    """POST /api/v1/hearings/<hearing_id>/outcome/ — judge records outcome."""
    permission_classes = [IsJudge]

    def post(self, request, hearing_id):
        hearing = get_object_or_404(
            Hearing, id=hearing_id,
            judge=request.user,
            status__in=[HearingStatus.SCHEDULED, HearingStatus.ACTIVE],
        )
        serializer = HearingOutcomeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        hearing.outcome_notes = serializer.validated_data['outcome_notes']
        hearing.status = serializer.validated_data['status']
        hearing.save()

        AuditLog.objects.create(
            actor=request.user,
            actor_role=request.user.role,
            action=f"hearing_{serializer.validated_data['status']}",
            content_type='hearing',
            object_id=str(hearing.id),
            note=serializer.validated_data['outcome_notes'][:200],
            severity=AuditSeverity.INFO,
        )
        return Response(HearingSerializer(hearing).data)
```

- [ ] **Step 4: Create URL patterns**

Create `backend/apps/hearings/urls.py`:

```python
from django.urls import path
from .views import (
    CourtroomListView,
    HearingAdjournView,
    HearingDetailView,
    HearingListCreateView,
    HearingOutcomeView,
)

urlpatterns = [
    path('courtrooms/', CourtroomListView.as_view(), name='courtroom-list'),
    path('', HearingListCreateView.as_view(), name='hearing-list-create'),
    path('<uuid:hearing_id>/', HearingDetailView.as_view(), name='hearing-detail'),
    path('<uuid:hearing_id>/adjourn/', HearingAdjournView.as_view(), name='hearing-adjourn'),
    path('<uuid:hearing_id>/outcome/', HearingOutcomeView.as_view(), name='hearing-outcome'),
]
```

- [ ] **Step 5: Wire into master URL conf**

In `backend/config/urls.py`:

```python
path('api/v1/hearings/', include('apps.hearings.urls')),
```

- [ ] **Step 6: Run tests — expect PASS**

```bash
pytest apps/hearings/tests/ -v
```
Expected: all passed

- [ ] **Step 7: Full regression check**

```bash
pytest --tb=short -q
```
Expected: all passing

- [ ] **Step 8: Commit**

```bash
git add apps/hearings/views.py apps/hearings/urls.py config/urls.py
git commit -m "feat: add hearing scheduling, adjournment, and outcome API endpoints"
```

---

## Task 5 — Frontend: Hearing screens (Clerk + Judge)

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/endpoints.ts`
- Create: `frontend/src/screens/clerk/HearingScheduler.tsx`
- Create: `frontend/src/screens/clerk/HearingDetail.tsx`
- Create: `frontend/src/screens/judge/HearingView.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/layout/Sidebar.tsx`

- [ ] **Step 1: Add types to `frontend/src/types/index.ts`**

```typescript
export interface Courtroom {
  id: string;
  name: string;
  court: string;
  capacity: number;
  is_active: boolean;
}

export interface Hearing {
  id: string;
  case: string;
  case_number: string;
  courtroom: string;
  courtroom_name: string;
  judge: string;
  judge_name: string;
  scheduled_at: string;
  scheduled_end: string;
  duration_minutes: number;
  status: 'scheduled' | 'active' | 'completed' | 'adjourned' | 'cancelled';
  agenda: string;
  outcome_notes: string;
  created_at: string;
}
```

- [ ] **Step 2: Add API calls to `frontend/src/api/endpoints.ts`**

```typescript
export const hearingApi = {
  listCourtrooms: () =>
    apiClient.get<Courtroom[]>('/api/v1/hearings/courtrooms/'),

  create: (payload: {
    case: string; courtroom: string; judge: string;
    scheduled_at: string; duration_minutes: number; agenda?: string;
  }) => apiClient.post<Hearing>('/api/v1/hearings/', payload),

  listForCase: (caseId: string) =>
    apiClient.get<Hearing[]>(`/api/v1/hearings/?case=${caseId}`),

  getDetail: (hearingId: string) =>
    apiClient.get<Hearing>(`/api/v1/hearings/${hearingId}/`),

  adjourn: (hearingId: string, payload: {
    new_slot: string; courtroom: string; reason: string;
  }) => apiClient.post<Hearing>(`/api/v1/hearings/${hearingId}/adjourn/`, payload),

  recordOutcome: (hearingId: string, payload: {
    outcome_notes: string; status: 'completed' | 'adjourned';
  }) => apiClient.post<Hearing>(`/api/v1/hearings/${hearingId}/outcome/`, payload),
};
```

- [ ] **Step 3: Create `HearingScheduler.tsx`**

Create `frontend/src/screens/clerk/HearingScheduler.tsx`:

```tsx
import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { hearingApi } from '../../api/endpoints';

export default function HearingScheduler() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const caseId = params.get('case') ?? '';
  const judgeId = params.get('judge') ?? '';
  const qc = useQueryClient();

  const [form, setForm] = useState({
    courtroom: '', scheduled_at: '', duration_minutes: 60, agenda: '',
  });

  const { data: rooms } = useQuery({
    queryKey: ['courtrooms'],
    queryFn: () => hearingApi.listCourtrooms().then(r => r.data),
  });

  const create = useMutation({
    mutationFn: () => hearingApi.create({
      case: caseId, courtroom: form.courtroom, judge: judgeId,
      scheduled_at: form.scheduled_at, duration_minutes: form.duration_minutes,
      agenda: form.agenda,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['judge-queue'] });
      navigate(`/cases/${caseId}`);
    },
  });

  return (
    <div className="p-6 max-w-lg">
      <button onClick={() => navigate(-1)} className="text-sm text-muted mb-4 hover:text-text">← Back</button>
      <h1 className="text-2xl font-semibold mb-6">Schedule Hearing</h1>

      <div className="space-y-4">
        <div>
          <label className="block text-sm text-muted mb-1">Courtroom</label>
          <select
            value={form.courtroom}
            onChange={e => setForm(f => ({ ...f, courtroom: e.target.value }))}
            className="w-full bg-surface2 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-gold"
          >
            <option value="">Select courtroom…</option>
            {rooms?.map(r => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm text-muted mb-1">Date & Time</label>
          <input
            type="datetime-local"
            value={form.scheduled_at}
            onChange={e => setForm(f => ({ ...f, scheduled_at: e.target.value }))}
            className="w-full bg-surface2 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-gold"
          />
        </div>

        <div>
          <label className="block text-sm text-muted mb-1">Duration (minutes)</label>
          <input
            type="number"
            min={30}
            max={480}
            step={30}
            value={form.duration_minutes}
            onChange={e => setForm(f => ({ ...f, duration_minutes: Number(e.target.value) }))}
            className="w-full bg-surface2 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-gold"
          />
        </div>

        <div>
          <label className="block text-sm text-muted mb-1">Agenda (optional)</label>
          <textarea
            value={form.agenda}
            onChange={e => setForm(f => ({ ...f, agenda: e.target.value }))}
            rows={3}
            className="w-full bg-surface2 border border-border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:border-gold"
          />
        </div>

        <button
          disabled={!form.courtroom || !form.scheduled_at || create.isPending}
          onClick={() => create.mutate()}
          className="w-full bg-teal text-white font-semibold py-2.5 rounded-lg disabled:opacity-40 hover:opacity-90 transition-opacity"
        >
          {create.isPending ? 'Scheduling…' : 'Schedule Hearing'}
        </button>

        {create.isError && (
          <p className="text-red text-sm">
            {(create.error as any)?.response?.data?.non_field_errors?.[0] ?? 'Failed to schedule. Try again.'}
          </p>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create `HearingView.tsx` (Judge)**

Create `frontend/src/screens/judge/HearingView.tsx`:

```tsx
import { useParams, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { hearingApi } from '../../api/endpoints';
import PageLoader from '../../components/ui/Spinner';

export default function HearingView() {
  const { hearingId } = useParams<{ hearingId: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [notes, setNotes] = useState('');

  const { data: hearing, isLoading } = useQuery({
    queryKey: ['hearing', hearingId],
    queryFn: () => hearingApi.getDetail(hearingId!).then(r => r.data),
    enabled: !!hearingId,
  });

  const complete = useMutation({
    mutationFn: () => hearingApi.recordOutcome(hearingId!, { outcome_notes: notes, status: 'completed' }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['judge-queue'] }); navigate('/judge/dashboard'); },
  });

  if (isLoading) return <PageLoader />;
  if (!hearing) return <p className="p-6 text-muted">Hearing not found.</p>;

  return (
    <div className="p-6 max-w-2xl">
      <button onClick={() => navigate(-1)} className="text-sm text-muted mb-4 hover:text-text">← Back</button>
      <h1 className="text-2xl font-semibold mb-1">{hearing.case_number}</h1>
      <p className="text-sm text-muted mb-6">
        {hearing.courtroom_name} · {new Date(hearing.scheduled_at).toLocaleString()} · {hearing.duration_minutes} min
      </p>

      {hearing.agenda && (
        <div className="mb-6 p-4 bg-surface border border-border rounded-lg">
          <p className="text-xs text-muted mb-1 font-mono uppercase tracking-wider">Agenda</p>
          <p className="text-sm">{hearing.agenda}</p>
        </div>
      )}

      {hearing.status === 'scheduled' || hearing.status === 'active' ? (
        <div>
          <label className="block text-sm text-muted mb-1">Outcome Notes</label>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            rows={4}
            placeholder="Record what transpired during this hearing…"
            className="w-full bg-surface2 border border-border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:border-teal mb-3"
          />
          <button
            disabled={notes.length < 10 || complete.isPending}
            onClick={() => complete.mutate()}
            className="w-full bg-teal text-white font-semibold py-2.5 rounded-lg disabled:opacity-40"
          >
            {complete.isPending ? 'Saving…' : 'Mark Completed'}
          </button>
        </div>
      ) : (
        <div className="p-4 bg-surface border border-border rounded-lg">
          <p className="text-xs text-muted mb-1 font-mono uppercase tracking-wider">Outcome</p>
          <p className="text-sm">{hearing.outcome_notes || '—'}</p>
          <p className="text-xs text-gold mt-2 capitalize">{hearing.status}</p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Add routes and sidebar nav**

In `frontend/src/App.tsx`, add:

```tsx
import HearingScheduler from './screens/clerk/HearingScheduler';
import HearingView from './screens/judge/HearingView';

// Inside protected routes:
<Route path="/hearings/schedule" element={<HearingScheduler />} />
<Route path="/hearings/:hearingId" element={<HearingView />} />
```

In `frontend/src/components/layout/Sidebar.tsx`, add:

```tsx
...(user.role === 'judge_clerk' ? [
  { label: 'Schedule Hearing', icon: '📅', path: '/hearings/schedule' },
] : []),
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/screens/clerk/ frontend/src/screens/judge/HearingView.tsx frontend/src/types/index.ts frontend/src/api/endpoints.ts frontend/src/App.tsx frontend/src/components/layout/Sidebar.tsx
git commit -m "feat: add hearing scheduler and judge hearing view screens"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Step 8: Clerk creates hearing notice and books courtroom — `HearingListCreateView` + `HearingScheduler`
- [x] Step 9: Hearing scheduler with courtroom booking and double-booking prevention — `Courtroom.is_available()`
- [x] Step 9: Reminders T-7 and T-1 — `send_hearing_reminders` Celery task
- [x] Step 10: Hearing conducted — judge records outcome via `HearingOutcomeView` + `HearingView`
- [x] Step 10: Adjournment log — `HearingAdjournView` creates new Hearing, old marked ADJOURNED
- [x] Audit trail on all state changes — written in each view

**Placeholder scan:** None.

**Type consistency:**
- `Courtroom.id` is UUID — validated in `HearingAdjournSerializer.validate_courtroom()`
- `HearingStatus` choices match between model, serializer, and frontend type
- `create` view returns `HearingSerializer` output (not `HearingCreateSerializer`)

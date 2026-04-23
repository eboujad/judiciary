# Phase 2A — Judge Assignment & Workload Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable Chief Justice to see registered cases, view real-time judge workload stats, assign a judge to each case, and have judges see their own assigned case queue.

**Architecture:** New `apps/assignments` Django app with two models (`JudgeProfile`, `CaseAssignment`), a stateless workload-analysis service function, 4 API endpoints, and 2 new React screens. Reuses existing permission system pattern — two new permission classes added to `core/permissions.py`.

**Tech Stack:** Django 5.1, DRF, pytest-django, factory-boy, React + TypeScript + Tailwind, React Query, Zustand (authStore)

---

## File Map

### Create
| File | Responsibility |
|------|---------------|
| `backend/apps/assignments/__init__.py` | App package marker |
| `backend/apps/assignments/models.py` | `JudgeProfile`, `CaseAssignment` models |
| `backend/apps/assignments/services.py` | `get_judge_workload()` — pure workload analysis |
| `backend/apps/assignments/serializers.py` | Request/response shapes for all 4 endpoints |
| `backend/apps/assignments/views.py` | 4 view classes |
| `backend/apps/assignments/urls.py` | URL patterns for this app |
| `backend/apps/assignments/admin.py` | Django admin registration |
| `backend/apps/assignments/tests/__init__.py` | Test package |
| `backend/apps/assignments/tests/test_models.py` | Model & service unit tests |
| `backend/apps/assignments/tests/test_views.py` | API integration tests |
| `frontend/src/screens/chief_justice/AssignmentQueue.tsx` | CJ: list REGISTERED cases |
| `frontend/src/screens/chief_justice/AssignmentDetail.tsx` | CJ: pick judge, view workload |
| `frontend/src/screens/judge/JudgeDashboard.tsx` | Judge: my case queue |

### Modify
| File | Change |
|------|--------|
| `backend/core/permissions.py` | Add `IsChiefJustice`, `IsJudge`, `IsJudgeClerk` |
| `backend/apps/cases/models.py` | Add `REGISTERED → ASSIGNED` to `ALLOWED_TRANSITIONS` |
| `backend/config/settings/base.py` | Add `apps.assignments` to `LOCAL_APPS` |
| `backend/config/urls.py` | Include `apps.assignments.urls` at `/api/v1/assignments/` |
| `frontend/src/App.tsx` | Add routes for 3 new screens |
| `frontend/src/components/layout/Sidebar.tsx` | Add nav items for chief justice & judge roles |
| `frontend/src/api/endpoints.ts` | Add assignment API calls |
| `frontend/src/types/index.ts` | Add `JudgeWorkload`, `CaseAssignment` types |

---

## Task 1 — Add `IsChiefJustice`, `IsJudge`, `IsJudgeClerk` permission classes

**Files:**
- Modify: `backend/core/permissions.py`
- Test: `backend/apps/assignments/tests/test_views.py` (used in Task 5)

- [ ] **Step 1: Read existing permissions file**

```bash
cat backend/core/permissions.py
```

- [ ] **Step 2: Write failing tests for new permission classes**

Create `backend/apps/assignments/tests/__init__.py` (empty) and `backend/apps/assignments/tests/test_permissions.py`:

```python
import pytest
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory
from apps.users.models import User, UserRole
from core.permissions import IsChiefJustice, IsJudge, IsJudgeClerk


def make_user(role):
    u = User.__new__(User)
    u.role = role
    u.is_authenticated = True
    return u


@pytest.mark.parametrize("role,expected", [
    (UserRole.CHIEF_JUSTICE, True),
    (UserRole.JUDGE, False),
    (UserRole.REGISTRAR, False),
    (UserRole.LAWYER, False),
])
def test_is_chief_justice(role, expected):
    perm = IsChiefJustice()
    request = APIRequestFactory().get('/')
    request.user = make_user(role)
    assert perm.has_permission(request, None) == expected


@pytest.mark.parametrize("role,expected", [
    (UserRole.JUDGE, True),
    (UserRole.CHIEF_JUSTICE, False),
    (UserRole.LAWYER, False),
])
def test_is_judge(role, expected):
    perm = IsJudge()
    request = APIRequestFactory().get('/')
    request.user = make_user(role)
    assert perm.has_permission(request, None) == expected


@pytest.mark.parametrize("role,expected", [
    (UserRole.JUDGE_CLERK, True),
    (UserRole.JUDGE, False),
    (UserRole.LAWYER, False),
])
def test_is_judge_clerk(role, expected):
    perm = IsJudgeClerk()
    request = APIRequestFactory().get('/')
    request.user = make_user(role)
    assert perm.has_permission(request, None) == expected
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
cd backend
pytest apps/assignments/tests/test_permissions.py -v
```
Expected: `ImportError: cannot import name 'IsChiefJustice'`

- [ ] **Step 4: Add three permission classes to `core/permissions.py`**

Append after the last existing permission class:

```python
class IsChiefJustice(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.CHIEF_JUSTICE
        )


class IsJudge(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.JUDGE
        )


class IsJudgeClerk(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.JUDGE_CLERK
        )
```

Make sure `UserRole` is imported at the top of `core/permissions.py` — it already imports from `apps.users.models`, so just add `UserRole` to that import.

- [ ] **Step 5: Run tests — expect PASS**

```bash
pytest apps/assignments/tests/test_permissions.py -v
```
Expected: 10 passed

- [ ] **Step 6: Commit**

```bash
git add core/permissions.py apps/assignments/tests/__init__.py apps/assignments/tests/test_permissions.py
git commit -m "feat: add IsChiefJustice, IsJudge, IsJudgeClerk permission classes"
```

---

## Task 2 — Create `apps/assignments` models (`JudgeProfile`, `CaseAssignment`)

**Files:**
- Create: `backend/apps/assignments/__init__.py`
- Create: `backend/apps/assignments/models.py`
- Create: `backend/apps/assignments/admin.py`
- Modify: `backend/config/settings/base.py`
- Test: `backend/apps/assignments/tests/test_models.py`

- [ ] **Step 1: Write failing model tests**

Create `backend/apps/assignments/tests/test_models.py`:

```python
import pytest
from django.core.exceptions import ValidationError
from apps.users.models import User, UserRole
from apps.cases.models import Case, CaseStatus, CourtTier, CaseType
from apps.assignments.models import JudgeProfile, CaseAssignment
from apps.assignments.services import get_judge_workload


@pytest.fixture
def judge_user(db):
    return User.objects.create_user(
        email='judge@judiciary.gm',
        password='testpass123',
        first_name='Fatou',
        last_name='Jallow',
        role=UserRole.JUDGE,
    )


@pytest.fixture
def cj_user(db):
    return User.objects.create_user(
        email='cj@judiciary.gm',
        password='testpass123',
        first_name='Lamin',
        last_name='Camara',
        role=UserRole.CHIEF_JUSTICE,
    )


@pytest.fixture
def judge_profile(db, judge_user):
    return JudgeProfile.objects.create(
        user=judge_user,
        court=CourtTier.HIGH,
        specialisations=[CaseType.CIVIL_CLAIM, CaseType.LAND_DISPUTE],
        max_caseload=10,
        is_available=True,
    )


@pytest.fixture
def registered_case(db):
    from apps.firms.models import LawFirm, Lawyer
    firm = LawFirm.objects.create(
        name='Test Firm',
        bar_number='GBR-001',
        address='Banjul',
        status='active',
    )
    lawyer_user = User.objects.create_user(
        email='lawyer@firm.gm',
        password='testpass',
        role=UserRole.LAWYER,
    )
    lawyer = Lawyer.objects.create(user=lawyer_user, firm=firm, bar_number='LAW-001')
    return Case.objects.create(
        title='Test Case',
        court=CourtTier.HIGH,
        case_type=CaseType.CIVIL_CLAIM,
        status=CaseStatus.REGISTERED,
        submitted_by=lawyer,
        case_number='GJ-2026-HC-00001',
    )


class TestJudgeProfile:
    def test_str(self, judge_profile, judge_user):
        assert 'Fatou Jallow' in str(judge_profile)
        assert 'high' in str(judge_profile).lower() or 'HIGH' in str(judge_profile)

    def test_active_case_count_zero_when_no_assignments(self, judge_profile):
        assert judge_profile.active_case_count() == 0

    def test_active_case_count_increments_on_assignment(self, judge_profile, registered_case, cj_user):
        CaseAssignment.objects.create(
            case=registered_case,
            judge=judge_profile.user,
            assigned_by=cj_user,
        )
        registered_case.status = CaseStatus.ASSIGNED
        registered_case.save()
        assert judge_profile.active_case_count() == 1

    def test_workload_pct_is_zero_with_no_cases(self, judge_profile):
        assert judge_profile.workload_pct() == 0.0

    def test_workload_pct_with_cases(self, judge_profile, registered_case, cj_user):
        CaseAssignment.objects.create(
            case=registered_case,
            judge=judge_profile.user,
            assigned_by=cj_user,
        )
        registered_case.status = CaseStatus.ASSIGNED
        registered_case.save()
        # 1 active / 10 max = 10%
        assert judge_profile.workload_pct() == 10.0


class TestCaseAssignment:
    def test_str(self, registered_case, judge_profile, cj_user):
        a = CaseAssignment.objects.create(
            case=registered_case,
            judge=judge_profile.user,
            assigned_by=cj_user,
        )
        assert registered_case.case_number in str(a)

    def test_one_assignment_per_case(self, registered_case, judge_profile, cj_user):
        CaseAssignment.objects.create(
            case=registered_case,
            judge=judge_profile.user,
            assigned_by=cj_user,
        )
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            CaseAssignment.objects.create(
                case=registered_case,
                judge=judge_profile.user,
                assigned_by=cj_user,
            )
```

- [ ] **Step 2: Run — expect ImportError (module doesn't exist yet)**

```bash
cd backend
pytest apps/assignments/tests/test_models.py -v
```
Expected: `ModuleNotFoundError: No module named 'apps.assignments'`

- [ ] **Step 3: Create the app package and models**

Create `backend/apps/assignments/__init__.py` (empty).

Create `backend/apps/assignments/models.py`:

```python
import uuid
from django.db import models
from apps.cases.models import CourtTier, CaseStatus


class JudgeProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='judge_profile',
        limit_choices_to={'role': 'judge'},
    )
    court = models.CharField(max_length=20, choices=CourtTier.choices)
    specialisations = models.JSONField(default=list, blank=True)
    max_caseload = models.PositiveIntegerField(default=20)
    is_available = models.BooleanField(default=True)
    admitted_at = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['user__last_name']

    def __str__(self):
        return f"Judge {self.user.get_full_name()} — {self.court}"

    def active_case_count(self):
        return CaseAssignment.objects.filter(
            judge=self.user,
            case__status__in=[
                CaseStatus.ASSIGNED,
                CaseStatus.HEARING_SCHEDULED,
                CaseStatus.ACTIVE,
                CaseStatus.JUDGMENT_PENDING,
            ],
        ).count()

    def workload_pct(self):
        if self.max_caseload == 0:
            return 100.0
        return round((self.active_case_count() / self.max_caseload) * 100, 1)


class CaseAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.OneToOneField(
        'cases.Case',
        on_delete=models.CASCADE,
        related_name='assignment',
    )
    judge = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='assigned_cases',
        limit_choices_to={'role': 'judge'},
    )
    assigned_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='case_assignments_made',
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)
    suggested_judges = models.JSONField(default=list)

    class Meta:
        ordering = ['-assigned_at']

    def __str__(self):
        return f"{self.case.case_number} → {self.judge.get_full_name()}"
```

Create `backend/apps/assignments/admin.py`:

```python
from django.contrib import admin
from .models import JudgeProfile, CaseAssignment


@admin.register(JudgeProfile)
class JudgeProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'court', 'max_caseload', 'is_available']
    list_filter = ['court', 'is_available']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']


@admin.register(CaseAssignment)
class CaseAssignmentAdmin(admin.ModelAdmin):
    list_display = ['case', 'judge', 'assigned_by', 'assigned_at']
    list_filter = ['assigned_at']
    search_fields = ['case__case_number', 'judge__email']
    readonly_fields = ['assigned_at', 'suggested_judges']
```

- [ ] **Step 4: Register app in settings and create migration**

In `backend/config/settings/base.py`, add `'apps.assignments'` to `LOCAL_APPS`:

```python
LOCAL_APPS = [
    'apps.users',
    'apps.firms',
    'apps.cases',
    'apps.documents',
    'apps.payments',
    'apps.audit',
    'apps.notifications',
    'apps.assignments',   # ← add this line
]
```

Then create the migration:

```bash
cd backend
python manage.py makemigrations assignments
python manage.py migrate
```

Expected output: `Applying assignments.0001_initial... OK`

- [ ] **Step 5: Run model tests — expect PASS**

```bash
pytest apps/assignments/tests/test_models.py -v
```
Expected: 8 passed

- [ ] **Step 6: Commit**

```bash
git add apps/assignments/ config/settings/base.py
git commit -m "feat: add JudgeProfile and CaseAssignment models"
```

---

## Task 3 — Add `REGISTERED → ASSIGNED` transition to Case state machine

**Files:**
- Modify: `backend/apps/cases/models.py`
- Test: `backend/apps/assignments/tests/test_models.py` (extend)

- [ ] **Step 1: Read the Case model transition logic**

```bash
grep -n "ALLOWED_TRANSITIONS\|transition_to" backend/apps/cases/models.py
```

Note the exact variable name and structure used.

- [ ] **Step 2: Write failing test**

Append to `backend/apps/assignments/tests/test_models.py`:

```python
class TestCaseTransitionToAssigned:
    def test_registered_can_transition_to_assigned(self, registered_case):
        registered_case.transition_to(CaseStatus.ASSIGNED)
        assert registered_case.status == CaseStatus.ASSIGNED

    def test_draft_cannot_transition_to_assigned(self, registered_case):
        registered_case.status = CaseStatus.DRAFT
        with pytest.raises(ValueError):
            registered_case.transition_to(CaseStatus.ASSIGNED)
```

- [ ] **Step 3: Run — verify test_draft_cannot_transition fails correctly and test_registered fails**

```bash
pytest apps/assignments/tests/test_models.py::TestCaseTransitionToAssigned -v
```
Expected: both fail (REGISTERED → ASSIGNED not yet in ALLOWED_TRANSITIONS)

- [ ] **Step 4: Add the transition to `apps/cases/models.py`**

Find `ALLOWED_TRANSITIONS` in `apps/cases/models.py` and add:

```python
CaseStatus.REGISTERED: [CaseStatus.ASSIGNED],
```

The ALLOWED_TRANSITIONS dict should now include this entry alongside the existing ones.

- [ ] **Step 5: Run tests — expect PASS**

```bash
pytest apps/assignments/tests/test_models.py -v
```
Expected: all pass (10 tests)

- [ ] **Step 6: Commit**

```bash
git add apps/cases/models.py apps/assignments/tests/test_models.py
git commit -m "feat: allow REGISTERED → ASSIGNED case status transition"
```

---

## Task 4 — Workload analysis service

**Files:**
- Create: `backend/apps/assignments/services.py`
- Test: `backend/apps/assignments/tests/test_services.py`

- [ ] **Step 1: Write failing service tests**

Create `backend/apps/assignments/tests/test_services.py`:

```python
import pytest
from apps.users.models import User, UserRole
from apps.cases.models import Case, CaseStatus, CourtTier, CaseType
from apps.assignments.models import JudgeProfile, CaseAssignment
from apps.assignments.services import get_judge_workload


@pytest.fixture
def two_judges(db):
    j1_user = User.objects.create_user(
        email='j1@judiciary.gm', password='pass',
        first_name='Alpha', last_name='Bah', role=UserRole.JUDGE,
    )
    j2_user = User.objects.create_user(
        email='j2@judiciary.gm', password='pass',
        first_name='Beta', last_name='Sowe', role=UserRole.JUDGE,
    )
    p1 = JudgeProfile.objects.create(
        user=j1_user, court=CourtTier.HIGH,
        specialisations=[CaseType.CIVIL_CLAIM],
        max_caseload=5, is_available=True,
    )
    p2 = JudgeProfile.objects.create(
        user=j2_user, court=CourtTier.HIGH,
        specialisations=[CaseType.CRIMINAL_COMPLAINT],
        max_caseload=5, is_available=True,
    )
    return p1, p2


@pytest.fixture
def unavailable_judge(db):
    user = User.objects.create_user(
        email='j3@judiciary.gm', password='pass',
        first_name='Gamma', last_name='Darboe', role=UserRole.JUDGE,
    )
    return JudgeProfile.objects.create(
        user=user, court=CourtTier.HIGH,
        max_caseload=5, is_available=False,
    )


class TestGetJudgeWorkload:
    def test_returns_all_available_judges(self, two_judges, unavailable_judge):
        result = get_judge_workload()
        ids = [r['judge_id'] for r in result]
        assert len([i for i in ids if i in ids]) == 2
        # unavailable judge must not appear
        assert str(unavailable_judge.user.id) not in ids

    def test_filters_by_court(self, two_judges, db):
        mag_user = User.objects.create_user(
            email='jmag@judiciary.gm', password='pass', role=UserRole.JUDGE,
        )
        JudgeProfile.objects.create(
            user=mag_user, court=CourtTier.MAGISTRATE,
            max_caseload=5, is_available=True,
        )
        result = get_judge_workload(court=CourtTier.HIGH)
        assert all(r['court'] == CourtTier.HIGH for r in result)

    def test_specialisation_match_flag(self, two_judges):
        p1, p2 = two_judges
        result = get_judge_workload(case_type=CaseType.CIVIL_CLAIM)
        result_by_id = {r['judge_id']: r for r in result}
        assert result_by_id[str(p1.user.id)]['specialisation_match'] is True
        assert result_by_id[str(p2.user.id)]['specialisation_match'] is False

    def test_sorted_specialisation_match_first(self, two_judges):
        result = get_judge_workload(case_type=CaseType.CIVIL_CLAIM)
        # p1 matches specialisation, should come first
        assert result[0]['specialisation_match'] is True

    def test_workload_pct_correct(self, two_judges, db):
        p1, p2 = two_judges
        cj = User.objects.create_user(
            email='cj@j.gm', password='pass', role=UserRole.CHIEF_JUSTICE,
        )
        from apps.firms.models import LawFirm, Lawyer
        firm = LawFirm.objects.create(name='F', bar_number='GBR-99', address='Banjul', status='active')
        lu = User.objects.create_user(email='lx@f.gm', password='pass', role=UserRole.LAWYER)
        lawyer = Lawyer.objects.create(user=lu, firm=firm, bar_number='LAW-99')

        case = Case.objects.create(
            title='C1', court=CourtTier.HIGH, case_type=CaseType.CIVIL_CLAIM,
            status=CaseStatus.ASSIGNED, submitted_by=lawyer, case_number='GJ-2026-HC-99001',
        )
        CaseAssignment.objects.create(case=case, judge=p1.user, assigned_by=cj)

        result = get_judge_workload()
        result_by_id = {r['judge_id']: r for r in result}
        # p1 has 1/5 = 20%
        assert result_by_id[str(p1.user.id)]['workload_pct'] == 20.0
        assert result_by_id[str(p2.user.id)]['workload_pct'] == 0.0

    def test_is_recommended_false_when_at_capacity(self, two_judges, db):
        p1, _ = two_judges
        cj = User.objects.create_user(
            email='cj2@j.gm', password='pass', role=UserRole.CHIEF_JUSTICE,
        )
        from apps.firms.models import LawFirm, Lawyer
        firm = LawFirm.objects.create(name='F2', bar_number='GBR-98', address='Banjul', status='active')
        lu = User.objects.create_user(email='lx2@f.gm', password='pass', role=UserRole.LAWYER)
        lawyer = Lawyer.objects.create(user=lu, firm=firm, bar_number='LAW-98')

        for i in range(5):   # fill up max_caseload=5
            case = Case.objects.create(
                title=f'C{i}', court=CourtTier.HIGH, case_type=CaseType.CIVIL_CLAIM,
                status=CaseStatus.ASSIGNED, submitted_by=lawyer,
                case_number=f'GJ-2026-HC-{i:05d}',
            )
            CaseAssignment.objects.create(case=case, judge=p1.user, assigned_by=cj)

        result = get_judge_workload()
        result_by_id = {r['judge_id']: r for r in result}
        assert result_by_id[str(p1.user.id)]['is_recommended'] is False
```

- [ ] **Step 2: Run — expect ImportError**

```bash
pytest apps/assignments/tests/test_services.py -v
```
Expected: `ImportError: cannot import name 'get_judge_workload'`

- [ ] **Step 3: Write the service**

Create `backend/apps/assignments/services.py`:

```python
from apps.assignments.models import JudgeProfile, CaseAssignment
from apps.cases.models import CaseStatus


_ACTIVE_STATUSES = [
    CaseStatus.ASSIGNED,
    CaseStatus.HEARING_SCHEDULED,
    CaseStatus.ACTIVE,
    CaseStatus.JUDGMENT_PENDING,
]


def get_judge_workload(court=None, case_type=None):
    """
    Returns a list of available judges with live workload stats.
    Sorted: specialisation-matched judges first, then by workload ascending.

    Args:
        court: CourtTier value — if given, filter to judges of that court only.
        case_type: CaseType value — if given, flag judges whose specialisations include it.

    Returns:
        list of dicts with keys:
            judge_id, judge_name, court, specialisations,
            active_cases, max_caseload, workload_pct,
            specialisation_match, is_recommended
    """
    profiles = (
        JudgeProfile.objects
        .select_related('user')
        .filter(is_available=True)
    )
    if court:
        profiles = profiles.filter(court=court)

    result = []
    for profile in profiles:
        active_count = CaseAssignment.objects.filter(
            judge=profile.user,
            case__status__in=_ACTIVE_STATUSES,
        ).count()

        specialisation_match = bool(
            case_type and profile.specialisations and case_type in profile.specialisations
        )

        workload_pct = (
            round((active_count / profile.max_caseload) * 100, 1)
            if profile.max_caseload
            else 100.0
        )

        result.append({
            'judge_id': str(profile.user.id),
            'judge_name': profile.user.get_full_name(),
            'court': profile.court,
            'specialisations': profile.specialisations,
            'active_cases': active_count,
            'max_caseload': profile.max_caseload,
            'workload_pct': workload_pct,
            'specialisation_match': specialisation_match,
            'is_recommended': active_count < profile.max_caseload,
        })

    result.sort(key=lambda j: (not j['specialisation_match'], j['workload_pct']))
    return result
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest apps/assignments/tests/test_services.py -v
```
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add apps/assignments/services.py apps/assignments/tests/test_services.py
git commit -m "feat: add judge workload analysis service"
```

---

## Task 5 — Serializers

**Files:**
- Create: `backend/apps/assignments/serializers.py`

No separate tests — serializers are validated via view tests in Task 6.

- [ ] **Step 1: Create `backend/apps/assignments/serializers.py`**

```python
from rest_framework import serializers
from apps.users.models import User, UserRole
from .models import JudgeProfile, CaseAssignment


class JudgeWorkloadSerializer(serializers.Serializer):
    judge_id = serializers.UUIDField()
    judge_name = serializers.CharField()
    court = serializers.CharField()
    specialisations = serializers.ListField(child=serializers.CharField())
    active_cases = serializers.IntegerField()
    max_caseload = serializers.IntegerField()
    workload_pct = serializers.FloatField()
    specialisation_match = serializers.BooleanField()
    is_recommended = serializers.BooleanField()


class CaseAssignSerializer(serializers.Serializer):
    judge_id = serializers.UUIDField()
    note = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_judge_id(self, value):
        try:
            user = User.objects.get(id=value, role=UserRole.JUDGE)
        except User.DoesNotExist:
            raise serializers.ValidationError('No active judge with this ID.')
        return value


class CaseAssignmentSerializer(serializers.ModelSerializer):
    judge_name = serializers.CharField(source='judge.get_full_name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True)
    case_number = serializers.CharField(source='case.case_number', read_only=True)
    case_title = serializers.CharField(source='case.title', read_only=True)

    class Meta:
        model = CaseAssignment
        fields = [
            'id', 'case_number', 'case_title',
            'judge_name', 'assigned_by_name',
            'assigned_at', 'note', 'suggested_judges',
        ]
        read_only_fields = fields
```

- [ ] **Step 2: Commit**

```bash
git add apps/assignments/serializers.py
git commit -m "feat: add assignment serializers"
```

---

## Task 6 — Views and URL wiring

**Files:**
- Create: `backend/apps/assignments/views.py`
- Create: `backend/apps/assignments/urls.py`
- Modify: `backend/config/urls.py`
- Test: `backend/apps/assignments/tests/test_views.py`

- [ ] **Step 1: Write failing view tests**

Create `backend/apps/assignments/tests/test_views.py`:

```python
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User, UserRole
from apps.cases.models import Case, CaseStatus, CourtTier, CaseType
from apps.assignments.models import JudgeProfile, CaseAssignment
from apps.firms.models import LawFirm, Lawyer


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def cj_user(db):
    return User.objects.create_user(
        email='cj@judiciary.gm', password='pass',
        first_name='Chief', last_name='Justice',
        role=UserRole.CHIEF_JUSTICE,
    )


@pytest.fixture
def judge_user(db):
    return User.objects.create_user(
        email='judge@judiciary.gm', password='pass',
        first_name='Fatou', last_name='Jallow',
        role=UserRole.JUDGE,
    )


@pytest.fixture
def judge_profile(db, judge_user):
    return JudgeProfile.objects.create(
        user=judge_user, court=CourtTier.HIGH,
        specialisations=[CaseType.CIVIL_CLAIM],
        max_caseload=10, is_available=True,
    )


@pytest.fixture
def registered_case(db):
    firm = LawFirm.objects.create(name='Firm A', bar_number='GBR-001', address='Banjul', status='active')
    lu = User.objects.create_user(email='lawyer@firm.gm', password='pass', role=UserRole.LAWYER)
    lawyer = Lawyer.objects.create(user=lu, firm=firm, bar_number='LAW-001')
    return Case.objects.create(
        title='Land Dispute v Respondent',
        court=CourtTier.HIGH,
        case_type=CaseType.CIVIL_CLAIM,
        status=CaseStatus.REGISTERED,
        submitted_by=lawyer,
        case_number='GJ-2026-HC-00001',
    )


class TestChiefJusticeQueueView:
    def test_unauthenticated_returns_401(self, api_client, registered_case):
        url = reverse('assignment-queue')
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_lawyer_returns_403(self, api_client, registered_case):
        lu = User.objects.create_user(email='lx@f.gm', password='pass', role=UserRole.LAWYER)
        api_client.force_authenticate(lu)
        url = reverse('assignment-queue')
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_cj_sees_only_registered_cases(self, api_client, cj_user, registered_case):
        api_client.force_authenticate(cj_user)
        url = reverse('assignment-queue')
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        ids = [c['id'] for c in resp.data['results']]
        assert str(registered_case.id) in ids

    def test_draft_case_not_in_queue(self, api_client, cj_user, registered_case):
        registered_case.status = CaseStatus.DRAFT
        registered_case.save()
        api_client.force_authenticate(cj_user)
        url = reverse('assignment-queue')
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        ids = [c['id'] for c in resp.data['results']]
        assert str(registered_case.id) not in ids


class TestJudgeWorkloadListView:
    def test_cj_gets_judge_list(self, api_client, cj_user, judge_profile):
        api_client.force_authenticate(cj_user)
        url = reverse('judge-workload')
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert any(j['judge_id'] == str(judge_profile.user.id) for j in resp.data)

    def test_filters_by_court(self, api_client, cj_user, judge_profile):
        api_client.force_authenticate(cj_user)
        url = reverse('judge-workload') + f'?court={CourtTier.MAGISTRATE}'
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert all(j['court'] == CourtTier.MAGISTRATE for j in resp.data)

    def test_specialisation_match_flag(self, api_client, cj_user, judge_profile):
        api_client.force_authenticate(cj_user)
        url = reverse('judge-workload') + f'?case_type={CaseType.CIVIL_CLAIM}'
        resp = api_client.get(url)
        entry = next(j for j in resp.data if j['judge_id'] == str(judge_profile.user.id))
        assert entry['specialisation_match'] is True


class TestCaseAssignView:
    def test_cj_assigns_judge(self, api_client, cj_user, judge_profile, registered_case):
        api_client.force_authenticate(cj_user)
        url = reverse('case-assign', kwargs={'case_id': registered_case.id})
        resp = api_client.post(url, {'judge_id': str(judge_profile.user.id), 'note': 'Good fit'}, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        registered_case.refresh_from_db()
        assert registered_case.status == CaseStatus.ASSIGNED
        assert CaseAssignment.objects.filter(case=registered_case).exists()

    def test_cannot_assign_non_registered_case(self, api_client, cj_user, judge_profile, registered_case):
        registered_case.status = CaseStatus.DRAFT
        registered_case.save()
        api_client.force_authenticate(cj_user)
        url = reverse('case-assign', kwargs={'case_id': registered_case.id})
        resp = api_client.post(url, {'judge_id': str(judge_profile.user.id)}, format='json')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_cannot_assign_invalid_judge_id(self, api_client, cj_user, registered_case):
        import uuid
        api_client.force_authenticate(cj_user)
        url = reverse('case-assign', kwargs={'case_id': registered_case.id})
        resp = api_client.post(url, {'judge_id': str(uuid.uuid4())}, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_lawyer_cannot_assign(self, api_client, registered_case, judge_profile):
        lu = User.objects.create_user(email='lx2@f.gm', password='pass', role=UserRole.LAWYER)
        api_client.force_authenticate(lu)
        url = reverse('case-assign', kwargs={'case_id': registered_case.id})
        resp = api_client.post(url, {'judge_id': str(judge_profile.user.id)}, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestJudgeCaseQueueView:
    def test_judge_sees_assigned_cases(self, api_client, judge_profile, registered_case, cj_user):
        CaseAssignment.objects.create(
            case=registered_case,
            judge=judge_profile.user,
            assigned_by=cj_user,
        )
        registered_case.status = CaseStatus.ASSIGNED
        registered_case.save()
        api_client.force_authenticate(judge_profile.user)
        url = reverse('judge-queue')
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        ids = [c['id'] for c in resp.data['results']]
        assert str(registered_case.id) in ids

    def test_judge_does_not_see_other_judges_cases(self, api_client, judge_profile, registered_case, cj_user, db):
        other_judge = User.objects.create_user(
            email='j2@judiciary.gm', password='pass', role=UserRole.JUDGE,
        )
        CaseAssignment.objects.create(
            case=registered_case,
            judge=other_judge,
            assigned_by=cj_user,
        )
        registered_case.status = CaseStatus.ASSIGNED
        registered_case.save()
        api_client.force_authenticate(judge_profile.user)
        url = reverse('judge-queue')
        resp = api_client.get(url)
        ids = [c['id'] for c in resp.data['results']]
        assert str(registered_case.id) not in ids
```

- [ ] **Step 2: Run — expect URL-resolution errors**

```bash
pytest apps/assignments/tests/test_views.py -v
```
Expected: `NoReverseMatch` or `ImportError` — views don't exist yet

- [ ] **Step 3: Create views**

Create `backend/apps/assignments/views.py`:

```python
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog, AuditSeverity
from apps.cases.models import Case, CaseStatus
from apps.cases.serializers import CaseListSerializer
from apps.users.models import User, UserRole
from core.permissions import IsChiefJustice, IsJudge

from .models import CaseAssignment, JudgeProfile
from .serializers import CaseAssignSerializer, CaseAssignmentSerializer, JudgeWorkloadSerializer
from .services import get_judge_workload


class ChiefJusticeQueueView(generics.ListAPIView):
    """GET /api/v1/assignments/queue/ — REGISTERED cases awaiting judge assignment."""
    serializer_class = CaseListSerializer
    permission_classes = [IsChiefJustice]

    def get_queryset(self):
        return (
            Case.objects
            .filter(status=CaseStatus.REGISTERED)
            .select_related('submitted_by__user', 'submitted_by__firm')
            .order_by('registered_at')
        )


class JudgeWorkloadListView(APIView):
    """GET /api/v1/assignments/judges/ — judge list with live workload stats."""
    permission_classes = [IsChiefJustice]

    def get(self, request):
        court = request.query_params.get('court')
        case_type = request.query_params.get('case_type')
        data = get_judge_workload(court=court, case_type=case_type)
        serializer = JudgeWorkloadSerializer(data, many=True)
        return Response(serializer.data)


class CaseAssignView(APIView):
    """POST /api/v1/assignments/cases/<case_id>/assign/ — assign a judge."""
    permission_classes = [IsChiefJustice]

    def post(self, request, case_id):
        case = get_object_or_404(Case, id=case_id, status=CaseStatus.REGISTERED)
        serializer = CaseAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        judge = get_object_or_404(
            User,
            id=serializer.validated_data['judge_id'],
            role=UserRole.JUDGE,
        )

        suggested = get_judge_workload(court=case.court, case_type=case.case_type)

        assignment = CaseAssignment.objects.create(
            case=case,
            judge=judge,
            assigned_by=request.user,
            note=serializer.validated_data.get('note', ''),
            suggested_judges=suggested,
        )

        case.transition_to(CaseStatus.ASSIGNED)
        case.save()

        AuditLog.objects.create(
            actor=request.user,
            actor_role=request.user.role,
            action=f'case_assigned:{judge.get_full_name()}',
            content_type='case',
            object_id=str(case.id),
            note=f'Assigned to Judge {judge.get_full_name()}',
            severity=AuditSeverity.INFO,
        )

        return Response(CaseAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class JudgeCaseQueueView(generics.ListAPIView):
    """GET /api/v1/assignments/judge/queue/ — judge's own assigned cases."""
    serializer_class = CaseListSerializer
    permission_classes = [IsJudge]

    def get_queryset(self):
        return (
            Case.objects
            .filter(
                assignment__judge=self.request.user,
                status__in=[
                    CaseStatus.ASSIGNED,
                    CaseStatus.HEARING_SCHEDULED,
                    CaseStatus.ACTIVE,
                    CaseStatus.JUDGMENT_PENDING,
                ],
            )
            .select_related('submitted_by__user', 'submitted_by__firm')
            .order_by('registered_at')
        )
```

- [ ] **Step 4: Create URL patterns**

Create `backend/apps/assignments/urls.py`:

```python
from django.urls import path
from .views import (
    ChiefJusticeQueueView,
    JudgeWorkloadListView,
    CaseAssignView,
    JudgeCaseQueueView,
)

urlpatterns = [
    path('queue/', ChiefJusticeQueueView.as_view(), name='assignment-queue'),
    path('judges/', JudgeWorkloadListView.as_view(), name='judge-workload'),
    path('cases/<uuid:case_id>/assign/', CaseAssignView.as_view(), name='case-assign'),
    path('judge/queue/', JudgeCaseQueueView.as_view(), name='judge-queue'),
]
```

- [ ] **Step 5: Wire into master URL conf**

In `backend/config/urls.py`, add one line to the `urlpatterns` list:

```python
path('api/v1/assignments/', include('apps.assignments.urls')),
```

- [ ] **Step 6: Run tests — expect PASS**

```bash
pytest apps/assignments/tests/test_views.py -v
```
Expected: 12 passed

- [ ] **Step 7: Run full test suite to check for regressions**

```bash
pytest --tb=short -q
```
Expected: all passing

- [ ] **Step 8: Commit**

```bash
git add apps/assignments/views.py apps/assignments/urls.py apps/assignments/serializers.py config/urls.py
git commit -m "feat: add judge assignment API endpoints"
```

---

## Task 7 — Frontend: types, API calls, routes

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/endpoints.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/layout/Sidebar.tsx`

- [ ] **Step 1: Add types to `frontend/src/types/index.ts`**

Append these interfaces:

```typescript
export interface JudgeWorkload {
  judge_id: string;
  judge_name: string;
  court: string;
  specialisations: string[];
  active_cases: number;
  max_caseload: number;
  workload_pct: number;
  specialisation_match: boolean;
  is_recommended: boolean;
}

export interface CaseAssignment {
  id: string;
  case_number: string;
  case_title: string;
  judge_name: string;
  assigned_by_name: string;
  assigned_at: string;
  note: string;
  suggested_judges: JudgeWorkload[];
}
```

- [ ] **Step 2: Add API calls to `frontend/src/api/endpoints.ts`**

Append:

```typescript
// Assignments
export const assignmentApi = {
  getQueue: () =>
    apiClient.get<PaginatedResponse<Case>>('/api/v1/assignments/queue/'),

  getJudges: (params?: { court?: string; case_type?: string }) =>
    apiClient.get<JudgeWorkload[]>('/api/v1/assignments/judges/', { params }),

  assignJudge: (caseId: string, judgeId: string, note?: string) =>
    apiClient.post<CaseAssignment>(`/api/v1/assignments/cases/${caseId}/assign/`, {
      judge_id: judgeId,
      note: note ?? '',
    }),

  getJudgeQueue: () =>
    apiClient.get<PaginatedResponse<Case>>('/api/v1/assignments/judge/queue/'),
};
```

- [ ] **Step 3: Add routes to `frontend/src/App.tsx`**

Inside the protected routes section, add:

```tsx
import AssignmentQueue from './screens/chief_justice/AssignmentQueue';
import AssignmentDetail from './screens/chief_justice/AssignmentDetail';
import JudgeDashboard from './screens/judge/JudgeDashboard';

// Inside the router:
<Route path="/assignments/queue" element={<AssignmentQueue />} />
<Route path="/assignments/cases/:caseId/assign" element={<AssignmentDetail />} />
<Route path="/judge/dashboard" element={<JudgeDashboard />} />
```

- [ ] **Step 4: Add sidebar nav items to `frontend/src/components/layout/Sidebar.tsx`**

In the nav items array, add conditional entries for chief_justice and judge roles:

```tsx
// After existing nav items, within the role-conditional section:
...(user.role === 'chief_justice' ? [
  { label: 'Assignment Queue', icon: '⚖️', path: '/assignments/queue' },
] : []),
...(user.role === 'judge' ? [
  { label: 'My Cases', icon: '📋', path: '/judge/dashboard' },
] : []),
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/endpoints.ts frontend/src/App.tsx frontend/src/components/layout/Sidebar.tsx
git commit -m "feat: add assignment API types and routes"
```

---

## Task 8 — Frontend: Chief Justice screens

**Files:**
- Create: `frontend/src/screens/chief_justice/AssignmentQueue.tsx`
- Create: `frontend/src/screens/chief_justice/AssignmentDetail.tsx`

- [ ] **Step 1: Create `AssignmentQueue.tsx`**

```tsx
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { assignmentApi } from '../../api/endpoints';
import StatusBadge from '../../components/ui/StatusBadge';
import PageLoader from '../../components/ui/Spinner';

export default function AssignmentQueue() {
  const navigate = useNavigate();
  const { data, isLoading } = useQuery({
    queryKey: ['assignment-queue'],
    queryFn: () => assignmentApi.getQueue().then(r => r.data),
  });

  if (isLoading) return <PageLoader />;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-1">Assignment Queue</h1>
      <p className="text-sm text-gray-400 mb-6">
        Registered cases awaiting judge assignment
      </p>

      {data?.results.length === 0 && (
        <p className="text-gray-400 text-sm">No cases awaiting assignment.</p>
      )}

      <div className="space-y-3">
        {data?.results.map(c => (
          <div
            key={c.id}
            className="bg-surface border border-border rounded-lg p-4 flex items-center justify-between hover:border-gold cursor-pointer transition-colors"
            onClick={() => navigate(`/assignments/cases/${c.id}/assign`)}
          >
            <div>
              <span className="font-mono text-xs text-gold">{c.case_number}</span>
              <p className="font-medium mt-0.5">{c.title}</p>
              <p className="text-xs text-muted mt-1">
                {c.court} · {c.case_type} · {c.firm_name}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <StatusBadge status={c.status} />
              <span className="text-gray-400 text-lg">→</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `AssignmentDetail.tsx`**

```tsx
import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { assignmentApi } from '../../api/endpoints';
import PageLoader from '../../components/ui/Spinner';
import type { JudgeWorkload } from '../../types';

function WorkloadBar({ pct }: { pct: number }) {
  const color = pct >= 90 ? 'bg-red' : pct >= 70 ? 'bg-amber' : 'bg-green';
  return (
    <div className="w-full bg-surface2 rounded-full h-1.5 mt-1">
      <div className={`${color} h-1.5 rounded-full`} style={{ width: `${Math.min(pct, 100)}%` }} />
    </div>
  );
}

export default function AssignmentDetail() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [selectedJudge, setSelectedJudge] = useState<string>('');
  const [note, setNote] = useState('');

  const { data: judges, isLoading: loadingJudges } = useQuery({
    queryKey: ['judges', caseId],
    queryFn: () => assignmentApi.getJudges().then(r => r.data),
    enabled: !!caseId,
  });

  const assign = useMutation({
    mutationFn: () => assignmentApi.assignJudge(caseId!, selectedJudge, note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assignment-queue'] });
      navigate('/assignments/queue');
    },
  });

  if (loadingJudges) return <PageLoader />;

  return (
    <div className="p-6 max-w-2xl">
      <button onClick={() => navigate(-1)} className="text-sm text-muted mb-4 hover:text-text">
        ← Back to queue
      </button>
      <h1 className="text-2xl font-semibold mb-1">Assign Judge</h1>
      <p className="text-sm text-gray-400 mb-6">Select a judge based on workload and specialisation.</p>

      <div className="space-y-3 mb-6">
        {judges?.map((j: JudgeWorkload) => (
          <label
            key={j.judge_id}
            className={`block border rounded-lg p-4 cursor-pointer transition-colors ${
              selectedJudge === j.judge_id
                ? 'border-gold bg-gold/5'
                : 'border-border hover:border-border2'
            }`}
          >
            <input
              type="radio"
              name="judge"
              value={j.judge_id}
              checked={selectedJudge === j.judge_id}
              onChange={() => setSelectedJudge(j.judge_id)}
              className="sr-only"
            />
            <div className="flex items-start justify-between">
              <div>
                <p className="font-medium">{j.judge_name}</p>
                <p className="text-xs text-muted mt-0.5">
                  {j.court} · {j.active_cases}/{j.max_caseload} active cases
                  {j.specialisation_match && (
                    <span className="ml-2 text-green">★ specialisation match</span>
                  )}
                </p>
                <WorkloadBar pct={j.workload_pct} />
              </div>
              <span className={`text-xs font-mono ${j.is_recommended ? 'text-green' : 'text-red'}`}>
                {j.workload_pct}%
              </span>
            </div>
          </label>
        ))}
      </div>

      <label className="block mb-4">
        <span className="text-sm text-muted">Assignment note (optional)</span>
        <textarea
          value={note}
          onChange={e => setNote(e.target.value)}
          rows={3}
          className="mt-1 w-full bg-surface2 border border-border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:border-gold"
          placeholder="Reason for this assignment…"
        />
      </label>

      <button
        disabled={!selectedJudge || assign.isPending}
        onClick={() => assign.mutate()}
        className="w-full bg-gold text-ink font-semibold py-2.5 rounded-lg disabled:opacity-40 hover:bg-gold-light transition-colors"
      >
        {assign.isPending ? 'Assigning…' : 'Confirm Assignment'}
      </button>

      {assign.isError && (
        <p className="text-red text-sm mt-2">Assignment failed. Please try again.</p>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/screens/chief_justice/
git commit -m "feat: add Chief Justice assignment queue and assignment detail screens"
```

---

## Task 9 — Frontend: Judge Dashboard screen

**Files:**
- Create: `frontend/src/screens/judge/JudgeDashboard.tsx`

- [ ] **Step 1: Create `JudgeDashboard.tsx`**

```tsx
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { assignmentApi } from '../../api/endpoints';
import StatusBadge from '../../components/ui/StatusBadge';
import PageLoader from '../../components/ui/Spinner';

export default function JudgeDashboard() {
  const navigate = useNavigate();
  const { data, isLoading } = useQuery({
    queryKey: ['judge-queue'],
    queryFn: () => assignmentApi.getJudgeQueue().then(r => r.data),
  });

  if (isLoading) return <PageLoader />;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-1">My Cases</h1>
      <p className="text-sm text-gray-400 mb-6">Cases assigned to you</p>

      <div className="grid gap-3">
        {data?.results.length === 0 && (
          <p className="text-gray-400 text-sm">No cases assigned yet.</p>
        )}
        {data?.results.map(c => (
          <div
            key={c.id}
            className="bg-surface border border-border rounded-lg p-4 flex items-center justify-between hover:border-teal cursor-pointer transition-colors"
            onClick={() => navigate(`/cases/${c.id}`)}
          >
            <div>
              <span className="font-mono text-xs text-teal">{c.case_number}</span>
              <p className="font-medium mt-0.5">{c.title}</p>
              <p className="text-xs text-muted mt-1">
                {c.court} · {c.case_type}
              </p>
            </div>
            <StatusBadge status={c.status} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/screens/judge/
git commit -m "feat: add Judge Dashboard screen"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Step 6: Workload analysis — `services.py` + `JudgeWorkloadListView`
- [x] Step 7: Chief Justice case assignment — `CaseAssignView` + `AssignmentQueue` + `AssignmentDetail`
- [x] Judge case queue — `JudgeCaseQueueView` + `JudgeDashboard`
- [x] Audit log on assignment — written in `CaseAssignView`
- [x] State machine transition REGISTERED → ASSIGNED — Task 3
- [x] Workload sorted by specialisation match then load — `services.py`

**Placeholder scan:** None — all code blocks are complete.

**Type consistency:**
- `JudgeWorkload.judge_id` (UUID string) used consistently in service, serializer, and frontend type
- `CaseAssignment.id` returned from POST 201 response
- `get_full_name()` used throughout (matches Django's User method)

---

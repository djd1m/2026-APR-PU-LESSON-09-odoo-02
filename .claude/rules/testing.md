# Testing Rules — СтройУправ

## Strategy

| Layer | Tool | Coverage Target | Focus |
|-------|------|:---------------:|-------|
| Unit (backend) | pytest | 80% | Estimate calculations, business logic |
| Unit (frontend) | Vitest | 70% | Components, hooks |
| Integration | pytest + testcontainers | Key flows | AI provider, ЮKassa webhook, DB |
| E2E | Playwright | Critical paths | Onboarding, estimate, billing |
| AI Accuracy | Custom benchmark | 50-case dataset | Estimate precision vs manual |

## Test Naming

```python
# Pattern: test_<what>_<scenario>_<expected>
def test_estimate_valid_input_returns_gesn_items():
def test_estimate_empty_description_raises_400():
def test_budget_deviation_above_15pct_triggers_alert():
```

## Fixtures

```python
# conftest.py — shared fixtures
@pytest.fixture
def project_factory(db_session):
    """Create test project with default values."""

@pytest.fixture
def ai_client_mock():
    """Mock OpenAI-compatible client (no real API calls in unit tests)."""

@pytest.fixture
def gesn_rates():
    """Load test ГЭСН rates from fixtures/gesn_test_rates.csv."""
```

## Rules

### ALWAYS
- Write tests BEFORE marking a feature as done
- Mock AI providers in unit tests (use `vcrpy` cassettes for integration)
- Test tenant isolation: verify user A cannot access user B's data
- Test RBAC: verify foreman cannot access admin endpoints
- Test with Russian text (UTF-8 edge cases in project names, estimate descriptions)
- Run `pytest` before every commit

### NEVER
- Skip tests to save time
- Use production AI API keys in tests
- Write tests that depend on execution order
- Mock the database in integration tests (use testcontainers PostgreSQL)

## AI Accuracy Testing

```python
# Nightly benchmark: compare AI estimates vs manual
class TestAIAccuracy:
    @pytest.fixture
    def benchmark_dataset(self):
        """50 real estimates with known correct values."""
        return load_csv("tests/fixtures/benchmark_estimates.csv")

    def test_total_cost_within_20pct(self, benchmark_dataset):
        """AI estimate total must be within ±20% of manual estimate."""
        for case in benchmark_dataset:
            ai_result = generate_estimate(case.description)
            assert abs(ai_result.total - case.expected_total) / case.expected_total < 0.20

    def test_gesn_codes_match_rate_above_80pct(self, benchmark_dataset):
        """At least 80% of ГЭСН codes must match manual selection."""
```

## E2E Critical Paths (Playwright)

1. Registration → Onboarding quiz → First project created
2. Create estimate → Export PDF → Verify ГЭСН codes present
3. Create task → Assign brigade → Upload photo → Check progress
4. Trial expiration → Paywall → ЮKassa payment → Access restored
5. Invite subcontractor → They register → See shared project

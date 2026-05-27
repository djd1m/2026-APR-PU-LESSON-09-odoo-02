# Pseudocode: СтройУправ

Алгоритмы и data flows ключевых подсистем MVP.
Нотация: Python-like pseudocode, domain terms на русском, technical terms на английском.

---

## 1. AI Estimator Algorithm (AI-сметчик)

Основной flow: текстовое описание работ --> парсинг --> поиск по ГЭСН/ФЕР --> расчёт --> оптимизация.

```python
# =============================================================================
# AI-СМЕТЧИК: Главный pipeline
# Input:  описание работ (текст или чертёж PDF/фото)
# Output: структурированная смета с расценками ГЭСН/ФЕР + оптимизации
# SLA:    < 60 сек для объекта до 200 м²
# =============================================================================

function generate_estimate(input: EstimateRequest) -> Estimate:
    # --- STEP 1: Input parsing ---
    if input.type == "text":
        parsed = parse_text_description(input.text)
    elif input.type == "drawing":
        # OCR через Qwen3-VL (Cloud.ru) или GPT-4o (fallback)
        image_data = extract_image(input.file)
        parsed = ai_vision_parse(image_data)
        # parsed содержит: помещения, площади, виды работ
        # Accuracy target: >= 85% для площадей
    else:
        raise InvalidInputError("Поддерживаются текст и чертёж")

    # --- STEP 2: Нормализация и классификация работ ---
    work_items = []
    for raw_item in parsed.work_descriptions:
        # AI классифицирует описание в стандартные виды работ
        classified = ai_classify_work(
            description=raw_item,
            model="qwen3-coder-480b",      # Cloud.ru primary
            fallback_model="gpt-4o"         # OpenAI fallback
        )
        work_items.append(WorkItem(
            description=raw_item,
            work_type=classified.type,       # e.g. "электромонтаж", "штукатурка"
            unit=classified.unit,            # e.g. "м²", "м.п.", "шт"
            quantity=classified.quantity,     # распознанный объём
            confidence=classified.confidence
        ))

    # --- STEP 3: ГЭСН/ФЕР lookup ---
    estimate_lines = []
    for item in work_items:
        # Семантический поиск по векторной базе ГЭСН/ФЕР
        # Используем Cloud.ru Managed RAG + bge-reranker-v2-m3
        candidates = rag_search(
            query=f"{item.work_type} {item.description}",
            collection="gesn_fer_database",
            top_k=5,
            min_score=0.7
        )

        if not candidates:
            # Fallback: полнотекстовый поиск по Elasticsearch
            candidates = fulltext_search(
                query=item.work_type,
                index="gesn_fer",
                top_k=5
            )

        best_match = candidates[0]  # highest relevance score

        # Получаем актуальный индекс Минстроя (квартальное обновление)
        current_index = get_minstroy_index(
            region=input.region,
            work_category=best_match.category,
            quarter=current_quarter()
        )

        # --- STEP 4: Расчёт стоимости ---
        base_cost = best_match.base_rate * item.quantity
        indexed_cost = base_cost * current_index.coefficient
        # Накладные расходы и сметная прибыль по нормативу
        overhead = indexed_cost * best_match.overhead_rate      # накладные
        profit = indexed_cost * best_match.profit_rate          # сметная прибыль
        total = indexed_cost + overhead + profit

        estimate_lines.append(EstimateLine(
            gesn_code=best_match.code,           # e.g. "ГЭСНр 61-01-001-01"
            description=best_match.description,
            unit=item.unit,
            quantity=item.quantity,
            base_rate=best_match.base_rate,
            index=current_index.coefficient,
            cost=total,
            source_confidence=item.confidence,
            match_score=best_match.relevance_score
        ))

    # --- STEP 5: AI-оптимизация ---
    suggestions = generate_optimization_suggestions(estimate_lines)

    estimate = Estimate(
        project=input.project_name,
        region=input.region,
        lines=estimate_lines,
        total=sum(line.cost for line in estimate_lines),
        nds=sum(line.cost for line in estimate_lines) * 0.20,  # НДС 20%
        grand_total=total_with_nds,
        suggestions=suggestions,
        created_at=now(),
        accuracy_disclaimer="Предварительная оценка. Требуется проверка сметчика."
    )

    # Сохраняем для data flywheel (обучение модели)
    save_estimate_for_training(estimate, input)

    return estimate


# =============================================================================
# AI-оптимизация: подсказки по снижению стоимости
# =============================================================================

function generate_optimization_suggestions(lines: List[EstimateLine]) -> List[Suggestion]:
    suggestions = []

    for line in lines:
        # Сравнение с рыночными бенчмарками
        market_avg = get_market_benchmark(line.gesn_code, line.region)

        if market_avg and line.cost / line.quantity > market_avg * 1.10:
            # Цена > 10% выше среднерыночной
            deviation_pct = ((line.cost / line.quantity) / market_avg - 1) * 100
            suggestions.append(Suggestion(
                type="OVERPRICED",
                line=line,
                message=f"{line.description}: на {deviation_pct:.0f}% дороже рынка",
                potential_savings=(line.cost / line.quantity - market_avg) * line.quantity
            ))

        # Альтернативные расценки (ФЕР вместо ГЭСН или наоборот)
        alternatives = find_alternative_rates(line.gesn_code)
        for alt in alternatives:
            if alt.total_cost < line.cost * 0.90:  # экономия > 10%
                suggestions.append(Suggestion(
                    type="ALTERNATIVE",
                    line=line,
                    message=f"Альтернатива: {alt.code} — экономия {line.cost - alt.total_cost:.0f} ₽",
                    potential_savings=line.cost - alt.total_cost
                ))

    # Сортируем по потенциальной экономии (descending)
    suggestions.sort(key=lambda s: s.potential_savings, reverse=True)
    return suggestions[:10]  # top-10 рекомендаций
```

---

## 2. Project Dashboard Data Flow

Агрегация данных из задач, фото, бюджета в единый dashboard.

```python
# =============================================================================
# DASHBOARD: Aggregation pipeline
# SLA: < 2 сек (P95) для загрузки
# Стратегия: materialized views + кэш Redis, обновление event-driven
# =============================================================================

# --- Модель данных (упрощённая) ---

class Project:
    id: int
    name: str
    address: str
    status: enum(ACTIVE, PAUSED, COMPLETED, ARCHIVED)
    planned_start: date
    planned_end: date
    budget_plan: Decimal            # плановый бюджет
    company_id: int
    manager_id: int                 # ответственный менеджер

class DashboardCard:
    project: Project
    progress_pct: float             # 0-100
    budget_fact: Decimal
    budget_plan: Decimal
    budget_deviation_pct: float
    health: enum(GREEN, YELLOW, RED)
    tasks_total: int
    tasks_done: int
    overdue_tasks: int
    last_photo: Photo               # последнее фото
    last_activity: datetime
    alerts: List[Alert]


# --- Агрегационный pipeline ---

function build_dashboard(user: User, filters: DashboardFilters) -> Dashboard:
    # Шаг 1: Получаем проекты пользователя (с учётом роли)
    projects = get_user_projects(user, filters)
    # admin  -> все проекты компании
    # manager -> свои проекты
    # foreman -> назначенные проекты
    # client  -> проекты, где он заказчик (view-only)

    cards = []
    for project in projects:
        # Шаг 2: Агрегация задач (из materialized view)
        task_stats = cache.get(f"task_stats:{project.id}")
        if not task_stats:
            task_stats = db.query("""
                SELECT
                    count(*)                              AS total,
                    count(*) FILTER (WHERE state = 'done') AS done,
                    count(*) FILTER (WHERE deadline < NOW()
                        AND state NOT IN ('done','cancelled')) AS overdue
                FROM project_task
                WHERE project_id = :pid
            """, pid=project.id)
            cache.set(f"task_stats:{project.id}", task_stats, ttl=300)

        # Шаг 3: Прогресс (взвешенный по трудоёмкости)
        progress = calculate_progress(project.id)

        # Шаг 4: Бюджет факт vs план
        budget = get_budget_summary(project.id)

        # Шаг 5: Health score
        health = determine_health(
            progress=progress,
            budget_deviation=budget.deviation_pct,
            overdue_count=task_stats.overdue,
            days_remaining=project.days_remaining
        )

        # Шаг 6: AI-алерты
        alerts = get_active_alerts(project.id)

        # Шаг 7: Последняя активность
        last_photo = get_latest_photo(project.id)

        cards.append(DashboardCard(
            project=project,
            progress_pct=progress,
            budget_fact=budget.fact,
            budget_plan=budget.plan,
            budget_deviation_pct=budget.deviation_pct,
            health=health,
            tasks_total=task_stats.total,
            tasks_done=task_stats.done,
            overdue_tasks=task_stats.overdue,
            last_photo=last_photo,
            last_activity=max(last_photo.created_at, task_stats.last_update),
            alerts=alerts
        ))

    # Сортировка: RED первыми, потом YELLOW, потом GREEN
    cards.sort(key=lambda c: {"RED": 0, "YELLOW": 1, "GREEN": 2}[c.health])

    return Dashboard(
        cards=cards,
        summary=DashboardSummary(
            total_projects=len(cards),
            total_budget_plan=sum(c.budget_plan for c in cards),
            total_budget_fact=sum(c.budget_fact for c in cards),
            avg_progress=mean(c.progress_pct for c in cards),
            alerts_count=sum(len(c.alerts) for c in cards)
        )
    )


function calculate_progress(project_id: int) -> float:
    """Взвешенный прогресс: weight = плановая трудоёмкость задачи."""
    tasks = db.query("""
        SELECT planned_hours, actual_progress
        FROM project_task
        WHERE project_id = :pid AND state != 'cancelled'
    """, pid=project_id)

    if not tasks:
        return 0.0

    total_weight = sum(t.planned_hours or 1 for t in tasks)
    weighted_progress = sum(
        (t.planned_hours or 1) * (t.actual_progress or 0)
        for t in tasks
    )
    return (weighted_progress / total_weight) * 100


function determine_health(progress, budget_deviation, overdue_count, days_remaining) -> str:
    """
    RED:    бюджет > +15% ИЛИ просрочено > 3 задач ИЛИ прогресс отстаёт > 20%
    YELLOW: бюджет +5..+15% ИЛИ просрочено 1-3 ИЛИ прогресс отстаёт 10-20%
    GREEN:  всё в норме
    """
    if budget_deviation > 15 or overdue_count > 3:
        return "RED"
    if budget_deviation > 5 or overdue_count >= 1:
        return "YELLOW"
    return "GREEN"
```

---

## 3. Task Management State Machine

```python
# =============================================================================
# TASK STATE MACHINE
# States:  новая -> в_работе -> на_проверке -> выполнена
#          любое -> отменена (кроме выполнена)
# =============================================================================

TASK_STATES = {
    "new":        "Новая",
    "in_progress": "В работе",
    "review":     "На проверке",
    "done":       "Выполнена",
    "cancelled":  "Отменена"
}

# Допустимые переходы: state -> [allowed next states]
TRANSITIONS = {
    "new":         ["in_progress", "cancelled"],
    "in_progress": ["review", "new", "cancelled"],       # можно вернуть
    "review":      ["done", "in_progress", "cancelled"],  # можно отклонить
    "done":        [],                                     # финальное
    "cancelled":   ["new"]                                 # можно реактивировать
}

# Кто может выполнять переходы
TRANSITION_PERMISSIONS = {
    ("new", "in_progress"):       ["foreman", "manager", "admin"],
    ("in_progress", "review"):    ["foreman", "manager", "admin"],
    ("in_progress", "new"):       ["manager", "admin"],
    ("review", "done"):           ["manager", "admin"],         # только руководство
    ("review", "in_progress"):    ["manager", "admin"],         # отклонение
    ("*", "cancelled"):           ["manager", "admin"],
    ("cancelled", "new"):         ["manager", "admin"],
}


function transition_task(task: Task, new_state: str, user: User, comment: str = None):
    old_state = task.state

    # Валидация перехода
    if new_state not in TRANSITIONS[old_state]:
        raise InvalidTransitionError(
            f"Переход {old_state} -> {new_state} запрещён"
        )

    # Проверка прав
    permission_key = (old_state, new_state)
    if permission_key not in TRANSITION_PERMISSIONS:
        permission_key = ("*", new_state)
    allowed_roles = TRANSITION_PERMISSIONS.get(permission_key, [])
    if user.role not in allowed_roles:
        raise PermissionDeniedError(
            f"Роль {user.role} не может выполнить {old_state} -> {new_state}"
        )

    # Выполняем переход
    task.state = new_state
    task.updated_at = now()
    task.updated_by = user.id

    # Логируем в историю
    TaskHistory.create(
        task_id=task.id,
        old_state=old_state,
        new_state=new_state,
        user_id=user.id,
        comment=comment,
        timestamp=now()
    )

    # --- Побочные эффекты (side effects) ---

    if new_state == "in_progress":
        # Уведомляем бригаду
        notify_crew(task.crew_id, NotificationType.TASK_STARTED, task)

    elif new_state == "review":
        # Уведомляем менеджера проекта
        notify_user(task.project.manager_id, NotificationType.TASK_READY_FOR_REVIEW, task)

    elif new_state == "done":
        # 1) Пересчитываем прогресс проекта
        recalculate_project_progress(task.project_id)
        # 2) Уведомляем заказчика (если есть портал)
        notify_client_portal(task.project_id, NotificationType.TASK_COMPLETED, task)
        # 3) Проверяем зависимые задачи — разблокируем
        unblock_dependent_tasks(task.id)
        # 4) Обновляем бюджет (факт)
        update_budget_fact(task)

    elif new_state == "cancelled":
        # Освобождаем ресурсы бригады
        release_crew_assignment(task)

    db.commit()


function unblock_dependent_tasks(completed_task_id: int):
    """Проверяем задачи, зависящие от завершённой. Если все зависимости
    выполнены — переводим из blocked в new."""
    dependents = db.query("""
        SELECT task_id FROM task_dependency
        WHERE depends_on_id = :tid
    """, tid=completed_task_id)

    for dep in dependents:
        task = Task.get(dep.task_id)
        all_deps_done = db.query("""
            SELECT bool_and(t.state = 'done')
            FROM task_dependency td
            JOIN project_task t ON t.id = td.depends_on_id
            WHERE td.task_id = :tid
        """, tid=task.id)

        if all_deps_done:
            task.is_blocked = False
            notify_crew(task.crew_id, NotificationType.TASK_UNBLOCKED, task)
```

---

## 4. Photo Processing Pipeline

```python
# =============================================================================
# ФОТОФИКСАЦИЯ: Upload -> geotag -> link to task -> progress update
# Storage: S3-compatible (MinIO)
# Offline: фото сохраняются локально в PWA, sync при подключении
# =============================================================================

function upload_photo(request: PhotoUploadRequest, user: User) -> Photo:
    file = request.file
    task_id = request.task_id

    # --- STEP 1: Валидация ---
    validate_file(file, max_size_mb=20, allowed_types=["image/jpeg", "image/png", "image/heic"])
    task = Task.get(task_id)
    assert_user_has_access(user, task.project_id)

    # --- STEP 2: Извлечение метаданных ---
    exif = extract_exif(file)
    geotag = GeoTag(
        latitude=exif.gps_latitude or request.latitude,     # из EXIF или из запроса
        longitude=exif.gps_longitude or request.longitude,
        accuracy=exif.gps_accuracy or request.gps_accuracy
    )
    timestamp = exif.datetime_original or request.timestamp or now()

    # --- STEP 3: Валидация геолокации ---
    if geotag.latitude and task.project.address_coordinates:
        distance = haversine(geotag, task.project.address_coordinates)
        if distance > 500:  # метров
            geotag.warning = f"Фото сделано в {distance:.0f}м от объекта"
            # Не блокируем, но помечаем

    # --- STEP 4: Обработка изображения ---
    # Генерация thumbnail (async через Celery)
    thumbnail_task = celery.send_task("generate_thumbnail", args=[file], kwargs={
        "sizes": [(150, 150), (400, 400), (800, 800)]
    })

    # --- STEP 5: Upload в S3 ---
    s3_key = f"projects/{task.project_id}/photos/{uuid4()}.{file.extension}"
    s3.upload(
        bucket="stroyuprav-photos",
        key=s3_key,
        body=file.content,
        content_type=file.content_type,
        metadata={
            "project_id": str(task.project_id),
            "task_id": str(task_id),
            "user_id": str(user.id),
            "geotag": json.dumps(geotag.to_dict()),
            "timestamp": timestamp.isoformat()
        }
    )

    # --- STEP 6: Сохраняем в БД ---
    photo = Photo.create(
        task_id=task_id,
        project_id=task.project_id,
        user_id=user.id,
        s3_key=s3_key,
        geotag=geotag,
        taken_at=timestamp,
        uploaded_at=now(),
        thumbnails={}  # заполнится после async обработки
    )

    # --- STEP 7: Обновление прогресса задачи ---
    update_task_progress_from_photos(task)

    # --- STEP 8: Уведомления ---
    if task.project.client_portal_enabled:
        notify_client_portal(
            task.project_id,
            NotificationType.NEW_PHOTO,
            {"task": task.name, "photo_url": photo.thumbnail_url}
        )

    return photo


function update_task_progress_from_photos(task: Task):
    """
    Эвристика: количество фотоотчётов коррелирует с прогрессом.
    Не заменяет ручное обновление, но даёт baseline.
    """
    photo_count = Photo.count(task_id=task.id)
    expected_photos = task.expected_photo_count or 5  # по умолчанию 5 фото на задачу

    # Photo-based progress (макс 80% — финальные 20% за ручное подтверждение)
    photo_progress = min(photo_count / expected_photos, 0.80) * 100

    # Берём максимум между текущим прогрессом и photo-based
    if photo_progress > task.actual_progress:
        task.actual_progress = photo_progress
        task.progress_source = "auto_photo"
        recalculate_project_progress(task.project_id)


# --- OFFLINE SYNC (PWA Service Worker) ---

# На клиенте (JavaScript pseudocode):
function sync_offline_photos():
    """Вызывается при восстановлении подключения к интернету."""
    pending = IndexedDB.getAll("pending_photos")

    for photo_data in pending:
        try:
            response = api.post("/photos/upload", body=photo_data)
            if response.ok:
                IndexedDB.delete("pending_photos", photo_data.local_id)
        except NetworkError:
            break  # вернёмся при следующем sync
```

---

## 5. Budget Control Algorithm

```python
# =============================================================================
# БЮДЖЕТ: Факт vs План, отклонения, AI-алерты
# Обновляется при: добавлении расходов, закрытии задач, пересчёте индексов
# =============================================================================

class BudgetCategory:
    MATERIALS = "materials"       # материалы
    LABOR = "labor"               # работы (ФОТ бригад)
    EQUIPMENT = "equipment"       # техника/оборудование
    OVERHEAD = "overhead"         # накладные
    OTHER = "other"

class BudgetEntry:
    project_id: int
    category: BudgetCategory
    description: str
    planned: Decimal              # из сметы
    actual: Decimal               # факт (из expenses)
    task_id: int                  # привязка к задаче (optional)


function calculate_budget_summary(project_id: int) -> BudgetSummary:
    """Факт vs План с разбивкой по категориям."""

    # Плановый бюджет — из последней утверждённой сметы
    plan_lines = db.query("""
        SELECT category, SUM(amount) as total
        FROM estimate_line el
        JOIN estimate e ON e.id = el.estimate_id
        WHERE e.project_id = :pid AND e.status = 'approved'
        GROUP BY category
    """, pid=project_id)

    # Фактические расходы — из проведённых документов
    fact_lines = db.query("""
        SELECT category, SUM(amount) as total
        FROM expense
        WHERE project_id = :pid AND status = 'confirmed'
        GROUP BY category
    """, pid=project_id)

    plan_by_cat = {row.category: row.total for row in plan_lines}
    fact_by_cat = {row.category: row.total for row in fact_lines}
    all_categories = set(plan_by_cat.keys()) | set(fact_by_cat.keys())

    breakdowns = []
    total_plan = Decimal(0)
    total_fact = Decimal(0)

    for cat in all_categories:
        plan = plan_by_cat.get(cat, Decimal(0))
        fact = fact_by_cat.get(cat, Decimal(0))
        deviation = fact - plan
        deviation_pct = (deviation / plan * 100) if plan > 0 else None

        breakdowns.append(BudgetBreakdown(
            category=cat,
            plan=plan,
            fact=fact,
            deviation=deviation,
            deviation_pct=deviation_pct
        ))
        total_plan += plan
        total_fact += fact

    total_deviation = total_fact - total_plan
    total_deviation_pct = (total_deviation / total_plan * 100) if total_plan > 0 else 0

    return BudgetSummary(
        project_id=project_id,
        plan=total_plan,
        fact=total_fact,
        deviation=total_deviation,
        deviation_pct=total_deviation_pct,
        breakdowns=breakdowns,
        calculated_at=now()
    )


function check_budget_alerts(project_id: int):
    """Проверяем отклонения и генерируем алерты."""
    summary = calculate_budget_summary(project_id)

    # Глобальное отклонение
    if summary.deviation_pct > 15:
        create_alert(
            project_id=project_id,
            severity="critical",
            type="BUDGET_OVERRUN",
            message=f"Бюджет превышен на {summary.deviation_pct:.1f}% "
                    f"(+{summary.deviation:,.0f} ₽)",
            notify_roles=["admin", "manager"]
        )
    elif summary.deviation_pct > 5:
        create_alert(
            project_id=project_id,
            severity="warning",
            type="BUDGET_WARNING",
            message=f"Внимание: отклонение бюджета {summary.deviation_pct:.1f}%",
            notify_roles=["manager"]
        )

    # По категориям
    for bd in summary.breakdowns:
        if bd.deviation_pct and bd.deviation_pct > 20:
            create_alert(
                project_id=project_id,
                severity="warning",
                type="CATEGORY_OVERRUN",
                message=f"Категория «{CATEGORY_NAMES[bd.category]}»: "
                        f"+{bd.deviation_pct:.0f}% ({bd.deviation:,.0f} ₽)",
                notify_roles=["manager"]
            )

    # AI-прогноз: экстраполяция на основе текущего темпа расходов
    forecast = forecast_budget_completion(project_id, summary)
    if forecast.projected_total > summary.plan * 1.10:
        create_alert(
            project_id=project_id,
            severity="info",
            type="BUDGET_FORECAST",
            message=f"AI-прогноз: при текущем темпе итоговые расходы составят "
                    f"{forecast.projected_total:,.0f} ₽ (план: {summary.plan:,.0f} ₽)",
            notify_roles=["admin", "manager"]
        )


function forecast_budget_completion(project_id, summary) -> BudgetForecast:
    """Линейная экстраполяция факта на основе прогресса проекта."""
    progress = calculate_progress(project_id)  # 0-100

    if progress < 5:
        return BudgetForecast(projected_total=summary.plan, confidence=0.2)

    # Факт / прогресс = расход на 1% прогресса -> экстраполируем на 100%
    cost_per_pct = summary.fact / progress
    projected_total = cost_per_pct * 100
    # Confidence растёт с прогрессом
    confidence = min(progress / 100, 0.9)

    return BudgetForecast(
        projected_total=projected_total,
        confidence=confidence,
        burn_rate_per_day=summary.fact / max(project_elapsed_days(project_id), 1)
    )
```

---

## 6. Auth Flow

```python
# =============================================================================
# AUTH: JWT + Refresh Tokens + RBAC
# Tokens: httpOnly cookies (НЕ localStorage — Phase 4 security finding)
# =============================================================================

ROLES = {
    "admin":   {"level": 100, "description": "Руководитель компании"},
    "manager": {"level": 70,  "description": "Менеджер проекта"},
    "foreman": {"level": 40,  "description": "Прораб / бригадир"},
    "client":  {"level": 10,  "description": "Заказчик (view-only)"}
}

ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)


function register(request: RegisterRequest) -> AuthResponse:
    # Валидация
    validate_email(request.email)
    validate_password(request.password)  # min 8 chars, complexity check

    # Проверяем уникальность
    if User.exists(email=request.email):
        raise ConflictError("Email уже зарегистрирован")

    # Создаём пользователя
    user = User.create(
        email=request.email,
        password_hash=bcrypt.hash(request.password, rounds=12),
        name=request.name,
        phone=request.phone,
        role="admin",           # первый в компании = admin
        company=Company.create(name=request.company_name),
        email_verified=False
    )

    # ВАЖНО: НЕ назначаем роль из request — только admin по умолчанию
    # (Phase 4 finding: privilege escalation через register endpoint)

    # Создаём trial подписку
    Subscription.create(
        company_id=user.company_id,
        plan="trial",
        started_at=now(),
        expires_at=now() + timedelta(days=14)
    )

    # Отправляем email подтверждение
    send_verification_email(user)

    # Выдаём токены
    return issue_tokens(user)


function login(request: LoginRequest) -> AuthResponse:
    user = User.get_by_email(request.email)
    if not user or not bcrypt.verify(request.password, user.password_hash):
        # Не раскрываем, что именно неверно
        raise AuthError("Неверный email или пароль")

    if user.is_locked:
        raise AuthError("Аккаунт заблокирован. Обратитесь в поддержку.")

    # Сбрасываем счётчик неудачных попыток
    user.failed_login_attempts = 0
    user.last_login = now()

    return issue_tokens(user)


function issue_tokens(user: User) -> AuthResponse:
    """Генерируем JWT access + refresh token."""

    access_token = jwt.encode(
        payload={
            "sub": str(user.id),
            "role": user.role,
            "company_id": str(user.company_id),
            "exp": now() + ACCESS_TOKEN_TTL,
            "iat": now(),
            "type": "access"
        },
        key=env("JWT_SECRET"),           # ОБЯЗАТЕЛЬНО из env, НЕ hardcoded
        algorithm="HS256"
    )

    refresh_token = generate_secure_random(64)  # opaque token, НЕ JWT
    RefreshToken.create(
        token_hash=sha256(refresh_token),   # храним хэш, не plain
        user_id=user.id,
        expires_at=now() + REFRESH_TOKEN_TTL,
        device_info=request.user_agent
    )

    response = AuthResponse(user=user.to_public())
    # Токены — ТОЛЬКО в httpOnly cookies
    response.set_cookie("access_token", access_token,
        httponly=True, secure=True, samesite="Strict",
        max_age=ACCESS_TOKEN_TTL.total_seconds())
    response.set_cookie("refresh_token", refresh_token,
        httponly=True, secure=True, samesite="Strict",
        path="/api/auth/refresh",           # ограничиваем path
        max_age=REFRESH_TOKEN_TTL.total_seconds())

    return response


function refresh_tokens(request: Request) -> AuthResponse:
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise AuthError("Refresh token отсутствует")

    stored = RefreshToken.get_by_hash(sha256(refresh_token))
    if not stored or stored.expires_at < now() or stored.revoked:
        raise AuthError("Refresh token невалиден или истёк")

    # Ротация: старый refresh token отзываем, выдаём новый
    stored.revoked = True
    stored.revoked_at = now()

    user = User.get(stored.user_id)
    return issue_tokens(user)


# --- Middleware: проверка доступа ---

function require_auth(min_role: str = None):
    """Декоратор для защищённых эндпоинтов."""
    def middleware(request):
        token = request.cookies.get("access_token")
        if not token:
            raise AuthError("Не авторизован", status=401)

        try:
            payload = jwt.decode(token, key=env("JWT_SECRET"), algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise AuthError("Токен истёк", status=401)
        except jwt.InvalidTokenError:
            raise AuthError("Невалидный токен", status=401)

        if payload["type"] != "access":
            raise AuthError("Неверный тип токена", status=401)

        user = User.get(payload["sub"])

        if min_role and ROLES[user.role]["level"] < ROLES[min_role]["level"]:
            raise AuthError("Недостаточно прав", status=403)

        request.user = user
        return next(request)
    return middleware
```

---

## 7. Billing Pipeline

```python
# =============================================================================
# BILLING: Trial -> Подписка -> ЮKassa рекуррентные платежи
# Trial: 14 дней, автоматическое напоминание на 12-й день
# =============================================================================

PLANS = {
    "free":         {"price_monthly": 0,      "objects": 1,  "ai_estimates": 3},
    "brigadir":     {"price_monthly": 2990,    "objects": 5,  "ai_estimates": 20},
    "company":      {"price_monthly": 9900,    "objects": 20, "ai_estimates": 100},
    "general":      {"price_monthly": 29900,   "objects": 999, "ai_estimates": 999},
    "enterprise":   {"price_monthly": 49900,   "objects": 999, "ai_estimates": 999},
}

ANNUAL_DISCOUNT = 0.20  # 20% скидка при годовой оплате


# --- Trial lifecycle ---

function check_trial_expiry():
    """Cron job: ежедневно проверяет trial подписки."""
    # День 12: напоминание
    expiring_soon = Subscription.query(
        plan="trial",
        expires_at__between=(now() + timedelta(days=1), now() + timedelta(days=3))
    )
    for sub in expiring_soon:
        notify_user(sub.company.admin_id, NotificationType.TRIAL_EXPIRING,
            {"days_left": (sub.expires_at - now()).days})

    # Истёкшие: переводим на free
    expired = Subscription.query(plan="trial", expires_at__lt=now())
    for sub in expired:
        sub.plan = "free"
        sub.trial_expired = True
        db.commit()
        notify_user(sub.company.admin_id, NotificationType.TRIAL_EXPIRED)

        # Если > 1 объекта — замораживаем лишние
        projects = Project.query(company_id=sub.company_id, status="ACTIVE")
        if len(projects) > PLANS["free"]["objects"]:
            for p in projects[1:]:  # оставляем только первый
                p.status = "FROZEN"
            notify_user(sub.company.admin_id, NotificationType.PROJECTS_FROZEN)


# --- Subscription upgrade/downgrade ---

function change_plan(company_id: int, new_plan: str, billing_cycle: str) -> Subscription:
    sub = Subscription.get(company_id=company_id)
    old_plan = sub.plan

    # Проверяем лимиты нового плана
    active_projects = Project.count(company_id=company_id, status="ACTIVE")
    if active_projects > PLANS[new_plan]["objects"]:
        raise PlanLimitError(
            f"У вас {active_projects} объектов, план «{new_plan}» "
            f"позволяет {PLANS[new_plan]['objects']}"
        )

    price = PLANS[new_plan]["price_monthly"]
    if billing_cycle == "annual":
        price = price * 12 * (1 - ANNUAL_DISCOUNT)
        period = timedelta(days=365)
    else:
        period = timedelta(days=30)

    if new_plan == "free":
        # Отменяем рекуррент в ЮKassa
        if sub.yukassa_subscription_id:
            yukassa.cancel_recurring(sub.yukassa_subscription_id)
        sub.plan = "free"
        sub.next_payment_at = None
        db.commit()
        return sub

    # --- ЮKassa payment ---
    if not sub.yukassa_payment_method_id:
        # Первый платёж: создаём payment с сохранением метода
        payment = yukassa.create_payment(
            amount=price,
            currency="RUB",
            description=f"СтройУправ — план «{PLAN_NAMES[new_plan]}»",
            save_payment_method=True,
            confirmation={"type": "redirect", "return_url": RETURN_URL},
            metadata={"company_id": str(company_id), "plan": new_plan}
        )
        return PaymentPending(redirect_url=payment.confirmation.confirmation_url)
    else:
        # Рекуррентный платёж с сохранённым методом
        payment = yukassa.create_payment(
            amount=price,
            currency="RUB",
            payment_method_id=sub.yukassa_payment_method_id,
            description=f"СтройУправ — продление «{PLAN_NAMES[new_plan]}»",
            metadata={"company_id": str(company_id), "plan": new_plan}
        )

    sub.plan = new_plan
    sub.price = price
    sub.billing_cycle = billing_cycle
    sub.next_payment_at = now() + period
    db.commit()
    return sub


# --- ЮKassa Webhook handler ---

function handle_yukassa_webhook(request: Request):
    """Обработка webhook от ЮKassa."""
    # HMAC verification (Phase 4 finding: ОБЯЗАТЕЛЬНО)
    signature = request.headers.get("X-YooKassa-Signature")
    if not verify_hmac(request.body, signature, env("YUKASSA_WEBHOOK_SECRET")):
        raise SecurityError("Invalid webhook signature")

    event = json.loads(request.body)
    payment = event["object"]

    if event["event"] == "payment.succeeded":
        company_id = payment["metadata"]["company_id"]
        plan = payment["metadata"]["plan"]

        sub = Subscription.get(company_id=company_id)
        sub.plan = plan
        sub.status = "active"
        sub.last_payment_at = now()
        sub.yukassa_payment_method_id = payment.get("payment_method", {}).get("id")

        # Разморозить проекты если были frozen
        frozen = Project.query(company_id=company_id, status="FROZEN")
        for p in frozen[:PLANS[plan]["objects"]]:
            p.status = "ACTIVE"

        db.commit()

    elif event["event"] == "payment.canceled":
        # Платёж не прошёл
        company_id = payment["metadata"]["company_id"]
        notify_user(
            Subscription.get(company_id=company_id).company.admin_id,
            NotificationType.PAYMENT_FAILED
        )

    return {"status": "ok"}
```

---

## 8. AI Provider Routing (LiteLLM Gateway)

```python
# =============================================================================
# AI PROVIDER ROUTING: Cloud.ru primary, OpenAI fallback
# Gateway: LiteLLM (OpenAI-compatible API)
# Retry: exponential backoff, provider switch on 3 failures
# =============================================================================

PROVIDER_CONFIG = {
    "cloud_ru": {
        "base_url": "https://api.cloud.ru/v1",
        "api_key": env("CLOUD_RU_API_KEY"),  # ОБЯЗАТЕЛЬНО из env
        "priority": 1,                       # primary
        "rate_limit_rps": 15,
        "models": {
            "estimate":    "qwen3-coder-480b",      # сметные расчёты
            "chat":        "t-pro-it-2.0",           # русскоязычный ассистент
            "embedding":   "bge-reranker-v2-m3",     # поиск по ГЭСН
            "vision":      "qwen3-vl",               # чертежи
            "analytics":   "deepseek-v3",            # прогнозы
        },
        "cost_per_1m_input":  35,   # ₽
        "cost_per_1m_output": 70,   # ₽
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_key": env("OPENAI_API_KEY"),
        "priority": 2,                       # fallback
        "rate_limit_rps": 60,
        "models": {
            "estimate":    "gpt-4o",
            "chat":        "gpt-4o-mini",
            "embedding":   "text-embedding-3-small",
            "vision":      "gpt-4o",
            "analytics":   "gpt-4o",
        },
        "cost_per_1m_input":  250,  # ₽ (at exchange rate)
        "cost_per_1m_output": 1000, # ₽
    }
}

# Состояние circuit breaker (in-memory + Redis for multi-instance)
provider_state = {
    "cloud_ru": {"failures": 0, "circuit_open_until": None},
    "openai":   {"failures": 0, "circuit_open_until": None}
}

CIRCUIT_BREAKER_THRESHOLD = 3       # failures перед размыканием цепи
CIRCUIT_BREAKER_TIMEOUT = 60        # секунд до retry
MAX_RETRIES = 3
BASE_BACKOFF = 1.0                  # seconds


function ai_request(task_type: str, messages: list, **kwargs) -> AIResponse:
    """
    Единая точка входа для AI-запросов.
    Роутинг: Cloud.ru -> OpenAI (fallback).
    """
    providers = sorted(
        PROVIDER_CONFIG.items(),
        key=lambda p: p[1]["priority"]
    )

    last_error = None

    for provider_name, config in providers:
        state = provider_state[provider_name]

        # Circuit breaker: пропускаем если цепь разомкнута
        if state["circuit_open_until"] and now() < state["circuit_open_until"]:
            log.warn(f"Circuit open for {provider_name}, skipping")
            continue

        model = config["models"].get(task_type)
        if not model:
            continue

        # Retry loop с exponential backoff
        for attempt in range(MAX_RETRIES):
            try:
                response = litellm.completion(
                    model=f"{provider_name}/{model}",
                    messages=messages,
                    api_base=config["base_url"],
                    api_key=config["api_key"],
                    timeout=30,
                    **kwargs
                )

                # Успех: сбрасываем circuit breaker
                state["failures"] = 0
                state["circuit_open_until"] = None

                # Логируем usage для биллинга
                log_ai_usage(
                    provider=provider_name,
                    model=model,
                    task_type=task_type,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    cost=calculate_cost(config, response.usage),
                    latency_ms=response.response_ms
                )

                return response

            except RateLimitError:
                wait = BASE_BACKOFF * (2 ** attempt)
                log.warn(f"Rate limit {provider_name}, retry in {wait}s")
                sleep(wait)

            except (TimeoutError, ServiceUnavailableError) as e:
                state["failures"] += 1
                last_error = e

                if state["failures"] >= CIRCUIT_BREAKER_THRESHOLD:
                    state["circuit_open_until"] = now() + timedelta(seconds=CIRCUIT_BREAKER_TIMEOUT)
                    log.error(f"Circuit OPEN for {provider_name}: {e}")
                    break  # переключаемся на следующий provider

                wait = BASE_BACKOFF * (2 ** attempt)
                log.warn(f"Error {provider_name} (attempt {attempt+1}): {e}, retry in {wait}s")
                sleep(wait)

    # Все провайдеры упали
    raise AIServiceUnavailable(
        "Все AI-провайдеры недоступны. Попробуйте позже.",
        last_error=last_error
    )


function calculate_cost(config: dict, usage) -> Decimal:
    input_cost = (usage.prompt_tokens / 1_000_000) * config["cost_per_1m_input"]
    output_cost = (usage.completion_tokens / 1_000_000) * config["cost_per_1m_output"]
    return Decimal(str(input_cost + output_cost))
```

---

## 9. Key API Endpoints

```python
# =============================================================================
# KEY API ENDPOINTS: Request / Response pseudocode
# Base URL: /api/v1
# Auth: JWT в httpOnly cookie (кроме login/register)
# =============================================================================


# --- POST /api/v1/auth/register ---
# Регистрация новой компании + admin

Request:
    POST /api/v1/auth/register
    Content-Type: application/json
    {
        "email": "alexey@stroyka.ru",
        "password": "S3cur3P@ss!",
        "name": "Алексей Петров",
        "phone": "+79161234567",
        "company_name": "РемонтПро"
    }

Response (201):
    Set-Cookie: access_token=...; HttpOnly; Secure; SameSite=Strict
    Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Strict; Path=/api/auth/refresh
    {
        "user": {
            "id": "uuid",
            "email": "alexey@stroyka.ru",
            "name": "Алексей Петров",
            "role": "admin",
            "company": {"id": "uuid", "name": "РемонтПро"}
        },
        "subscription": {
            "plan": "trial",
            "expires_at": "2026-06-10T00:00:00Z"
        }
    }


# --- POST /api/v1/estimates/generate ---
# Генерация AI-сметы
# @require_auth(min_role="foreman")

Request:
    POST /api/v1/estimates/generate
    Cookie: access_token=...
    Content-Type: application/json
    {
        "project_id": "uuid",
        "input_type": "text",
        "description": "Ремонт 2-комнатной квартиры 65 м²: демонтаж обоев, выравнивание стен, штукатурка, покраска, замена электропроводки, укладка ламината",
        "region": "moscow"
    }

Response (200):
    {
        "estimate_id": "uuid",
        "project_id": "uuid",
        "lines": [
            {
                "gesn_code": "ГЭСНр 61-04-001-01",
                "description": "Снятие обоев",
                "unit": "м²",
                "quantity": 180.0,
                "base_rate": 42.50,
                "index": 8.21,
                "cost": 62803.50,
                "match_score": 0.94
            },
            ...
        ],
        "total": 485000.00,
        "nds": 97000.00,
        "grand_total": 582000.00,
        "suggestions": [
            {
                "type": "OVERPRICED",
                "line_code": "ГЭСНр 65-02-003-01",
                "message": "Электромонтаж: на 14% дороже среднерыночной",
                "potential_savings": 12400.00
            }
        ],
        "accuracy_disclaimer": "Предварительная оценка. Требуется проверка сметчика.",
        "processing_time_ms": 4200
    }


# --- GET /api/v1/dashboard ---
# Главный экран: все проекты пользователя
# @require_auth()

Request:
    GET /api/v1/dashboard?status=active&sort=health
    Cookie: access_token=...

Response (200):
    {
        "summary": {
            "total_projects": 8,
            "total_budget_plan": 12500000.00,
            "total_budget_fact": 9870000.00,
            "avg_progress": 62.5,
            "alerts_count": 3
        },
        "projects": [
            {
                "id": "uuid",
                "name": "Ремонт ул. Ленина 42",
                "progress_pct": 45.2,
                "health": "RED",
                "budget": {"plan": 2500000, "fact": 2890000, "deviation_pct": 15.6},
                "tasks": {"total": 24, "done": 11, "overdue": 4},
                "last_photo": {"url": "...", "taken_at": "2026-05-27T14:30:00Z"},
                "alerts": [
                    {"severity": "critical", "message": "Бюджет превышен на 15.6%"}
                ]
            },
            ...
        ]
    }


# --- POST /api/v1/projects/{id}/tasks ---
# Создание задачи
# @require_auth(min_role="foreman")

Request:
    POST /api/v1/projects/uuid/tasks
    Cookie: access_token=...
    {
        "name": "Штукатурка стен — кухня",
        "description": "Выравнивание стен цементной штукатуркой по маякам",
        "crew_id": "uuid",
        "deadline": "2026-06-05",
        "priority": "high",
        "depends_on": ["uuid-of-demolition-task"],
        "planned_hours": 24,
        "estimate_line_id": "uuid"
    }

Response (201):
    {
        "id": "uuid",
        "name": "Штукатурка стен — кухня",
        "state": "new",
        "crew": {"id": "uuid", "name": "Бригада Иванова"},
        "deadline": "2026-06-05",
        "priority": "high",
        "is_blocked": true,
        "blocked_by": ["Демонтаж — кухня"],
        "created_at": "2026-05-27T10:00:00Z"
    }


# --- PATCH /api/v1/tasks/{id}/state ---
# Смена статуса задачи (state machine)
# @require_auth()

Request:
    PATCH /api/v1/tasks/uuid/state
    Cookie: access_token=...
    {
        "new_state": "in_progress",
        "comment": "Бригада приступила, материалы на объекте"
    }

Response (200):
    {
        "id": "uuid",
        "old_state": "new",
        "new_state": "in_progress",
        "transitioned_by": "Сергей Иванов",
        "comment": "Бригада приступила, материалы на объекте",
        "timestamp": "2026-05-27T08:15:00Z",
        "notifications_sent": ["crew_push"]
    }


# --- POST /api/v1/tasks/{id}/photos ---
# Загрузка фото с геотегом
# @require_auth(min_role="foreman")

Request:
    POST /api/v1/tasks/uuid/photos
    Cookie: access_token=...
    Content-Type: multipart/form-data
    file: <binary JPEG>
    latitude: 55.7558
    longitude: 37.6173
    timestamp: "2026-05-27T14:30:00Z"

Response (201):
    {
        "id": "uuid",
        "task_id": "uuid",
        "url": "https://cdn.stroyuprav.ru/projects/.../photo.jpg",
        "thumbnails": {
            "small": "https://cdn.stroyuprav.ru/.../150x150.jpg",
            "medium": "https://cdn.stroyuprav.ru/.../400x400.jpg"
        },
        "geotag": {
            "latitude": 55.7558,
            "longitude": 37.6173,
            "warning": null
        },
        "taken_at": "2026-05-27T14:30:00Z",
        "task_progress_updated": true,
        "new_progress_pct": 60.0
    }


# --- GET /api/v1/projects/{id}/budget ---
# Бюджет проекта: факт vs план
# @require_auth(min_role="manager")

Request:
    GET /api/v1/projects/uuid/budget
    Cookie: access_token=...

Response (200):
    {
        "project_id": "uuid",
        "plan": 2500000.00,
        "fact": 2890000.00,
        "deviation": 390000.00,
        "deviation_pct": 15.6,
        "forecast": {
            "projected_total": 3200000.00,
            "confidence": 0.72,
            "burn_rate_per_day": 28500.00
        },
        "breakdowns": [
            {"category": "materials",  "plan": 1200000, "fact": 1350000, "deviation_pct": 12.5},
            {"category": "labor",      "plan": 900000,  "fact": 1050000, "deviation_pct": 16.7},
            {"category": "equipment",  "plan": 250000,  "fact": 310000,  "deviation_pct": 24.0},
            {"category": "overhead",   "plan": 150000,  "fact": 180000,  "deviation_pct": 20.0}
        ],
        "alerts": [
            {"severity": "critical", "type": "BUDGET_OVERRUN", "message": "Бюджет превышен на 15.6%"},
            {"severity": "warning",  "type": "CATEGORY_OVERRUN", "message": "Техника: +24.0%"}
        ]
    }


# --- POST /api/v1/billing/subscribe ---
# Оформление подписки через ЮKassa
# @require_auth(min_role="admin")

Request:
    POST /api/v1/billing/subscribe
    Cookie: access_token=...
    {
        "plan": "company",
        "billing_cycle": "monthly"
    }

Response (200):
    {
        "status": "pending_payment",
        "redirect_url": "https://yoomoney.ru/checkout/payments/v2/...",
        "plan": "company",
        "price": 9900,
        "billing_cycle": "monthly"
    }
```

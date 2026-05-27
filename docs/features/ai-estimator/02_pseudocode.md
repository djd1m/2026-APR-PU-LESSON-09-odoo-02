# Pseudocode: AI-Estimator (F01)

Algorithms for the AI estimator pipeline. Python-like pseudocode.

---

## 1. Main Pipeline: Text Description -> Estimate

```python
# =============================================================================
# ENTRY POINT: POST /api/v1/estimate/generate
# Celery task — runs async, returns task_id immediately
# =============================================================================

@celery_task(bind=True, max_retries=2, default_retry_delay=10)
async def task_generate_estimate(self, request: EstimateRequest, user: User):
    """
    Pipeline: description -> AI parse -> ГЭСН lookup -> index -> total
    All money as Decimal. Never Float.
    """
    # 0. Check usage limits
    usage = get_usage(user.tenant_id, current_month())
    plan_limit = get_plan_limit(user.plan)
    if usage.count >= plan_limit and not usage.has_overage_payment:
        raise QuotaExceededError(
            remaining=0,
            overage_price=Decimal("490.00")
        )

    try:
        # 1. Parse input
        if request.input_type == "text":
            work_items = await parse_text_input(request.description, request.area_m2)
        elif request.input_type == "drawing":
            work_items = await parse_drawing_input(request.file_id)
        else:
            raise ValueError(f"Unknown input_type: {request.input_type}")

        # 2. ГЭСН/ФЕР lookup for each work item
        estimate_lines = []
        for item in work_items:
            line = await resolve_gesn_line(item, request.region)
            estimate_lines.append(line)

        # 3. Calculate totals
        subtotal = sum(line.cost for line in estimate_lines)  # Decimal
        nds = subtotal * Decimal("0.20")
        grand_total = subtotal + nds

        # 4. Save estimate
        estimate = save_estimate(
            tenant_id=user.tenant_id,
            project_id=request.project_id,
            input_type=request.input_type,
            region=request.region,
            lines=estimate_lines,
            subtotal=subtotal,
            nds_amount=nds,
            grand_total=grand_total
        )

        # 5. Increment usage counter
        increment_usage(user.tenant_id, current_month())

        # 6. Async: run optimization in background
        task_optimize.delay(estimate.id)

        return {"status": "completed", "estimate_id": estimate.id}

    except AIProviderError as e:
        # Retry with exponential backoff
        self.retry(exc=e)
    except Exception as e:
        mark_estimate_error(request.id, str(e))
        raise
```

## 2. Text Input Parser

```python
async def parse_text_input(description: str, area_m2: float) -> list[WorkItem]:
    """
    Send description to Cloud.ru LLM, get structured work items.
    AI provider: OpenAI-compatible SDK (Cloud.ru primary, env-var switch).
    """
    # Sanitize input — strip prompt injection attempts
    sanitized = sanitize_ai_input(description)

    client = OpenAI(
        base_url=env("AI_BASE_URL"),       # Cloud.ru endpoint
        api_key=env("AI_API_KEY"),         # crash if missing
    )

    prompt = f"""
    Ты — профессиональный сметчик. Разбери описание работ на отдельные позиции.
    Для каждой позиции определи:
    - work_type: стандартный вид работ (штукатурка, электромонтаж, и т.д.)
    - unit: единица измерения (м², м.п., шт, комплект)
    - quantity: объём работ (число)
    - description: краткое описание

    Описание работ: {sanitized}
    Общая площадь: {area_m2} м²

    Ответ в JSON: {{"items": [...]}}
    """

    response = await client.chat.completions.create(
        model=env("AI_MODEL", "qwen3-coder-480b"),
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.1,                   # low temp for deterministic output
        timeout=30                         # hard timeout
    )

    parsed = json.loads(response.choices[0].message.content)

    work_items = []
    for item in parsed["items"]:
        work_items.append(WorkItem(
            description=item["description"],
            work_type=item["work_type"],
            unit=item["unit"],
            quantity=Decimal(str(item["quantity"])),  # Decimal(str()) — never Decimal(float)
            confidence=0.0  # set after ГЭСН matching
        ))

    return work_items
```

## 3. Drawing Parser (Vision AI)

```python
async def parse_drawing_input(file_id: str) -> list[WorkItem]:
    """
    Process PDF/image drawing via Cloud.ru vision model.
    SLA: < 90 sec. Accuracy target: >= 85% for areas.
    """
    # 1. Download file from S3
    file_bytes = await s3_download(bucket="drawings", key=file_id)
    mime = validate_mime(file_bytes, allowed=["application/pdf", "image/jpeg", "image/png"])

    # 2. Convert PDF pages to images if needed
    if mime == "application/pdf":
        images = pdf_to_images(file_bytes, dpi=300, max_pages=10)
    else:
        images = [file_bytes]

    # 3. Vision AI — extract rooms, areas, work types
    client = OpenAI(
        base_url=env("AI_BASE_URL"),
        api_key=env("AI_API_KEY"),
    )

    all_items = []
    for image in images:
        base64_img = base64.b64encode(image).decode()

        response = await client.chat.completions.create(
            model=env("AI_VISION_MODEL", "qwen3-vl"),
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": DRAWING_PARSE_PROMPT},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{base64_img}"
                    }}
                ]
            }],
            response_format={"type": "json_object"},
            temperature=0.1,
            timeout=60
        )

        parsed = json.loads(response.choices[0].message.content)
        # parsed: {"rooms": [{"name": "Кухня", "area_m2": 12.5, "works": [...]}]}

        for room in parsed["rooms"]:
            for work in room["works"]:
                all_items.append(WorkItem(
                    description=f"{room['name']}: {work['description']}",
                    work_type=work["work_type"],
                    unit=work.get("unit", "м²"),
                    quantity=Decimal(str(work.get("quantity", room["area_m2"]))),
                    confidence=0.0
                ))

    return all_items

DRAWING_PARSE_PROMPT = """
Ты — сметчик, анализирующий строительный чертёж.
Определи все помещения, их площади (в м²) и необходимые работы.
Для каждого помещения укажи стандартные виды работ (штукатурка, стяжка, электрика и т.д.).
Ответ в JSON: {"rooms": [{"name": "...", "area_m2": N, "works": [...]}]}
"""
```

## 4. ГЭСН/ФЕР Lookup

```python
async def resolve_gesn_line(item: WorkItem, region: str) -> EstimateLine:
    """
    Search ГЭСН/ФЕР base, apply Минстрой index, calculate cost.
    Two-stage search: semantic (Elasticsearch KNN) -> fulltext fallback.
    """
    # Stage 1: Semantic search via Elasticsearch KNN
    query_vector = await get_embedding(
        text=f"{item.work_type} {item.description}",
        model=env("EMBEDDING_MODEL", "bge-m3")
    )

    candidates = es_client.search(
        index="gesn_fer",
        body={
            "knn": {
                "field": "description_vector",
                "query_vector": query_vector,
                "k": 5,
                "num_candidates": 50
            },
            "_source": ["code", "description", "unit", "base_rate",
                        "overhead_rate", "profit_rate", "category"]
        }
    )

    hits = candidates["hits"]["hits"]

    # Stage 2: Fulltext fallback if no semantic hits
    if not hits or hits[0]["_score"] < 0.7:
        candidates = es_client.search(
            index="gesn_fer",
            body={
                "query": {
                    "multi_match": {
                        "query": item.work_type,
                        "fields": ["description^3", "keywords^2"],
                        "fuzziness": "AUTO"
                    }
                },
                "size": 5
            }
        )
        hits = candidates["hits"]["hits"]

    if not hits:
        raise GESNNotFoundError(f"No ГЭСН/ФЕР match for: {item.work_type}")

    best = hits[0]["_source"]
    match_score = hits[0]["_score"]

    # Get current Минстрой index
    index_row = await db.fetchone("""
        SELECT coefficient FROM su_minstroy_index
        WHERE region = $1 AND work_category = $2 AND quarter = $3
    """, region, best["category"], current_quarter())

    if not index_row:
        raise IndexNotFoundError(f"No Минстрой index for {region}/{best['category']}/{current_quarter()}")

    coefficient = Decimal(str(index_row["coefficient"]))
    base_rate = Decimal(str(best["base_rate"]))
    overhead_rate = Decimal(str(best["overhead_rate"]))
    profit_rate = Decimal(str(best["profit_rate"]))

    # Calculate cost (all Decimal arithmetic)
    base_cost = base_rate * item.quantity
    indexed_cost = base_cost * coefficient
    overhead = indexed_cost * overhead_rate
    profit = indexed_cost * profit_rate
    total = indexed_cost + overhead + profit

    return EstimateLine(
        gesn_code=best["code"],
        description=best["description"],
        unit=item.unit,
        quantity=item.quantity,
        base_rate=base_rate,
        index_coefficient=coefficient,
        overhead_amount=overhead,
        profit_amount=profit,
        cost=total,
        match_score=float(match_score),
        manual_override=False,
        is_overpriced=False  # set by optimization step
    )
```

## 5. Optimization Algorithm

```python
async def task_optimize(estimate_id: str):
    """
    Compare each line against market benchmarks.
    Flag items >10% above market. Suggest alternatives.
    Top-10 suggestions sorted by potential savings.
    """
    estimate = await db.fetch_estimate_with_lines(estimate_id)
    suggestions = []

    for line in estimate.lines:
        # 1. Market benchmark comparison
        benchmark = await get_market_benchmark(line.gesn_code, estimate.region)

        if benchmark:
            unit_cost = line.cost / line.quantity  # Decimal division
            if unit_cost > benchmark * Decimal("1.10"):
                deviation_pct = ((unit_cost / benchmark) - Decimal("1")) * Decimal("100")
                savings = (unit_cost - benchmark) * line.quantity
                suggestions.append(Suggestion(
                    type="OVERPRICED",
                    line_gesn_code=line.gesn_code,
                    deviation_pct=deviation_pct,
                    potential_savings=savings,
                    message=f"{line.description}: на {deviation_pct:.0f}% дороже рынка"
                ))

                # Mark line as overpriced
                await db.update_line(line.id, is_overpriced=True)

        # 2. Find alternative codes (ГЭСН <-> ФЕР cross-reference)
        alternatives = await find_alternatives(line.gesn_code, estimate.region)
        for alt in alternatives:
            if alt.total_cost < line.cost * Decimal("0.90"):
                savings = line.cost - alt.total_cost
                suggestions.append(Suggestion(
                    type="ALTERNATIVE",
                    line_gesn_code=line.gesn_code,
                    alternative_code=alt.code,
                    potential_savings=savings,
                    message=f"Альтернатива: {alt.code} — экономия {savings:.0f} ₽"
                ))

    # Sort by savings, take top 10
    suggestions.sort(key=lambda s: s.potential_savings, reverse=True)
    await save_suggestions(estimate_id, suggestions[:10])


async def find_alternatives(gesn_code: str, region: str) -> list:
    """
    Cross-reference ГЭСН -> ФЕР or vice versa.
    Query Elasticsearch for codes with same work_category but different type.
    """
    source = await es_client.get(index="gesn_fer", id=gesn_code)
    alt_type = "fer" if source["type"] == "gesn" else "gesn"

    results = es_client.search(
        index="gesn_fer",
        body={
            "query": {
                "bool": {
                    "must": [
                        {"term": {"type": alt_type}},
                        {"match": {"description": source["description"]}}
                    ]
                }
            },
            "size": 3
        }
    )
    return [calculate_total(hit, region) for hit in results["hits"]["hits"]]
```

## 6. Export (PDF / Excel)

```python
async def export_estimate(estimate_id: str, format: str, company_header: dict) -> str:
    """
    Generate PDF or Excel, upload to S3, return pre-signed URL.
    """
    estimate = await db.fetch_estimate_with_lines(estimate_id)

    if format == "pdf":
        buffer = generate_pdf(estimate, company_header)
        content_type = "application/pdf"
        ext = "pdf"
    elif format == "xlsx":
        buffer = generate_xlsx(estimate, company_header)
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"
    else:
        raise ValueError(f"Unsupported format: {format}")

    # Upload to S3
    key = f"exports/{estimate.tenant_id}/{estimate_id}.{ext}"
    await s3_upload(bucket="estimates", key=key, body=buffer, content_type=content_type)

    # Generate pre-signed URL (TTL 1 hour)
    url = s3_presign(bucket="estimates", key=key, ttl=3600)
    return url


def generate_pdf(estimate: Estimate, header: dict) -> bytes:
    """
    PDF layout:
    1. Company header (name, INN)
    2. Estimate metadata (project, region, date)
    3. Table: №, Код ГЭСН/ФЕР, Наименование, Ед., Кол-во, Цена, Индекс, Итого
    4. Subtotals: Итого, НДС 20%, ВСЕГО
    5. Disclaimer: "Предварительная оценка"
    """
    # Use reportlab or weasyprint
    # All money formatted as Decimal with 2 decimal places
    # Overpriced lines highlighted in yellow
    ...


def generate_xlsx(estimate: Estimate, header: dict) -> bytes:
    """
    Excel: same layout as PDF, with formulas for totals.
    Use openpyxl. Format money cells as #,##0.00.
    """
    ...
```

## 7. Usage Tracking

```python
async def get_usage(tenant_id: int, month: str) -> UsageInfo:
    """
    Count AI generations for tenant in current month.
    """
    count = await db.fetchval("""
        SELECT COUNT(*) FROM su_estimate
        WHERE tenant_id = $1
          AND status = 'completed'
          AND date_trunc('month', created_at) = $2::date
    """, tenant_id, f"{month}-01")

    plan = await get_tenant_plan(tenant_id)

    return UsageInfo(
        count=count,
        limit=plan.ai_estimate_limit,  # 3, 20, 100, or unlimited
        remaining=max(0, plan.ai_estimate_limit - count),
        has_overage_payment=await check_overage_payment(tenant_id, month)
    )
```

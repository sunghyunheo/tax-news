# 세무 뉴스 브리핑

국세청·기재부, 세무 전문지, 키워드 뉴스, 법령·판례를 매일 자동 수집해
GitHub Pages 정적 페이지로 발행한다.

## 구조

```
sources.json                  수집 소스 정의 (여기만 고치면 소스 추가/삭제 끝)
collect.py                    RSS/Atom 수집 → data/latest.json + data/archive/YYYY-MM-DD.json
render.py                     data/latest.json → docs/index.html (검색·카테고리 필터 포함)
docs/                         GitHub Pages 발행 대상 (index.html, latest.json)
data/archive/                 날짜별 스냅샷 (과거 이력 보존)
.github/workflows/daily.yml   매일 07:10 KST 수집 → 커밋 → Pages 배포
```

의존성 없음 — 파이썬 표준 라이브러리만 사용한다.

## 최초 1회 설정

```bash
git init -b main
git add .
git commit -m "init: 세무 뉴스 브리핑"
git remote add origin https://github.com/<사용자명>/tax-news.git
git push -u origin main
```

그다음 GitHub 저장소에서:

1. **Settings → Pages → Source** 를 `GitHub Actions` 로 변경
2. **Settings → Actions → General → Workflow permissions** 를 `Read and write` 로 변경
3. **Actions 탭 → daily-tax-news → Run workflow** 로 첫 실행

URL: `https://<사용자명>.github.io/tax-news/`

## 로컬에서 확인

```bash
python collect.py && python render.py && start docs/index.html
```

## 소스 추가

`sources.json` 의 해당 카테고리 `feeds` 배열에 `{"name": "...", "url": "..."}` 를 추가한다.
RSS 주소가 없는 매체는 Google News 검색 피드로 대체할 수 있다:

```
https://news.google.com/rss/search?q=<URL인코딩된_검색어>&hl=ko&gl=KR&ceid=KR:ko
```

`site:example.co.kr` 처럼 도메인을 지정하면 특정 매체만 걸러낼 수 있다.

## 수집 정책

- 제목·링크·요약문 일부만 저장한다 (본문 저작권은 각 언론사).
- `settings.max_age_days` (기본 7일) 보다 오래된 기사는 버린다.
- URL 정규화 후 중복 제거 — 같은 기사가 여러 피드에 걸리면 먼저 만난 쪽만 남는다.

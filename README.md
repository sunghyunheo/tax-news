# 세무 뉴스 브리핑

SK네트웍스 세무팀용 일일 브리핑. 경정청구·세법개정·대기업 조사동향·판례 등
카테고리별로 뉴스를 매일 자동 수집해 GitHub Pages 정적 페이지로 발행한다.

## 구조

```
sources.json                  카테고리·소스·분류 키워드 정의 (여기만 고치면 끝)
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

## 카테고리

SK네트웍스 세무팀 관점으로 8개 카테고리를 둔다. `sources.json` 의 `categories` 배열 순서가
페이지 표시 순서이고, `priority` 가 분류 우선순위다 (작을수록 기사를 먼저 가져간다).

| 카테고리 | 담는 내용 |
|---|---|
| 세액 이슈 | 경정청구, 수정신고·기한후신고, 가산세, 환급, 세액공제·감면 |
| 주요 세법 개정 | 세법개정안, 시행령·시행규칙, 조특법·국세기본법, 세제개편 |
| 대기업 세무조사 동향 | 대기업 조사, 조사국 동향, 추징, 심층조사, 역외탈세 |
| 조세불복 · 판례 | 조세심판원 심판례, 대법원·행정법원 판결, 과세전적부심·이의신청 |
| 국제조세 · 이전가격 | 이전가격·정상가격, 글로벌 최저한세(필라2), 조세조약·원천징수, 관세·원산지 |
| 그룹 · 업종 이슈 | SK 관련, 지주회사, 부당행위계산부인, 합병·분할, 렌탈·리스 과세 |
| 국세청 · 기재부 발표 | 보도자료, 예규·유권해석, 납부기한·세정지원 |
| 그 밖의 세무 뉴스 | 위에 안 걸린 세무 기사 (세무 관련어가 없으면 버린다) |

## 수집 방식 두 가지

1. **카테고리 전용 검색 피드** (`categories[].feeds`)
   Google News 검색 결과가 그 카테고리로 직행한다. 좁은 주제를 겨냥할 때 쓴다.

2. **전문지 전체기사 풀** (`pools`)
   일간NTN·세정일보·택스워치·조세일보·한국세정신문·조세금융신문의 전체기사를 받아
   `categories[].match` 키워드로 카테고리에 배분한다. 하루 100건 이상이 들어오므로
   판례·이전가격처럼 일반 뉴스 검색에 잘 안 잡히는 주제를 여기서 건진다.
   화면에서 기사 옆 초록 태그가 어떤 키워드로 분류됐는지 보여준다.

## 소스·키워드 수정

`sources.json` 만 고치면 된다.

- 검색 피드 추가: 해당 카테고리 `feeds` 에 `{"name": "...", "url": "..."}` 추가
- 분류 키워드 추가: 해당 카테고리 `match` 배열에 단어 추가 (소문자로, 부분일치)
- 카테고리 순서 변경: `categories` 배열 순서를 바꾸면 화면 순서가 바뀐다
- 분류 우선순위 변경: `priority` 숫자를 조정한다

Google News 검색 피드 주소 형식:

```
https://news.google.com/rss/search?q=<URL인코딩된_검색어>&hl=ko&gl=KR&ceid=KR:ko
```

`site:example.co.kr` 처럼 도메인을 지정하면 특정 매체만 걸러낼 수 있다.

## 수집 정책

- 제목·링크·요약문 일부만 저장한다 (본문 저작권은 각 언론사).
- `settings.max_age_days` (기본 14일) 보다 오래된 기사는 버린다.
- 중복 제거 2단: URL 정규화 + 제목 지문(매체명 제거 후 비교). 같은 보도가 여러 매체로
  실려도 하나만 남는다.
- 카테고리는 상호배타적이다 — 한 기사는 한 카테고리에만 들어간다.

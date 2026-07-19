# OpenDevs Agentic Assurance Profile

> **번역 안내:** 이 문서는 영어 [README.md](README.md)의 참고용 번역입니다. 규범 문서는 영어 [PROFILE.md](PROFILE.md)입니다. 이 README와 모든 번역은 참고용 요약이며, 서로 다를 경우 PROFILE.md가 우선합니다. 번역과 영어 원문이 다를 경우에는 영어 원문이 우선합니다.

> AI 코딩 에이전트가 상당 부분을 만들거나 유지보수하는 소프트웨어를 위한, 가볍고 증거 중심적인 채택 프로필입니다.

**상태:** 릴리스됨 — 최신 릴리스는 [releases 페이지](https://github.com/MosslandOpenDevs/agentic-assurance-profile/releases) 참조  
**저장소:** `MosslandOpenDevs/agentic-assurance-profile`  
**현재 성숙도:** 참조 프로필이며 인증 제도가 아님

코드 생성이 아무리 값싸져도 소프트웨어 개발에는 여전히 비싼 부분이 남습니다. 이 프로필은 프로젝트가 바로 그 부분을 잃지 않도록 돕습니다.

- 이 시스템을 왜 이렇게 설계했는가
- 어떤 성질이 계속 참이어야 하는가
- 무엇이 그 성질을 실제로 강제하는가
- 어떤 증거(evidence)가 프로젝트의 주장(claim)을 뒷받침하는가
- 어떤 반론과 한계, 잔여 위험이 남아 있는가
- 어떤 결정에는 여전히 인간의 명시적 판단이 필요한가

이 프로필이 따라가는 작업 흐름은 다음과 같습니다.

```text
Intent
  → Claims
  → Invariants
  → Enforcement
  → Evidence
  → Defeaters
  → Residuals
  → Human acceptance
```

이 프로필을 채택(adoption)하기 위해 에디터, 프로그래밍 언어, 에이전트 벤더, 배포 플랫폼, 기존 명세 workflow를 바꿀 필요는 없습니다.

---

## 왜 필요한가

AI 코딩 에이전트가 구현을 만들어 내고 고치는 속도는, 팀이 의도(intent)를 복원하고 가정을 검증하고 변경의 결과를 파악하는 속도를 앞지를 수 있습니다.

그래서 생기는 위험은 결함 있는 코드에 그치지 않습니다. 시스템이 내부적으로는 일관되어 보여도, 실제로는 잘못된 요구사항을 구현하고 있을 수 있습니다. 우연히 생긴 동작을 그대로 굳히거나, 어디에도 명시되지 않은 불변조건(invariant)을 약화시키거나, 증거가 받쳐 주지 못하는 주장을 대외적으로 내걸 수도 있습니다.

이 프로필은 다음을 프로젝트의 일급 산출물(first-class artifact)로 다룹니다.

| 산출물 | 답하는 질문 |
|---|---|
| 의도와 비목표 | 이 시스템은 무엇을 위한 것이고, 무엇을 위한 것이 아닌가? |
| 주장 | 프로젝트가 사용자, 운영자, 연동자에게 무엇을 단언하는가? |
| 불변조건 | 허용된 모든 상태와 변경에 걸쳐 무엇이 계속 참이어야 하는가? |
| 강제 수단(enforcement) | 무엇이 불변조건 위반을 막는가? |
| 증거 | 무엇이 주장과 불변조건을 재현 가능하게 뒷받침하는가? |
| 반증 요인(defeater) | 어떤 구체적인 이유로 주장이 거짓이 되거나 불완전해질 수 있는가? |
| 잔차(residual) | 어떤 불확실성과 한계, 감수하기로 한 위험이 남아 있는가? |

목표는 불확실성을 전부 없애는 데 있지 않습니다. 입증된 성질과 남은 의심 사이의 경계를 누구나 검사할 수 있게 만드는 데 있습니다.

---

## 기원

이 프로필의 뿌리는 Donald Knuth가 한 세대 전에 답했던 질문에 닿아 있습니다. 《TeX: The Program》은 프로그램을 단지 실행되는 물건이 아니라 사람에게 설명해야 할 대상으로 다뤘습니다. 추론 과정과 불변조건, 프로그램이 왜 옳은지를 밝히는 논증이 작업 그 자체의 일부였습니다. AI 코딩 에이전트는 그 규율을 선택 사항으로 만들어 주던 경제 구조를 뒤집었습니다. 구현은 값싸졌지만 설계 근거, 불변조건, 증거, 알려진 한계는 저절로 쓰이지 않습니다. 그리고 코드가 의도를 기록하는 속도보다 빨리 나올 때 프로젝트가 잃는 것이 바로 이것들입니다.

직접적인 계기는 실무에서 나왔습니다. Mossland의 프로젝트인 [Passport](https://passport.moss.land)는 통상적인 코드 에디터 없이 거의 전부를 AI 코딩 에이전트로 만들었습니다. 그렇게 일해 보면 공백이 손에 잡힙니다. 소유자의 일은 코드를 쓰는 데서 주장, 불변조건, 증거, 잔여 위험을 관리하는 쪽으로 옮겨 갑니다. 그 관리에는 오래가고 들여다볼 수 있는 형식이 필요한데, 이 프로필이 바로 그 형식입니다.

---

## 이 프로젝트는 무엇인가

OpenDevs Agentic Assurance Profile의 성격은 다음과 같습니다.

- AI 에이전트가 참여하는 소프트웨어 엔지니어링을 위한 **저장소 단위 채택 프로필**
- **brownfield 우선**: 이미 존재하는 시스템을 복원하고 관리하는 데서 출발
- **증거 중심**: 에이전트의 설명을 그 자체로 증명으로 받아들이지 않음
- **모델 중립, 도구 중립**
- 기존의 명세, Issue, Pull Request, 테스트, CI, release workflow와 호환
- 인간의 의도, 구현 통제, 검증 증거, 남은 불확실성을 하나로 잇는 방법

## 이 프로젝트가 아닌 것

다음은 이 프로필이 아닙니다.

- 새로운 코딩 에이전트 지시 형식
- `AGENTS.md`, Agent Skills, OpenSpec, Spec Kit, ADR, RFC, 혹은 프로젝트에 이미 자리 잡은 workflow의 대체물
- 보안 감사, 침투 테스트, 형식 증명, 인증
- 채택한 프로젝트가 안전하고 버그가 없으며 완전하고 어떤 환경에나 맞는다는 선언
- 공개 취약점 장부
- 비밀 정보, 악용 가능한 공격 경로, 민감한 내부 구조, 개인정보, 미조치 발견 사항을 공개할 이유

**Conformance(적합)는 채택한 프로필이 정한 대로 약속, 통제, 증거, 남은 의심이 표현되어 있다는 뜻입니다. “취약점이 없다”는 뜻이 아닙니다.**

---

## 기존 관행과의 관계

이 프로필은 일부러 얇게 만들었습니다. 기존 생태계를 대체하지 않고 그 사이를 잇는 조정 계층입니다.

| 기존 수단 | 역할 |
|---|---|
| `AGENTS.md` | 코딩 에이전트가 늘 따르는 지침과 읽기 순서 |
| Agent Skills / `SKILL.md` | 특정 작업에 재사용하는 절차 |
| OpenSpec, Spec Kit, ADR, RFC 등 | 변경 명세와 의사결정 workflow |
| 테스트, schema, 제약, 스캐너, CI | 강제와 검증을 실제로 수행하는 장치 |
| `SECURITY.md`와 GitHub 비공개 취약점 신고 | 취약점의 비공개 접수와 조율된 공개(coordinated disclosure) |
| OpenSSF Security Insights | 보안 관행과 태세를 기계가 읽을 수 있는 형태로 공개하는 문서 |
| 이 프로필 | 의도, 주장, 불변조건, 증거, 반증 요인, 잔차 사이의 추적성 |

채택하는 프로젝트는 이미 가진 것을 재사용하면 됩니다. 기존 산출물의 이름만 바꿔 달려고 병렬 문서 체계를 새로 만드는 일은 이 프로필이 의도하는 바가 아닙니다.

---

## 공개 저장소에서의 안전

### 핵심 원칙

> **공개 assurance는 프로젝트가 아는 것을 공개해도 안전하도록 정제해 내놓은 단면이지, 프로젝트의 비공개 보안 기록 전체가 아닙니다.**

이 프로필을 공개 저장소에 적용한다고 해서 실제로 악용 가능한 약점까지 공개해야 하는 것은 아닙니다. 공개 투명성과 책임 있는 취약점 처리는 서로 다른 의무입니다.

### 두 장부 모델

기록을 논리적으로 둘로 나눕니다.

1. **공개 assurance 뷰(단면)** — 저장소와 그 사용자에게 공개해도 안전한 내용
2. **제한된 보안 기록** — 비공개 Security Advisory, 비공개 트래커 등 접근이 통제된 시스템으로 관리하는 내용

| 대체로 공개해도 안전한 것 | 악용 가능하거나 민감한 상태로 남아 있는 동안 제한할 것 |
|---|---|
| 제품의 목적과 명시적 비목표 | secret, token, key, credential, 개인정보 |
| 개략적인 신뢰 경계 | 공격 비용을 실질적으로 낮추는 내부 호스트명, 권한 구조, 접근 경로 |
| 안정된 주장·불변조건 문구 | 미조치 취약점의 재현 절차나 개념 증명 |
| 민감하지 않은 통제 범주 | 아직 메워지지 않은 통제 공백의 정확한 우회 조건 |
| 테스트 이름과 재현 가능한 공개 검사 | 민감한 로그, production 스냅샷, 비공개 증거, 사용자 기록 |
| 정제를 거친 증거 현황 | 조율된 공개 전의 embargo 대상 발견 사항과 영향 버전 분석 |
| 공개해도 무방한 한계 | 세부를 밝히는 순간 곧바로 악용 가능한 잔차 |
| 조율을 마치고 공개한 advisory | 신고자 신원과 비공개 서신 |

판단이 서지 않으면 먼저 비공개 경로로 보냅니다. 비공개로 받은 내용은 나중에 정제해 공개할 수 있습니다. 반대로 한 번 공개 저장소에 올라간 정보는 최신판에서 지워도 실질적으로 비공개가 되지 않습니다.

### 공개 등급

프로젝트는 assurance 자료에 다음과 같은 공개 등급(disclosure class)을 매길 수 있습니다.

- `PUBLIC` — 전체 내용을 공개 저장소에 기록해도 됩니다.
- `SUMMARY_ONLY` — 악용에 쓸 수 없는 요약과 상태만 공개합니다.
- `RESTRICTED` — 공개 저장소에 commit하지 않습니다.
- `EMBARGOED` — 수정이 이루어지고 조율된 공개 여부가 결정될 때까지 비공개로 둡니다.

공개 프로필에는 어떤 통제나 증거 의무가 제한된 경로에서 검토 중이라는 사실까지는 적을 수 있습니다. 다만 공격 경로는 드러내지 않습니다. 그 상태를 밝히는 것만으로도 실질적 위험이 생긴다면 상태 표시 자체를 생략합니다.

### 보안 신고

공개 채택 저장소에는 다음을 권장합니다.

1. `SECURITY.md`를 둡니다.
2. 가능하다면 GitHub **Private Vulnerability Reporting**을 켭니다.
3. 악용이 의심되는 취약점은 공개 Issue가 아닌 다른 경로로 안내합니다.
4. triage, 재현, 수정, 조율된 공개는 draft GitHub Security Advisory 등 비공개 채널에서 진행합니다.
5. 문제를 고쳤거나 공개가 승인된 뒤에만 정제된 프로필 갱신을 공개합니다.

자세한 내용은 [SECURITY.md](SECURITY.md)와 [Disclosure and issue model](docs/DISCLOSURE-AND-ISSUES.md)에 있습니다.

---

## 프로필 문서와 GitHub Issue

역할 분담은 간단합니다.

> **프로필 산출물은 오래 유지되는 프로젝트 상태를 기술합니다. Issue는 그 상태를 바꾸거나 분명히 하는 데 필요한 작업을 추적합니다.**

| GitHub 객체 또는 저장소 산출물 | 기능 |
|---|---|
| `PROFILE.md` | 이 프로필의 공통 규범 의무 |
| 프로젝트별 주장, 불변조건, 잔차 | 프로젝트의 현재 사실과 감수하기로 한 불확실성 |
| GitHub Issue | 제안, 질문, 민감하지 않은 공백, 작업 항목 |
| Pull Request | 구현이나 프로필 산출물의 검토 가능한 변경 |
| CI·증거 산출물 | 주장이나 불변조건을 재현 가능하게 뒷받침하는 근거 |
| GitHub Security Advisory | 악용 가능하거나 민감한 취약점의 비공개 처리 |
| Release/tag | 코드, 프로필 고정, 증거, 잔차 상태를 묶은 버전 스냅샷 |

### 의미는 Issue 번호가 아니라 안정된 ID에 둡니다

프로필 요구사항과 로컬 assurance 항목에는 변하지 않는 ID를 붙입니다. 예를 들면 다음과 같습니다.

```text
AAP-CORE-004
CLAIM-IDENTITY-002
INV-AUTH-007
RES-DATA-003
```

Issue와 Pull Request는 이 ID를 참조합니다. ID를 GitHub Issue 번호에서 따오면 안 됩니다. Issue는 옮겨지고, 닫히고, 중복되고, 쪼개질 수 있지만, assurance 항목은 시스템 역사의 일부로 계속 남기 때문입니다.

Issue 필드 예시는 다음과 같습니다.

```markdown
## Affected assurance IDs

- AAP-CORE-004
- INV-AUTH-007
- RES-DATA-003
```

### Issue를 닫는 것과 assurance를 끝내는 것은 다릅니다

코드를 merge하거나 Issue를 닫는 것만으로는 부족합니다. 관련된 영속 산출물까지 갱신해야 변경이 완료됩니다.

```text
Issue or change proposal
  → Pull Request
  → implementation / control update
  → deterministic verification
  → independent contradiction search when required
  → evidence bound to revision or deployment
  → claims / invariants / residuals updated
  → Issue closed
```

`Closes #123`은 Pull Request를 merge하는 것만으로 Issue가 내건 수용 기준(필요한 프로필·증거 갱신 포함)이 실제로 모두 충족될 때만 씁니다. 그렇지 않으면 `Related to #123`처럼 Issue를 닫지 않는 참조를 씁니다.

### Issue를 어디에 올릴 것인가

| 주제 | 올릴 곳 |
|---|---|
| 프로필 공통 문구, schema, 용어, 호환성 | 이 중앙 프로필 저장소 |
| 프로젝트별 채택, conformance 공백, 도메인 불변조건, 증거 작업 | 채택한 프로젝트의 저장소 |
| 악용 가능하거나 그럴 소지가 있는 보안 발견 사항 | 비공개 취약점 신고 / draft Security Advisory |
| 민감한 악용 세부가 없는 일반적인 보안 강화 | 공개해도 안전하다면 프로젝트의 공개 Issue |
| 수정을 마치고 공개한 취약점 | 공개 advisory와 정제된 문서·Issue 참조 |

전체 분류 규칙은 [Disclosure and issue model](docs/DISCLOSURE-AND-ISSUES.md)에 있습니다.

---

## 채택 방식

**채택은 파일 복사가 아니라 프로필 분류에서 시작합니다.** `core`, `service`, `trust-critical`, `data-curation`, `agent-runtime` 중 무엇이 해당하는지는 저장소가 *무엇이고 무엇을 약속하는가*에 대한 판정이며, 파일을 만들기 전에 증거로 정합니다([docs/ADOPTION.md §4.0](docs/ADOPTION.md)). 구성(layout)은 그 분류를 따라 정해지는 것이지, 저장소 크기로 정해지지 않습니다.

`core` 하나만 해당할 때는 파일 네 개로 채택합니다. `adoption.yaml`에 `layout: lite`를 선언하고 assurance 내용 전체를 `assurance.yaml` 한 파일에 담는 lite 구성입니다.

```text
AGENTS.md
AGENTIC_ASSURANCE.md
.agentic-assurance/
├── adoption.yaml
└── assurance.yaml
```

`service`부터는(또는 `core`에서도 원한다면) 레지스터마다 파일을 따로 두는 split 구성을 사용합니다.

```text
AGENTS.md
AGENTIC_ASSURANCE.md
.agentic-assurance/
└── adoption.yaml
assurance/
├── SYSTEM.md
└── RESIDUALS.yaml
```

다음 산출물은 해당 사항이 있을 때만 도입합니다.

```text
assurance/
├── INVARIANTS.yaml   # recommended at core; required from `service`
├── CLAIMS.yaml
├── DEFEATERS.yaml
├── THREAT_MODEL.md
├── decisions/
├── reviews/
└── evidence/
```

상위 프로필은 버전과 전체 commit SHA로 고정(pin)해야 합니다. 채택 작업을 맡은 에이전트가 유동적인 `main` 브랜치를 말없이 따라가거나, 프로필을 복사해 버전 추적 없는 로컬 fork로 고쳐 쓰면 안 됩니다.

### 권장 프로필

| 프로필 | 용도 |
|---|---|
| `core` | AI 에이전트가 상당 부분을 만들거나 유지하는 모든 저장소 |
| `service` | 배포된 웹사이트, API, worker, 상태를 가진 백엔드, 운영 서비스 |
| `trust-critical` | 신원, 인가, 프라이버시, 보안, 금융, 거버넌스, 공개 검증 가능성을 내세우는 경우 |
| `data-curation` | 외부에서 수집하거나 편집, 채점, 분류, 추천을 거치는 데이터 |
| `agent-runtime` | production에서 동작하는 모델 기반 에이전트나 workflow |
| `archived` | 운영과 기능 개발이 멈춘 참고용 저장소 |

### brownfield 채택 순서

이미 존재하는 저장소라면 다음 순서를 밟습니다.

1. 저장소가 무엇이고 무엇을 약속하는지로 프로필을 분류합니다 — `service` / `trust-critical` / `data-curation` / `agent-runtime` 트리거 중 하나라도 걸리면 `file:line` 증거와 함께 승격하고, `core`라고 가정하지 않습니다([§4.0](docs/ADOPTION.md)).
2. 기존 명세, 테스트, workflow, 정책, release 통제를 살핍니다.
3. 기능 코드는 건드리지 않고, 실제로 만들어진 그대로의 시스템을 복원합니다.
4. 그렇게 내린 결론을 `VERIFIED`, `INFERRED`, `UNKNOWN`, `CONTRADICTED`로 분류합니다.
5. 목적, 비목표, 핵심 주장, 핵심 불변조건, 모호한 동작은 사람의 검토를 받습니다.
6. conformance 공백과 잔차를 기록합니다.
7. 범위를 좁힌 별도의 Issue와 Pull Request로 보완합니다.
8. 증거를 commit, 산출물 digest, release, 배포 식별자에 결부합니다.

파일만 만들었다고 채택한 것이 아닙니다.

**당신이 저장소에 “이 프로필을 적용하라”는 지시를 받은 AI 에이전트라면** — 이 링크 하나뿐인 한마디 지시라도 — 템플릿 복사부터 시작하지 마십시오. 먼저: (1) 이 프로필을 최신 release 커밋으로 **고정(pin)**합니다(유동적인 `main`은 유효한 pin이 아닙니다 — [버전 관리](#버전-관리) 참고). (2) 대상 저장소의 프로필을 그것이 무엇이고 무엇을 약속하는지로 **분류**하되([§4.0](docs/ADOPTION.md)) `core`라고 가정하지 않습니다. (3) 그다음 [docs/ADOPTION.md §4](docs/ADOPTION.md)의 brownfield 순서를 따라, 분류한 집합을 `adoption.yaml`의 `profiles:` 필드에 선언하고, 결과를 브랜치에 올려 merge 없이 human owner에게 넘깁니다. [§0 시작 프롬프트](docs/ADOPTION.md)가 이 지시의 더 자세한 형태입니다 — 쓸 수 있으면 쓰되, 위 단계는 받은 것이 이 링크뿐일 때도 그대로 유효합니다.

실전 채택 절차는 [docs/ADOPTION.md](docs/ADOPTION.md)에서 안내합니다. 병렬 파일을 새로 만드는 대신 기존 저장소 관례를 프로필 산출물에 대응시키는 방법은 [docs/MAPPINGS.md](docs/MAPPINGS.md)에서 다룹니다. 채택을 AI 에이전트에게 맡긴다면 “프로필을 적용하라”는 한마디 대신 [docs/ADOPTION.md §0](docs/ADOPTION.md)의 시작 프롬프트를 건네십시오. 채택 결과를 검토하는 human owner는 [docs/REVIEW-GUIDE.md](docs/REVIEW-GUIDE.md)에서 시작하십시오. 낯선 용어는 [docs/GLOSSARY.md](docs/GLOSSARY.md)에 정리되어 있습니다.

---

## 저장소 구성

이 중앙 저장소는 다음과 같이 구성되어 있습니다.

```text
.
├── .github/
│   ├── CODEOWNERS
│   ├── ISSUE_TEMPLATE/
│   │   ├── adoption-question.yml
│   │   ├── clarification.yml
│   │   ├── config.yml
│   │   ├── profile-change.yml
│   │   └── tooling-defect.yml
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/
│       ├── adopter-validate.yml
│       └── self-check.yml
├── .gitignore
├── CHANGELOG.md
├── CONTRIBUTING.md
├── GOVERNANCE.md
├── LICENSE                  (Apache-2.0)
├── LICENSE-docs             (CC-BY-4.0)
├── PROFILE.md
├── README.ko.md
├── README.md
├── RELEASING.md
├── SECURITY.md
├── VERSION
├── docs/
│   ├── ADOPTION.md
│   ├── DISCLOSURE-AND-ISSUES.md
│   ├── GLOSSARY.md
│   ├── MAPPINGS.md
│   └── REVIEW-GUIDE.md
├── schemas/
│   ├── adoption.schema.json
│   ├── assurance-lite.schema.json
│   ├── claims.schema.json
│   ├── defeaters.schema.json
│   ├── invariants.schema.json
│   └── residuals.schema.json
├── scripts/
│   └── validate.py
└── templates/
    ├── AGENTIC_ASSURANCE.md
    ├── AGENTS.md
    ├── CLAIMS.yaml
    ├── DEFEATERS.yaml
    ├── INVARIANTS.yaml
    ├── LICENSE              (CC0-1.0)
    ├── RESIDUALS.yaml
    ├── SYSTEM.md
    ├── THREAT_MODEL.md
    ├── adoption.yaml
    ├── assurance.yaml
    └── github/
        ├── CODEOWNERS
        ├── ISSUE_TEMPLATE/
        │   ├── bug.yml
        │   ├── config.yml
        │   ├── conformance-gap.yml
        │   ├── evidence-gap.yml
        │   ├── feature.yml
        │   └── residual-review.yml
        └── PULL_REQUEST_TEMPLATE.md
```

---

## 버전 관리

이 프로필은 semantic versioning을 따르고, tag를 붙인 release를 공개하는 것이 좋습니다.

- **Major:** 의무를 없애거나 약화하거나 실질적으로 바꿉니다.
- **Minor:** 하위 호환을 지키면서 요구사항, 프로필, 필드를 더합니다.
- **Patch:** 의무의 의도는 그대로 두고 문구를 다듬거나 schema를 고칩니다.

채택 저장소는 사람이 읽는 버전과 정확한 commit SHA를 함께 고정합니다. 업그레이드는 영향 검토를 거치는 명시적인 프로젝트 변경으로 다룹니다.

release 절차는 [RELEASING.md](RELEASING.md)에 정의되어 있습니다. 루트의 `VERSION` 파일은 저장소의 release 상태를 기록합니다. 첫 release 전에는 `unreleased`, release commit에서는 정확한 tag 문자열, release 사이에는 `-dev` 접미사가 붙은 값을 가집니다. 채택하는 쪽은 자신이 선언한 버전과 `VERSION` 값이 일치하는 commit만 고정합니다.

---

## 기여 방법

다음 주제는 공개 Issue로 다룹니다.

- 프로필 내용을 분명히 하려는 질문
- 민감하지 않은 schema·validator 결함
- 기존 workflow와의 호환성
- 현재 유효한 취약점을 드러내지 않는 제안
- 문서 개선

악용이 의심되는 취약점은 공개 Issue에 올리지 말고 [SECURITY.md](SECURITY.md)를 따릅니다.

Pull Request에는 다음을 밝힙니다.

- 영향을 받는 프로필 ID
- 동작과 호환성에 미치는 영향
- 추가하거나 바꾼 증거
- 새로 생기거나 해소되거나 수정된 잔차
- 공개 등급 분류
- 다루는 Issue 또는 advisory

규범 문서, schema, 템플릿을 바꾸는 결정 권한과 승인 규칙은 [GOVERNANCE.md](GOVERNANCE.md)에 정의되어 있습니다.

---

## 설계 원칙

이 프로필은 프로젝트에 불확실성이 없다고 선언하라고 요구하지 않습니다.

요구하는 것은 특정 revision이나 release를 기준으로 다음을 밝히는 일입니다.

- 무엇을 의도하는가
- 무엇을 주장하는가
- 무엇이 위반을 막는가
- 어떤 증거가 있는가
- 무엇이 아직도 주장을 무너뜨릴 수 있는가
- 남은 불확실성의 경계가 어디인가

그 경계가 곧 assurance 산출물입니다.

---

## 라이선스

이 저장소는 경로에 따라 세 가지 라이선스를 사용합니다.

| 파일 | 라이선스 | 적용 범위 |
|---|---|---|
| [LICENSE](LICENSE) | Apache-2.0 | `schemas/`, `scripts/`, `.github/` workflow, 앞으로 추가될 validator·도구 코드 |
| [LICENSE-docs](LICENSE-docs) | CC-BY-4.0 | `PROFILE.md`, `README.md`, `README.ko.md`, `docs/`, `SECURITY.md`를 비롯한 모든 산문 |
| [templates/LICENSE](templates/LICENSE) | CC0-1.0 | `templates/` 아래 전부 |

코드는 Apache-2.0입니다. 덕분에 schema, validator, workflow 자동화를 특허 조항을 갖춘 표준 코드 라이선스로 재사용할 수 있습니다. 산문은 CC-BY-4.0입니다. 프로필 본문과 문서를 출처만 밝히면 자유롭게 공유하고 고쳐 쓸 수 있습니다. 템플릿은 CC0-1.0으로 퍼블릭 도메인에 헌정했습니다. 채택 저장소로 그대로 복사해도 출처 표기 의무가 생기지 않습니다.

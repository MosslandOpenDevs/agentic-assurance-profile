# OpenDevs Agentic Assurance Profile

> **번역 안내:** 이 문서는 영어 [README.md](README.md)의 참고용 번역입니다. 규범 문서는 영어 [PROFILE.md](PROFILE.md)이며, 번역과 원문이 다를 경우 영어 원문이 우선합니다.

> AI 코딩 에이전트가 상당 부분 작성하거나 유지보수하는 소프트웨어를 위한 경량·증거 중심 채택 프로필

**상태:** Draft / experimental (`v0.1.0` 목표)  
**저장소:** `MosslandOpenDevs/agentic-assurance-profile`  
**현재 성격:** 참조 프로필이며 인증 제도가 아님

이 프로필은 코드 생성 비용이 낮아져도 여전히 비싼 다음 요소를 보존하기 위한 것입니다.

- 왜 시스템이 이런 방식으로 설계되었는가;
- 어떤 성질이 항상 참이어야 하는가;
- 무엇이 그 성질을 실제로 강제하는가;
- 어떤 증거가 프로젝트의 주장을 뒷받침하는가;
- 어떤 반론·한계·잔차가 남아 있는가;
- 어떤 결정은 반드시 인간 권한으로 남아야 하는가.

작업 사슬은 다음과 같습니다.

```text
의도
  → 주장
  → 불변조건
  → 강제 장치
  → 증거
  → 반증 요인
  → 잔차
  → 인간의 수용 결정
```

프로그래밍 언어, 코드 에디터, 에이전트 vendor, 배포 플랫폼, 기존 명세 체계를 바꾸지 않고 채택할 수 있습니다.

---

## 왜 필요한가

AI 코딩 에이전트는 팀이 의도를 복원하고 가정을 검증하며 변경 영향을 이해하는 속도보다 더 빠르게 구현을 생산하고 수정할 수 있습니다.

위험은 단순한 코드 결함만이 아닙니다. 프로그램 내부는 일관되어 보여도 잘못된 요구사항을 구현하거나, 우연히 생긴 동작을 보존하거나, 명시되지 않은 불변조건을 약화하거나, 증거보다 강한 공개 주장을 할 수 있습니다.

이 프로필은 다음을 1급 프로젝트 산출물로 취급합니다.

| 산출물 | 답하는 질문 |
|---|---|
| 의도와 비목표 | 이 시스템은 무엇을 위한 것이고, 무엇을 위한 것이 아닌가? |
| 주장 | 사용자·운영자·통합 대상에게 무엇을 말하는가? |
| 불변조건 | 허용된 모든 상태와 변경에서 무엇이 항상 참이어야 하는가? |
| 강제 장치 | 불변조건 위반을 무엇이 실제로 막는가? |
| 증거 | 무엇이 주장이나 불변조건을 재현 가능하게 뒷받침하는가? |
| 반증 요인 | 어떤 구체적 이유로 주장이 거짓이거나 불완전할 수 있는가? |
| 잔차 | 어떤 불확실성·한계·수용된 위험이 남아 있는가? |

목표는 모든 불확실성을 없애는 것이 아니라, 입증된 범위와 남은 의심의 경계를 검사 가능하게 만드는 것입니다.

---

## 이 프로젝트가 하는 일

OpenDevs Agentic Assurance Profile은 다음과 같습니다.

- AI 에이전트 보조 개발을 위한 **repository-level adoption profile**;
- 이미 존재하는 시스템을 복원하고 통제하는 **brownfield-first** 접근;
- 에이전트의 서술 자체를 증거로 인정하지 않는 **evidence-oriented** 접근;
- 모델·도구·언어·플랫폼 중립;
- 기존 명세, Issue, PR, 테스트, CI, 릴리스 체계와 함께 쓰는 연결 계층;
- 인간의 의도, 구현 통제, 검증 증거, 잔여 불확실성을 추적하는 방법.

## 이 프로젝트가 하지 않는 일

다음은 아닙니다.

- 새로운 코딩 에이전트 지침 형식;
- `AGENTS.md`, Agent Skills, OpenSpec, Spec Kit, ADR, RFC 또는 프로젝트의 기존 workflow의 대체재;
- 보안 감사, 침투 테스트, 형식 증명, 인증;
- 채택 프로젝트가 안전하거나, 버그가 없거나, 완전하거나, 모든 환경에 적합하다는 선언;
- 공개 취약점 원장;
- 비밀정보, 공격 가능한 경로, 민감한 토폴로지, 개인정보, 미수정 취약점을 공개하라는 요구.

**Conformance는 프로젝트의 약속·통제·증거·잔차가 채택한 프로필에 따라 표현되어 있다는 뜻입니다. “취약점이 없다”는 뜻이 아닙니다.**

---

## 기존 체계와의 관계

이 프로필은 새로운 생태계를 만들기보다 기존 도구 사이를 잇는 얇은 계층입니다.

| 기존 체계 | 역할 |
|---|---|
| `AGENTS.md` | 코딩 에이전트가 항상 읽을 지침과 읽기 순서 |
| Agent Skills / `SKILL.md` | 특정 작업용 재사용 절차 |
| OpenSpec, Spec Kit, ADR, RFC 등 | 변경 명세와 설계 결정 workflow |
| 테스트, 스키마, constraint, scanner, CI | 강제 및 검증 수단 |
| `SECURITY.md`와 GitHub private vulnerability reporting | 비공개 취약점 접수와 coordinated disclosure |
| OpenSSF Security Insights | 공개 가능한 보안 관행·posture의 기계 판독 표현 |
| 이 프로필 | 의도–주장–불변조건–증거–반증–잔차의 추적성 |

이미 충분한 체계가 있다면 재사용하며, 명칭만 바꾼 병렬 문서 시스템을 만들지 않습니다.

---

## 공개 저장소에 적용해도 안전한가

### 중앙 원칙

> **공개 assurance는 프로젝트가 가진 지식의 정제된 공개 투영물이지, 완전한 비공개 보안 원장이 아닙니다.**

공개 저장소에 프로필을 적용한다고 해서 공격 가능한 약점을 모두 공개할 필요는 없습니다. 투명성과 책임 있는 취약점 처리는 서로 다른 의무입니다.

### 두 개의 원장

논리적으로 다음 두 기록을 분리합니다.

1. **공개 assurance view** — 저장소와 사용자에게 공개해도 안전한 정보
2. **restricted security record** — Security Advisory, private tracker 등 접근 통제된 공간의 정보

| 일반적으로 공개 가능 | 수정·공개 결정 전까지 제한해야 함 |
|---|---|
| 제품 목적과 명시적 비목표 | secret, token, key, credential, 개인정보 |
| 고수준 신뢰 경계 | 공격 비용을 실질적으로 낮추는 내부 host·권한 토폴로지·접근 경로 |
| 안정적인 claim·invariant 문장 | 미수정 취약점의 재현 절차와 PoC |
| 비민감한 control 종류 | 현재 control gap의 정확한 우회 조건 |
| 공개 테스트 이름과 재현 가능한 검증 | 민감 로그, production snapshot, 비공개 evidence, 사용자 기록 |
| 정제된 evidence 상태 | coordinated disclosure 전 embargoed finding과 affected-version 분석 |
| 공개 가능한 limitation | 내용을 공개하면 즉시 악용 가능한 residual |
| 조정 후 공개된 advisory | 신고자 신원과 비공개 대화 |

판단이 애매하면 우선 비공개 경로로 보냅니다. 나중에 정제해서 공개할 수 있지만, 공개 Git history에 들어간 정보는 최신 파일에서 삭제해도 실질적으로 비공개가 되지 않습니다.

### 공개 등급

프로젝트는 assurance 정보를 다음처럼 분류할 수 있습니다.

- `PUBLIC` — 전체를 공개 저장소에 기록 가능;
- `SUMMARY_ONLY` — 공격에 직접 도움이 되지 않는 요약과 상태만 공개;
- `RESTRICTED` — 공개 저장소에 commit 금지;
- `EMBARGOED` — 수정 및 coordinated disclosure 결정 전까지 비공개.

공개 프로필에는 특정 control이나 evidence 의무가 제한된 검토 중이라는 사실을 기재할 수 있지만, 공격 경로 자체를 드러내면 안 됩니다. 그 상태 표시만으로도 실질적 위험이 생기는 경우에는 상태 자체도 생략합니다.

### 보안 신고 경로

각 공개 채택 저장소는 다음을 갖추는 것이 좋습니다.

1. `SECURITY.md`;
2. 가능한 경우 GitHub **Private Vulnerability Reporting** 활성화;
3. 악용 가능한 취약점을 public Issue에서 다루지 않는 규칙;
4. Draft Security Advisory 또는 다른 비공개 채널을 통한 triage·재현·수정·coordinated disclosure;
5. 수정 또는 공개 승인 후 정제된 profile 갱신.

세부 규칙은 [SECURITY.md](SECURITY.md)와 [Disclosure and issue model](docs/DISCLOSURE-AND-ISSUES.md)을 참고합니다.

---

## Profile 문서와 GitHub Issue의 관계

책임 분리는 간단합니다.

> **Profile artifact는 지속되는 프로젝트 상태를 기술하고, Issue는 그 상태를 변경·보완하기 위한 작업을 추적합니다.**

| 객체 | 역할 |
|---|---|
| `PROFILE.md` | 중앙 프로필의 일반 규범 |
| 프로젝트별 claim·invariant·residual | 현재 프로젝트의 사실·약속·수용된 불확실성 |
| GitHub Issue | 제안, 질문, 비민감 gap, 작업 항목 |
| Pull Request | 구현 또는 profile artifact의 검토 가능한 변경 |
| CI/evidence artifact | claim·invariant를 뒷받침하는 재현 가능한 결과 |
| GitHub Security Advisory | 악용 가능하거나 민감한 취약점의 비공개 처리 |
| Release/tag | 코드·프로필 pin·evidence·residual 상태의 versioned snapshot |

### 의미는 Issue 번호가 아니라 stable ID로 고정한다

프로필 요구사항과 로컬 assurance 항목에는 stable ID를 부여합니다. 예:

```text
AAP-CORE-004
CLAIM-IDENTITY-002
INV-AUTH-007
RES-DATA-003
```

Issue와 PR은 이 ID를 참조합니다. Issue는 이동·분할·중복·종료될 수 있으므로 Issue 번호를 assurance ID로 사용하지 않습니다.

```markdown
## Affected assurance IDs

- AAP-CORE-004
- INV-AUTH-007
- RES-DATA-003
```

### Issue 종료는 assurance 해결과 같지 않다

코드가 merge되거나 Issue가 닫힌 것만으로는 충분하지 않습니다. 해당하는 durable artifact가 갱신되어야 변경이 완료됩니다.

```text
Issue / change proposal
  → Pull Request
  → 구현·control 변경
  → deterministic verification
  → 필요 시 독립적인 contradiction search
  → revision/deployment에 evidence 결박
  → claim/invariant/residual 갱신
  → Issue 종료
```

PR이 Issue의 acceptance criteria와 profile/evidence 갱신까지 실제로 완료할 때만 `Closes #123`을 씁니다. 일부만 진행했다면 `Related to #123`처럼 비종료 참조를 사용합니다.

### 어느 저장소에서 다룰 것인가

| 주제 | 위치 |
|---|---|
| 일반 프로필 문구, schema, 용어, 호환성 | 중앙 profile repo |
| 프로젝트별 채택, conformance gap, 도메인 invariant, evidence 작업 | 해당 프로젝트 repo |
| 악용 가능하거나 가능성이 의심되는 보안 finding | Private vulnerability report / Draft Security Advisory |
| 공격 세부가 없는 일반 hardening | 공개해도 안전할 때 프로젝트 Issue |
| 수정 후 공개된 취약점 | 공개 advisory와 정제된 profile/Issue 참조 |

전체 라우팅 규칙은 [Disclosure and issue model](docs/DISCLOSURE-AND-ISSUES.md)을 참고합니다.

---

## 채택 구조

채택 저장소에는 최소한 다음을 둡니다.

```text
AGENTS.md
AGENTIC_ASSURANCE.md
.agentic-assurance/
└── adoption.yaml
assurance/
├── SYSTEM.md
├── INVARIANTS.yaml
└── RESIDUALS.yaml
```

필요할 때만 확장합니다.

```text
assurance/
├── CLAIMS.yaml
├── DEFEATERS.yaml
├── THREAT_MODEL.md
├── decisions/
├── reviews/
└── evidence/
```

중앙 프로필은 버전과 full commit SHA로 pin합니다. 에이전트는 floating `main`을 조용히 따르거나 중앙 프로필을 복사해 추적되지 않는 local fork로 만들면 안 됩니다.

### Profile 종류

| Profile | 적용 대상 |
|---|---|
| `core` | AI 에이전트가 상당 부분 작성·유지하는 저장소 |
| `service` | 운영 중인 웹사이트, API, worker, stateful backend 또는 운영 서비스 |
| `trust-critical` | identity, authorization, privacy, security, financial, governance, public-verifiability claim |
| `data-curation` | 외부 출처, 편집, 점수화, 분류, 추천 데이터 |
| `agent-runtime` | production에서 실행되는 model-driven agent/workflow |
| `archived` | 운영·기능 개발을 중단한 reference-only 저장소 |

### 기존 저장소 채택 순서

1. 기존 명세·테스트·workflow·정책·release control을 확인한다.
2. 기능 코드를 바꾸지 않고 as-built system을 복원한다.
3. 결론을 `VERIFIED`, `INFERRED`, `UNKNOWN`, `CONTRADICTED`로 분류한다.
4. 목적·비목표·critical claim·critical invariant·모호한 동작을 인간이 검토한다.
5. conformance gap과 residual을 기록한다.
6. 별도의 범위가 정해진 Issue와 PR로 보완한다.
7. evidence를 commit, artifact digest, release, deployment ID에 결박한다.

파일 생성만으로 채택이 완료되는 것은 아닙니다.

실용적인 채택 절차는 [docs/ADOPTION.md](docs/ADOPTION.md)를, 병렬 파일을 새로 만드는 대신 기존 저장소 관례를 프로필 산출물에 매핑하는 방법은 [docs/MAPPINGS.md](docs/MAPPINGS.md)를 참고합니다.

---

## 중앙 저장소 구조

이 중앙 저장소의 구조는 다음과 같습니다.

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
│   └── MAPPINGS.md
├── schemas/
│   ├── adoption.schema.json
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
    └── github/
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

Semantic Versioning과 tagged release를 사용합니다.

- **Major:** 의무를 제거·약화하거나 의미를 크게 변경;
- **Minor:** backward-compatible requirement/profile/field 추가;
- **Patch:** 의무의 의미를 바꾸지 않는 표현·schema 수정.

채택 저장소는 사람이 읽는 version과 정확한 commit SHA를 함께 pin하며, 업그레이드는 영향 검토를 수반한 명시적 변경으로 처리합니다.

릴리스 절차는 [RELEASING.md](RELEASING.md)에 정의되어 있습니다. 루트 `VERSION` 파일은 저장소의 릴리스 상태를 기록합니다. 첫 릴리스 전에는 `unreleased`, 릴리스 commit에서는 정확한 tag 문자열, 릴리스 사이에는 `-dev` suffix가 붙은 값을 가집니다. 채택 저장소는 자신이 선언한 version과 `VERSION` 값이 일치하는 commit만 pin합니다.

---

## 기여와 보안

공개 Issue에 적합한 항목:

- profile clarification;
- 비민감 schema·validator defect;
- 기존 workflow와의 호환성;
- active vulnerability를 노출하지 않는 제안;
- 문서 개선.

악용 가능성이 있는 취약점은 public Issue에 적지 말고 [SECURITY.md](SECURITY.md)를 따릅니다.

PR에는 다음을 기록합니다.

- 영향받는 profile ID;
- behavioral·compatibility impact;
- 추가·변경된 evidence;
- 신규·해결·수정된 residual;
- disclosure classification;
- 관련 Issue 또는 advisory.

규범 문서·schema·template 변경에 대한 결정 권한과 승인 규칙은 [GOVERNANCE.md](GOVERNANCE.md)에 정의되어 있습니다.

---

## 설계 원칙

이 프로필은 불확실성이 0이라고 선언하라고 요구하지 않습니다.

특정 revision 또는 release에 대해 다음을 말할 수 있게 합니다.

- 무엇을 의도하는가;
- 무엇을 주장하는가;
- 무엇이 위반을 막는가;
- 어떤 증거가 있는가;
- 무엇이 여전히 주장을 무너뜨릴 수 있는가;
- 남은 불확실성이 어디서 멈추는가.

그 경계가 assurance artifact입니다.

---

## 라이선스

이 저장소는 경로별로 세 개의 라이선스를 사용합니다.

| 파일 | 라이선스 | 적용 범위 |
|---|---|---|
| [LICENSE](LICENSE) | Apache-2.0 | `schemas/`, `scripts/`, `.github/` workflow, 향후 validator·tooling 코드 |
| [LICENSE-docs](LICENSE-docs) | CC-BY-4.0 | `PROFILE.md`, `README.md`, `README.ko.md`, `docs/`, `SECURITY.md` 및 그 밖의 모든 문서 |
| [templates/LICENSE](templates/LICENSE) | CC0-1.0 | `templates/` 아래의 모든 파일 |

코드에는 특허 조항을 갖춘 표준 코드 라이선스로 재사용할 수 있도록 Apache-2.0을 적용합니다. 문서에는 출처 표기와 함께 공유·수정할 수 있도록 CC-BY-4.0을 적용합니다. 템플릿은 채택 저장소로 복사할 때 출처 표기 의무가 생기지 않도록 CC0-1.0으로 퍼블릭 도메인에 제공합니다.

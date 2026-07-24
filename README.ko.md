# OpenDevs Agentic Assurance Profile

> **번역 안내:** 이 문서는 영어 [README.md](README.md)의 참고용 번역입니다. 규범 문서는 영어 [PROFILE.md](PROFILE.md)입니다. 이 README와 모든 번역은 참고용 요약이며, 서로 다를 경우 PROFILE.md가 우선합니다. 번역과 영어 원문이 다를 경우에는 영어 원문이 우선합니다.

> AI 코딩 에이전트가 상당 부분을 만들거나 유지보수하는 소프트웨어를 위한, 가볍고 증거 중심적인 채택 프로필입니다.

**상태:** 릴리스됨 — 최신 릴리스는 [releases 페이지](https://github.com/MosslandOpenDevs/agentic-assurance-profile/releases) 참조  
**저장소:** `MosslandOpenDevs/agentic-assurance-profile`  
**현재 성숙도:** 참조 프로필이며 인증 제도가 아님

> **규범 상태:** [PROFILE.md](PROFILE.md)가 규범 문서입니다. 이 README와 모든 번역은 참고용 요약이며, 서로 다를 경우 PROFILE.md가 우선합니다.

코드 생성은 값싸지만, 그 주변의 추론은 그렇지 않습니다. 이 프로필은 그 추론을 오래가고 검사 가능한 저장소 산출물로 남깁니다:

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

**저장소에 "이 프로필을 적용하라"는 지시를 받았습니까(사람 또는 AI 에이전트)?** [프로필 적용하기](#프로필-적용하기-ai-에이전트-또는-사람)를 참고하십시오.

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

이 프로필의 뿌리는 Donald Knuth가 한 세대 전에 답했던 질문에 닿아 있습니다. 《TeX: The Program》은 프로그램을 단지 실행되는 물건이 아니라 사람에게 설명해야 할 대상으로 다뤘습니다. 추론 과정과 불변조건, 프로그램이 왜 옳은지를 밝히는 논증이 작업 그 자체의 일부였습니다. AI 코딩 에이전트는 그 규율을 선택 사항으로 만들어 주던 경제 구조를 뒤집었습니다. 구현은 값싸졌습니다. 설계 근거, 불변조건, 증거, 알려진 한계는 그렇지 않으며 — 코드가 의도의 기록을 앞지를 때 프로젝트가 잃는 것이 바로 이것들입니다.

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

이웃한 도구들은 저마다 다른 질문에 답합니다. 명세 workflow는 이번 변경이 무엇을 해야 하는지를 기록합니다. 분석 도구와 코드 리뷰 도구는 작성된 코드에서 위험을 찾아냅니다. provenance 도구는 에이전트가 실제로 무엇을 했는지를 남깁니다. 이 프로필이 맡는 것은 그러고도 남는 질문입니다. **인간이 승인한 약속과 그 사람이 받아들이기로 한 위험이, 이번 변경 뒤에도 그대로인가?** 여기에 답하려면 변경 하나보다 오래 남는 산출물이 필요합니다. 단위가 Pull Request가 아니라 저장소인 이유, 그리고 다른 도구들의 산출물을 다시 만들지 않고 증거로 받아 쓰는 이유가 여기에 있습니다.

## 이 프로젝트가 아닌 것

다음은 이 프로필이 아닙니다.

- 새로운 코딩 에이전트 지시 형식
- `AGENTS.md`, Agent Skills, OpenSpec, Spec Kit, ADR, RFC, 혹은 프로젝트에 이미 자리 잡은 workflow의 대체물
- 보안 감사, 침투 테스트, 형식 증명, 인증
- 채택한 프로젝트가 안전하고 버그가 없으며 완전하고 어떤 환경에나 맞는다는 선언
- 공개 취약점 장부
- 비밀 정보, 악용 가능한 공격 경로, 민감한 내부 구조, 개인정보, 미조치 발견 사항을 공개할 이유

**Active 채택에서 conformance(적합)는 채택한 프로필이 정한 대로 약속, 통제, 증거, 남은 의심이 표현되어 있다는 뜻입니다. 배타적인 `archived`에서는 참고 전용 자격과 네 가지 필수 역사 정보가 표현되고 human owner에게 확인되었다는 뜻이며, 현재 운영에 대한 assurance를 주장하지 않습니다. 어느 쪽도 "취약점이 없다"는 뜻이 아닙니다.**

---

## 기존 관행과의 관계

이 프로필은 일부러 얇게 만들었습니다. 기존 생태계를 대체하지 않고 그 사이를 잇는 조정 계층입니다.

| 기존 수단 | 역할 |
|---|---|
| `AGENTS.md` | 코딩 에이전트가 늘 따르는 지침과 읽기 순서 |
| Agent Skills / `SKILL.md` | 특정 작업에 재사용하는 절차 |
| OpenSpec, Spec Kit, Kiro, ADR, RFC 등 | 변경 명세와 의사결정 workflow |
| 테스트, schema, 제약, 스캐너, 코드 리뷰 도구, CI | 강제와 검증을 실제로 수행하는 장치 |
| 에이전트 변경 기록과 세션 로그 | 에이전트가 무엇을 읽고 실행하고 바꿨는지에 대한 provenance |
| SLSA, in-toto 등의 attestation | release의 빌드와 아티팩트 provenance |
| `SECURITY.md`와 GitHub 비공개 취약점 신고 | 취약점의 비공개 접수와 조율된 공개(coordinated disclosure) |
| OpenSSF Security Insights | 보안 관행과 태세를 기계가 읽을 수 있는 형태로 공개하는 문서 |
| 이 프로필 | 의도, 주장, 불변조건, 증거, 반증 요인, 잔차 사이의 추적성 |

채택하는 프로젝트는 이미 가진 것을 재사용하면 됩니다. 기존 산출물의 이름만 바꿔 달려고 병렬 문서 체계를 새로 만드는 일은 이 프로필이 의도하는 바가 아닙니다.

위 수단들이 산출물을 내놓을 때, 이 프로필은 그것을 다시 만들지 않고 참조합니다. 명세 workflow는 의도와 변경 범위를, 검증 도구와 attestation은 증거를, 리뷰 결과는 반증 요인 후보를 공급합니다. 그 산출물을 register에서 참조하되 그것이 증명하는 범위를 넘겨 말하지 않는 방법은 [docs/MAPPINGS.md §5](docs/MAPPINGS.md)에 정리했습니다. 어떤 도구도 대신 만들어 주지 않는 부분도 있습니다. 의도, 주장의 문구, 반증 요인의 처리, 잔차의 수용은 사람의 결정으로 남습니다([PROFILE.md §3](PROFILE.md)).

---

## 공개 저장소에서의 안전

> **공개 assurance는 프로젝트가 아는 것을 공개해도 안전하도록 정제해 내놓은 단면이지, 프로젝트의 비공개 보안 기록 전체가 아닙니다.**

이 프로필을 공개 저장소에 적용한다고 해서 실제로 악용 가능한 약점까지 공개해야 하는 것은 아닙니다. 공개 투명성과 책임 있는 취약점 처리는 서로 다른 의무입니다. 기록을 **두 장부**로 나눠 둡니다 — 저장소와 그 사용자에게 공개해도 안전한 공개 assurance 뷰와, 아직 악용 가능하거나 민감한 것을 담는 제한된 보안 기록(비공개 advisory나 그 밖의 접근 통제 시스템)입니다. 공개해도 안전한 자료에는 제품의 목적과 비목표, 개략적인 신뢰 경계, 안정된 주장과 불변조건, 정제를 거친 증거 현황이 있습니다. secret, 권한 있는 내부 구조, 미조치 취약점의 재현 절차, 신고자 신원은 제한된 채로 둡니다. 판단이 서지 않으면 먼저 비공개 경로로 보냅니다 — 한 번 공개 저장소에 올라간 정보는 최신판에서 지워도 실질적으로 비공개가 되지 않습니다.

assurance 자료에는 공개 등급(disclosure class)이 붙습니다 — `PUBLIC`, `SUMMARY_ONLY`, `RESTRICTED`, `EMBARGOED`([PROFILE.md §13](PROFILE.md)과 [docs/GLOSSARY.md](docs/GLOSSARY.md)에 정의). 통제는 그 상태를 밝히는 것이 공격 경로 자체를 드러내지 않을 때에 한해 "제한된 검토 중"으로 공개할 수 있습니다. 공개가 실질적 위험을 낳는다면 상태 표시 자체를 생략합니다.

**보안 신고** — 모든 공개 채택 저장소는 `SECURITY.md`를 두고, GitHub **Private Vulnerability Reporting**을 켜며, 악용이 의심되는 취약점을 공개 Issue가 아닌 draft Security Advisory로 보내 triage와 조율된 공개(coordinated disclosure)를 진행하고, 수정이나 공개가 승인된 뒤에만 정제된 프로필 갱신을 공개해야 합니다.

보안 신고 lifecycle과 공개 등급이 Issue·advisory로 어떻게 라우팅되는지는 [SECURITY.md](SECURITY.md)와 [Disclosure and issue model](docs/DISCLOSURE-AND-ISSUES.md)에 있습니다.

---

## 프로필 문서와 GitHub Issue

역할 분담은 간단합니다.

> **프로필 산출물은 오래 유지되는 프로젝트 상태를 기술합니다. Issue는 그 상태를 바꾸거나 분명히 하는 데 필요한 작업을 추적합니다.**

`PROFILE.md`와 로컬 주장·불변조건·잔차가 오래가는 사실이고, Issue, Pull Request, CI 증거, Security Advisory, release tag는 그 상태를 움직이는 작업과 증거입니다. Issue를 닫거나 Pull Request를 merge하는 것만으로는 assurance 항목이 해소되지 **않습니다** — 오래가는 산출물(주장, 불변조건, 잔차)과 그 증거까지 갱신되어야 변경이 완료됩니다.

프로필 요구사항과 로컬 assurance 항목에는 변하지 않는 ID를 붙입니다(`AAP-CORE-004`, `CLAIM-IDENTITY-002`, `INV-AUTH-007`, `RES-DATA-003`). Issue와 Pull Request는 이 ID를 참조합니다. ID를 GitHub Issue 번호에서 따오면 안 됩니다 — Issue는 옮겨지고 닫히고 중복되고 쪼개질 수 있지만 assurance 항목은 계속 남기 때문입니다. 관련된 각 Issue와 PR은 영향을 받는 ID를 밝힙니다.

```markdown
## Affected assurance IDs

- AAP-CORE-004
- INV-AUTH-007
- RES-DATA-003
```

상태/작업 모델 전체, 안정된 ID의 namespace, Issue/PR 라우팅(중앙 프로필 vs. 채택 프로젝트 vs. 비공개 보안 신고), `Closes #`와 `Related to #` 규칙, 닫힘과 해소를 구분하는 lifecycle은 [docs/DISCLOSURE-AND-ISSUES.md](docs/DISCLOSURE-AND-ISSUES.md)에 있습니다.

---

## 프로필 적용하기 (AI 에이전트 또는 사람)

채택은 **파일 복사가 아니라 프로필 분류에서 시작합니다.** 해당하는 프로필 집합은 저장소가 무엇이고 무엇을 약속하는가에 대한 *판정*이며, 파일을 하나라도 쓰기 전에 증거로 정하고, 그 뒤의 모든 것의 규모를 결정합니다. 구성(layout)은 그 분류를 따라 정해지지 저장소 크기로 정해지지 않습니다. `core` 하나만으로 확인된 저장소는 `layout: lite`의 `assurance.yaml` 단일 파일 형태를 쓸 수 있고, specialized active 프로필이 하나라도 있거나 배타적인 `archived` 프로필이면 레지스터마다 파일을 따로 두는 split 구성을 씁니다. 상위 프로필은 버전과 전체 commit SHA로 고정(pin)하며 — 유동적인 `main`도, 복사해 고친 버전 추적 없는 로컬 fork도 안 됩니다. 파일을 만들었다고 채택이 아닙니다. 채택은 merge가 아니라 사람의 결정으로 끝납니다.

**당신이 저장소에 "이 프로필을 적용하라"는 지시를 받았다면 — 이 링크 하나뿐인 한마디 지시라도 — 템플릿 복사부터 시작하지 마십시오.** 먼저 **이름이 명시된 human owner 또는 거버넌스 주체가 존재하는지** 확인합니다([docs/ADOPTION.md §1](docs/ADOPTION.md)). 그런 주체 없이는 채택을 진행할 수 없습니다. 그런 다음:

1. 이 프로필을 버전 *그리고* 전체 40자 commit SHA로 함께 **고정(pin)**합니다. 유동적인 `main`은 유효한 pin이 아닙니다([버전 관리](#버전-관리), [docs/ADOPTION.md §2](docs/ADOPTION.md)).
2. 대상 저장소를 그 크기가 아니라 그것이 *무엇이고 무엇을 약속하는가*로 **분류**합니다([docs/ADOPTION.md §4.0](docs/ADOPTION.md); 트리거와 권장 프로필 집합은 [PROFILE.md §5](PROFILE.md)에 있습니다). 애매하면 상위 프로필로 올려 잡습니다. specialized 트리거가 하나도 걸리지 않는 active 저장소일 때만 `[core]`를 선언하고, 참고 전용 자격이 증거로 온전히 확립될 때에 한해 `archived`를 배타적인 대안으로 선택합니다. 분류한 집합은 handoff 문구뿐 아니라 강제되는 `adoption.yaml`의 `profiles:` 필드에 적습니다.
3. [docs/ADOPTION.md §4](docs/ADOPTION.md)의 해당 경로를 **따릅니다.** active 경로는 **기능 코드를 바꾸지 않고** 읽기 전용으로 시스템을 복원하고(§4.1) 동작을 분류한 다음(§4.2), §4.3 검토 항목과 §4.4 단계적 보완으로 이어집니다. `archived` 경로는 §6.6의 네 가지 역사 정보를 기록하는 더 좁은 §4.1/§4.3 분기입니다.
4. *(선택)* handoff 전에, 고정한 체크아웃에서 [§3.6.1 `aap check` pre-flight](docs/ADOPTION.md)(또는 전체 §3.6 검증)를 실행해 구조적 공백을 일찍 잡아냅니다 — `python3 scripts/aap.py check --project-root /path/to/your/repo`(종료 코드 `0` 통과 / `1` findings / `2` 설정 / `3` 내부). 편의용 self-check이며 **기록상의 gate도, owner 승인도 아닙니다.** 강제되는 gate는 여전히 재사용 workflow입니다.
5. 결과를 브랜치에 draft pull request로 올려 **넘깁니다 — merge하지 마십시오.** merge는 §4.3 검토를 마친 human owner의 몫입니다. owner가 쓰는 언어로 아직 아무것도 결정되지 않았음을 밝히고 owner가 내려야 할 결정을 하나하나 나열한 요약으로 마무리합니다([docs/REVIEW-GUIDE.md](docs/REVIEW-GUIDE.md)). draft를 확정되었다거나 완전하다거나 끝났다고 절대 말하지 마십시오.

[§0 시작 프롬프트](docs/ADOPTION.md)가 이 지시의 더 자세한 형태입니다 — 에이전트에게는 그저 "프로필을 적용하라"고만 하지 말고 그 프롬프트를 건네십시오. 다만 위 단계는 받은 것이 이 링크뿐일 때도 그대로 유효합니다. 병렬 파일을 새로 만드는 대신 기존 저장소 관례를 프로필 산출물에 대응시키는 방법은 [docs/MAPPINGS.md](docs/MAPPINGS.md)에서 다룹니다. draft를 검토하는 owner는 [docs/REVIEW-GUIDE.md](docs/REVIEW-GUIDE.md)에서 시작하고, 낯선 용어는 [docs/GLOSSARY.md](docs/GLOSSARY.md)에 정리되어 있습니다.

---

## 저장소 구성

이 중앙 저장소의 최상위 구성은 다음과 같습니다.

```text
.
├── PROFILE.md        # sole normative text — the obligations this profile governs
├── README.md         # this overview (README.ko.md is the Korean translation)
├── schemas/          # JSON Schemas for the adopter YAML artifacts (claims, defeaters, invariants, residuals, adoption)
├── scripts/          # validate.py — the `aap` validator (see docs/ADOPTION.md §3.6)
├── templates/        # files an adopter copies into their repo (assurance YAML, AGENTS.md, github/ scaffolding, …)
├── docs/             # informative guides: ADOPTION.md, DISCLOSURE-AND-ISSUES.md, GLOSSARY.md, REVIEW-GUIDE.md, MAPPINGS.md
└── .github/          # this repo's own CODEOWNERS, issue/PR templates, and CI workflows
```

루트에는 통상적인 거버넌스 파일(CHANGELOG, CONTRIBUTING, GOVERNANCE, RELEASING, SECURITY, VERSION)도 있습니다. `templates/`의 전체 내용과 무엇을 어디에 복사할지는 [docs/ADOPTION.md](docs/ADOPTION.md)를 참고하십시오.

---

## 버전 관리

이 프로필은 semantic versioning을 따르고, tag를 붙인 release를 공개하는 것이 좋습니다.

- **Major:** 의무를 없애거나 약화하거나 실질적으로 바꿉니다.
- **Minor:** 하위 호환을 지키면서 요구사항, 프로필, 필드를 더합니다.
- **Patch:** 의무의 의도는 그대로 두고 문구를 다듬거나 schema를 고칩니다.

`v1.0.0` 이전에는 프로필이 활발한 개발 단계입니다. 이 프로젝트는 semantic versioning의 초기 개발 단계 재량에 대한 governing interpretation에 따라, 의무를 새로 더하거나 강화하는 것을 minor로 다룹니다(이미 적합하던 채택에 새 내용이 필요해질 수 있으며, 그 영향은 changelog에 명시합니다). 이는 이 프로필이 정한 `0.x` 운용 정책이지 보편적인 SemVer 규칙이라는 주장이 아닙니다. `v1.0.0`부터는 의무를 실질적으로 바꾸는 것이 major입니다.

채택 저장소는 사람이 읽는 버전과 정확한 commit SHA를 함께 고정합니다. 업그레이드는 영향 검토를 거치는 명시적인 프로젝트 변경으로 다룹니다.

release 절차는 [RELEASING.md](RELEASING.md)에 정의되어 있습니다. 루트의 `VERSION` 파일은 저장소의 release 상태를 기록합니다. 첫 release 전에는 `unreleased`, release commit에서는 정확한 tag 문자열, release 사이에는 `-dev` 접미사가 붙은 값을 가집니다. 채택하는 쪽은 자신이 선언한 버전과 `VERSION` 값이 일치하는 commit만 고정합니다.

---

## 기여 방법

제안된 개발 방향은 비규범 문서인 [v0.5 작업 설계 및 실행 계획](docs/V0.5-DESIGN.md)에 기록되어 있습니다.

프로필 내용을 분명히 하려는 질문, 민감하지 않은 schema·validator 결함, workflow 호환성 질문, 문서 개선, 현재 유효한 취약점을 드러내지 않는 제안은 공개 Issue로 다룹니다. 악용이 의심되는 취약점은 공개 Issue에 올리지 **말고** [SECURITY.md](SECURITY.md)를 따릅니다.

Pull Request에는 다음을 밝힙니다 — 영향을 받는 프로필 ID, 동작과 호환성에 미치는 영향, 추가하거나 바꾼 증거, 새로 생기거나 해소되거나 수정된 잔차, 공개 등급 분류, 다루는 Issue 또는 advisory.

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

코드는 Apache-2.0입니다 — schema·validator·workflow 자동화를 특허 조항을 갖춘 표준 라이선스로 재사용하기 위함입니다. 산문은 CC-BY-4.0으로, 출처만 밝히면 공유·수정할 수 있습니다. 템플릿은 CC0-1.0으로, 채택 저장소에 복사해도 출처 표기 의무가 없습니다.

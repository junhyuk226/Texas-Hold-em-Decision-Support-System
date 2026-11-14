**Language / 언어:** [English](#texas-holdem-decision-support-tool) | [한국어](#korean)

# Texas Hold'em Decision-Support Tool

**Python · Streamlit · Monte Carlo Simulation · AI-Assisted Development**

An offline Texas Hold'em analysis application that estimates showdown equity and compares it with pot odds to support a single, immediate call decision. It combines a weighted opponent-range baseline, 25,000-trial Monte Carlo simulation, expected-value calculations, and an interactive Streamlit interface.

> **Educational use only.** This application uses abstract points and simulated cards. It does not connect to poker accounts, handle money, place bets, automate online play, or guarantee profitable decisions.

## Project overview

The project translates a card-game decision problem into a small quantitative workflow:

1. Enter the hero's cards, community cards, number of players, and current pot/call amounts.
2. Estimate showdown outcomes under an explicitly stated opponent-card assumption.
3. Compare estimated pot-share equity with the break-even equity implied by pot odds.
4. Review the calculation, uncertainty display, and decision-support output.

The tool is designed for offline learning and analysis, not as a professional poker solver.

## Features

- **52-card visual picker** with duplicate-card prevention, undo, and flexible keyboard shortcuts.
- **2–10 player tables** with responsive seat layouts and heads-up handling.
- **Weighted opponent baseline:** a fixed `typical` weighted range for beginner-facing use. It is a modeling assumption, not an observed or empirically calibrated population range.
- **Monte Carlo equity estimation:** 25,000 simulated deals by default in the application, using a reproducible seed.
- **Win / tie / loss and pot-share equity:** ties contribute a fractional share of the pot.
- **Pot odds and single-call EV:** transparent calculations for one immediate call decision.
- **Decision-support guidance:** CHECK / BET candidates when no call is due, and FOLD / CALL with a heuristic RAISE candidate when facing a bet. Bet/raise sizing is not optimized.
- **Four analytical views:** equity versus pot odds over the hand, pot/additional-call amounts, Monte Carlo convergence, and win/tie/loss counts.
- **Light and dark chart palettes**, Korean/English interface toggle, local JSON hand history, and JSON/CSV export.

## Analytical methodology

### Monte Carlo equity

Each simulated deal samples unseen cards without replacement for the remaining board and opponent hands. The evaluator compares the best five-card hand available to each player. A strict win contributes 1 to equity, a loss contributes 0, and a tie contributes the hero's fractional share of the pot.

The application uses a fixed weighted `typical` opponent baseline and 25,000 trials per analysis. The model does not infer actual opponent behavior. Results are conditional on this assumed distribution.

### Sampling uncertainty

For observations bounded in `[0, 1]`, the app reports a conservative two-sided 95% Hoeffding half-width:

\[
\epsilon = \sqrt{\frac{\ln(2/0.05)}{2n}}
\]

At 25,000 trials, the half-width is approximately **±0.858939 percentage points (±0.86 pp)**. This quantifies Monte Carlo sampling uncertainty only. It does not measure whether the opponent-range assumption matches real players, and it is not a 95% probability that a recommendation is correct.

### Pot odds and call EV

For current pot `P`, additional call amount `C`, and estimated pot-share equity `E`:

- `Pot Odds = C / (P + C)` (0 when `C = 0`)
- `Call EV = E × P − (1 − E) × C`

This is a **single immediate call** model. It excludes later betting rounds, rake, implied odds, side pots, stack constraints, and tournament ICM.

### Action suggestions and limitations

When no amount is due, the interface can show CHECK or a small BET candidate. When facing a bet, the call calculation supports FOLD/CALL guidance; a RAISE candidate can appear when simple equity thresholds are met. BET/RAISE sizing is heuristic rather than EV-optimal. The model does not calculate fold equity, opponent response probabilities, position effects, or a multi-street game tree. This is **not a GTO solver** or an opponent tracker.

## Technology

- Python 3.10+
- Streamlit 1.65.0
- pandas 2.3.3
- Plotly 6.9.0
- Python standard library for card evaluation, simulation, probability calculations, and local persistence

## Run locally (Windows)

1. Install Python 3.10 or later.
2. Open the project folder in File Explorer.
3. Double-click `run_windows.bat`.

The first run creates a project-local `.venv/` if needed, installs the pinned requirements, checks dependencies, and launches Streamlit. Open the local URL printed in the terminal (normally `http://127.0.0.1:8501`). Press `Ctrl+C` in the terminal to stop the app.

Alternatively, open Command Prompt in the project folder and run:

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

## Run locally (macOS)

1. Install Python 3.10 or later.
2. Download or clone this repository.
3. From the project directory, run:

```bash
bash run_mac.command
```

The first run requires internet access to download the pinned Python packages. The script creates a project-local `.venv/` only if one does not exist, installs the pinned requirements, checks dependencies, and launches Streamlit. It does not reuse another project's environment or data directory. Once dependencies are installed, the app performs its analysis locally.

Alternatively, run the commands manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open `http://127.0.0.1:8501` if the browser does not open automatically. Press `Control+C` in the terminal to stop the app.

## Run automated tests

```bash
python -m unittest discover -s tests -v
python -m compileall -q .
```

The included suite covers hand-ranking edge cases, 400 randomized comparisons against exhaustive five-card evaluation, 1,000 frozen regression cases based on the v7 evaluator, Monte Carlo reproducibility and bounds, multiway simulations, heads-up input boundaries, session progression, chart construction, theme contrast, storage validation, and UI branch smoke tests.

**Latest development-container result:** 145 tests passed; Python compilation passed. The UI smoke tests use a Streamlit API stub. A final launch and native-widget/theme check in a real macOS browser is still required before claiming full end-to-end UI validation.

## Data and privacy

Hand history is stored locally at `data/hand_history/hands.json` and can be exported from the app. The application stores card selections, abstract point amounts, table settings, and calculation results. Do not add names, account details, or other personal information to saved records.

The repository's `.gitignore` excludes the complete `data/` directory, hand-history JSON/CSV exports, `.venv/`, Streamlit secrets, environment files, caches, and OS/editor artifacts. The committed `.streamlit/config.toml` disables Streamlit usage statistics, turns off the first-run email prompt, and binds the app to `127.0.0.1` so it is not exposed to other devices on the local network. No personal hand history or local virtual environment is included in the release source. See [Security and Privacy Notes](docs/SECURITY_AND_PRIVACY.md) for the release-package review scope and remaining considerations. The application code contains no account login, payment, bet execution, opponent tracking, or hand-history upload feature. Installing Python dependencies requires an internet connection; application analysis runs locally after installation.

## AI-assisted development and contributor role

AI-assisted coding tools were used to support implementation, debugging, and iterative refinement. The project developer directed product requirements and feature priorities, reviewed analytical outputs, identified issues, and guided changes to the user flow and visualizations. The code should therefore be described as an **AI-assisted development project**, not as software written entirely independently by the developer.

## Project structure

```text
.
├── app.py
├── poker_engine.py
├── decision_helpers.py
├── storage.py
├── i18n.py
├── ui_helpers.py
├── theme_helpers.py
├── requirements.txt
├── .streamlit/
│   └── config.toml
├── run_mac.command
├── run_windows.bat
├── CHANGELOG.md
├── docs/
│   ├── acceptance_matrix.md
│   ├── code_metrics.md
│   ├── methodology.md
│   ├── portfolio_summary.md
│   └── validation_report.md
└── tests/
    ├── fixtures/
    └── test_*.py
```

## License

No open-source license is currently included. Unless a license is added, the source is viewable but reuse, modification, and redistribution are not granted by this repository. Add an explicit license only after the copyright holder chooses the intended permissions.

---

# Korean (한국어)

**Texas Hold'em 의사결정 지원 도구**

**Python · Streamlit · Monte Carlo Simulation · AI-Assisted Development**

텍사스 홀덤의 쇼다운 지분(Equity)을 추정하고, 이를 팟 오즈(Pot Odds)와 비교하여 한 번의 즉각적인 콜(Call) 의사결정을 분석하는 오프라인 애플리케이션입니다. 가중치 기반 상대 범위 기준 모델, 기본 25,000회 Monte Carlo 시뮬레이션, 기대값(Expected Value, EV) 계산 및 Streamlit 인터페이스를 결합했습니다.

> **교육 및 확률 학습 목적의 도구입니다.** 추상 포인트와 시뮬레이션된 카드를 사용하며, 포커 계정에 접속하거나 실제 금전을 처리하거나 베팅을 실행하거나 온라인 플레이를 자동화하지 않습니다. 수익을 보장하지 않습니다.

## 프로젝트 개요

이 프로젝트는 카드 게임의 의사결정 문제를 다음과 같은 정량적 분석 과정으로 구성합니다.

1. 내 카드, 커뮤니티 카드, 플레이어 수, 현재 팟 및 추가 콜 금액을 입력합니다.
2. 명시된 상대 카드 분포 가정에 따라 쇼다운 결과를 추정합니다.
3. 추정한 팟 지분(Equity)을 팟 오즈가 의미하는 손익분기 지분율과 비교합니다.
4. 계산 결과, 오차 정보 및 의사결정 참고 결과를 확인합니다.

이 도구는 오프라인 학습과 분석을 위한 것으로, 전문 포커 솔버를 표방하지 않습니다.

## 주요 기능

- **52장 카드 시각 선택기:** 중복 카드 방지, 실행 취소(Undo), 유연한 키보드 단축 입력
- **2~10인 테이블:** 반응형 좌석 배치 및 헤즈업(2인) 상황 지원
- **가중치 기반 상대 범위 기준 모델:** 초보자용 고정 `typical` 가중치 범위를 사용합니다. 실제 관측 데이터로 보정된 모집단 모델은 아닙니다.
- **Monte Carlo Equity 추정:** 앱 기본 설정에서 25,000회 시뮬레이션을 실행하며, 재현 가능한 난수 시드를 사용합니다.
- **승리 / 무승부 / 패배 및 팟 지분(Equity):** 무승부는 팟의 분할 지분만큼 반영합니다.
- **팟 오즈 및 단일 콜 EV:** 한 번의 즉각적인 콜 의사결정을 투명한 계산으로 분석합니다.
- **의사결정 참고 정보:** 콜할 금액이 없을 때 CHECK / BET 후보를 표시하고, 베팅을 마주한 상황에서는 FOLD / CALL 및 휴리스틱 기반 RAISE 후보를 표시할 수 있습니다. BET / RAISE 금액은 최적화된 사이징이 아닙니다.
- **4가지 분석 시각화:** 핸드 진행에 따른 Equity와 Pot Odds, 팟 및 추가 콜 금액, Monte Carlo 수렴 과정, 승리 / 무승부 / 패배 횟수
- **사용 편의 기능:** 라이트 / 다크 차트 테마, 한국어 / 영어 인터페이스 전환, 로컬 JSON 핸드 기록 및 JSON / CSV 내보내기

## 분석 방법

### Monte Carlo Equity

각 시뮬레이션은 공개되지 않은 카드 중에서 남은 보드 카드와 상대 홀 카드를 중복 없이 추출합니다. 핸드 평가기는 각 플레이어가 사용할 수 있는 카드 중 가장 강한 5장 조합을 비교합니다. 단독 승리는 Equity에 1, 패배는 0, 무승부는 내가 받는 팟의 분할 지분을 반영합니다.

앱은 고정 가중치 `typical` 상대 기준 모델과 분석당 25,000회 시뮬레이션을 사용합니다. 실제 상대의 행동을 추론하지 않으며, 결과는 이 분포 가정에 조건부입니다.

### 표본오차

`[0, 1]` 범위의 관측값에 대해 앱은 보수적인 양측 95% Hoeffding 반폭을 표시합니다.

\[
\epsilon = \sqrt{\frac{\ln(2/0.05)}{2n}}
\]

25,000회 시뮬레이션에서 반폭은 약 **±0.858939%p (약 ±0.86 percentage points)** 입니다. 이는 Monte Carlo 표본 추출의 불확실성만 정량화합니다. 상대 범위 가정이 실제 플레이어와 일치하는지 측정하지 않으며, 의사결정 추천이 옳을 확률을 뜻하지도 않습니다.

### 팟 오즈와 콜 EV

현재 팟을 `P`, 추가 콜 금액을 `C`, 추정 팟 지분을 `E`라고 할 때:

- `Pot Odds = C / (P + C)` (`C = 0`이면 0)
- `Call EV = E × P − (1 − E) × C`

이 모델은 **현재 시점의 단일 콜 의사결정**만 다룹니다. 이후 베팅 라운드, 레이크(Rake), 임플라이드 오즈(Implied Odds), 사이드 팟, 스택 제약 및 토너먼트 ICM은 포함하지 않습니다.

### 액션 제안 및 한계

콜할 금액이 없으면 인터페이스는 CHECK 또는 소액 BET 후보를 표시할 수 있습니다. 베팅을 마주하면 콜 계산을 바탕으로 FOLD / CALL 판단을 제공하며, 단순 Equity 임계값을 충족하면 RAISE 후보가 표시될 수 있습니다. BET / RAISE 사이징은 기대값을 최적화한 방식이 아니라 휴리스틱입니다. 모델은 폴드 에퀴티, 상대방의 대응 확률, 포지션 효과 또는 여러 베팅 라운드에 걸친 게임 트리를 계산하지 않습니다. 따라서 이 도구는 **GTO 솔버**나 상대 추적기가 아닙니다.

## 기술 스택

- Python 3.10 이상
- Streamlit 1.65.0
- pandas 2.3.3
- Plotly 6.9.0
- 카드 평가, 시뮬레이션, 확률 계산 및 로컬 저장을 위한 Python 표준 라이브러리

## 로컬 실행 (Windows)

1. Python 3.10 이상을 설치합니다.
2. 파일 탐색기에서 프로젝트 폴더를 엽니다.
3. `run_windows.bat`을 더블클릭합니다.

최초 실행 시 프로젝트 내부에 `.venv/`가 없으면 생성하고, 고정된 패키지 요구사항을 설치한 뒤 의존성을 확인하고 Streamlit을 실행합니다. 터미널에 표시되는 로컬 주소를 엽니다(일반적으로 `http://127.0.0.1:8501`). 앱을 종료하려면 터미널에서 `Ctrl+C`를 누릅니다.

명령 프롬프트에서 직접 실행하려면 프로젝트 폴더에서 다음 명령을 사용합니다.

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

## 로컬 실행 (macOS)

1. Python 3.10 이상을 설치합니다.
2. 저장소를 다운로드하거나 복제합니다.
3. 프로젝트 폴더에서 다음 명령을 실행합니다.

```bash
bash run_mac.command
```

최초 실행 시 고정된 Python 패키지를 다운로드하기 위해 인터넷 연결이 필요합니다. 스크립트는 현재 프로젝트에 `.venv/`가 없을 때만 생성하고, 고정된 패키지를 설치한 뒤 의존성을 확인하고 Streamlit을 실행합니다. 다른 프로젝트의 가상환경이나 데이터 폴더를 재사용하지 않습니다. 의존성 설치 후 분석은 로컬에서 수행됩니다.

수동 실행 명령은 다음과 같습니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

브라우저가 자동으로 열리지 않으면 `http://127.0.0.1:8501`에 접속합니다. 앱을 종료하려면 터미널에서 `Control+C`를 누릅니다.

## 자동 테스트 실행

프로젝트 루트에서 다음 명령을 실행합니다.

```bash
python -m unittest discover -s tests -v
python -m compileall -q .
```

테스트에는 핸드 랭킹 경계 사례, 5장 조합 완전 탐색과 비교한 무작위 7장 패 평가 400건, v7 평가기를 기준으로 고정한 회귀 케이스 1,000건, Monte Carlo 재현성 및 오차 범위, 멀티웨이 시뮬레이션, 헤즈업 입력 경계, 세션 진행, 차트 구성, 테마 대비, 저장 데이터 검증 및 UI 분기 스모크 테스트가 포함됩니다.

**개발 컨테이너에서 기록된 최신 결과는 테스트 145개 통과 및 Python 컴파일 통과입니다.** UI 스모크 테스트는 Streamlit API 스텁을 사용합니다. 따라서 실제 macOS 브라우저의 모든 네이티브 위젯과 테마 동작까지 검증했다는 의미는 아닙니다. 전체 End-to-End UI 검증을 주장하기 전 실제 운영체제와 브라우저에서 최종 실행 확인이 필요합니다.

## 데이터 및 개인정보 보호

핸드 기록은 로컬의 `data/hand_history/hands.json`에 저장되며 앱에서 내보낼 수 있습니다. 애플리케이션은 카드 선택, 추상 포인트 금액, 테이블 설정 및 계산 결과를 저장합니다. 저장 기록에 이름, 계정 정보 또는 기타 개인정보를 입력하지 마세요.

저장소의 `.gitignore`는 `data/` 디렉터리 전체, 핸드 기록 JSON / CSV, `.venv/`, Streamlit 비밀 설정, 환경 변수 파일, 캐시 및 운영체제 / 편집기 파일을 제외합니다. 공개 소스에는 개인 핸드 기록이나 로컬 가상환경이 포함되지 않습니다. `.streamlit/config.toml`은 Streamlit 사용 통계를 비활성화하고 최초 실행 이메일 입력을 끄며, 앱을 `127.0.0.1`에 바인딩하여 로컬 네트워크의 다른 기기에 노출되지 않도록 설정합니다.

앱 코드에는 계정 로그인, 결제, 베팅 실행, 상대 추적 또는 핸드 기록 업로드 기능이 없습니다. Python 의존성 설치에는 인터넷 연결이 필요하지만 설치 후 분석은 로컬에서 실행됩니다. 공개 패키지 검토 범위와 남은 고려 사항은 [보안 및 개인정보 보호 안내](docs/SECURITY_AND_PRIVACY.md)를 참고하세요.

## AI 보조 개발 및 기여 범위

구현, 디버깅 및 반복 개선 과정에서 AI 기반 코딩 도구를 활용했습니다. 프로젝트 개발자는 제품 요구사항과 기능 우선순위를 정하고, 분석 목표와 출력 결과를 검토했으며, 문제를 식별하고 사용자 흐름과 시각화의 개선 방향을 주도했습니다. 따라서 이 프로젝트는 개발자가 모든 코드를 독립적으로 작성한 결과물이 아니라 **AI 보조 개발(AI-assisted development)을 활용한 프로젝트**로 설명합니다.

## 프로젝트 구조

```text
.
├── app.py
├── poker_engine.py
├── decision_helpers.py
├── storage.py
├── i18n.py
├── ui_helpers.py
├── theme_helpers.py
├── requirements.txt
├── .streamlit/
│   └── config.toml
├── run_mac.command
├── run_windows.bat
├── CHANGELOG.md
├── docs/
│   ├── acceptance_matrix.md
│   ├── code_metrics.md
│   ├── methodology.md
│   ├── portfolio_summary.md
│   └── validation_report.md
└── tests/
    ├── fixtures/
    └── test_*.py
```

## 라이선스

현재 저장소에는 오픈소스 라이선스가 포함되어 있지 않습니다. 별도 라이선스가 추가되기 전까지 소스 열람은 가능하지만, 다른 사람에게 코드 재사용·수정·재배포 권한이 부여된 것은 아닙니다. 저작권자가 허용할 사용 범위를 결정한 후 명시적인 라이선스를 추가해야 합니다.

# Kiwoom Trading System

키움증권 REST API와 WebSocket을 기반으로 구축하는
한국 주식 단기매매 지원 시스템입니다.

## Current Phase

Phase 34 — demo Kiwoom Cash BUY-Order Provider Send Eligibility Candidate Snapshot 기반선 v1.0

검증된 현재 기준선:

- Windows 프로젝트 전용 Python 3.13 가상환경
- Kiwoom CLI와 Windows 자격 증명 관리자 인증
- demo 환경과 mock 서버 이중 확인
- REST 종목 기본정보 조회
- WebSocket LOGIN과 실시간 종목 등록
- 삼성전자 005930, 실시간 유형 0B 등록
- 서버 PING 수신과 echo 응답
- 제한시간 수신과 정상 연결 종료
- 전체 단위테스트와 실제 demo 연결검증

## Safety Principle

Signal -> Risk Check -> Order Permission -> Order

신호엔진과 주문엔진은 직접 연결하지 않습니다.

현재 WebSocket 기준선에는 주문 기능이 없습니다.
실전 서버 연결과 실계좌 자동주문은 허용하지 않습니다.

API Key, App Secret, Access Token, 계좌 비밀정보는
소스코드, 로그, Git에 저장하지 않습니다.

## Phase 6 — 실시간 체결 데이터 정규화 기반선

Phase 6은 키움 WebSocket의 국내주식 실시간 체결 `0B` 원시 데이터를 전략·위험관리 모듈이 사용할 수 있는 안정적인 형식으로 변환한다.

### 입력 기준

- 최상위 메시지는 `trnm=REAL`이어야 한다.
- `data[*].type=0B`인 주식체결 항목만 정규화한다.
- 핵심 FID는 `20=체결시간`, `10=현재가`, `15=거래량`이다.
- 원본 FID 값은 문자열로 수신하며 정규화 후에도 감사용 `raw_values`에 보존한다.

### 시장 구분

- `005930`: KRX
- `005930_NX`: NXT
- `005930_AL`: SOR

시장 접미사를 삭제해 종목코드를 통합하더라도 원본 item과 시장 구분은 별도 필드로 유지한다.

### 부호와 단위

- 현재가의 부호는 원본 방향 정보와 가격 절댓값으로 분리한다.
- 거래량의 `+`는 매수체결, `-`는 매도체결로 보존한다.
- 등락률과 체결강도는 부동소수점 오차를 피하기 위해 `Decimal`로 변환한다.
- 누적거래대금 FID `14`의 단위는 백만원이다.

### 시간 기준

- 수신시각은 시간대가 포함된 값만 허용한다.
- 체결시간 `HHmmss`는 수신일의 KST 날짜와 결합한다.
- 시간대가 없는 수신시각이나 유효하지 않은 체결시간은 차단한다.

### 안전범위

- 입력 원본을 변경하지 않는다.
- 정규화된 원본 FID 매핑은 읽기 전용으로 보존한다.
- 누락된 핵심 FID, 잘못된 숫자, 음수 누적값, 잘못된 시장 코드는 예외로 차단한다.
- 이 단계에는 전략 판단, Risk Gate, 주문, 실계좌 연결이 포함되지 않는다.

## Phase 7 — 실시간 체결 파이프라인 기반선

Phase 5의 demo WebSocket 수신과 Phase 6의 `0B` 체결 정규화를
유한 `asyncio.Queue`로 연결한다. 단일 수신 흐름을 유지하고,
정규화할 수 없는 개별 패킷은 계수·격리하며 정상 패킷 처리는
계속한다. 종료 시 큐에 들어간 항목을 모두 처리하고 처리 건수,
정규화 성공 건수, 오류 건수와 최대 큐 깊이를 반환한다.

이 단계는 demo 조회·검증 전용이며 전략, Risk Gate, 주문,
실계좌 자동주문, 데이터베이스 저장 및 무제한 재접속을 포함하지
않는다.

## Phase 8 — 실시간 체결 상태 계산 기반선

Phase 6의 정규화된 `NormalizedTrade`를 입력으로 받아 종목과 시장별
관측 상태를 불변 객체로 계산한다. 각 체결을 적용할 때마다 기존 상태를
변경하지 않고 새로운 상태를 반환한다.

### 계산 범위

- 최초·최종 체결시각과 가격
- 관측 고가와 저가
- 전체·매수·매도·방향 미확인 체결 건수
- 전체·매수·매도 체결량과 순매수 체결량
- `가격 × 체결량`으로 계산한 관측 체결대금
- 정수 누계와 `Decimal` 나눗셈을 이용한 거래량 가중 평균가격

관측 체결대금은 입력 구간에서 직접 계산한 값이며, 키움 FID `14`의
서버 누적거래대금과는 별개의 값이다.

### 상태 전이 안전범위

- 하나의 상태에는 동일한 종목코드와 시장의 체결만 적용한다.
- 마지막 체결시각보다 오래된 체결은 차단한다.
- 동일 초에 발생한 복수 체결은 허용한다.
- 체결량·매수매도 방향·시간대 정보의 정규화 불변조건을 다시 확인한다.
- 이전 상태 객체와 정규화된 입력 객체를 변경하지 않는다.

이 단계에는 전략 신호, Risk Gate, 주문, 실계좌 연결, 데이터베이스 저장,
기존 실시간 파이프라인 연결 및 재접속 정책 변경이 포함되지 않는다.

## Phase 9 — 실시간 체결 파이프라인과 종목·시장별 상태 계산 연결 기반선

Phase 7의 `RealtimePipelineResult.trades`와 Phase 8의
`update_realtime_trade_state`를 연결하여, 한 번의 demo 파이프라인 실행에서
종목코드와 시장별 최신 관측 상태를 계산한다.

### 구현 범위

- 새 통합 모듈 `src/kiwoom_trading_system/state/realtime_trade_state_pipeline.py`를 추가한다.
- Phase 7의 기존 수신·정규화 결과와 지표를 변경하지 않고 재사용한다.
- 상태 매핑의 키는 `(instrument_code, venue)`로 하여 종목과 시장을 분리한다.
- 각 정규화 체결을 Phase 8의 `update_realtime_trade_state`에 순서대로 적용한다.
- 개별 `RealtimeTradeStateError`는 계수·격리하고 이후 정상 체결 처리를 계속한다.
- 예상하지 않은 예외는 성공으로 숨기지 않고 호출자에게 전파한다.
- 결과에는 기존 파이프라인 결과, 종목·시장별 상태, 상태 갱신 성공·오류 지표를 포함한다.
- 반환 상태 매핑은 복사본을 기반으로 읽기 전용으로 공개한다.
- 공개 인터페이스는 `src/kiwoom_trading_system/state/__init__.py`에서 내보낸다.

### 제외 범위

- 전략 신호, 종목 선정, 매수·매도 판단
- Risk Gate, 주문 허가, 주문 전송, 실계좌 자동주문
- 모바일 팝업 알림과 외부 메시지 전송
- 데이터베이스·파일 영속 저장과 재시작 복구
- WebSocket 재접속·재구독·무제한 반복 정책
- 새로운 외부 패키지와 의존성 추가
- `pyproject.toml`, `uv.lock` 및 기존 Phase 6~8 테스트 변경
- Phase 6의 `realtime_trade.py`, Phase 7의 `realtime_pipeline.py`,
  Phase 8의 `realtime_trade_state.py` 동작 변경

### 완료 기준

- 기존 Phase 7 파이프라인 결과와 Phase 8 상태 계산 결과가 하나의 통합 결과로 반환된다.
- 동일 종목의 KRX·NXT·SOR 상태가 서로 섞이지 않는다.
- 여러 종목의 체결이 각각 독립된 상태로 누적된다.
- 상태 오류가 발생한 체결과 정상 체결의 처리 결과가 지표로 구분된다.
- 이전 상태, 정규화 체결, 기존 파이프라인 결과를 변경하지 않는다.
- 변경 파일이 승인된 Phase 9 범위를 벗어나지 않는다.
- 기존 테스트와 Phase 9 신규 테스트가 모두 통과한다.

### 테스트 기준

- `tests/test_realtime_trade_state_pipeline.py`에 최소 6개의 단위테스트를 추가한다.
- 단일 종목·단일 시장의 상태 생성과 누적 계산을 검증한다.
- 동일 종목의 KRX·NXT 상태 분리와 복수 종목 상태 분리를 검증한다.
- 고가·저가·체결량·순매수 체결량·관측 체결대금·VWAP 계산을 검증한다.
- `RealtimeTradeStateError` 격리·계수와 이후 정상 체결 계속 처리를 검증한다.
- 예상하지 않은 예외 전파와 반환 매핑의 읽기 전용성을 검증한다.
- mock 입력만 사용하며 실전 WebSocket과 실계좌 주문을 호출하지 않는다.
- 기존 59개 테스트를 포함하여 전체 65개 이상의 테스트가 통과해야 한다.

## Phase 10 — demo 당일거래량 상위 후보 조회·정규화 기반선

Phase 10은 키움 공식 국내주식 순위정보 조회 TR `ka10030`을 이용해 당일거래량 상위 종목을 조회하고, 이후 실시간 관찰 대상으로 전달할 수 있는 후보 데이터로 정규화하는 읽기 전용 기반선이다.

### 공식 입력 범위

- API ID는 `ka10030`, 요청 경로는 `/api/dostk/rkinfo`를 사용한다.
- 실행 환경은 demo(mockapi)만 허용하고 real 환경은 네트워크 호출 전에 차단한다.
- `mrkt_tp`는 `000=전체`, `001=코스피`, `101=코스닥`만 허용한다.
- `sort_tp`는 `1=거래량`, `2=거래회전율`, `3=거래대금`의 공식 의미를 보존한다.
- 안전 기본값은 `mang_stk_incls=1`로 하여 관리종목을 제외한다.
- 거래량·가격·거래대금·장운영 구분 필터는 공식 요청 문자열과 함께 요청 메타데이터에 보존한다.
- 공식 요청값 `stex_tp`의 의미는 `1=KRX`, `2=NXT`, `3=통합조회`로 보존한다.
- Kiwoom mockapi가 KRX만 지원하므로 실제 demo(mockapi) 네트워크 호출은 `stex_tp=1`만 허용한다.
- `stex_tp=2`와 `stex_tp=3`은 실제 demo 네트워크 호출 전에 차단하며, 해당 값의 스키마 검증은 네트워크 없는 mock 단위테스트에서만 수행한다.
- `stex_tp=3`은 조회 범위이며 체결시장 `MarketVenue.SOR`로 변환하지 않는다.
- 후보 수 제한은 프로젝트 내부 안전장치이며 키움 공식 API 한도로 표현하지 않는다.
- 내부 후보 수 상수는 `DEFAULT_CANDIDATE_LIMIT=20`, `MIN_CANDIDATE_LIMIT=1`, `MAX_CANDIDATE_LIMIT=100`으로 고정한다.

### 정규화 계약

- 응답 키 `tdy_trde_qty_upper`의 모든 행을 API 반환 순서대로 검증한다.
- 후보에는 종목코드, 종목명, 현재가, 등락률, 거래량, 거래회전율, 거래금액과 요청 단위의 `exchange_scope`를 포함한다.
- 현재가 원문은 `raw_current_price`에 문자열 그대로 보존한다.
- 정규화 가격은 `current_price = abs(int(raw_current_price))`로 계산하고 원문 부호는 `current_price_sign`에 별도로 보존한다.
- 현재가 부호를 매수·매도 방향으로 해석하지 않는다.
- 등락률과 거래회전율은 문자열에서 직접 `Decimal`로 변환하며 중간에 `float`를 사용하지 않는다.
- 거래금액 원문은 `raw_trade_amount`에 보존하고, 키움 공식 단위인 백만원을 드러내는 `trade_amount_million_krw = int(raw_trade_amount)`로 정규화한다.
- 키움 공식 `ka10030` 명세에서 응답 필드 `trde_amt`의 단위는 `백만원`으로 확인되므로 원 단위로 환산하거나 단위를 재추론하지 않는다.
- 처리 순서는 전체 행 검증과 예상 오류 격리, 첫 번째 정상 종목 유지 방식의 중복 제거, 후보 수 제한 적용 순서로 고정한다.
- 예상 가능한 개별 행 오류는 격리·계수하고 이후 정상 행 처리를 계속한다.
- Kiwoom 비정상 반환코드와 예상하지 못한 예외는 성공으로 숨기지 않고 호출자에게 전파한다.
- 원본 응답과 요청 메타데이터는 입력 객체에서 분리한 재귀적 스냅샷으로 보존한다.

### 구현 범위

- Kiwoom REST 요청과 응답 검증은 `src/kiwoom_trading_system/brokers/kiwoom/rest/volume_ranking.py`에 둔다.
- 후보 정규화는 `src/kiwoom_trading_system/screening/volume_ranking.py`에 둔다.
- 공개 인터페이스는 `src/kiwoom_trading_system/screening/__init__.py`에서 내보낸다.
- 후보와 결과 메트릭은 `frozen=True` 데이터 클래스로 정의한다.
- 후보 목록은 `tuple`로 반환한다.
- 매핑은 원본 매핑을 먼저 복사하고 내부 값까지 재귀적으로 동결한 뒤 `MappingProxyType`으로 공개한다.
- 변경 가능한 원본 매핑을 직접 감싼 동적 `MappingProxyType` 뷰를 반환하지 않는다.
- 결과에는 정상 후보 수, 잘못된 행 수, 중복 행 수, 제한으로 제외된 후보 수를 포함한다.
- 기존 Phase 4~9 구현과 공개 동작을 변경하지 않는다.
- 새로운 외부 패키지와 의존성을 추가하지 않는다.

### 제외 범위

- 실시간 조건검색 `ka10173`과 조건검색 해제 `ka10174`
- 조건식 생성·변경 및 사용자 저장 조건식 의존
- 실제 demo에서 `stex_tp=2` 또는 `stex_tp=3`으로 요청하는 동작
- real 서버 연결과 실계좌 조회
- 후보 종목의 WebSocket 자동 등록·해제
- `MarketVenue.SOR` 추론과 Phase 6~9 체결 상태 의미 변경
- 거래금액에 1,000,000을 곱해 원 단위로 환산하거나 다른 화폐 단위로 재해석하는 동작
- 전략 점수, 매수·매도 신호와 종가매수 판단
- Risk Gate, 주문 허가, 주문 전송과 실계좌 자동주문
- 뉴스·공시·선물·미결제약정·수급 데이터 결합
- 데이터베이스·파일 저장, 재시작 복구와 모바일 팝업 알림
- 무한 재시도, 백그라운드 상시 실행과 스케줄링
- `pyproject.toml`, `uv.lock` 및 기존 Phase 4~9 테스트 변경

### 완료 기준

- Phase 10 구현 변경은 `src/kiwoom_trading_system/brokers/kiwoom/rest/volume_ranking.py`, `src/kiwoom_trading_system/screening/volume_ranking.py`, `src/kiwoom_trading_system/screening/__init__.py`, `tests/test_volume_ranking.py`, `README.md`로 제한한다.
- 정상 응답 정규화와 API 반환 순서 보존을 검증한다.
- 실제 demo 호출이 KRX로 제한되고 NXT·통합조회 요청은 네트워크 전에 차단됨을 검증한다.
- 통합조회 요청값을 `MarketVenue.SOR`로 변환하지 않음을 검증한다.
- 현재가 원문 부호 보존, 가격 절댓값 정규화와 매수·매도 방향 미추론을 검증한다.
- 거래금액 원문 보존, `백만원` 단위 정규화와 원 단위 미환산을 검증한다.
- 전체 행 검증, 오류 격리, 첫 정상 행 중복 제거, 후보 수 제한의 처리 순서를 검증한다.
- 기본 후보 수 20, 최솟값 1과 최댓값 100의 내부 제한을 검증한다.
- 비정상 반환코드와 예상하지 못한 예외 전파를 검증한다.
- 후보·메트릭·원본 응답·요청 메타데이터의 재귀적 불변성을 검증한다.
- 최소 12개의 Phase 10 단위테스트와 기존 65개 테스트를 합쳐 전체 77개 이상의 테스트가 통과해야 한다.
- 최종 demo 검증은 `stex_tp=1`과 후보 수 20으로 한 번만 제한하여 수행한다.
- mock 단위테스트와 최종 demo 검증에서 WebSocket·주문·실계좌를 호출하지 않는다.
- 키, 토큰, 계좌정보와 민감정보를 코드·테스트·로그·Git에 저장하지 않는다.

## Phase 11 — demo 당일거래량 상위 후보의 실시간 감시목록 변환 기반선

Phase 11은 Phase 10의 `VolumeRankingResult`를 이후 실시간 관찰 단계가 사용할 수 있는 불변 감시목록으로 변환한다. 이 단계는 네트워크에 연결하거나 WebSocket 등록 패킷을 전송하지 않는다.

### 입력·출력 계약

- 입력은 Phase 10의 공개 결과형 `VolumeRankingResult`로 제한한다.
- 후보는 Phase 10의 반환 순서와 원래 순위인 `source_rank`를 보존한다.
- 종목코드는 정확히 ASCII 숫자 6자리인 경우만 감시목록에 포함한다.
- 잘못된 종목코드는 `invalid_code_count`로 계수·격리하고 이후 후보 처리를 계속한다.
- 중복 종목코드는 첫 번째 정상 후보만 유지하고 `duplicate_code_count`로 계수한다.
- 빈 후보 결과는 오류가 아닌 빈 불변 감시목록으로 반환한다.
- 실시간 유형은 키움 국내주식 체결가 유형 `0B`로 고정한다.
- 결과, 후보, 지표와 종목코드 목록은 불변 데이터 클래스와 튜플로 공개한다.
- 원본 `VolumeRankingResult`와 그 후보는 변경하지 않는다.

### 구현 범위

- 신규 모듈 `src/kiwoom_trading_system/screening/realtime_watchlist.py`
- 공개 내보내기 `src/kiwoom_trading_system/screening/__init__.py`
- 신규 단위테스트 `tests/test_realtime_watchlist.py`
- 현재 단계와 공식 범위를 기록하는 `README.md`

### 제외 범위

- WebSocket 연결·종목 등록·등록 해제와 등록 패킷 전송
- 복수 종목 등록 가능 수와 서버 동작에 대한 미확인 가정
- REST 재조회와 실전 서버 호출
- 전략 신호, Risk Gate, 주문, 계좌 처리와 모바일 팝업 알림
- 데이터베이스·파일 영속 저장
- 기존 Phase 5~10 공개 함수와 처리 계약 변경
- 새로운 외부 패키지와 의존성 추가

### 완료 기준

- 후보 순서·원래 순위·종목명·조회 거래소 범위가 보존된다.
- ASCII 숫자 6자리 검증, 오류 격리와 방어적 중복 제거가 검증된다.
- 입력 수가 정상·오류·중복 처리 수의 합과 일치한다.
- 빈 결과와 잘못된 입력형의 동작이 명확히 검증된다.
- 반환 객체의 불변성과 원본 결과 불변성을 검증한다.
- 신규 단위테스트 최소 12개와 기존 전체 테스트가 모두 통과한다.
- 테스트 중 WebSocket·REST·주문·실계좌 네트워크를 호출하지 않는다.
- 변경 파일은 승인된 Phase 11의 4개 경로로 제한한다.

## Phase 12 — demo 실시간 감시목록 WebSocket 등록 요청 변환 기반선

Phase 12는 Phase 11의 `RealtimeWatchlist`를 키움 SDK의 `build_reg_packet`에 전달하여 하나의 `REG` 요청 dict로 변환하는 순수 계층이다. WebSocket 연결이나 송신은 수행하지 않는다.

### 입력·출력 계약

- 입력은 `RealtimeWatchlist`로 제한한다.
- Phase 11에서 확정한 종목 순서와 빈 목록을 그대로 `item` list로 변환한다.
- 실시간 유형은 `"0B"`만 허용한다.
- `type=["0B"]`, `grp_no="1"`, `refresh="1"`을 SDK 빌더에 전달한다.
- 호출마다 새로운 `item`·`type` list를 생성하고 입력 감시목록을 변경하지 않는다.
- 빈 감시목록의 서버 정책을 추정하지 않고 빈 `item` list로 순수 변환한다.

### 공개 API

- 신규 모듈 `src/kiwoom_trading_system/brokers/kiwoom/websocket/watchlist_registration.py`
- `build_demo_watchlist_registration_request`
- `DEMO_REGISTRATION_GROUP_NO`
- `DEMO_REGISTRATION_REFRESH`

### 제외 범위

- WebSocket 연결·로그인·송신·수신
- `REMOVE`, 재접속, heartbeat와 장시간 실행
- 실전 서버·REST·주문·원격 알림
- Phase 11 감시목록과 기존 WebSocket 기준선 변경
- 의존성·가상환경·잠금파일 변경

### 완료 기준

- 신규 단위테스트 12개와 기존 전체 회귀시험이 통과한다.
- 변경 파일은 승인된 Phase 12의 4개 경로로 제한한다.

## Phase 13 — demo 실시간 감시목록 WebSocket 등록 송수신 기반선

Phase 13은 Phase 12의 순수 `REG` 변환 결과를 기존 demo WebSocket 안전장치로 송신하고, 제한된 시간과 메시지 수 안에서 응답을 수신한 뒤 연결을 종료하는 기반선이다.

### 입력·세션 계약

- 입력은 `RealtimeWatchlist`로 제한한다.
- 빈 감시목록은 환경 조회와 클라이언트 생성 전에 명시적으로 거부한다.
- 등록 패킷은 Phase 12의 `build_demo_watchlist_registration_request`만 사용한다.
- 기존 demo 환경 검증과 공식 mock WebSocket URL 검증을 그대로 재사용한다.
- `duration_seconds`와 `max_messages`로 수신을 제한한다.
- `REG` 또는 `REAL` 수신 시 등록 확인 상태를 기록한다.
- 비동기 콜백은 `REAL` 메시지에만 호출한다.
- 실패 응답과 송신·콜백 예외는 숨기지 않고 호출자에게 전달한다.
- 정상 종료·시간 초과·예외 모두 `finally`에서 클라이언트를 닫는다.

### 구현 범위

- 신규 모듈 `src/kiwoom_trading_system/brokers/kiwoom/websocket/watchlist_baseline.py`
- 공개 내보내기 `src/kiwoom_trading_system/brokers/kiwoom/websocket/__init__.py`
- 신규 단위테스트 `tests/test_watchlist_baseline.py`
- 현재 단계와 계약을 기록하는 `README.md`

### 제외 범위

- 실전 WebSocket·REST·주문 서버 호출
- 등록 해제, 재접속, heartbeat, 무기한 수신
- 주문 생성·수정·취소와 계좌 상태 변경
- 원격 알림·푸시·외부 메시지 전송
- 의존성·가상환경·잠금파일 변경
- 기존 Phase 5·11·12 구현 변경
- 커밋과 원격 저장소 push

### 완료 기준

- 신규 비동기 단위테스트 12개가 실제 네트워크 없이 통과한다.
- 기존 110개를 포함한 전체 122개 회귀시험이 통과한다.
- README는 엄격한 UTF-8로 디코딩되고 손상 문자를 포함하지 않는다.
- 변경 파일은 승인된 Phase 13의 4개 경로로 제한한다.

## Phase 14 — demo 실시간 감시목록 WebSocket 등록 해제 요청 변환 기반선

Phase 14는 `RealtimeWatchlist`를 키움 SDK의 `build_remove_packet`에
전달하여 하나의 `REMOVE` 요청 dict로 변환하는 순수 계층이다.
WebSocket 연결·송신·수신은 수행하지 않는다.

### 변환 계약

- 그룹 번호는 Phase 12 등록과 같은 `"1"`을 사용한다.
- 종목 순서와 기본 실시간 타입 `"0B"`를 그대로 보존한다.
- `REMOVE` 요청에는 `refresh` 필드를 추가하지 않는다.
- 빈 종목 목록은 그룹·타입 전체 해제로 확대될 수 있으므로
  SDK 호출 전에 `ValueError`로 거부한다.
- 입력 감시목록과 후보·metrics 객체를 변경하지 않는다.
- SDK 예외를 숨기거나 다른 예외로 변환하지 않는다.

### 구현 범위

- 신규 모듈
  `src/kiwoom_trading_system/brokers/kiwoom/websocket/watchlist_unregistration.py`
- 공개 상수 `DEMO_UNREGISTRATION_GROUP_NO`
- 공개 함수 `build_demo_watchlist_unregistration_request`
- 신규 단위테스트 `tests/test_watchlist_unregistration.py`
- 패키지 공개 export와 README 단계 설명 갱신

### 제외 범위

- WebSocket 연결·송신·수신과 서버 응답 처리
- 기존 등록 요청 변환기와 Phase 13 송수신 기반선 변경
- 등록 해제 패킷의 실제 전송
- 실전 서버, 주문, 인증, 재접속, heartbeat, 원격 push
- 전략·리스크·screening·환경·dependency lock 변경

### 검증 기준

- Phase 14 타깃 단위테스트 12개
- 전체 테스트 134개 수집 및 회귀 실행
- AST 구문·금지 네트워크 의존성·충돌 마커·공백 오류 검사
- 변경 경로를 승인된 Phase 14의 4개 경로로 제한

## Phase 15 — demo 실시간 감시목록 WebSocket 등록 해제 송수신 기반선

Phase 15는 Phase 14의 순수 `REMOVE` 요청을 Phase 13의 제한된 demo
WebSocket 송수신 수명주기에 연결한다. 모든 검증은 mock 클라이언트와
로컬 단위테스트만 사용하며 실제 서버에는 연결하지 않는다.

### 계약

- 등록 해제 요청은 `build_demo_watchlist_unregistration_request`만 사용한다.
- 성공 응답의 `trnm="REMOVE"`를 등록 해제 승인으로 기록한다.
- 송신과 수신은 `duration_seconds`와 `max_messages`로 제한한다.
- 정상·서버 실패·송신 오류·시간초과·종료 오류에서 `close()`를 한 번 시도한다.
- 입력 감시목록과 생성된 `REMOVE` 요청을 변경하지 않는다.
- Phase 12 등록 변환, Phase 13 등록 송수신, Phase 14 해제 변환을 재사용한다.

### 공개 API

- `run_demo_watchlist_unregistration_baseline`
- `demo_watchlist_unregistration_baseline_passed`

### 제외 범위

- 실전·demo 실제 WebSocket 연결과 외부 네트워크 호출
- 실전 인증, 주문, 계좌 변경, 재접속과 heartbeat
- 의존성, `.env`, 자격증명과 잠금파일 변경
- Git stage, commit과 push

### 완료 기준

- Phase 15 신규 mock 단위테스트 12개와 기존 전체 테스트를 통과한다.
- 전체 146개 테스트를 독립적으로 5회 통과한다.
- 변경 경로를 승인된 Phase 15의 4개 파일로 제한한다.

## Phase 16 — demo 실시간 감시목록 WebSocket 통합 수명주기 기반선

Phase 16은 Phase 12의 `REG` 요청과 Phase 14의 `REMOVE` 요청을 하나의
mock WebSocket 클라이언트와 하나의 demo 연결에서 순서대로 검증한다.
모든 단위테스트는 외부 네트워크·인증·실제 서버 연결 없이 실행한다.

### 계약

- `REG → 성공 REG 응답 → 제한된 REAL → REMOVE → 성공 REMOVE 응답 → close`
  순서를 하나의 연결과 하나의 메시지 iterator에서 수행한다.
- 요청은 기존 등록·등록 해제 생성기를 그대로 호출하며 생성된 dict를 변경하지 않는다.
- 입력 감시목록, 후보와 metrics 객체를 변경하지 않는다.
- `duration_seconds`는 통합 수신 기한이며 `max_realtime_messages`는 `REAL`
  메시지 수만 제한한다.
- `asyncio.wait_for` 시간초과·취소, 서버·송신·연결·종료 예외를 성공 상태로
  바꾸지 않고 `close()`를 한 번 시도한 뒤 전파한다.
- Phase 13·15 공개 함수와 반환 계약은 변경하지 않는다.

### 공개 API

- `run_demo_watchlist_lifecycle_baseline`
- `demo_watchlist_lifecycle_baseline_passed`

### 제외 범위

- 실전·demo 실제 WebSocket 및 REST 연결과 기타 외부 네트워크 호출
- 실제 인증, 주문, 계좌·잔고 변경, 재접속, heartbeat와 상시 실행
- 의존성, `.env`, 자격증명, `pyproject.toml`과 `uv.lock` 변경
- Git stage, commit과 push

### 완료 기준

- Phase 16 신규 mock 단위테스트 16개와 Phase 12~16 타깃 테스트를 통과한다.
- 전체 162개 테스트를 독립적으로 5회 통과한다.
- 변경 경로를 승인된 Phase 16의 4개 파일로 제한한다.

## Phase 17 — demo 실시간 감시목록 WebSocket 연결 종료 감지·재연결·감시목록 재등록 복구 기반선 v1.0

- 범위: demo·mock WebSocket에서 정상 스트림 종료 또는 연결 계열 오류를 감지하고 제한된 재연결을 수행한다.
- 재등록: 각 재연결은 SDK 연결(LOGIN 포함) 완료 뒤 동일한 감시목록 REG 요청을 다시 보낸다.
- 수신 통제: 연결마다 하나의 비동기 메시지 반복자만 순차 사용하며 REAL 수신 한도는 재연결 전후 누적한다.
- 재시도: 기본 최대 2회, 0.25초부터 최대 2초까지 제한된 지수 backoff를 사용한다.
- 예외: 공유 실행기한 만료, 취소, 서버 응답 실패, 치명 오류와 REMOVE 전송 이후 종료는 재시도하지 않고 정리 후 전파한다.
- 종료: 성공·실패·취소 모두 생성한 각 클라이언트를 정확히 한 번 닫는다.
- 제외: 실전 서버, 실계좌, 주문, 외부 네트워크 실행, 인증·의존성 변경, 기존 Phase 12~16 공개 계약 변경.
- 테스트: Phase 17 mock 테스트 14개와 기존 162개를 합친 전체 176개 회귀 테스트를 통과해야 한다.

## Phase 18 — demo 실시간 감시목록 WebSocket 복구 스트림·체결 정규화·종목·시장별 상태 계산 통합 기반선 v1.0

- 입력: Phase 17이 등록 승인 뒤 수락한 `REAL` 메시지만 비동기 callback으로 순서대로 전달한다.
- 복구: 재연결 전후 callback 순서와 누적 REAL 한도를 보존하며 callback은 전달 메시지마다 한 번 호출한다.
- 오류 분류: callback의 `OSError`를 포함한 처리 오류는 연결 오류로 오인해 재시도하지 않고 정리 후 원래 예외를 전파한다.
- 정규화: Phase 6의 `normalize_trade_packet`으로 `0B` 체결만 정규화하며 예상 가능한 정규화 오류는 기록하고 다음 REAL을 계속 처리한다.
- 상태: Phase 8의 `update_realtime_trade_state`를 사용하여 `(종목코드, KRX/NXT/SOR)`별 관측 상태를 분리한다.
- 결과: 요약·상태 mapping과 오류 메시지 tuple을 복사해 읽기 전용 결과로 반환한다.
- 의미: 신뢰 가능한 거래 고유 ID가 없으므로 서버 재전송 중복 제거는 하지 않으며, 결과는 수신된 스트림 기준 관측 상태다.
- 예외: 예상 가능한 `TradeNormalizationError`와 `RealtimeTradeStateError`만 격리하며 나머지 오류·시간초과·취소·복구 소진은 전파한다.
- 제외: 실전 서버·실계좌·주문·전략·Risk Gate·모바일 팝업 알림·영속화·재시작 복원·인증·의존성·Git stage/commit/push.
- 테스트: Phase 18 mock 테스트를 14개 이상 추가하고 기존 176개를 포함한 전체 190개 이상 회귀 테스트를 통과해야 한다.

## Phase 19 — demo 실시간 감시목록 후보 메타데이터·관측 상태 전략 입력 스냅샷 기반선 v1.0

Phase 19는 Phase 11의 감시목록 후보 메타데이터와 Phase 18의 복구 스트림 관측 상태를 결합하여, 이후 전략 계층이 읽을 수 있는 불변 관측 스냅샷을 만드는 순수 변환 기반선이다.
Phase 19 구현·검증이 완료되기 전까지 `Current Phase`는 Phase 18로 유지한다.

### 입력 계약

- 입력은 `RealtimeWatchlist`와 `WatchlistRecoveryStatePipelineResult`로 제한한다.
- 감시목록 후보의 순서, `source_rank`, `stock_code`, `stock_name`, `exchange_scope`, `realtime_type`을 보존한다.
- Phase 18 상태 키의 종목코드는 감시목록에 존재해야 한다.
- 상태 키의 종목코드·시장과 `RealtimeTradeState` 내부 종목코드·시장이 일치해야 한다.
- 새로운 시장 의미, 전략 의미 또는 주문 의미를 추론하지 않는다.
- 잘못된 입력 타입은 `TypeError`, 계약 불일치는 Phase 19 전용 `WatchlistObservationError`로 차단한다.

### 출력 계약

- 후보별 불변 결과 `WatchlistCandidateObservation`을 반환한다.
- 전체 불변 결과 `WatchlistObservationSnapshot`을 반환한다.
- 후보별 상태는 `MarketVenue -> RealtimeTradeState` 읽기 전용 mapping으로 공개한다.
- 체결이 아직 없는 후보도 제거하지 않고 빈 상태 mapping으로 유지한다.
- snapshot은 감시목록 순서의 observation tuple, 전체 후보 수, 관측 후보 수, 미관측 후보 수, 전체 상태 수와 realtime type을 보존한다.
- 입력 감시목록, Phase 18 결과, 상태 객체와 원본 mapping을 변경하지 않는다.

### 공개 API

- 신규 모듈 `src/kiwoom_trading_system/strategies/watchlist_observation.py`
- `WatchlistObservationError`
- `WatchlistCandidateObservation`
- `WatchlistObservationSnapshot`
- `build_watchlist_observation_snapshot`
- 공개 export는 `src/kiwoom_trading_system/strategies/__init__.py`에서 제공한다.

### 상태·예외·시간초과·취소·종료 계약

- Phase 19는 순수 동기 변환 계층으로 WebSocket client, task, queue 또는 background loop를 생성하지 않는다.
- 자체 timeout을 만들지 않고 cancellation을 포착하거나 변환하지 않는다.
- `connect`, `send`, `recv`, `close`를 호출하지 않는다.
- Phase 17·18의 시간초과, 취소, 복구 소진과 예상하지 않은 예외를 성공으로 바꾸지 않는다.

### 재시도·복구 경계

- Phase 19의 retry와 reconnect 횟수는 0이다.
- WebSocket 재연결·재등록·bounded exponential backoff는 Phase 17의 책임으로 유지한다.
- Phase 19는 체결 정규화를 다시 수행하지 않고 Phase 18 상태를 다시 계산하지 않는다.

### 구현 허용 경로

- `README.md`
- `src/kiwoom_trading_system/strategies/__init__.py`
- `src/kiwoom_trading_system/strategies/watchlist_observation.py`
- `tests/test_watchlist_observation.py`

### 제외 범위

- `brokers`, `market_data`, `screening`, `state`, `orders`, `risk`, `alerts` 기존 구현 변경
- 기존 테스트 파일 변경
- 전략 점수, 매수·매도 신호, 종목 선정과 매매 판단
- Risk Gate, 주문 허가, 주문 생성·수정·취소·전송과 실계좌 변경
- 실전 WebSocket·REST·계좌 조회와 외부 네트워크 호출
- 모바일 팝업 알림, 데이터베이스·파일 영속 저장과 재시작 복원
- Credential, `.env`, `pyproject.toml`, `uv.lock`과 dependency 변경
- Git stage, commit, push, reset, restore, clean

### 테스트·완료 기준

- Phase 19 구현 시 신규 mock 단위테스트를 최소 16개 추가한다.
- 후보 순서·메타데이터 보존, KRX/NXT/SOR 상태 분리, 미관측 후보 유지와 입력 불변성을 검증한다.
- 예상하지 않은 종목 상태, 종목코드·시장 불일치와 잘못된 입력 타입을 검증한다.
- 결과 tuple·상태 mapping의 불변성과 package public export identity를 검증한다.
- 실제 네트워크·Credential·주문·계좌를 사용하지 않는다.
- 현재 196개 전체 회귀테스트를 보존하고 Phase 19 신규 16개를 포함하여 구현 후 최소 212개 이상이 통과해야 한다.
- failures=0, errors=0, skipped=0, 테스트 프로세스 exit code=0과 예상·실행 테스트 수 일치를 모두 만족해야 한다.
- 구현 변경은 승인된 4개 경로로만 제한하고 commit·push는 별도 승인한다.

## Phase 20 — demo 실시간 감시목록 관측 스냅샷 전략 진입 신호 후보 평가 기반선 v1.0

Phase 20는 Phase 19의 `WatchlistObservationSnapshot`을 입력으로 받아, 순수 동기 evaluator가 각 후보를 `NO_SIGNAL` 또는 `ENTRY_CANDIDATE`로 평가하고 향후 Risk Check가 소비할 수 있는 불변 전략 진입 신호 스냅샷을 만드는 기반선이다.
Phase 20 구현·검증이 완료되기 전까지 `Current Phase`는 Phase 19로 유지한다.

### 입력 계약
- 입력은 `WatchlistObservationSnapshot`과 순수 동기 `evaluator`로 제한한다.
- `evaluator`는 후보별 `WatchlistCandidateObservation`을 정확히 1회 평가한다.
- 잘못된 snapshot 타입 또는 호출 불가능한 evaluator는 `TypeError`로 차단한다.
- evaluator 반환값은 `WatchlistSignalEvaluation`이어야 하며 다른 타입은 `TypeError`로 차단한다.
- Phase 19 후보 순서, `source_rank`, `stock_code`, `stock_name`, `exchange_scope`, `realtime_type`을 보존한다.
- Phase 19의 관측 상태를 다시 계산하거나 새로운 시장 의미를 추론하지 않는다.

### Signal 계약
- `WatchlistSignalDecision`은 `NO_SIGNAL`과 `ENTRY_CANDIDATE`만 허용한다.
- `NO_SIGNAL`은 `venue=None`이어야 한다.
- `ENTRY_CANDIDATE`는 `venue`를 반드시 지정해야 한다.
- `ENTRY_CANDIDATE`의 venue는 해당 후보의 `observation.states`에 실제 존재하는 `MarketVenue`만 허용한다.
- 관측 상태가 없는 후보는 `ENTRY_CANDIDATE`가 될 수 없다.
- KRX·NXT·SOR 중 어느 시장을 사용할지 builder가 자동 선택하거나 추론하지 않는다.
- `reason_code`는 비어 있거나 공백만 있는 문자열을 허용하지 않는다.
- `ENTRY_CANDIDATE`는 주문 승인, Risk Gate 통과 또는 실제 매수 명령을 의미하지 않는다.
- 향후 연결 순서는 `ENTRY_CANDIDATE -> Risk Check -> Order Permission -> Order`로 유지한다.

### 출력 계약
- 후보별 불변 결과 `WatchlistCandidateSignal`을 반환한다.
- 전체 불변 결과 `WatchlistSignalSnapshot`을 반환한다.
- 입력 후보를 제거하거나 재정렬하지 않고 모든 후보를 결과에 유지한다.
- snapshot은 signal tuple, 전체 후보 수, `NO_SIGNAL` 수, `ENTRY_CANDIDATE` 수와 realtime type을 보존한다.
- 입력 snapshot, candidate observation, state mapping과 evaluator 반환 객체를 변경하지 않는다.
- evaluator의 예상하지 않은 예외는 성공으로 숨기지 않고 호출자에게 그대로 전파한다.

### 공개 API
- 신규 모듈 `src/kiwoom_trading_system/strategies/watchlist_signal.py`
- `WatchlistSignalError`
- `WatchlistSignalDecision`
- `WatchlistSignalEvaluation`
- `WatchlistCandidateSignal`
- `WatchlistSignalSnapshot`
- `build_watchlist_signal_snapshot`
- 공개 export는 `src/kiwoom_trading_system/strategies/__init__.py`에서 제공한다.

### 실행·재시도·복구 경계
- Phase 20은 순수 동기 변환 계층으로 WebSocket client, task, queue 또는 background loop를 생성하지 않는다.
- 자체 timeout, retry, reconnect 횟수는 0이다.
- `connect`, `send`, `recv`, `close`를 호출하지 않는다.
- Phase 17·18의 재연결·정규화·상태 계산 책임을 가져오지 않는다.
- Phase 19의 observation snapshot을 변경하거나 재생성하지 않는다.

### 구현 허용 경로
- `README.md`
- `src/kiwoom_trading_system/strategies/__init__.py`
- `src/kiwoom_trading_system/strategies/watchlist_signal.py`
- `tests/test_watchlist_signal.py`

### 제외 범위
- 실제 전략 공식, threshold, confidence score와 임의 numeric scoring
- `SELL`, `EXIT`, 청산 판단과 보유 포지션 관리
- 손절가, 목표가, 주문수량과 자금배분
- Risk Gate, 주문 허가, 주문 생성·수정·취소·전송
- 실전 WebSocket·REST·계좌·잔고 조회와 외부 네트워크 호출
- Credential, `.env`, `pyproject.toml`, `uv.lock`과 dependency 변경
- 모바일 팝업 알림, 데이터베이스·파일 영속 저장과 재시작 복원
- `brokers`, `market_data`, `screening`, `state`, `orders`, `risk`, `alerts` 기존 구현 변경
- 기존 테스트 파일 변경
- Git stage, commit, push, reset, restore, clean

### 테스트·완료 기준
- Phase 20 구현 시 신규 mock 단위테스트를 최소 20개 추가한다.
- 정상 `NO_SIGNAL`과 `ENTRY_CANDIDATE`, 후보 순서·메타데이터·realtime type 보존을 검증한다.
- KRX·NXT·SOR venue 검증, 미관측 후보의 ENTRY 차단과 잘못된 venue를 검증한다.
- 잘못된 snapshot/evaluator/평가 반환 타입과 비어 있는 `reason_code`를 검증한다.
- evaluator 예상 밖 예외 전파, 입력·출력 불변성과 package public export identity를 검증한다.
- 실제 네트워크·Credential·계좌·주문을 사용하지 않는다.
- 현재 212개 전체 회귀테스트를 보존하고 Phase 20 신규 최소 20개를 포함하여 구현 후 최소 232개 이상이 통과해야 한다.
- failures=0, errors=0, skipped=0, 테스트 프로세스 exit code=0과 예상·실행 테스트 수 일치를 모두 만족해야 한다.
- 구현 변경은 승인된 4개 경로로만 제한하고 commit·push는 별도 승인한다.

## Phase 21 — demo 전략 진입 신호 후보 Risk Check 평가 스냅샷 기반선 v1.0

Phase 21은 Phase 20의 `WatchlistSignalSnapshot`을 입력으로 받아, `ENTRY_CANDIDATE` 후보만 순수 동기 checker로 Risk Check하고 주문 허가와 분리된 불변 Risk 평가 스냅샷을 만드는 기반선이다.
Phase 21 구현·검증이 완료되기 전까지 `Current Phase`는 Phase 20으로 유지한다.

### 입력 계약
- 입력은 `WatchlistSignalSnapshot`과 순수 동기 `checker`로 제한한다.
- `NO_SIGNAL` 후보에는 checker를 호출하지 않는다.
- `ENTRY_CANDIDATE` 후보마다 해당 `WatchlistCandidateSignal`을 checker에 정확히 1회 전달한다.
- 잘못된 snapshot 타입 또는 호출 불가능한 checker는 `TypeError`로 차단한다.
- checker 반환값은 `WatchlistRiskEvaluation`이어야 하며 다른 타입은 `TypeError`로 차단한다.
- Phase 20 후보 순서, `source_rank`, `stock_code`, `stock_name`, `exchange_scope`, `realtime_type`, signal decision, `venue`, signal `reason_code`를 보존한다.
- Phase 20의 signal decision이나 venue를 다시 계산하거나 변경하지 않는다.

### Risk Check 계약
- `WatchlistRiskDecision`은 `RISK_CLEAR`와 `RISK_BLOCKED`만 허용한다.
- `WatchlistRiskEvaluation`은 `decision`, `reason_code` 두 필드로 구성한다.
- Risk Check를 실제 수행한 결과의 `reason_code`는 비어 있거나 공백만 있는 문자열을 허용하지 않는다.
- `NO_SIGNAL` 후보는 Risk Check 미적용으로 유지하고 `risk_decision=None`, `risk_reason_code=None`으로 기록한다.
- `RISK_CLEAR`는 현재 checker가 차단 사유를 반환하지 않았다는 뜻일 뿐 주문 허가, 주문 승인 또는 실제 매수 명령을 의미하지 않는다.
- `RISK_BLOCKED` 후보는 Phase 21 결과에서 차단 상태로 보존하며 `ENTRY_CANDIDATE` 또는 주문 가능 상태로 되돌리지 않는다.
- 실제 계좌 비중, 손실한도, 주문수량, 손절·목표가 등 numeric Risk 정책을 builder가 임의 생성하거나 추론하지 않는다.
- 연결 순서는 `ENTRY_CANDIDATE -> Risk Check -> Order Permission -> Order`를 유지한다.

### 출력 계약
- 후보별 불변 결과 `WatchlistCandidateRisk`를 반환한다.
- 전체 불변 결과 `WatchlistRiskSnapshot`을 반환한다.
- `WatchlistCandidateRisk`는 `source_rank`, `stock_code`, `stock_name`, `exchange_scope`, `realtime_type`, `signal_decision`, `venue`, `signal_reason_code`, `risk_decision`, `risk_reason_code`를 보존한다.
- `WatchlistRiskSnapshot`은 `risks`, `candidate_count`, `no_signal_count`, `risk_checked_count`, `risk_clear_count`, `risk_blocked_count`, `realtime_type`을 보존한다.
- `candidate_count = no_signal_count + risk_checked_count`를 만족해야 한다.
- `risk_checked_count = risk_clear_count + risk_blocked_count`를 만족해야 한다.
- Phase 20의 `entry_candidate_count`와 Phase 21의 `risk_checked_count`는 일치해야 한다.
- 입력 후보를 제거하거나 재정렬하지 않고 모든 후보를 결과에 유지한다.
- 입력 snapshot, candidate signal과 checker 반환 객체를 변경하지 않는다.
- checker의 예상하지 않은 예외는 `RISK_BLOCKED`나 성공으로 숨기지 않고 호출자에게 그대로 전파한다.

### 공개 API
- 신규 모듈 `src/kiwoom_trading_system/risk/watchlist_risk.py`
- `WatchlistRiskError`
- `WatchlistRiskDecision`
- `WatchlistRiskEvaluation`
- `WatchlistCandidateRisk`
- `WatchlistRiskSnapshot`
- `build_watchlist_risk_snapshot`
- builder 시그니처는 `build_watchlist_risk_snapshot(snapshot, checker)`로 고정한다.
- 공개 export는 `src/kiwoom_trading_system/risk/__init__.py`에서 제공한다.

### 실행·재시도·복구 경계
- Phase 21은 순수 동기 변환 계층으로 WebSocket client, task, queue 또는 background loop를 생성하지 않는다.
- 자체 timeout, retry, reconnect 횟수는 0이다.
- REST/WebSocket, `connect`, `send`, `recv`, `close`를 호출하지 않는다.
- Credential, 계좌, 잔고, 주문 API에 접근하지 않는다.
- 파일·데이터베이스 영속 저장을 수행하지 않는다.
- Phase 20의 signal snapshot을 변경하거나 재생성하지 않는다.

### 구현 허용 경로
- `README.md`
- `src/kiwoom_trading_system/risk/__init__.py`
- `src/kiwoom_trading_system/risk/watchlist_risk.py`
- `tests/test_watchlist_risk.py`

### 제외 범위
- 최대 투자금액·비중, 1회·일일 손실한도 등 numeric Risk threshold와 임의 scoring
- 손절가, 목표가, 주문수량, 자금배분과 포지션 관리
- Order Permission, 주문 승인과 주문 생성·수정·취소·전송
- `SELL`, `EXIT`와 청산 판단
- 실전 WebSocket·REST·계좌·잔고 조회와 외부 네트워크 호출
- Credential, `.env`, `pyproject.toml`, `uv.lock`과 dependency 변경
- 모바일 팝업 알림, 데이터베이스·파일 영속 저장과 재시작 복원
- `brokers`, `market_data`, `screening`, `state`, `orders`, `alerts` 기존 구현 변경
- Phase 20 `strategies/watchlist_signal.py`와 기존 테스트 파일 변경
- Git stage, commit, push, reset, restore, clean

### 테스트·완료 기준
- Phase 21 구현 시 신규 mock 단위테스트를 최소 24개 추가한다.
- 정상 `RISK_CLEAR`, `RISK_BLOCKED`, `NO_SIGNAL` checker 미호출과 ENTRY 후보당 checker 정확히 1회 호출을 검증한다.
- 후보 순서·메타데이터·venue·signal reason 보존과 혼합 후보 처리를 검증한다.
- 잘못된 snapshot/checker/평가 반환 타입과 비어 있는 Risk `reason_code`를 검증한다.
- checker 예상 밖 예외 전파, count 산술 불변조건, 입력·출력 불변성과 package public export identity를 검증한다.
- 실제 네트워크·Credential·계좌·주문을 사용하지 않는다.
- 현재 239개 전체 회귀테스트를 보존하고 Phase 21 신규 최소 24개를 포함하여 구현 후 최소 263개 이상이 통과해야 한다.
- failures=0, errors=0, skipped=0, 테스트 프로세스 exit code=0과 예상·실행 테스트 수 일치를 모두 만족해야 한다.
- 구현 변경은 승인된 4개 경로로만 제한하고 commit·push는 별도 승인한다.

## Phase 22 — demo Risk Check 통과 후보 Order Permission 평가 스냅샷 기반선 v1.0

### 목적

Phase 21 `WatchlistRiskSnapshot`에서 `RISK_CLEAR`로 판정된 후보만 후속 주문 허가 정책(Order Permission)으로 평가한다.
이 단계는 내부 정책 게이트만 정의하며 실제 주문 승인, 주문가능수량 조회, 주문 생성·정정·취소·전송은 수행하지 않는다.

### 처리 순서

`ENTRY_CANDIDATE -> Risk Check -> Order Permission -> Order`

- Phase 21 `RISK_BLOCKED` 후보는 Order Permission checker 호출 대상이 아니다.
- Phase 21 `RISK_CLEAR` 후보만 Order Permission checker를 정확히 1회 호출한다.
- Order Permission 결과는 `ORDER_PERMITTED` 또는 `ORDER_DENIED` 중 하나다.
- `ORDER_PERMITTED`는 내부 정책상 후속 Order 단계로 전달 가능하다는 뜻이며, 키움증권 주문 승인·주문가능금액·체결 가능성을 뜻하지 않는다.

### 구현 패키지 및 예정 경로

- package: `kiwoom_trading_system.orders`
- `src/kiwoom_trading_system/orders/__init__.py`
- `src/kiwoom_trading_system/orders/watchlist_order_permission.py`
- `tests/test_watchlist_order_permission.py`

이 Phase 22 계약 등록 단계에서는 위 구현 파일을 생성·수정하지 않는다.

### 공개 API 계약

`kiwoom_trading_system.orders`는 구현 완료 시 아래 이름을 공개한다.

- `WatchlistOrderPermissionError`
- `WatchlistOrderPermissionDecision`
- `WatchlistOrderPermissionEvaluation`
- `WatchlistCandidateOrderPermission`
- `WatchlistOrderPermissionSnapshot`
- `build_watchlist_order_permission_snapshot`

### Decision 계약

`WatchlistOrderPermissionDecision`은 아래 두 값만 허용한다.

- `ORDER_PERMITTED`
- `ORDER_DENIED`

`ORDER_DENIED`는 정상적인 정책 판정 결과이며 예외가 아니다.

### WatchlistOrderPermissionEvaluation

frozen dataclass로 구현하며 필드 순서를 고정한다.

1. `decision`
2. `reason_code`

`reason_code`는 비어 있지 않은 문자열이어야 한다.

### WatchlistCandidateOrderPermission

frozen dataclass로 구현하며 Phase 21의 후보 추적 필드를 그대로 보존한 뒤 Order Permission 결과를 추가한다.

1. `source_rank`
2. `stock_code`
3. `stock_name`
4. `exchange_scope`
5. `realtime_type`
6. `signal_decision`
7. `venue`
8. `signal_reason_code`
9. `risk_decision`
10. `risk_reason_code`
11. `order_permission_decision`
12. `order_permission_reason_code`

upstream 값은 임의 보정·정규화·재해석하지 않는다.

### WatchlistOrderPermissionSnapshot

frozen dataclass로 구현하며 필드 순서를 고정한다.

1. `permissions`
2. `candidate_count`
3. `no_signal_count`
4. `risk_checked_count`
5. `risk_clear_count`
6. `risk_blocked_count`
7. `permission_checked_count`
8. `order_permitted_count`
9. `order_denied_count`
10. `realtime_type`

`permissions`에는 Order Permission checker를 실제 수행한 `RISK_CLEAR` 후보 결과만 들어간다.

### Builder 계약

공개 builder 이름과 인자 순서를 아래와 같이 고정한다.

`build_watchlist_order_permission_snapshot(snapshot, checker)`

- `snapshot`은 Phase 21 `WatchlistRiskSnapshot`이어야 한다.
- `checker`는 Order Permission 평가 callable이어야 한다.
- `checker`는 각 `RISK_CLEAR` 후보에 대해 정확히 1회 호출한다.
- `RISK_BLOCKED` 후보에 대해서는 `checker`를 호출하지 않는다.
- 입력 후보 순서를 보존하며 `source_rank`를 재번호하지 않는다.
- 성공 시 하나의 완전한 `WatchlistOrderPermissionSnapshot`만 반환한다.
- 부분 성공 Snapshot은 반환하지 않는다.

### Count 불변식

성공 반환 시 아래 관계를 모두 만족해야 한다.

- `candidate_count = no_signal_count + risk_checked_count`
- `risk_checked_count = risk_clear_count + risk_blocked_count`
- `permission_checked_count = risk_clear_count`
- `permission_checked_count = order_permitted_count + order_denied_count`
- `len(permissions) = permission_checked_count`

Phase 21에서 전달받은 count와 `realtime_type`은 임의 수정하지 않는다.

### 오류 및 실패 계약

아래 상황은 `WatchlistOrderPermissionError` 계열의 fail-closed 실패로 처리한다.

- `snapshot` 타입 또는 구조가 계약과 다름
- upstream count 불변식 위반
- 후보 필드 또는 `source_rank` 계약 위반
- `checker`가 callable이 아님
- `checker` 호출 중 예외 발생
- `checker` 반환 타입이 `WatchlistOrderPermissionEvaluation`이 아님
- 허용되지 않은 decision 값
- 빈 문자열 또는 공백-only `reason_code`
- 부분 결과만 생성된 상태

임의 retry, 오류 무시, 자동 보정, 부분 Snapshot 반환은 금지한다.

### 보안·네트워크·주문 경계

Phase 22에서는 아래 작업을 수행하지 않는다.

- 키움 실제 주문 `kt10000`, `kt10001`, `kt10002`, `kt10003`
- 계좌 기반 주문가능수량 조회 `kt00011`
- 주문 수량·가격·거래유형 생성
- 주문 생성·정정·취소·전송
- 실계좌·예수금·잔고 접근
- App Key, Secret, token, Credential 접근
- REST/WebSocket 외부 네트워크 접속
- dependency 추가·변경

테스트는 mock/local 순수 로직으로만 수행한다.

### 호환성 계약

- Phase 20 공개 API와 동작을 변경하지 않는다.
- Phase 21 공개 API와 동작을 변경하지 않는다.
- Phase 21 `WatchlistRiskSnapshot`이 Phase 22의 유일한 upstream 입력 계약이다.
- `orders` 이외의 새 `order` 또는 `execution` package를 만들지 않는다.
- 기존 `src/kiwoom_trading_system/orders/__init__.py`와 호환되도록 구현한다.

### 테스트 계약

구현 단계에서는 최소한 아래를 검증한다.

- 공개 export와 builder signature
- enum 값 정확성
- 모든 Phase 22 dataclass의 frozen 여부와 필드 순서
- 빈 입력
- 전부 `RISK_BLOCKED`
- 전부 `RISK_CLEAR`
- PERMITTED/DENIED 혼합
- `RISK_BLOCKED` checker 미호출
- 각 `RISK_CLEAR` checker 정확히 1회 호출
- source order 및 `source_rank` 보존
- count 불변식
- invalid snapshot/type/decision/reason
- checker exception
- 부분 결과 금지
- Phase 20/21 compatibility
- 전체 회귀테스트

### Phase 경계

이 계약을 README에 등록하는 것만으로 Phase 22 구현이 완료된 것으로 보지 않는다.
Phase 22 구현·테스트·검증·closure가 모두 완료되기 전까지 `Current Phase`는 Phase 21로 유지한다.
README 계약 등록 이후에도 별도 승인 전에는 구현, `git add`, commit, push, 실주문, 실계좌, 외부 네트워크를 수행하지 않는다.

## Phase 23 — demo `ORDER_PERMITTED` 후보 Order Intent 생성 스냅샷 기반선 v1.0

### 목적과 경계

Phase 23은 Phase 22 `WatchlistOrderPermissionSnapshot`을 입력으로 받아 `ORDER_PERMITTED` 후보만 broker-neutral Order Intent로 변환하고, 검증된 불변 스냅샷으로 집계하는 순수 Order-layer 기반선이다.

Phase 23의 Order Intent는 순수 Order-layer 모델이다. 키움 `kt00011`, `kt10000`, `kt10001`, `kt10002`, `kt10003`, 실계좌, credential, OAuth/token 및 외부 네트워크에 접근하거나 의존하지 않는다.

`demo`는 키움 모의투자 서버 호출 허용을 뜻하지 않는다. Phase 23은 `api.kiwoom.com`과 `mockapi.kiwoom.com` 모두 호출하지 않는다.

연결 순서는 다음과 같이 유지한다.

`ENTRY_CANDIDATE -> Risk Check -> Order Permission -> Order Intent -> [향후 Account / Buying-Power Validation] -> [향후 Broker Mapping] -> [향후 Order Submission]`

### 입력 계약

입력은 Phase 22 `WatchlistOrderPermissionSnapshot`이다.

- `ORDER_PERMITTED` 후보만 Order Intent planner 호출 대상이다.
- `ORDER_DENIED` 후보에는 planner를 호출하지 않는다.
- Phase 22의 후보 순서와 `source_rank`를 그대로 보존한다.
- Phase 22의 upstream 필드와 count를 임의 보정·정규화·재해석하지 않는다.

### 공개 API 계약

구현 완료 시 `kiwoom_trading_system.orders`는 아래 7개 이름을 공개한다.

- `WatchlistOrderIntentError`
- `WatchlistOrderIntentSide`
- `WatchlistOrderIntentStyle`
- `WatchlistOrderIntentEvaluation`
- `WatchlistCandidateOrderIntent`
- `WatchlistOrderIntentSnapshot`
- `build_watchlist_order_intent_snapshot`

### Order Side 계약

`WatchlistOrderIntentSide`는 Phase 23 v1.0에서 아래 값만 허용한다.

- `BUY`

현재 upstream은 신규 진입 후보 흐름이므로 `SELL`, `SHORT`, `COVER`, `EXIT`를 임의 추가하지 않는다. 매도·청산은 별도 upstream 계약과 별도 Phase에서 정의한다.

### Order Style 계약

`WatchlistOrderIntentStyle`은 Phase 23 v1.0에서 아래 두 값만 허용한다.

- `MARKET`
- `LIMIT`

키움 broker-specific `trde_tp`, IOC, FOK, 시간외 주문유형 및 실제 SOR routing을 Phase 23 순수 모델에 포함하지 않는다.

### `WatchlistOrderIntentEvaluation`

`frozen=True`, `slots=True`인 dataclass로 구현하며 필드 순서를 고정한다.

1. `order_side`
2. `order_style`
3. `requested_quantity`
4. `limit_price`
5. `reason_code`

계약은 다음과 같다.

- `order_side`는 반드시 `WatchlistOrderIntentSide.BUY`이다.
- 문자열 `"BUY"`를 enum으로 자동 변환하지 않는다.
- `requested_quantity`는 `type(value) is int`이고 `value > 0`이어야 한다.
- `bool`, `float`, 문자열을 수량으로 자동 변환하거나 반올림하지 않는다.
- `requested_quantity`는 요청수량이며 실제 주문가능수량이 아니다.
- `MARKET`은 `limit_price is None`이어야 한다.
- `LIMIT`은 `type(limit_price) is int`이고 `limit_price > 0`이어야 한다.
- `bool`, `float`, 문자열을 가격으로 자동 변환하거나 반올림하지 않는다.
- `reason_code`는 비어 있지 않은 문자열이어야 하며 whitespace-only를 허용하지 않는다.
- builder는 `reason_code`를 임의 trim·정규화·대체하지 않는다.

Phase 23은 positive quantity/price의 구조적 타당성만 확인하며 현금잔고, 예수금, 증거금, 실제 주문가능수량, 종목별 최대주문수량, 호가단위, 상·하한가, 시장 session, 거래정지, 실제 주문 가능 여부와 체결 가능성을 확인하지 않는다.

### `WatchlistCandidateOrderIntent`

`frozen=True`, `slots=True`인 dataclass로 구현하며 Phase 22의 12개 후보 추적 필드를 정확히 앞부분에 보존한 뒤 Order Intent 결과를 추가한다.

1. `source_rank`
2. `stock_code`
3. `stock_name`
4. `exchange_scope`
5. `realtime_type`
6. `signal_decision`
7. `venue`
8. `signal_reason_code`
9. `risk_decision`
10. `risk_reason_code`
11. `order_permission_decision`
12. `order_permission_reason_code`
13. `order_side`
14. `order_style`
15. `requested_quantity`
16. `limit_price`
17. `order_intent_reason_code`

1~12번 upstream 필드는 수정·trim·normalize·변환·재해석·재번호하지 않는다.

`venue`는 upstream 추적정보로만 보존하며 키움 주문의 `dmst_stex_tp` 또는 실제 routing 값으로 변환하지 않는다.

### `WatchlistOrderIntentSnapshot`

`frozen=True`, `slots=True`인 dataclass로 구현하며 필드 순서를 고정한다.

1. `intents`
2. `candidate_count`
3. `no_signal_count`
4. `risk_checked_count`
5. `risk_clear_count`
6. `risk_blocked_count`
7. `permission_checked_count`
8. `order_permitted_count`
9. `order_denied_count`
10. `intent_planned_count`
11. `market_order_count`
12. `limit_order_count`
13. `realtime_type`

`intents`에는 planner가 성공한 `ORDER_PERMITTED` 후보만 포함하고 `ORDER_DENIED` 후보는 포함하지 않는다.

### Builder 계약

공개 builder 이름과 인자 순서는 아래와 같이 고정한다.

`build_watchlist_order_intent_snapshot(snapshot, planner)`

- `snapshot`은 Phase 22 `WatchlistOrderPermissionSnapshot`이어야 한다.
- `planner`는 동기 순수 callable이어야 한다.
- `ORDER_PERMITTED` 후보마다 planner를 정확히 1회 호출한다.
- `ORDER_DENIED` 후보에는 planner를 0회 호출한다.
- planner 반환값은 `WatchlistOrderIntentEvaluation`이어야 한다.
- 입력 후보 순서를 보존하고 `source_rank`를 재번호하지 않는다.
- builder는 수량·가격·주문스타일·자금배분·position sizing을 임의 계산하거나 추론하지 않는다.
- builder는 완전한 성공 시 하나의 `WatchlistOrderIntentSnapshot`만 반환한다.
- 부분 성공 Snapshot은 반환하지 않는다.

planner와 builder는 async 외부 I/O, awaitable 반환, REST, WebSocket, 파일 기반 credential 조회, OS credential store 조회, 환경변수 Kiwoom credential 조회, 계좌 조회, `kt00011`, `kt10000`, `kt10001`, `kt10002`, `kt10003`, 외부 HTTP 및 실제 주문 전송을 수행하지 않는다.

### Count 불변식

성공 반환 시 Phase 22의 기존 불변식을 모두 유지한다.

- `candidate_count = no_signal_count + risk_checked_count`
- `risk_checked_count = risk_clear_count + risk_blocked_count`
- `permission_checked_count = risk_clear_count`
- `permission_checked_count = order_permitted_count + order_denied_count`

Phase 23은 아래 불변식을 추가한다.

- `intent_planned_count = order_permitted_count`
- `len(intents) = intent_planned_count`
- `market_order_count + limit_order_count = intent_planned_count`

따라서 정상 성공 시 `len(intents) = intent_planned_count = order_permitted_count`를 만족한다.

유효한 빈 snapshot과 전부 `ORDER_DENIED`인 snapshot은 정상 결과이며 planner 호출 수는 0이다.

### 오류 및 실패 계약

아래 상황은 `WatchlistOrderIntentError` 계열의 fail-closed 실패로 처리한다.

- `snapshot` 타입 또는 구조가 계약과 다름
- upstream count 불변식 위반
- upstream 후보 필드 또는 `source_rank` 계약 위반
- `planner`가 callable이 아님
- async/coroutine planner 또는 awaitable 반환
- planner 호출 중 예외 발생
- planner 반환 타입이 `WatchlistOrderIntentEvaluation`이 아님
- `BUY` 이외의 direction
- 허용되지 않은 order style
- `requested_quantity`가 int가 아니거나 bool이거나 0 이하
- `MARKET`인데 `limit_price`가 존재
- `LIMIT`인데 `limit_price`가 없거나 int가 아니거나 bool이거나 0 이하
- 빈 문자열 또는 whitespace-only `reason_code`
- 부분 결과만 생성된 상태

planner 자체 예외는 `WatchlistOrderIntentError`의 원인으로 exception chaining을 통해 보존한다.

임의 retry, 오류 무시, default Intent 생성, fallback quantity/price, 자동 clamp, 자동 보정 및 부분 Snapshot 반환을 금지한다.

### 키움 API·보안 경계

Phase 23에서는 다음을 호출하거나 접근하지 않는다.

- `kt00011` 주문가능수량 조회
- `kt10000` 주식 매수주문
- `kt10001` 주식 매도주문
- `kt10002` 주식 정정주문
- `kt10003` 주식 취소주문
- 실계좌 또는 모의계좌
- App Key, App Secret, access token
- OAuth/token 발급·폐기
- Windows Credential Manager 또는 keyring
- `.env` credential
- 외부 REST 또는 WebSocket
- `api.kiwoom.com`
- `mockapi.kiwoom.com`

Phase 23 때문에 신규 dependency를 추가하지 않으며 `pyproject.toml`과 `uv.lock`을 변경하지 않는다.

### 호환성 계약

Phase 23은 Phase 20 Signal, Phase 21 Risk, Phase 22 Order Permission의 공개 API와 의미를 변경하지 않는다.

기존 `kiwoom_trading_system.orders` package 아래에서 확장하며 새 `order`, `execution`, `broker_order` package를 임의 생성하지 않는다.

### 구현 허용 후보 경로

향후 구현이 별도 승인된 경우에만 아래 경로를 변경 후보로 한다.

- `src/kiwoom_trading_system/orders/__init__.py`
- `src/kiwoom_trading_system/orders/watchlist_order_intent.py`
- `tests/test_watchlist_order_intent.py`

README 계약 등록 단계에서는 위 구현 경로를 수정하지 않는다.

### 테스트 계약

향후 구현 단계에서 최소한 아래를 검증한다.

- 신규 7개 public export 정확성
- builder signature `(snapshot, planner)`
- `BUY`, `MARKET`, `LIMIT` enum 값
- frozen/slots 및 dataclass 필드 순서
- Phase 22 12개 후보 추적 필드 exact 보존
- 빈 snapshot
- 전부 `ORDER_DENIED`
- `ORDER_PERMITTED`별 planner 정확히 1회
- mixed PERMITTED/DENIED
- 입력 순서와 `source_rank` 보존
- BUY 이외 direction 거부
- quantity 0/음수/bool/float/string 거부
- MARKET price=None 강제
- LIMIT positive int price 강제
- LIMIT price 0/음수/bool/float/string 거부
- 빈/whitespace-only reason 거부
- 잘못된 planner 반환형
- coroutine/awaitable 거부
- planner exception chaining
- atomicity와 부분 Snapshot 금지
- count 불변식
- 외부 network와 credential 접근 없음
- `kt00011`, `kt10000`, `kt10001`, `kt10002`, `kt10003` 호출 없음
- Phase 20~22 공개 API 호환성
- 전체 회귀테스트

정확한 Phase 23 신규 테스트 개수는 구현 전 임의 확정하지 않는다.

### Current Phase

이 계약을 README에 등록해도 `Current Phase`는 `PHASE22`로 유지한다.

Phase 23 구현·검증·Closure가 완료되기 전까지 `Current Phase`를 `PHASE23`으로 변경하지 않는다.

## Phase 24 — demo Order Intent Account / Buying-Power Validation Snapshot 기반선 v1.0

### 목적과 경계

Phase 24는 Phase 23 `WatchlistOrderIntentSnapshot`을 입력으로 받아, 향후 Broker/Account Adapter가 공급한 broker-neutral Account / Buying-Power evidence를 검증하고, 각 Order Intent가 후속 Broker Mapping으로 전달 가능한지를 immutable Account Validation snapshot으로 집계하는 순수 Order-layer 기반선이다.

`demo`는 Kiwoom 모의계좌 API를 직접 조회한다는 의미가 아니다. Phase 24 core는 real/demo 계좌 API, OAuth/token, credential, REST/WebSocket, 주문/정정/취소를 직접 수행하지 않는다.

Phase 24는 Phase 20 Signal, Phase 21 Risk, Phase 22 Order Permission, Phase 23 Order Intent의 기존 공개 계약과 의미를 변경하지 않는다.

### 공식 module

공식 구현 module 경로:

`src/kiwoom_trading_system/orders/watchlist_account_validation.py`

공식 계약 테스트 경로:

`tests/test_watchlist_account_validation.py`

### Phase 24 public symbols

Phase 24 module의 공식 public symbol은 다음 7개이다.

1. `WatchlistAccountValidationError`
2. `WatchlistAccountValidationDecision`
3. `WatchlistIntentBuyingPowerEvidence`
4. `WatchlistAccountValidationContext`
5. `WatchlistCandidateAccountValidation`
6. `WatchlistAccountValidationSnapshot`
7. `build_watchlist_account_validation_snapshot`

`WatchlistAccountValidationError`는 `ValueError`를 상속한다.

### Decision contract

`WatchlistAccountValidationDecision`은 `str, Enum` 기반이며 exact value는 다음 두 개이다.

- `ACCOUNT_VALIDATION_PASSED`
- `ACCOUNT_VALIDATION_BLOCKED`

정상적인 account/buying-power 부족은 `BLOCKED`로 판정한다.
구조·타입·identity·invariant 오류는 `BLOCKED`로 숨기지 않고 `WatchlistAccountValidationError`로 처리한다.

### WatchlistIntentBuyingPowerEvidence

`WatchlistIntentBuyingPowerEvidence`는 `@dataclass(frozen=True, slots=True)`이다.

exact field order:

1. `source_rank`
2. `stock_code`
3. `exchange_scope`
4. `venue`
5. `order_side`
6. `order_style`
7. `requested_quantity`
8. `limit_price`
9. `reservation_amount`
10. `max_orderable_quantity`
11. `account_context_id`
12. `evidence_snapshot_id`

field rules:

- `source_rank`: exact `int`, `> 0`; `bool` 금지
- `stock_code`: non-empty `str`
- `exchange_scope`: non-empty `str`
- `venue`: `MarketVenue | None`
- `order_side`: exact `WatchlistOrderIntentSide`
- `order_style`: exact `WatchlistOrderIntentStyle`
- `requested_quantity`: exact `int`, `> 0`; `bool` 금지
- `limit_price`: `int | None`; upstream Intent와 exact match
- `reservation_amount`: exact `int`, KRW 단위, `> 0`; `bool` 금지
- `max_orderable_quantity`: exact `int`, `>= 0`; `bool` 금지
- `account_context_id`: non-empty opaque `str`
- `evidence_snapshot_id`: non-empty opaque `str`

`reservation_amount`는 Phase 24가 계산하는 값이 아니다.
향후 Broker/Account Adapter가 broker 규칙을 반영하여 정규화한 authoritative reservation amount이다.

`max_orderable_quantity`는 일반적인 현재 보유수량이 아니라, 해당 Intent 조건에서 Adapter가 정규화한 authoritative maximum orderable quantity이다.

### WatchlistAccountValidationContext

`WatchlistAccountValidationContext`는 `@dataclass(frozen=True, slots=True)`이다.

exact field order:

1. `account_context_id`
2. `evidence_snapshot_id`
3. `is_fresh`
4. `available_buying_power`
5. `evidences`

field rules:

- `account_context_id`: non-empty opaque `str`
- `evidence_snapshot_id`: non-empty opaque `str`
- `is_fresh`: exact `bool`이고 반드시 `True`
- `available_buying_power`: exact `int`, KRW 단위, `>= 0`; `bool` 금지
- `evidences`: `tuple[WatchlistIntentBuyingPowerEvidence, ...]`

계좌번호 원문, App Key, App Secret, access token을 domain model에 저장하지 않는다.

Phase 24는 wall-clock freshness threshold를 자체 계산하지 않는다.
향후 Adapter가 freshness를 판정한다.

`is_fresh is not True`이면 정상적인 `BLOCKED`가 아니라 contract ERROR이다.

`evidence_snapshot_id`는 Context와 모든 Evidence가 동일한 account/orderability normalization snapshot에서 생성됐는지 broker-neutral하게 검증하기 위한 identity이다.

### Intent / Evidence exact identity

`context.evidences[n]`은 반드시 `snapshot.intents[n]`과 positional하게 대응한다.

다음 8개 field가 exact match해야 한다.

1. `source_rank`
2. `stock_code`
3. `exchange_scope`
4. `venue`
5. `order_side`
6. `order_style`
7. `requested_quantity`
8. `limit_price`

추가로 모든 Evidence에 대해:

- `evidence.account_context_id == context.account_context_id`
- `evidence.evidence_snapshot_id == context.evidence_snapshot_id`

가 성립해야 한다.

Evidence 또는 Intent를 `source_rank`, 종목코드, 금액 등으로 재정렬하지 않는다.
Phase 23 `snapshot.intents`의 기존 tuple order를 그대로 유지한다.

다음은 모두 contract ERROR이다.

- missing evidence
- extra evidence
- duplicate `source_rank`
- 동일 `source_rank`인데 나머지 identity가 다른 evidence
- positional identity mismatch
- account context identity mismatch
- evidence snapshot identity mismatch

### MARKET / LIMIT buying-power contract

Phase 24는 MARKET 또는 LIMIT Order Intent의 authoritative buying power를 직접 계산하지 않는다.

Phase 24에서는 다음을 임의 proxy로 사용하지 않는다.

- current price
- ask price
- upper-limit price
- VI price
- 임의 시장가 추정가격
- fee rate
- tax rate
- margin rate

LIMIT에서도 `requested_quantity * limit_price`를 broker authoritative buying-power의 대체값으로 사용하지 않는다.

향후 Broker/Account Adapter가 실제 provider/account 규칙을 반영한 `reservation_amount`와 `max_orderable_quantity`를 Phase 24에 공급한다.

Phase 24는 공급된 `reservation_amount`를 다시 계산하지 않는다.

### Cumulative reservation policy

per-intent independent buying-power validation은 사용하지 않는다.

Phase 24는 snapshot-level cumulative reservation을 사용한다.

초기 상태:

`remaining_buying_power = context.available_buying_power`

`total_reserved_buying_power = 0`

평가는 `snapshot.intents`의 기존 tuple order로만 수행한다.
`source_rank` 또는 다른 field로 재정렬하지 않는다.

각 Intent의 평가 순서는 다음과 같다.

1. `requested_quantity > max_orderable_quantity`

   - `ACCOUNT_VALIDATION_BLOCKED`
   - reason code: `MAX_ORDERABLE_QUANTITY_INSUFFICIENT`
   - `remaining_buying_power` 차감 없음
   - `total_reserved_buying_power` 증가 없음

2. `reservation_amount > remaining_buying_power`

   - `ACCOUNT_VALIDATION_BLOCKED`
   - reason code: `BUYING_POWER_INSUFFICIENT`
   - `remaining_buying_power` 차감 없음
   - `total_reserved_buying_power` 증가 없음

3. 위 두 조건을 모두 통과

   - `ACCOUNT_VALIDATION_PASSED`
   - reason code: `ACCOUNT_VALIDATION_OK`
   - `remaining_buying_power -= reservation_amount`
   - `total_reserved_buying_power += reservation_amount`

exact boundary인:

`reservation_amount == remaining_buying_power`

는 `ACCOUNT_VALIDATION_PASSED`이다.

이 경우 해당 평가 후 `remaining_buying_power == 0`이다.

BLOCKED Intent의 `reservation_amount`는 `total_reserved_buying_power`에 포함하지 않는다.

### WatchlistCandidateAccountValidation

`WatchlistCandidateAccountValidation`은 `@dataclass(frozen=True, slots=True)`이다.

Phase 23 `WatchlistCandidateOrderIntent`의 기존 17개 field를 exact order로 보존한 뒤 다음 5개 field를 추가한다.

18. `account_validation_decision`
19. `account_validation_reason_code`
20. `reservation_amount`
21. `max_orderable_quantity`
22. `remaining_buying_power_after`

정상 reason code는 다음과 같다.

- PASS: `ACCOUNT_VALIDATION_OK`
- quantity 부족: `MAX_ORDERABLE_QUANTITY_INSUFFICIENT`
- buying power 부족: `BUYING_POWER_INSUFFICIENT`

### WatchlistAccountValidationSnapshot

`WatchlistAccountValidationSnapshot`은 `@dataclass(frozen=True, slots=True)`이다.

exact field order:

1. `validations`
2. `candidate_count`
3. `no_signal_count`
4. `risk_checked_count`
5. `risk_clear_count`
6. `risk_blocked_count`
7. `permission_checked_count`
8. `order_permitted_count`
9. `order_denied_count`
10. `intent_planned_count`
11. `market_order_count`
12. `limit_order_count`
13. `validation_checked_count`
14. `validation_passed_count`
15. `validation_blocked_count`
16. `initial_available_buying_power`
17. `total_reserved_buying_power`
18. `remaining_buying_power`
19. `account_context_id`
20. `evidence_snapshot_id`
21. `realtime_type`

### Builder contract

exact builder signature:

`build_watchlist_account_validation_snapshot(snapshot, context)`

Phase 24 builder에는 외부 validator callback을 두지 않는다.

broker-specific 계산은 Phase 24 이전의 Broker/Account Adapter normalization 단계에서 완료되고, Phase 24는 fixed contract validation과 cumulative reservation만 수행한다.

builder는 cumulative evaluation 전에 전체 upstream snapshot, Context, Evidence type, count, identity, freshness, numeric invariant를 먼저 검증한다.

구조 검증 중 하나라도 실패하면 cumulative evaluation 결과를 부분적으로 반환하지 않는다.

Phase 24는 atomic fail-closed contract를 유지한다.

### Empty snapshot

`intent_planned_count == 0`이어도 Context는 valid해야 한다.

필수 조건:

- `is_fresh is True`
- `account_context_id` non-empty
- `evidence_snapshot_id` non-empty
- `available_buying_power >= 0`
- `evidences == ()`

정상 empty 결과:

- `validations == ()`
- `validation_checked_count == 0`
- `validation_passed_count == 0`
- `validation_blocked_count == 0`
- `total_reserved_buying_power == 0`
- `remaining_buying_power == initial_available_buying_power`

### Exact invariants

Phase 24 신규 exact invariant:

- `len(context.evidences) == intent_planned_count`
- `len(validations) == validation_checked_count`
- `validation_checked_count == intent_planned_count`
- `validation_checked_count == validation_passed_count + validation_blocked_count`
- `initial_available_buying_power == total_reserved_buying_power + remaining_buying_power`
- `remaining_buying_power >= 0`
- `total_reserved_buying_power >= 0`
- output validation order == input `snapshot.intents` order
- each Evidence has exact one-to-one Intent identity
- upstream snapshot, Context, Evidence는 mutate하지 않는다.

`total_reserved_buying_power`에는 PASSED Intent의 `reservation_amount`만 포함한다.

Phase 23 upstream invariant도 Phase 24 builder 진입 시 재검증한다.

특히:

- `intent_planned_count == order_permitted_count`
- `len(intents) == intent_planned_count`
- `market_order_count + limit_order_count == intent_planned_count`
- upstream count invariants
- unique positive `source_rank`
- source order 보존

### PASSED / BLOCKED / ERROR 경계

정상 정책 판정:

- quantity 충분 + buying power 충분 => `ACCOUNT_VALIDATION_PASSED`
- `requested_quantity > max_orderable_quantity` => `ACCOUNT_VALIDATION_BLOCKED`
- `reservation_amount > remaining_buying_power` => `ACCOUNT_VALIDATION_BLOCKED`

contract ERROR:

- wrong snapshot type
- wrong Context type
- wrong Evidence type
- stale Context
- missing / duplicate / extra Evidence
- Intent / Evidence identity mismatch
- account/evidence snapshot identity mismatch
- bool / float / string numeric
- invalid negative numeric
- invalid enum/type
- malformed upstream count invariant
- unsupported upstream contract

정상적인 account/buying-power 부족 상태를 exception으로 처리하지 않는다.

구조 오류를 `ACCOUNT_VALIDATION_BLOCKED`로 숨기지 않는다.

### Package compatibility

Phase 24 module `__all__`에는 Phase 24의 공식 7개 public symbol을 둔다.

향후 `kiwoom_trading_system.orders` package attribute에서도 Phase 24 symbol에 접근할 수 있도록 Phase 23의 package exposure pattern을 유지하는 것을 구현 계약으로 한다.

그러나 기존 package-level `orders.__all__`은 Phase 22 exact 6-name contract를 그대로 유지한다.

Phase 24에서 package-level `orders.__all__`을 임의 확장하지 않는다.

### Broker / Account Adapter boundary

Phase 24 pure core에서는 다음을 직접 수행하거나 해석하지 않는다.

- `kt00010`
- `kt00011`
- `kt10000`
- `kt10001`
- `kt10002`
- `kt10003`
- OAuth/token
- credential
- `.env`
- Windows Credential Manager
- REST/WebSocket connection
- actual/demo account query
- broker raw response parsing/mapping
- `trde_tp`
- IOC/FOK
- KRX/NXT/SOR broker order mapping
- tick-size mapping
- price-limit validation
- market-session query
- trading-halt query
- Order Submission
- 실제 주문/정정/취소

실제 Kiwoom account/orderability 데이터 취득, raw response 해석, provider-specific calculation, normalization은 향후 Broker/Account Adapter 단계의 책임이다.

### Dependency / 허용경로

Phase 24 pure validation core에는 신규 dependency를 추가하지 않는다.

따라서 Phase 24 구현에서도 다음 파일은 변경 금지이다.

- `pyproject.toml`
- `uv.lock`

향후 Phase 24 구현 허용경로 후보는 다음 세 개로 제한한다.

- `src/kiwoom_trading_system/orders/__init__.py`
- `src/kiwoom_trading_system/orders/watchlist_account_validation.py`
- `tests/test_watchlist_account_validation.py`

별도 승인 없이 `order`, `execution`, `broker_order` 등 새로운 package를 만들지 않는다.

이번 README 공식 계약 등록 단계의 실제 변경 허용경로는 `README.md` 하나뿐이다.

### 최소 테스트 계약

향후 Phase 24 구현 검증은 최소 다음 범주를 포함한다.

- valid empty snapshot/context
- one MARKET PASSED
- one LIMIT PASSED
- exact buying-power boundary
- insufficient `max_orderable_quantity`
- insufficient remaining buying power
- all PASSED
- all BLOCKED
- mixed PASSED/BLOCKED
- cumulative oversubscription
- BLOCKED intent does not reserve
- deterministic input tuple order
- source-rank reordering 금지
- 각 Intent/Evidence identity field mismatch
- Context/Evidence account identity mismatch
- Context/Evidence snapshot identity mismatch
- missing Evidence
- duplicate Evidence
- extra Evidence
- stale Context
- wrong Context/Evidence type
- bool numeric rejection
- float/string numeric rejection
- negative numeric rejection
- zero boundary rules
- malformed upstream snapshot
- upstream count invariant failure
- atomic failure / no partial result
- dataclass frozen
- dataclass slots
- exact field order
- package attribute identity
- package-level `orders.__all__` preservation
- no broker/network/credential imports
- no Kiwoom API/TR IDs in Phase 24 pure core
- no actual order/account/network invocation

정확한 Phase 24 신규 테스트 개수는 구현 전 임의 확정하지 않는다.

### Current Phase

이 공식 계약을 README에 등록해도 `Current Phase`는 Phase 23으로 유지한다.

Phase 24 구현·검증·Closure가 완료되기 전까지 README 상단 `Current Phase`를 Phase 24로 변경하지 않는다.

Phase 24 README 계약 등록은 구현 승인이나 구현 완료를 의미하지 않는다.

## Phase 25 — demo Account-Validated Order Intent → Kiwoom REST Buy-Order Request Mapping Snapshot 기반선 v1.0

### 목적과 경계

Phase 25는 Phase 24 `WatchlistAccountValidationSnapshot`을 입력으로 받아 `ACCOUNT_VALIDATION_PASSED`인 BUY Order Intent만 Kiwoom REST 국내주식 매수주문 `kt10000`의 request body shape로 순수 변환하고, 그 결과를 immutable Mapping Snapshot으로 집계하는 broker-specific pure mapping 기반선이다.

`ACCOUNT_VALIDATION_BLOCKED`는 정상적인 제외 상태이며 exception으로 처리하지 않는다.

Phase 25는 request shape만 만들며 OAuth/token, credential, REST/WebSocket connection, HTTP POST, account query, order submission, correction/cancel, response handling을 수행하지 않는다.

Phase 25는 Phase 20 Signal, Phase 21 Risk, Phase 22 Order Permission, Phase 23 Order Intent, Phase 24 Account Validation의 기존 공개 계약과 의미를 변경하지 않는다.

### 공식 module

향후 구현 module:

`src/kiwoom_trading_system/brokers/kiwoom/rest/watchlist_order_mapping.py`

향후 계약 테스트:

`tests/test_watchlist_order_mapping.py`

### Phase 25 public symbols

Phase 25 module의 공식 public symbol은 다음 7개이다.

1. `KIWOOM_BUY_ORDER_API_ID`
2. `KIWOOM_ORDER_API_PATH`
3. `KiwoomOrderMappingError`
4. `KiwoomBuyOrderRequest`
5. `WatchlistCandidateKiwoomOrderMapping`
6. `WatchlistKiwoomOrderMappingSnapshot`
7. `build_watchlist_kiwoom_order_mapping_snapshot`

상수 계약:

- `KIWOOM_BUY_ORDER_API_ID = "kt10000"`
- `KIWOOM_ORDER_API_PATH = "/api/dostk/ordr"`

`KiwoomOrderMappingError`는 Phase 25 structural/type/identity/provider-shape contract 위반을 나타내는 `ValueError` 계열 오류로 사용한다.

### Input contract

Phase 25 builder의 입력은 Phase 24 `WatchlistAccountValidationSnapshot` 하나이다.

mapping 대상은 `account_validation_decision == ACCOUNT_VALIDATION_PASSED`인 `WatchlistCandidateAccountValidation`만이다.

`ACCOUNT_VALIDATION_BLOCKED` candidate는 정상 제외하며 `KiwoomOrderMappingError`로 바꾸지 않는다.

Phase 25는 Phase 24 validation 결과를 재평가하거나 buying power를 다시 계산하지 않는다.

Phase 24의 다음 identity와 business field를 trim, normalize, reinterpret, renumber하지 않는다.

- `source_rank`
- `stock_code`
- `stock_name`
- `exchange_scope`
- `realtime_type`
- `signal_decision`
- `venue`
- `signal_reason_code`
- `risk_decision`
- `risk_reason_code`
- `order_permission_decision`
- `order_permission_reason_code`
- `order_side`
- `order_style`
- `requested_quantity`
- `limit_price`
- `order_intent_reason_code`
- `account_validation_decision`
- `account_validation_reason_code`
- `reservation_amount`
- `max_orderable_quantity`
- `remaining_buying_power_after`

### Kiwoom provider contract

Phase 25의 provider request contract는 Kiwoom 공식 machine-readable `kiwoom_api_spec.json`과 승인 환경에 설치된 `kwcli 1.0.0`의 동일 spec을 기준으로 한다.

API contract:

- API ID: `kt10000`
- Method: `POST`
- Path: `/api/dostk/ordr`
- Format: JSON

request body exact field order:

1. `dmst_stex_tp`
2. `stk_cd`
3. `ord_qty`
4. `ord_uv`
5. `trde_tp`
6. `cond_uv`

field contract:

- `dmst_stex_tp`: String / Required Y / Length 3
- `stk_cd`: String / Required Y / Length 12
- `ord_qty`: String / Required Y / Length 12
- `ord_uv`: String / Required N / Length 12
- `trde_tp`: String / Required Y / Length 2
- `cond_uv`: String / Required N / Length 12

공식 human-readable `kiwoom_docs/주문.md`에는 현재 `trde_tp` Length가 `20`으로 표시되어 있으나, 공식 machine-readable `kiwoom_api_spec.json`과 승인 환경에 설치된 `kwcli 1.0.0` spec은 모두 Length `2`로 일치한다.

Phase 25는 machine-readable official spec + installed spec의 일치값인 `trde_tp` Length `2`를 authoritative provider-shape contract로 사용한다.

이 문서 불일치는 실제 Submission 지원 여부를 증명하는 근거로 사용하지 않는다.

### KiwoomBuyOrderRequest

`KiwoomBuyOrderRequest`는 `@dataclass(frozen=True, slots=True)`이다.

exact field order:

1. `dmst_stex_tp`
2. `stk_cd`
3. `ord_qty`
4. `ord_uv`
5. `trde_tp`
6. `cond_uv`

모든 field는 provider JSON body에 직접 대응하는 문자열이다.

`KiwoomBuyOrderRequest`에는 authorization header, token, base URL, HTTP client, response, `ord_no`, `return_code`, `return_msg` 또는 submission state를 포함하지 않는다.

### BUY / MARKET / LIMIT mapping contract

Phase 25는 BUY만 허용한다.

`order_side`는 정확히 `BUY`여야 한다.

MARKET:

- `order_style == MARKET`
- `limit_price is None`
- `trde_tp = "3"`
- `ord_uv = ""`
- `cond_uv = ""`

LIMIT:

- `order_style == LIMIT`
- `limit_price`는 `bool`이 아닌 exact positive `int`
- `trde_tp = "0"`
- `ord_uv = str(limit_price)`
- `cond_uv = ""`

quantity:

- `requested_quantity`는 `bool`이 아닌 exact positive `int`
- `ord_qty = str(requested_quantity)`
- provider Length 12를 초과하면 contract ERROR

price:

- LIMIT `ord_uv`는 provider Length 12를 초과할 수 없다.
- MARKET에서는 임의 가격을 생성하거나 current/ask/upper-limit/VI price를 proxy로 사용하지 않는다.
- Phase 25는 tick size, price limit, session, halt 또는 주문 가능 가격을 검증하지 않는다.

### Venue mapping contract

`dmst_stex_tp`의 유일한 source는 `venue.value`이다.

pure mapping:

- `MarketVenue.KRX.value -> "KRX"`
- `MarketVenue.NXT.value -> "NXT"`
- `MarketVenue.SOR.value -> "SOR"`

`exchange_scope`는 tracking metadata로만 보존하며 `dmst_stex_tp` routing source로 사용하지 않는다.

PASSED candidate의 `venue`는 유효한 `MarketVenue`여야 하며 `None`은 contract ERROR이다.

NXT/SOR pure mapping은 실제 demo/mock Submission 지원을 보증하지 않는다.

현재 human-readable provider 문서의 mock 환경 KRX-only 표기는 Phase 25 pure mapping을 KRX-only로 축소하는 근거로 사용하지 않는다.

실제 환경별 KRX/NXT/SOR Submission capability는 향후 별도 Submission Phase에서 당시 최신 provider contract를 다시 검증한 뒤 결정한다.

### WatchlistCandidateKiwoomOrderMapping

`WatchlistCandidateKiwoomOrderMapping`은 `@dataclass(frozen=True, slots=True)`이다.

Phase 24 `WatchlistCandidateAccountValidation`의 기존 22개 field를 exact order로 그대로 보존한 뒤 다음 field 하나를 추가한다.

23. `request`

`request`는 해당 candidate에서 생성한 `KiwoomBuyOrderRequest`이다.

candidate와 request 사이의 다음 identity는 exact match여야 한다.

- `candidate.venue.value == request.dmst_stex_tp`
- `candidate.stock_code == request.stk_cd`
- `str(candidate.requested_quantity) == request.ord_qty`

MARKET/LIMIT price/style mapping도 candidate와 request 사이에서 exact match여야 한다.

Phase 25는 PASSED candidate의 `source_rank`를 재번호하거나 재정렬하지 않는다.

### WatchlistKiwoomOrderMappingSnapshot

`WatchlistKiwoomOrderMappingSnapshot`은 `@dataclass(frozen=True, slots=True)`이다.

exact field order:

1. `mappings`
2. `candidate_count`
3. `no_signal_count`
4. `risk_checked_count`
5. `risk_clear_count`
6. `risk_blocked_count`
7. `permission_checked_count`
8. `order_permitted_count`
9. `order_denied_count`
10. `intent_planned_count`
11. `market_order_count`
12. `limit_order_count`
13. `validation_checked_count`
14. `validation_passed_count`
15. `validation_blocked_count`
16. `mapping_count`
17. `initial_available_buying_power`
18. `total_reserved_buying_power`
19. `remaining_buying_power`
20. `account_context_id`
21. `evidence_snapshot_id`
22. `realtime_type`

Phase 24 snapshot의 기존 count, buying-power summary, identity, realtime type은 의미를 변경하지 않고 그대로 전달한다.

### Builder contract

exact builder signature:

`build_watchlist_kiwoom_order_mapping_snapshot(snapshot)`

builder는 output 생성 전에 전체 upstream Phase 24 snapshot structure, type, count, identity, enum, numeric invariant와 provider field length를 먼저 검증한다.

구조 검증 중 하나라도 실패하면 부분 mapping 결과를 반환하지 않는다.

Phase 25는 atomic fail-closed contract를 유지한다.

정상 `ACCOUNT_VALIDATION_BLOCKED` candidate는 mapping을 만들지 않고 건너뛴다.

PASSED candidate의 기존 tuple relative order를 그대로 보존한다.

### Exact invariants

Phase 25 신규 exact invariant:

- `len(mappings) == mapping_count`
- `mapping_count == validation_passed_count`
- `validation_checked_count == validation_passed_count + validation_blocked_count`
- output mappings order == upstream PASSED candidate relative order
- mapped `source_rank`는 upstream 값을 그대로 보존하며 재번호하지 않는다.
- mapped `source_rank`는 unique positive exact `int`이며 `bool`을 허용하지 않는다.
- duplicate mapping을 허용하지 않는다.
- candidate/request identity는 exact match여야 한다.
- upstream snapshot과 candidate를 mutate하지 않는다.
- `validation_passed_count == 0`이면 `mappings == ()`이고 `mapping_count == 0`이다.

Phase 24의 기존 invariant를 Phase 25 builder 진입 시 전부 재검증한다.

특히 다음을 포함한다.

- `len(validations) == validation_checked_count`
- `validation_checked_count == intent_planned_count`
- `initial_available_buying_power == total_reserved_buying_power + remaining_buying_power`
- `remaining_buying_power >= 0`
- `total_reserved_buying_power >= 0`
- Phase 23/24 upstream count invariants
- source order 보존
- exact upstream identity

### ERROR boundary

다음은 모두 `KiwoomOrderMappingError`이며 partial result를 반환하지 않는다.

- wrong snapshot type
- malformed Phase 24 snapshot/count invariant
- duplicate or invalid `source_rank`
- invalid enum/type
- PASSED candidate의 `venue is None`
- unsupported `venue`
- non-BUY `order_side`
- unsupported `order_style`
- MARKET with non-None `limit_price`
- LIMIT with non-positive or non-exact-int `limit_price`
- `bool` / `float` / `str` numeric coercion
- non-positive or non-exact-int `requested_quantity`
- provider String Length overflow
- candidate/request identity mismatch
- unsupported upstream contract

정상 `ACCOUNT_VALIDATION_BLOCKED`는 ERROR가 아니다.

구조 오류를 BLOCKED 또는 빈 mapping으로 숨기지 않는다.

### Submission / authentication boundary

Phase 25 pure mapping에서는 다음을 직접 수행하거나 해석하지 않는다.

- OAuth/token 발급·폐기
- credential 조회·저장
- `.env`
- Windows Credential Manager
- REST/WebSocket connection
- HTTP POST
- `get_client`
- `fetch_page`
- actual/demo account query
- order submission
- correction/cancel
- `ord_no`
- `return_code`
- `return_msg`
- provider response parsing
- retry
- timeout
- network backoff
- 실제 주문 가능성 또는 체결 가능성 확인

Phase 25 output은 향후 Submission Phase의 입력 후보일 뿐 주문 전송 또는 주문 성공을 의미하지 않는다.

### Dependency / 허용경로

Phase 25 pure mapping에는 신규 dependency를 추가하지 않는다.

따라서 다음 파일은 변경 금지이다.

- `pyproject.toml`
- `uv.lock`
- `src/kiwoom_trading_system/brokers/kiwoom/rest/__init__.py`
- 기존 Phase 19~24 source/test

향후 Phase 25 구현 허용경로 후보는 다음 두 개로 제한한다.

- `src/kiwoom_trading_system/brokers/kiwoom/rest/watchlist_order_mapping.py`
- `tests/test_watchlist_order_mapping.py`

별도 승인 없이 package-level export를 추가하거나 기존 `__all__` 계약을 변경하지 않는다.

이번 README 공식 계약 등록 단계의 실제 변경 허용경로는 `README.md` 하나뿐이다.

### 최소 테스트 계약

향후 Phase 25 구현 검증은 최소 다음 범주를 포함한다.

- valid empty/all-BLOCKED snapshot
- one MARKET PASSED
- one LIMIT PASSED
- mixed PASSED/BLOCKED
- PASSED relative order preservation
- source_rank preservation / no renumbering
- duplicate source_rank rejection
- KRX/NXT/SOR pure mapping
- `exchange_scope` is not routing source
- MARKET `limit_price is None`
- MARKET non-None price rejection
- LIMIT exact positive int price
- LIMIT bool/float/string/non-positive price rejection
- requested_quantity exact positive int
- requested_quantity bool/float/string/non-positive rejection
- ord_qty Length overflow
- ord_uv Length overflow
- wrong snapshot type
- malformed Phase 24 counts/invariants
- invalid enum/type
- PASSED `venue is None`
- unsupported venue/style/side
- candidate/request identity exact match
- provider body exact field order
- provider field Type/Required/Length contract
- `trde_tp` Length 2 provenance contract
- dataclass frozen
- dataclass slots
- exact field order
- atomic failure / no partial result
- upstream input immutability
- no REST/WebSocket/credential/account/order invocation
- no new dependency
- prohibited path preservation

정확한 Phase 25 신규 테스트 개수는 구현 전에 임의 확정하지 않는다.

Phase 25 구현 후 Full Regression expected count는 현재 기준선 451개 + 실제 Phase 25 신규 테스트 수로 계산하며, failures=0, errors=0, skipped=0, 프로세스 exit code=0을 모두 만족해야 한다.

### Current Phase

이 공식 계약을 README에 등록해도 `Current Phase`는 Phase 24로 유지한다.

Phase 25 구현·검증·Closure가 완료되기 전까지 README 상단 `Current Phase`를 Phase 25로 변경하지 않는다.

Phase 25 README 계약 등록은 구현 승인이나 구현 완료를 의미하지 않는다.

## Phase 26 — demo Kiwoom Buy-Order Dry-Run Dispatch Plan Snapshot 기반선 v1.0

Status: CONTRACT APPROVED FOR README REGISTRATION
Implementation: NOT YET APPROVED
Order Submission: OUT OF SCOPE

### Purpose

Phase 26 consumes the Phase 25 `WatchlistKiwoomOrderMappingSnapshot` and builds a pure, non-sending dry-run dispatch-plan snapshot for demo Kiwoom buy-order requests.

Phase 26 MUST NOT transmit actual or demo orders.

### Upstream

- `WatchlistKiwoomOrderMappingSnapshot`
- `WatchlistCandidateKiwoomOrderMapping`
- `KiwoomBuyOrderRequest`

The Phase 25 request object MUST be preserved exactly.

No request remapping, recalculation, replacement, mutation, or reordering is allowed.

### Public API

The module public API is exactly:

1. `KIWOOM_DEMO_ORDER_BASE_URL`
2. `KIWOOM_ORDER_HTTP_METHOD`
3. `KIWOOM_ORDER_CONTENT_TYPE`
4. `KiwoomOrderDispatchPlanError`
5. `KiwoomDemoOrderDispatchDecision`
6. `KiwoomDemoOrderDispatchBlockReason`
7. `KiwoomBuyOrderDispatchPlan`
8. `WatchlistCandidateKiwoomOrderDispatchPlan`
9. `WatchlistKiwoomOrderDispatchPlanSnapshot`
10. `build_watchlist_kiwoom_order_dispatch_plan_snapshot`

No package-level re-export from `brokers/kiwoom/rest/__init__.py` is added in Phase 26.

### Constants

- `KIWOOM_DEMO_ORDER_BASE_URL = "https://mockapi.kiwoom.com"`
- `KIWOOM_ORDER_HTTP_METHOD = "POST"`
- `KIWOOM_ORDER_CONTENT_TYPE = "application/json;charset=UTF-8"`

Phase 25 `KIWOOM_BUY_ORDER_API_ID` and `KIWOOM_ORDER_API_PATH` are reused without remapping.

### Dispatch Decision

`KiwoomDemoOrderDispatchDecision`:

- `DRY_RUN_SUPPORTED`
- `DRY_RUN_BLOCKED`

`KiwoomDemoOrderDispatchBlockReason`:

- `DEMO_VENUE_UNSUPPORTED`

### Venue Policy

- KRX → `DRY_RUN_SUPPORTED`
- NXT → `DRY_RUN_BLOCKED / DEMO_VENUE_UNSUPPORTED`
- SOR → `DRY_RUN_BLOCKED / DEMO_VENUE_UNSUPPORTED`
- unknown or malformed venue → fail closed with `KiwoomOrderDispatchPlanError`

The KRX/NXT/SOR policy is based on the provider demo-order boundary that the Kiwoom mock order environment is KRX-only.

### KiwoomBuyOrderDispatchPlan

Exact field order:

1. `base_url: str`
2. `http_method: str`
3. `api_id: str`
4. `api_path: str`
5. `content_type: str`
6. `request: KiwoomBuyOrderRequest`
7. `decision: KiwoomDemoOrderDispatchDecision`
8. `block_reason: KiwoomDemoOrderDispatchBlockReason | None`
9. `send_authorized: bool`

The dataclass is frozen and slotted.

`send_authorized` MUST always be `False`.

### WatchlistCandidateKiwoomOrderDispatchPlan

Exact field order:

1. `source_mapping: WatchlistCandidateKiwoomOrderMapping`
2. `dispatch_plan: KiwoomBuyOrderDispatchPlan`

Required identity:

- `source_mapping is upstream_mapping`
- `dispatch_plan.request is upstream_mapping.request`

### WatchlistKiwoomOrderDispatchPlanSnapshot

Exact field order:

1. `source_snapshot: WatchlistKiwoomOrderMappingSnapshot`
2. `plans: tuple[WatchlistCandidateKiwoomOrderDispatchPlan, ...]`
3. `candidate_count: int`
4. `dry_run_supported_count: int`
5. `dry_run_blocked_count: int`
6. `send_authorized_count: int`

Required invariant:

- `send_authorized_count == 0`

An all-blocked snapshot is valid.

### Builder

`build_watchlist_kiwoom_order_dispatch_plan_snapshot(snapshot: WatchlistKiwoomOrderMappingSnapshot) -> WatchlistKiwoomOrderDispatchPlanSnapshot`

The builder MUST be pure and atomic.

Any structural validation failure MUST raise before returning a snapshot.

Partial result return is prohibited.

### Security and Side-Effect Boundary

Phase 26 MUST NOT:

- call `get_client`
- fetch OAuth tokens
- access credentials
- access `.env`
- connect to `api.kiwoom.com`
- connect to `mockapi.kiwoom.com`
- send an actual order
- send a demo order
- modify dependencies
- modify `pyproject.toml`
- modify `uv.lock`
- modify `brokers/kiwoom/rest/__init__.py`

### Idempotency / Retry Boundary

Phase 26 does not solve duplicate-order prevention or submission idempotency.

Future actual submission logic MUST NOT automatically retry or retransmit an order after an ambiguous timeout, cancellation, or network failure until broker-side reconciliation determines whether the original order was accepted.

### Implementation Paths

Future implementation is limited to:

- `src/kiwoom_trading_system/brokers/kiwoom/rest/watchlist_order_dispatch_plan.py`
- `tests/test_watchlist_order_dispatch_plan.py`

Implementation requires separate approval.

### Test Contract

Phase 26 implementation MUST add exactly 59 Phase 26 tests.

Existing pre-Phase26 regression baseline is 510 tests.

Expected full regression after Phase26 implementation is exactly 569 tests:

- failures = 0
- errors = 0
- skipped = 0

README registration alone does not change the 510-test baseline.

## Phase 27 — demo Kiwoom Buy-Order Submission Readiness & Reconciliation Gate Snapshot 기반선 v1.0

Order Submission: OUT OF SCOPE

Phase 27은 Phase 26 `WatchlistKiwoomOrderDispatchPlanSnapshot`을 exact upstream으로 받아,
실제 주문 전송 전에 submission readiness와 prior submission reconciliation 상태만 순수 동기식으로 평가하는
non-sending safety gate 기반선이다.

Phase 27 자체는 actual order authorization, actual Order Submission, credential/token/.env access,
external network, account/order action을 수행하지 않는다.

### Upstream

- `WatchlistKiwoomOrderDispatchPlanSnapshot`
- Phase 26 `source_snapshot`, candidate source plan, mapped request identity를 exact preserve한다.
- request/plan을 remap, recalculate, replace, mutate, reorder하지 않는다.
- contexts count는 Phase 26 plans count와 exact match여야 한다.
- context relative order는 Phase 26 plans relative order와 exact match여야 한다.
- pairwise `source_rank`는 exact match여야 한다.
- duplicate, missing, extra context를 허용하지 않는다.
- structure/type/count/identity/upstream invariant가 하나라도 깨지면 partial result 없이
  `KiwoomOrderSubmissionSafetyError`로 fail closed한다.

### Future Implementation Paths

향후 별도 구현 승인이 있는 경우에만 아래 두 경로를 허용한다.

- `src/kiwoom_trading_system/brokers/kiwoom/rest/watchlist_order_submission_safety.py`
- `tests/test_watchlist_order_submission_safety.py`

위 두 경로 이외의 README, package export, dependency, 다른 source/test 경로 변경은 별도 승인 없이는 허용하지 않는다.

### Public API

Phase 27 public API는 다음 8개로 제한한다.

1. `KiwoomOrderSubmissionSafetyError`
2. `KiwoomPriorSubmissionState`
3. `KiwoomOrderSubmissionSafetyDecision`
4. `KiwoomOrderSubmissionSafetyBlockReason`
5. `KiwoomOrderSubmissionSafetyContext`
6. `WatchlistCandidateKiwoomOrderSubmissionSafety`
7. `WatchlistKiwoomOrderSubmissionSafetySnapshot`
8. `build_watchlist_kiwoom_order_submission_safety_snapshot`

### KiwoomOrderSubmissionSafetyContext

Context fields:

1. `source_rank`
2. `prior_submission_state`
3. `prior_attempt_reference`
4. `reconciliation_reference`

모든 non-None reference는 local opaque identifier이며 broker idempotency key로 간주하지 않는다.
reference를 broker-native duplicate-prevention 또는 exactly-once 보장으로 해석하지 않는다.

### Prior Submission State

`KiwoomPriorSubmissionState`:

- `NEVER_ATTEMPTED`
- `CONFIRMED_NOT_ACCEPTED`
- `CONFIRMED_ACCEPTED`
- `AMBIGUOUS_UNRESOLVED`

Reference invariant:

- `NEVER_ATTEMPTED`
  - `prior_attempt_reference is None`
  - `reconciliation_reference is None`
- `AMBIGUOUS_UNRESOLVED`
  - `prior_attempt_reference` 필수
  - `reconciliation_reference`는 `None` 또는 local opaque reference
- `CONFIRMED_NOT_ACCEPTED`
  - `prior_attempt_reference` 필수
  - `reconciliation_reference` 필수
- `CONFIRMED_ACCEPTED`
  - `prior_attempt_reference` 필수
  - `reconciliation_reference` 필수

### Safety Decision

`KiwoomOrderSubmissionSafetyDecision`:

- `READY_FOR_CONFIRMATION`
- `SUBMISSION_BLOCKED`

`READY_FOR_CONFIRMATION`은 actual order authorization, send authorization 또는 주문 전송 완료를 의미하지 않는다.
이는 향후 actual Submission Phase에서 execution-time fresh explicit confirmation을 요청할 수 있는 상태일 뿐이다.

### Block Reason

`KiwoomOrderSubmissionSafetyBlockReason`:

- `DEMO_VENUE_UNSUPPORTED`
- `RECONCILIATION_REQUIRED`
- `ALREADY_ACCEPTED`

structure/type/count/identity/upstream invariant 오류는 BlockReason으로 축소하지 않고
`KiwoomOrderSubmissionSafetyError`로 fail closed한다.

### Venue Contract

Phase 27은 Phase 26 venue 또는 dispatch decision을 새로 mapping하지 않고 그대로 검증한다.

- KRX + Phase 26 `DRY_RUN_SUPPORTED`
  - prior submission state에 따라 readiness를 평가한다.
- NXT
  - `SUBMISSION_BLOCKED / DEMO_VENUE_UNSUPPORTED`
- SOR
  - `SUBMISSION_BLOCKED / DEMO_VENUE_UNSUPPORTED`
- unknown, malformed, inconsistent venue/decision
  - `KiwoomOrderSubmissionSafetyError`

현재 mock/demo submission capability가 KRX-only라는 provider contract를 Phase 27 readiness 경계에 반영한다.

### Prior Submission Decision Contract

`NEVER_ATTEMPTED`:

- KRX + upstream `DRY_RUN_SUPPORTED`이면 `READY_FOR_CONFIRMATION` 가능

`CONFIRMED_NOT_ACCEPTED`:

- KRX + upstream `DRY_RUN_SUPPORTED`이면 `READY_FOR_CONFIRMATION` 가능
- 과거 approval을 재사용하지 않는다.
- 향후 actual Submission Phase에서 execution-time fresh explicit confirmation이 필수다.

`CONFIRMED_ACCEPTED`:

- `SUBMISSION_BLOCKED / ALREADY_ACCEPTED`
- 재전송 금지

`AMBIGUOUS_UNRESOLVED`:

- `SUBMISSION_BLOCKED / RECONCILIATION_REQUIRED`
- broker-side reconciliation 전 retry/retransmit 금지

### Retry / Retransmit Contract

- `automatic_retry_permitted`는 항상 `False`다.
- snapshot `automatic_retry_permitted_count == 0`이어야 한다.
- Phase 27은 retry, retransmit, resend를 실행하지 않는다.
- broker-side acceptance가 ambiguous한 동안 실제 전송 후보로 되돌리지 않는다.

### Actual Submission Boundary

Phase 27에서 금지:

- actual Order Submission
- external network
- credential/token/.env access
- account/order action
- `get_client`
- `get_ws_client`
- OAuth/token acquisition
- dependency 변경
- 새 `submission_attempt_id` 생성
- broker idempotency 보장 주장

향후 actual Submission Phase의 interface 후보:

`READY_FOR_CONFIRMATION`
-> execution-time fresh explicit confirmation
-> 새 local `submission_attempt_id` 생성 후보
-> single outbound attempt
-> broker response/reconciliation

local `submission_attempt_id`는 broker idempotency 보장이 아니다.

network 시작 이후 timeout, cancellation, connection loss, response loss 등으로 broker 접수 여부가 불명확하면
`AMBIGUOUS_UNRESOLVED`로 처리하고 broker-side reconciliation 전 자동 retry/retransmit을 금지한다.

### Package / Provider Boundary

현재 승인 baseline의 설치본은 `kwcli 1.0.0`이다.

Phase 27은 `kwcli`, credential, network, account/order action을 사용하지 않으므로
online latest package version은 Phase 27 readiness 계약의 runtime dependency로 고정하지 않는다.

향후 actual Submission Phase의 계약 설계 또는 구현 전에 당시 최신 Kiwoom provider contract와
설치 package contract를 다시 검증하는 것을 필수 gate로 둔다.

### Implementation / Test Contract

향후 별도 구현 승인이 있는 경우 최소한 다음을 검증한다.

- Phase 26 snapshot/plan/request exact identity preserve
- contexts count/order/source_rank exact pairing
- duplicate/missing/extra context fail closed
- `NEVER_ATTEMPTED` reference invariant
- `AMBIGUOUS_UNRESOLVED` reference invariant
- confirmed state reference invariant
- KRX readiness path
- NXT/SOR demo venue block
- `CONFIRMED_NOT_ACCEPTED` fresh-confirmation boundary
- `CONFIRMED_ACCEPTED` retransmit block
- ambiguous reconciliation block
- `automatic_retry_permitted == False`
- snapshot `automatic_retry_permitted_count == 0`
- partial result 금지
- external network call count 0
- credential/token/.env access count 0
- account/order action count 0
- dependency 변경 없음
- Phase 26/25 compatibility와 full regression 유지

Phase 27 계약 등록 자체는 implementation 또는 Current Phase alignment를 의미하지 않는다.
README 공식 계약 등록 후에도 `Current Phase`는 별도 구현/Closure 승인 전까지 `PHASE26`으로 유지한다.

## Phase 28 — demo Kiwoom Buy-Order Preparation Confirmation & Single-Attempt Preparation Snapshot 기반선 v1.0

Order Submission: OUT OF SCOPE

Phase 28은 Phase 27 `WatchlistKiwoomOrderSubmissionSafetySnapshot`을 exact upstream으로 받아,
`READY_FOR_CONFIRMATION` 후보의 preparation confirmation과 local single-attempt preparation만
순수 동기식(non-sending)으로 평가하는 기반선이다.

Phase 28 자체는 actual Order Submission, HTTP/API call, external network,
credential/token/.env access, account/order action, provider client 생성 또는 OAuth/token acquisition을 수행하지 않는다.

### Upstream

- exact upstream: `WatchlistKiwoomOrderSubmissionSafetySnapshot`
- Phase 27 `source_snapshot`, `evaluations`, candidate `source_plan`,
  Phase 26 dispatch plan, Phase 25 `KiwoomBuyOrderRequest` identity를 exact preserve한다.
- upstream object를 remap, recalculate, replace, mutate, reorder하지 않는다.
- contexts count는 Phase 27 evaluations count와 exact match여야 한다.
- context relative order는 Phase 27 evaluations relative order와 exact match여야 한다.
- pairwise `source_rank`는 exact match여야 한다.
- duplicate, missing, extra context를 허용하지 않는다.
- structure/type/count/order/identity/reference invariant가 하나라도 깨지면 partial result 없이
  `KiwoomOrderAttemptPreparationError`로 fail closed한다.

### Public API

Phase 28 public API는 다음 8개로 제한한다.

1. `KiwoomOrderAttemptPreparationError`
2. `KiwoomOrderPreparationConfirmationState`
3. `KiwoomOrderAttemptPreparationDecision`
4. `KiwoomOrderAttemptPreparationBlockReason`
5. `KiwoomOrderAttemptPreparationContext`
6. `WatchlistCandidateKiwoomOrderAttemptPreparation`
7. `WatchlistKiwoomOrderAttemptPreparationSnapshot`
8. `build_watchlist_kiwoom_order_attempt_preparation_snapshot`

### KiwoomOrderPreparationConfirmationState

exact members:

- `NOT_CONFIRMED`
- `CONFIRMED_FOR_PREPARATION`

`CONFIRMED_FOR_PREPARATION`은 preparation confirmation일 뿐 actual send authorization,
execution-time fresh confirmation, broker acceptance 또는 주문 완료를 의미하지 않는다.

### KiwoomOrderAttemptPreparationDecision

exact members:

- `ATTEMPT_PREPARED`
- `ATTEMPT_BLOCKED`

`ATTEMPT_PREPARED`는 actual send authorization이 아니다.

### KiwoomOrderAttemptPreparationBlockReason

exact members:

- `UPSTREAM_SUBMISSION_BLOCKED`
- `CONFIRMATION_REQUIRED`

structure/type/count/order/identity/reference invariant 오류는 BlockReason으로 축소하지 않고
`KiwoomOrderAttemptPreparationError`로 fail closed한다.

### KiwoomOrderAttemptPreparationContext

exact fields:

1. `source_rank`
2. `confirmation_state`
3. `confirmation_reference`
4. `submission_attempt_reference`

Reference contract:

- `NOT_CONFIRMED`
  - `confirmation_reference is None`
  - `submission_attempt_reference is None`
- `CONFIRMED_FOR_PREPARATION`
  - `confirmation_reference` 필수
  - `submission_attempt_reference` 필수
- 모든 non-None reference는 `str`이어야 하고 `value.strip() != ""`이어야 한다.
- reference 값 자체는 normalize, trim, mutate하지 않고 exact preserve한다.
- non-None `confirmation_reference`는 snapshot 내 unique여야 한다.
- `submission_attempt_reference`는 snapshot 내 unique여야 한다.
- 같은 context에서 `confirmation_reference != submission_attempt_reference`여야 한다.
- 같은 candidate의 새 `submission_attempt_reference`는 Phase 27 context의
  기존 non-None `prior_attempt_reference`와 달라야 한다.
- local reference는 local opaque correlation reference일 뿐 broker idempotency key,
  broker duplicate-prevention key, broker order number 또는 exactly-once guarantee가 아니다.

### WatchlistCandidateKiwoomOrderAttemptPreparation

exact fields:

1. `source_evaluation`
2. `context`
3. `decision`
4. `block_reason`
5. `single_attempt_prepared`
6. `automatic_retry_permitted`

Decision contract:

- Phase 27 `READY_FOR_CONFIRMATION`
  + valid `CONFIRMED_FOR_PREPARATION`
  + valid references
  -> `ATTEMPT_PREPARED`
- Phase 27 `READY_FOR_CONFIRMATION`
  + `NOT_CONFIRMED`
  -> `ATTEMPT_BLOCKED / CONFIRMATION_REQUIRED`
- Phase 27 `SUBMISSION_BLOCKED`
  + valid non-confirmed context
  -> `ATTEMPT_BLOCKED / UPSTREAM_SUBMISSION_BLOCKED`
- Phase 27 `SUBMISSION_BLOCKED` candidate에 confirmation/reference를 강제로 주입하면
  `KiwoomOrderAttemptPreparationError`로 fail closed한다.
- `decision == ATTEMPT_PREPARED` iff `single_attempt_prepared is True`.
- `automatic_retry_permitted`는 항상 `False`다.

### WatchlistKiwoomOrderAttemptPreparationSnapshot

exact fields:

1. `source_snapshot`
2. `preparations`
3. `candidate_count`
4. `prepared_count`
5. `blocked_count`
6. `confirmation_required_count`
7. `automatic_retry_permitted_count`

Snapshot invariants:

- `candidate_count == len(preparations)`
- `prepared_count == count(decision == ATTEMPT_PREPARED)`
- `blocked_count == count(decision == ATTEMPT_BLOCKED)`
- `confirmation_required_count == count(block_reason == CONFIRMATION_REQUIRED)`
- `automatic_retry_permitted_count == 0`
- partial result를 허용하지 않는다.

### Builder

`build_watchlist_kiwoom_order_attempt_preparation_snapshot(
    source_snapshot: WatchlistKiwoomOrderSubmissionSafetySnapshot,
    contexts: tuple[KiwoomOrderAttemptPreparationContext, ...],
) -> WatchlistKiwoomOrderAttemptPreparationSnapshot`

순수 동기식 builder이며 network I/O나 provider/account/order action을 수행하지 않는다.

### Preparation Confirmation / Freshness Boundary

Phase 28은 wall-clock freshness, caller identity 또는 실제 사용자 interaction 시각을 스스로 증명하지 않는다.

- `confirmation_reference`는 caller가 preparation invocation에 제공하는 local opaque reference다.
- Phase 28은 visible input 범위의 type, nonblank, pairing, uniqueness, collision만 검증한다.
- Phase 28 snapshot만으로 cross-process confirmation reuse 또는 exactly-once confirmation을 보장하지 않는다.
- Phase 28 preparation confirmation을 향후 actual sender의 execution-time fresh confirmation으로 재사용해서는 안 된다.
- 향후 actual network submission 단계는 I/O 직전에 별도의 fresh explicit confirmation을 다시 요구해야 한다.

따라서:

- `CONFIRMED_FOR_PREPARATION != CONFIRMED_FOR_SEND`
- `ATTEMPT_PREPARED != SEND_AUTHORIZED`

### Idempotency / Retry / Retransmit

- `submission_attempt_reference`는 local opaque correlation reference다.
- broker duplicate suppression, broker idempotency, exactly-once delivery,
  cross-process uniqueness 또는 broker order-number equivalence를 보장하지 않는다.
- `automatic_retry_permitted`는 항상 `False`다.
- `automatic_retry_permitted_count == 0`이어야 한다.
- Phase 28은 retry, retransmit, resend를 실행하지 않는다.

### Reconciliation Boundary

Phase 28은 broker-side reconciliation을 수행하지 않는다.

Phase 27의 prior submission 상태와 safety decision을 그대로 존중한다.

- `CONFIRMED_ACCEPTED`에서 파생된 blocked candidate를 prepared로 승격하지 않는다.
- `AMBIGUOUS_UNRESOLVED`에서 파생된 reconciliation-required candidate를 prepared로 승격하지 않는다.
- broker acceptance가 ambiguous한 동안 reconciliation 전 automatic retry/retransmit을 금지한다.

### Risk / Permission / Account Boundary

기존 Risk / Permission / Intent / Account Validation / Mapping / Dispatch / Safety chain을 exact preserve한다.

Phase 28은:

- Risk Gate를 재계산하지 않는다.
- Risk Gate를 우회하지 않는다.
- Risk decision을 downgrade하지 않는다.
- account/buying-power를 다시 조회하거나 계산하지 않는다.
- `ATTEMPT_PREPARED`를 execution-time Risk 또는 Buying-Power freshness 보장으로 해석하지 않는다.

향후 actual Submission 계약은 Phase 28 결과만으로 outbound I/O를 허용해서는 안 되며,
execution-time Risk/Buying-Power freshness를 어떻게 검증할지 별도의 승인 계약으로 정의해야 한다.

### Kiwoom Provider Boundary

현재 공식 Kiwoom 국내주식 매수주문 `kt10000` 계약은
`POST /api/dostk/ordr`이며 authorization bearer token을 요구한다.
모의투자 주문은 KRX만 지원한다.

Phase 28은 이 provider 계약을 설계 근거로만 사용하고 다음을 수행하지 않는다.

- Authorization header 생성
- OAuth/token acquisition
- `get_client`
- `get_ws_client`
- HTTP POST
- API request 실행
- broker response parsing
- account/order action

Phase 25 request mapping과 Phase 26 dispatch plan을 다시 생성하거나 변경하지 않는다.

### Implementation Paths

향후 별도 구현 승인이 있는 경우에만 다음 두 경로를 구현 허용경로 후보로 둔다.

- `src/kiwoom_trading_system/brokers/kiwoom/rest/watchlist_order_attempt_preparation.py`
- `tests/test_watchlist_order_attempt_preparation.py`

별도 승인 없이는 다음을 변경하지 않는다.

- `README.md`의 기존 내용
- `src/kiwoom_trading_system/brokers/kiwoom/rest/__init__.py`
- 기존 Phase 27 / 26 / 25 source/tests
- `pyproject.toml`
- `uv.lock`
- 기타 repository path

### Test Contract

Phase 28 구현 시 targeted test method exact count는 64개로 고정한다.

- Phase 28 targeted tests: `64`
- Phase 27 compatibility: `72`
- Phase 26 compatibility: `59`
- Phase 25 compatibility: `59`
- pre-implementation full regression baseline: `641`
- expected post-implementation full regression: `705`

64개 targeted methods는 최소 다음 범주를 포함한다.

- Public API / enum / frozen-slots-dataclass / signature
- upstream snapshot/evaluation/plan/request identity
- context count/order/source_rank pairing
- duplicate/missing/extra context fail closed
- confirmation/reference type/nonblank/uniqueness/collision invariants
- READY/BLOCKED decision matrix와 malformed combination fail closed
- snapshot aggregate counts
- automatic retry false/count zero
- empty snapshot / all-blocked / mixed snapshot
- no remap/recalculate/replace/mutate/reorder
- no network/client/OAuth/token/credential/.env/account/order action
- no dependency change
- no REST package re-export
- Phase 27 / 26 / 25 compatibility와 full regression

### Current Phase Rule

Phase 28 공식 계약을 README에 등록하는 것만으로 Phase 28 구현 또는 Closure가 완료된 것이 아니다.

Phase 28 source/test 구현과 별도 Closure가 승인·검증되기 전까지
top-level `Current Phase`는 `PHASE27`을 유지한다.

## Phase 29 — demo Kiwoom Order Send Authorization Evidence Snapshot 기반선 v1.0

Order Submission: OUT OF SCOPE

Phase 29는 Phase 28 `WatchlistKiwoomOrderAttemptPreparationSnapshot`을 exact upstream으로 받아,
실제 주문 전송 전에 supplied authorization evidence snapshot을 순수 동기식 read-only로 평가하는
non-sending Send Authorization Evidence Gate 기반선이다.

Phase 29 자체는 provider/client 호출, credential/token/.env 접근, account 접근, external network,
actual `kt10000` POST, actual Order Submission, historical authorization consumption ledger mutation,
automatic retry/reclaim/retransmission을 수행하지 않는다.

`ATTEMPT_PREPARED != SEND_AUTHORIZED`를 유지한다.

`SEND_AUTHORIZED`는 Phase 29 authorization evidence snapshot 평가 시점의 decision일 뿐이다.

`SEND_AUTHORIZED != CURRENTLY_VALID_AT_POST_TIME`
`SEND_AUTHORIZED != AUTHORIZATION_CONSUMED`
`SEND_AUTHORIZED != ORDER_SUBMITTED`
`SEND_AUTHORIZED != ORDER_ACCEPTED`

### Public API

Phase 29 public API는 다음 exact 8개로 제한한다.

1. `KiwoomOrderSendAuthorizationError`
2. `KiwoomOrderSendAuthorizationState`
3. `KiwoomOrderSendAuthorizationDecision`
4. `KiwoomOrderSendAuthorizationBlockReason`
5. `KiwoomOrderSendAuthorizationContext`
6. `WatchlistCandidateKiwoomOrderSendAuthorization`
7. `WatchlistKiwoomOrderSendAuthorizationSnapshot`
8. `build_watchlist_kiwoom_order_send_authorization_snapshot`

`KiwoomOrderSendAuthorizationError`는 `RuntimeError`를 상속한다.

모든 type/count/order/identity/state-reference/authority/snapshot/freshness/coherence/duplicate/upstream
contract invariant 위반은 decision evaluation 전에 `KiwoomOrderSendAuthorizationError`로 fail closed한다.

partial result 또는 partial snapshot을 반환하지 않는다.

### Authorization state

`KiwoomOrderSendAuthorizationState`는 `str, Enum` 기반이며 exact member는 다음 두 개이다.

- `NOT_AUTHORIZED`
- `AUTHORIZED_FOR_SEND`

### Decision

`KiwoomOrderSendAuthorizationDecision`은 `str, Enum` 기반이며 exact member는 다음 두 개이다.

- `SEND_AUTHORIZED`
- `SEND_BLOCKED`

### Block reason

`KiwoomOrderSendAuthorizationBlockReason`은 `str, Enum` 기반이며 exact member는 다음 세 개이다.

- `UPSTREAM_ATTEMPT_BLOCKED`
- `SEND_AUTHORIZATION_REQUIRED`
- `AUTHORIZATION_STALE`

### KiwoomOrderSendAuthorizationContext

`KiwoomOrderSendAuthorizationContext`는 frozen immutable dataclass이다.

exact field order는 다음 7개이다.

1. `source_rank`
2. `submission_attempt_reference`
3. `authorization_state`
4. `send_authorization_reference`
5. `authorization_authority_reference`
6. `authorization_evidence_snapshot_id`
7. `is_fresh`

field contract:

- `source_rank`는 해당 Phase 28 source preparation의 `source_rank`와 exact match여야 한다.
- `submission_attempt_reference`는 해당 Phase 28 source preparation의 `submission_attempt_reference`와 exact match여야 한다.
- `authorization_state`는 exact `KiwoomOrderSendAuthorizationState`여야 한다.
- `AUTHORIZED_FOR_SEND`이면 `send_authorization_reference`는 exact `str`, non-empty, non-whitespace여야 한다.
- `NOT_AUTHORIZED`이면 `send_authorization_reference`는 exact `None`이어야 한다.
- `authorization_authority_reference`는 exact `str`, non-empty, non-whitespace, opaque, stable authority namespace identity이다.
- 같은 authority namespace identity를 다른 authority에 recycle/rebind하지 않는다.
- `send_authorization_reference`를 같은 authority namespace 내 다른 grant/attempt에 recycle/reassign하지 않는다.
- `authorization_evidence_snapshot_id`는 exact `str`, non-empty, non-whitespace opaque immutable evidence snapshot identity이다.
- `is_fresh`는 exact `bool`이어야 하며 `int` 대체를 허용하지 않는다.

`authorization_state`, `send_authorization_reference`, `authorization_authority_reference`,
`authorization_evidence_snapshot_id`, `is_fresh`는 동일 approved authority의 동일 immutable evidence snapshot에서
나온 하나의 atomic provenance assertion으로 취급한다.

Phase 29는 provider/network/authority call을 하지 않으므로 위 provenance가 실제 외부 authority에서 발행되었다는
사실 자체를 독립적으로 인증했다고 주장하지 않는다.

### Trusted provenance boundary

Phase 29 local validation은 다음을 검증한다.

- exact input types
- Phase 28 upstream registered contract invariants
- context count와 positional order
- pairwise `source_rank` identity
- pairwise `submission_attempt_reference` identity
- authorization state/reference structural invariant
- `authorization_authority_reference` local structural validity
- `authorization_evidence_snapshot_id` local structural validity
- `is_fresh` exact bool
- non-empty batch authority/snapshot/freshness coherence
- duplicate non-None `send_authorization_reference`
- decision invariant
- aggregate invariant

Phase 29는 다음 사실을 독립적으로 인증했다고 주장하지 않는다.

- `authorization_authority_reference`가 실제 승인된 external authority라는 사실
- grant가 실제 해당 authority에서 발행되었다는 사실
- grant가 실제 해당 `submission_attempt_reference`에 발행되었다는 사실
- snapshot ID가 실제 immutable authority snapshot을 가리킨다는 사실
- `is_fresh`가 실제 wall-clock/current authority 상태라는 사실
- historical grant consumption/reuse 상태

위 항목은 approved external authorization authority/controller/adapter가 제공하는 trusted provenance assertion으로 취급한다.

### PHASE28_UPSTREAM_CONTRACT_VALIDATION

authorization evidence validation 또는 decision evaluation 전에 Phase 28 upstream registered contract를 먼저 검증한다.

Phase 29는 Phase 28의 decision이나 KRX/demo capability를 다시 계산하지 않는다.

다만 다음 구조적 invariant는 exact 검증한다.

1. `source_snapshot`은 exact `WatchlistKiwoomOrderAttemptPreparationSnapshot`이어야 한다.
2. `source_snapshot.preparations`는 Phase 28 공식 contract의 exact tuple/container invariant를 만족해야 한다.
3. 모든 preparation member는 exact `WatchlistCandidateKiwoomOrderAttemptPreparation`이어야 한다.
4. `source_snapshot.candidate_count == len(source_snapshot.preparations)`이어야 한다.
5. Phase 28 snapshot의 공식 aggregate count invariant 전체를 만족해야 한다.
6. 각 preparation의 `decision` / `block_reason` 조합은 Phase 28 공식 contract와 exact 일치해야 한다.
7. 각 Phase 28 `submission_attempt_reference`는 Phase 28 공식 reference invariant를 만족해야 한다.
8. 각 preparation의 `automatic_retry_permitted`는 exact `False`여야 한다.
9. Phase 28 snapshot `automatic_retry_permitted_count`는 exact `0`이어야 한다.
10. Phase 28의 source/context/reference positional identity invariant를 만족해야 한다.
11. Phase 28 source objects를 remap/recalculate/replace/mutate/reorder하지 않는다.

하나라도 실패하면 Phase 29 authorization evidence validation이나 decision evaluation으로 진행하지 않고
partial result 없이 `KiwoomOrderSendAuthorizationError`로 fail closed한다.

### Validation order

validation order는 다음 순서로 고정한다.

1. Phase 28 upstream exact type / structure / aggregate / reference / decision invariant validation
2. Phase 29 context exact type / count / positional order
3. `source_rank` exact pairwise identity
4. `submission_attempt_reference` exact binding
5. authorization state/reference structural invariant
6. `authorization_authority_reference` validity
7. `authorization_evidence_snapshot_id` validity
8. authority/snapshot/freshness batch coherence
9. `is_fresh` exact bool
10. duplicate non-None `send_authorization_reference`
11. decision evaluation

### Batch coherence

non-empty batch에서는 다음 값이 모든 context에서 exact same이어야 한다.

- `authorization_authority_reference`
- `authorization_evidence_snapshot_id`
- `is_fresh`

mixed authority/snapshot/freshness는 contract ERROR이다.

non-None `send_authorization_reference`는 batch 안에서 중복될 수 없다.

`None`은 grant가 아니므로 여러 `NOT_AUTHORIZED` context에서 반복될 수 있다.

### Decision precedence

validation을 모두 통과한 뒤 다음 precedence를 적용한다.

1. Phase 28 `ATTEMPT_BLOCKED`
   - decision = `SEND_BLOCKED`
   - block_reason = `UPSTREAM_ATTEMPT_BLOCKED`

2. Phase 28 `ATTEMPT_PREPARED` + `is_fresh == False`
   - authorization state와 관계없이 decision = `SEND_BLOCKED`
   - block_reason = `AUTHORIZATION_STALE`

3. Phase 28 `ATTEMPT_PREPARED` + fresh + `NOT_AUTHORIZED`
   - decision = `SEND_BLOCKED`
   - block_reason = `SEND_AUTHORIZATION_REQUIRED`

4. Phase 28 `ATTEMPT_PREPARED` + fresh + `AUTHORIZED_FOR_SEND`
   - decision = `SEND_AUTHORIZED`
   - block_reason = `None`

stale `NOT_AUTHORIZED`는 `SEND_AUTHORIZATION_REQUIRED`보다 `AUTHORIZATION_STALE`가 우선한다.

### WatchlistCandidateKiwoomOrderSendAuthorization

`WatchlistCandidateKiwoomOrderSendAuthorization`은 frozen immutable dataclass이다.

exact field order는 다음 6개이다.

1. `source_preparation`
2. `context`
3. `decision`
4. `block_reason`
5. `send_authorized`
6. `automatic_retry_permitted`

invariant:

- `source_preparation`은 해당 Phase 28 preparation object identity를 exact preserve한다.
- `context`는 validated input context identity를 exact preserve한다.
- `send_authorized == (decision is SEND_AUTHORIZED)`
- `automatic_retry_permitted == False`

### WatchlistKiwoomOrderSendAuthorizationSnapshot

`WatchlistKiwoomOrderSendAuthorizationSnapshot`은 frozen immutable dataclass이다.

collection field는 tuple을 사용한다.

exact field order는 다음 9개이다.

1. `source_snapshot`
2. `authorizations`
3. `candidate_count`
4. `send_authorized_count`
5. `send_blocked_count`
6. `authorization_required_count`
7. `authorization_stale_count`
8. `upstream_blocked_count`
9. `automatic_retry_permitted_count`

aggregate invariant:

`candidate_count = send_authorized_count + send_blocked_count`

`send_blocked_count = authorization_required_count + authorization_stale_count + upstream_blocked_count`

`automatic_retry_permitted_count == 0`

empty source + empty contexts는 valid하며 모든 aggregate count는 0이다.

### Builder

exact synchronous builder signature:

`build_watchlist_kiwoom_order_send_authorization_snapshot(`
`    source_snapshot: WatchlistKiwoomOrderAttemptPreparationSnapshot,`
`    contexts: tuple[KiwoomOrderSendAuthorizationContext, ...],`
`) -> WatchlistKiwoomOrderSendAuthorizationSnapshot`

- positional order는 `source_snapshot`, `contexts`로 고정한다.
- defaults는 없다.
- `source_snapshot`은 exact `WatchlistKiwoomOrderAttemptPreparationSnapshot`이어야 한다.
- `contexts`는 exact tuple이어야 한다.
- 모든 context member는 exact `KiwoomOrderSendAuthorizationContext`여야 한다.
- return type은 exact `WatchlistKiwoomOrderSendAuthorizationSnapshot`이다.
- validation 완료 전 partial candidate/snapshot을 외부로 반환하지 않는다.

### Future Submission boundary

Phase 29는 authorization consumption을 수행하지 않는다.

future actual Submission Phase의 claim identity는 다음 exact 4-tuple이다.

`authorization_claim_identity = (`
`    authorization_authority_reference,`
`    authorization_evidence_snapshot_id,`
`    submission_attempt_reference,`
`    send_authorization_reference,`
`)`

future replay guard는 다음 exact 2-tuple이다.

`authorization_replay_guard = (`
`    authorization_authority_reference,`
`    send_authorization_reference,`
`)`

`send_authorization_reference` 단독은 claim identity가 아니다.

future actual Submission Phase에서는 하나의 approved authorization authority/controller가 보장하는
single authoritative atomic check-and-consume transaction 안에서 다음을 모두 검증한다.

- claim identity unconsumed
- replay guard unconsumed
- exact authority namespace 동일
- exact immutable evidence snapshot identity 동일
- exact `submission_attempt_reference` 동일
- exact `send_authorization_reference` 동일
- grant가 해당 exact attempt에 계속 binding
- grant가 revoked/invalidated되지 않음
- evidence/grant가 transaction 시점에 authoritative하게 fresh/current-valid

authority validity를 transaction 전에 별도로 prefetch한 뒤 local ledger transaction을 수행하는 방식은 허용하지 않는다.

위 조건이 모두 참일 때만 claim identity와 replay guard를 함께 consumed로 atomic commit한다.

partial consume / one-key-only success는 허용하지 않는다.

`AUTHORIZATION_CONSUMPTION_COMMITTED`가 성공한 순간을 해당 exact outbound attempt의
final authorization linearization point로 정의한다.

`AUTHORIZATION_CONSUMPTION_COMMITTED`는 해당 exact identity에 대한 irrevocable one-shot send reservation이다.

atomic commit 이후 일반적인 freshness expiry 또는 동일 grant의 후속 revoke는 이미 성공적으로 reserved된
그 exact outbound attempt를 소급 무효화하지 않는다.

authorization authority의 정책 또는 기술구조상 위 semantics를 보장할 수 없으면 다음으로 fail closed한다.

`ATOMIC_CONSUMPTION_SUPPORTED=NO`
`POST_PERMITTED=NO`

atomic check-and-consume 결과가 already-consumed, duplicate, conflict, stale, revoked, invalid,
timeout, cancellation, failure, unknown/ambiguous이면 `kt10000` POST를 시도하지 않는다.

automatic retry / automatic reclaim / automatic unconsume / authorization reuse / retransmission을 금지한다.

atomic consume success 이후 process가 실제 POST 전에 종료되어도 authorization은 consumed 상태로 유지한다.

actual POST가 시작된 이후 결과가 timeout/cancellation/connection loss/response loss 등으로 ambiguous하면
Phase 27 `AMBIGUOUS_UNRESOLVED` → broker-side reconciliation → no automatic retry/retransmission 계약을 승계한다.

### Phase 29 forbidden side effects

Phase 29 자체에서는 다음을 전부 금지한다.

- provider REST client call
- provider WebSocket client call
- OAuth/token access
- `.env`/credential access
- external network
- account access
- actual order action
- actual `kt10000` POST
- historical authorization consumption/replay ledger mutation
- automatic retry/reclaim/retransmission
- Phase 28 source object mutation

### Runtime targeted test manifest

Phase 29 runtime targeted test total은 exact `89`개이다.

- `Phase29PublicApiTests=10`
- `Phase29UpstreamIdentityTests=21`
- `Phase29AuthorizationEvidenceInvariantTests=24`
- `Phase29DecisionMatrixTests=8`
- `Phase29SnapshotAggregateTests=10`
- `Phase29ForbiddenSideEffectTests=8`
- `Phase29CompatibilityBoundaryTests=8`
- `TOTAL=89`

`EXPECTED_POST_IMPLEMENTATION_FULL_REGRESSION=705+89=794`

#### Phase29PublicApiTests — 10

- `test_public_api_exact_eight_symbols`
- `test_error_is_runtime_error`
- `test_state_enum_exact_members`
- `test_decision_enum_exact_members`
- `test_block_reason_enum_exact_members`
- `test_context_exact_fields_and_frozen`
- `test_candidate_exact_fields_and_frozen`
- `test_snapshot_exact_fields_and_frozen`
- `test_builder_exact_signature`
- `test_builder_sync_exact_return_type`

#### Phase29UpstreamIdentityTests — 21

- `test_rejects_nonexact_source_snapshot_type`
- `test_rejects_contexts_non_tuple`
- `test_rejects_nonexact_context_member_type`
- `test_rejects_missing_context`
- `test_rejects_extra_context`
- `test_rejects_context_positional_reordering`
- `test_rejects_source_rank_identity_mismatch`
- `test_rejects_submission_attempt_reference_mismatch`
- `test_preserves_source_snapshot_identity`
- `test_preserves_source_preparation_identity`
- `test_preserves_context_identity`
- `test_accepts_empty_source_with_empty_contexts`
- `test_rejects_phase28_preparations_non_tuple`
- `test_rejects_phase28_nonexact_preparation_member_type`
- `test_rejects_phase28_candidate_count_length_mismatch`
- `test_rejects_malformed_phase28_snapshot_aggregate`
- `test_rejects_malformed_phase28_preparation_decision_block_reason_invariant`
- `test_rejects_malformed_phase28_submission_attempt_reference_invariant`
- `test_rejects_phase28_automatic_retry_invariant_violation`
- `test_rejects_phase28_snapshot_automatic_retry_count_nonzero`
- `test_rejects_malformed_phase28_source_context_reference_identity`

#### Phase29AuthorizationEvidenceInvariantTests — 24

- `test_rejects_raw_string_authorization_state`
- `test_authorized_requires_send_reference_exact_str`
- `test_authorized_rejects_empty_send_reference`
- `test_authorized_rejects_whitespace_send_reference`
- `test_not_authorized_requires_none_send_reference`
- `test_authority_reference_requires_exact_str`
- `test_authority_reference_rejects_empty`
- `test_authority_reference_rejects_whitespace`
- `test_snapshot_id_requires_exact_str`
- `test_snapshot_id_rejects_empty`
- `test_snapshot_id_rejects_whitespace`
- `test_is_fresh_requires_exact_bool`
- `test_rejects_mixed_authority_batch`
- `test_rejects_mixed_snapshot_id_batch`
- `test_rejects_mixed_freshness_batch`
- `test_rejects_duplicate_non_none_send_reference`
- `test_allows_duplicate_none_send_references`
- `test_allows_distinct_send_references`
- `test_accepts_valid_authorized_pair`
- `test_accepts_valid_not_authorized_pair`
- `test_preserves_send_reference_exactly`
- `test_preserves_authority_and_snapshot_exactly`
- `test_candidate_send_authorized_matches_decision`
- `test_candidate_automatic_retry_is_false`

#### Phase29DecisionMatrixTests — 8

- `test_blocked_stale_not_authorized_is_upstream_blocked`
- `test_blocked_stale_authorized_is_upstream_blocked`
- `test_blocked_fresh_not_authorized_is_upstream_blocked`
- `test_blocked_fresh_authorized_is_upstream_blocked`
- `test_prepared_stale_not_authorized_is_stale`
- `test_prepared_stale_authorized_is_stale`
- `test_prepared_fresh_not_authorized_requires_authorization`
- `test_prepared_fresh_authorized_is_send_authorized`

#### Phase29SnapshotAggregateTests — 10

- `test_candidate_count_exact`
- `test_send_authorized_count_exact`
- `test_send_blocked_count_exact`
- `test_authorization_required_count_exact`
- `test_authorization_stale_count_exact`
- `test_upstream_blocked_count_exact`
- `test_automatic_retry_count_zero`
- `test_candidate_partition_invariant`
- `test_blocked_reason_sum_invariant`
- `test_empty_snapshot_all_counts_zero`

#### Phase29ForbiddenSideEffectTests — 8

- `test_no_provider_client_call`
- `test_no_websocket_client_call`
- `test_no_oauth_or_token_access`
- `test_no_dotenv_or_credential_access`
- `test_no_external_network`
- `test_no_account_access`
- `test_no_order_or_kt10000_call`
- `test_no_consumption_ledger_mutation`

#### Phase29CompatibilityBoundaryTests — 8

- `test_phase28_public_api_unchanged`
- `test_phase27_public_api_unchanged`
- `test_phase26_public_api_unchanged`
- `test_phase25_public_api_unchanged`
- `test_attempt_prepared_does_not_imply_send_authorized`
- `test_validation_failure_precedes_decision`
- `test_venue_capability_not_recomputed`
- `test_send_authorized_has_no_submission_or_consumption_semantics`

exact test name count는 89, unique name count는 89이며 duplicate는 0이어야 한다.

Future atomic-consumption ledger, actual authority transaction, actual POST,
broker ambiguous-result handling tests는 Phase 29 targeted 89에 포함하지 않는다.

위 future responsibility는 `FUTURE_SUBMISSION_BOUNDARY_TEST_MANIFEST`로 별도 유지하고,
향후 actual Submission Phase implementation 때 해당 Phase의 신규 테스트로 산입한다.

### Registration boundary

Phase 29 공식 계약 README 등록 자체는 Phase 29 source/test 구현 승인이 아니다.

README 등록 단계에서는 다음을 금지한다.

- Phase 29 source/test 생성 또는 수정
- `src/kiwoom_trading_system/brokers/kiwoom/rest/__init__.py` 변경
- dependency 변경
- credential/token/account/network/order 접근
- git add
- git commit
- git push
- Current Phase 변경

README 공식 계약 등록 후에도 `Current Phase`는 별도 구현/Closure 승인 전까지 `PHASE28`로 유지한다.

### Implementation allowed paths

Phase 29 implementation mutation allowlist는 exact 2개 경로로 제한한다.

- `src/kiwoom_trading_system/brokers/kiwoom/rest/watchlist_order_send_authorization.py`
- `tests/test_watchlist_order_send_authorization.py`

Phase 29 implementation 단계에서는 위 두 경로만 생성 또는 수정할 수 있다.

`README.md`는 Phase 29 implementation mutation allowlist에 포함하지 않는다.
Implementation Allowed Paths README Amendment Registration Actual Rerun으로 확정된 README exact identity를 Phase 29 implementation 동안 byte-for-byte 보존한다.
승인된 ` M README.md` 상태는 expected pre-existing approved change이며 dirty error로 처리하지 않는다.

`src/kiwoom_trading_system/brokers/kiwoom/rest/__init__.py`는 implementation allowed path가 아니며 기존 exact identity를 보존한다.
Phase 29 public API exact 8은 `src/kiwoom_trading_system/brokers/kiwoom/rest/watchlist_order_send_authorization.py` module-level public API로 제공하며 package-level re-export를 요구하지 않는다.

Phase 29 implementation에서는 그 밖의 기존 source/test, `README.md`, `rest/__init__.py`, `pyproject.toml`, `uv.lock`, `.env`, credential/token 관련 파일, Git index/commit/remote, Current Phase를 수정하지 않는다.

Future implementation commit path set과 git add/commit 권한은 별도 승인 대상이며, 본 allowed-path contract approval 또는 README amendment registration으로 자동 승인하지 않는다.

## Phase 30 — demo Kiwoom Cash BUY-Order Request Materialization Snapshot 기반선 v1.0

Order Submission: OUT OF SCOPE

`FROZEN_CONTRACT_IDENTITY_SHA256=A542DE4A23659E0B99A3FDE31F899FEF4FFD7B6A2ABBBA29C902ADBD5BE3F54D`

Phase 30은 Phase 29에서 검증된 authorization evidence와 upstream order-data provenance를 실제 provider/client 전송 없이 Kiwoom 국내주식 BUY 주문 request 형상의 immutable local snapshot으로 결정적으로 materialize하는 pure local boundary이다.

Phase 30 자체에서는 provider/client 호출, OAuth/token/.env 접근, account 조회, external network, 실제 `kt10000` POST, 주문 제출, 응답 파싱, 주문번호 처리, retry/retransmission, authorization consumption/replay ledger mutation을 수행하지 않는다.

`MATERIALIZED != AUTHORIZED_TO_SEND`
`MATERIALIZED != ORDER_SUBMITTED`
`MATERIALIZED != ORDER_ACCEPTED`

### Scope

Phase 30 exact scope는 다음과 같다.

- environment = `demo` only
- side = `BUY` only
- exchange = `KRX` only
- cash order only
- order style = `LIMIT` 또는 `MARKET`
- provider request body materialization
- deterministic materialization fingerprint
- immutable input/snapshot/body
- local provenance reference preservation
- no credentials
- no account access
- no network
- no provider call
- no order submission
- no retry

SELL=`kt10001`, NXT, SOR, credit order, amend/cancel, IOC/FOK, 조건부지정가, 시간외, 최유리, 최우선, 스톱지정가, 중간가, response parsing, order number, actual transport는 Phase 30 범위가 아니다.

SELL은 현재 local upstream `WatchlistOrderIntentSide`가 BUY-only이므로 Phase 30에 포함하지 않고 별도 후속 계약으로 분리한다.

### Public API

Phase 30 module-level public API는 exact 4개로 제한한다.

1. `WatchlistOrderSendRequestError`
2. `WatchlistOrderSendRequestInput`
3. `WatchlistOrderSendRequestSnapshot`
4. `build_demo_watchlist_order_send_request_snapshot`

`WatchlistOrderSendRequestError`는 `RuntimeError`를 상속한다.

exact synchronous builder signature:

`build_demo_watchlist_order_send_request_snapshot(`
`    request: WatchlistOrderSendRequestInput,`
`) -> WatchlistOrderSendRequestSnapshot`

defaults는 없다.

`src/kiwoom_trading_system/brokers/kiwoom/rest/__init__.py` package-level re-export는 Phase 30 계약에 포함하지 않는다.

### WatchlistOrderSendRequestInput

`WatchlistOrderSendRequestInput`은 frozen immutable dataclass이다.

exact field order는 다음 9개이다.

1. `environment`
2. `side`
3. `exchange`
4. `stock_code`
5. `quantity`
6. `order_style`
7. `limit_price`
8. `source_attempt_ref`
9. `authorization_evidence_ref`

field contract:

- `environment`는 exact `str` `"demo"`여야 한다.
- `side`는 exact `str` `"BUY"`여야 한다.
- `exchange`는 exact `str` `"KRX"`여야 한다.
- `stock_code`는 exact `str`, length 1..12, non-empty이며 leading/trailing whitespace와 control character를 허용하지 않는다.
- `quantity`는 exact `int`이고 `bool`을 허용하지 않으며 `> 0`, decimal representation length `<= 12`여야 한다.
- `order_style`은 exact `str` `"LIMIT"` 또는 `"MARKET"`이어야 한다.
- `LIMIT`이면 `limit_price`는 exact positive `int`, `bool` 금지, decimal representation length `<= 12`여야 한다.
- `MARKET`이면 `limit_price`는 exact `None`이어야 한다.
- `source_attempt_ref`는 exact `str`, length 1..128, non-empty, non-whitespace이며 control character를 허용하지 않는 opaque provenance reference이다.
- `authorization_evidence_ref`는 exact `str`, length 1..128, non-empty, non-whitespace이며 control character를 허용하지 않는 opaque provenance reference이다.

### Canonical provenance

`source_attempt_ref`의 canonical upstream provenance source는 Phase 29 `KiwoomOrderSendAuthorizationContext.submission_attempt_reference`이다.

`authorization_evidence_ref`의 canonical upstream provenance source는 Phase 29 `KiwoomOrderSendAuthorizationContext.authorization_evidence_snapshot_id`이다.

`send_authorization_reference`와 `authorization_authority_reference`는 각각 별도 의미를 유지하며 `authorization_evidence_ref`로 대체하거나 재해석하지 않는다.

Phase 30 builder는 Phase 29 object graph를 import/traverse/recompute하지 않는다. caller/adapter가 이미 검증된 opaque reference를 `WatchlistOrderSendRequestInput`에 공급한다.

`source_snapshot` object 자체를 `str(...)`, `repr(...)`, hash, object id 또는 임의 serialization으로 `source_attempt_ref`로 변환하는 것은 금지한다.

provenance reference의 존재는 actual order send permission을 의미하지 않는다.

### Provider request contract

Phase 30 BUY provider contract는 다음과 같이 고정한다.

- `api_id = "kt10000"`
- `http_method = "POST"`
- `api_path = "/api/dostk/ordr"`
- `dmst_stex_tp = "KRX"`
- `stk_cd = stock_code`
- `ord_qty = str(quantity)`
- `cond_uv = ""`

LIMIT:

- `ord_uv = str(limit_price)`
- `trde_tp = "0"`

MARKET:

- `ord_uv = ""`
- `trde_tp = "3"`

provider body exact key set는 다음 6개이다.

1. `dmst_stex_tp`
2. `stk_cd`
3. `ord_qty`
4. `ord_uv`
5. `trde_tp`
6. `cond_uv`

provider body의 모든 value는 `str`이다.

### WatchlistOrderSendRequestSnapshot

`WatchlistOrderSendRequestSnapshot`은 frozen immutable dataclass이다.

exact field order는 다음 15개이다.

1. `environment`
2. `side`
3. `exchange`
4. `api_id`
5. `http_method`
6. `api_path`
7. `body`
8. `source_attempt_ref`
9. `authorization_evidence_ref`
10. `materialization_fingerprint`
11. `transport_allowed`
12. `credential_accessed`
13. `network_performed`
14. `account_accessed`
15. `order_submitted`

`body`는 immutable mapping이어야 하며 builder 반환 후 mutation을 허용하지 않는다.

safety flags는 항상 다음과 같다.

- `transport_allowed == False`
- `credential_accessed == False`
- `network_performed == False`
- `account_accessed == False`
- `order_submitted == False`

### Deterministic materialization fingerprint

fingerprint field name은 exact `materialization_fingerprint`이다.

fingerprint envelope는 exact 다음 값을 포함한다.

- `environment`
- `side`
- `exchange`
- `api_id`
- `http_method`
- `api_path`
- provider `body`
- `source_attempt_ref`
- `authorization_evidence_ref`

canonical JSON:

`json.dumps(`
`    envelope,`
`    sort_keys=True,`
`    separators=(",", ":"),`
`    ensure_ascii=True,`
`    allow_nan=False,`
`)`

canonical JSON을 UTF-8 bytes로 encode한 후:

`hashlib.sha256(canonical_bytes).hexdigest()`

를 사용한다.

fingerprint는 lowercase 64-hex string이다.

known vector:

- `environment="demo"`
- `side="BUY"`
- `exchange="KRX"`
- `stock_code="005930"`
- `quantity=3`
- `order_style="LIMIT"`
- `limit_price=64500`
- `source_attempt_ref="attempt-1"`
- `authorization_evidence_ref="snapshot-1"`

expected fingerprint:

`95a9556fe973f96e40d664b3369d96366f6bc00fbc3ccd34cc14058925bebc69`

같은 exact input은 같은 fingerprint를 생성해야 하며, provider request 또는 두 provenance reference 중 하나가 달라지면 fingerprint도 달라져야 한다.

### Validation order and errors

validation order와 first-error precedence는 다음 exact 순서로 고정한다.

1. `ENVIRONMENT_PROHIBITED`
2. `SIDE_UNSUPPORTED`
3. `DEMO_EXCHANGE_UNSUPPORTED`
4. `STOCK_CODE_INVALID`
5. `QUANTITY_INVALID`
6. `ORDER_STYLE_UNSUPPORTED`
7. `LIMIT_PRICE_INVALID`
8. `MARKET_PRICE_MUST_BE_EMPTY`
9. `SOURCE_ATTEMPT_REF_INVALID`
10. `AUTHORIZATION_EVIDENCE_REF_INVALID`

복수 오류가 존재해도 위 순서의 첫 오류 하나만 raise한다.

validation failure에서는 partial body, partial snapshot 또는 fingerprint를 반환하지 않는다.

### State transition

Phase 30 state transition은 다음 세 단계뿐이다.

`INPUT -> VALIDATED -> MATERIALIZED`

failure는 fail closed이며 partial state를 외부에 반환하지 않는다.

automatic retry, retry counter, backoff, resend, reclaim, authorization reuse는 존재하지 않는다.

### Forbidden side effects

Phase 30 module과 builder에서는 다음을 모두 금지한다.

- provider REST/WebSocket client call
- OAuth/token access
- `.env`/credential access
- environment credential lookup
- account access
- external network
- file I/O
- actual order action
- actual `kt10000` POST
- response parsing
- order-number handling
- Phase 29 source object traversal
- source object mutation
- authorization consumption/replay ledger mutation
- retry/retransmission
- wall-clock/time dependency
- UUID generation
- randomness

### Runtime targeted test manifest

Phase 30 runtime targeted test total은 exact `42`개이다.

`EXPECTED_PRE_IMPLEMENTATION_FULL_REGRESSION=794`
`EXPECTED_NEW_TEST_DELTA=42`
`EXPECTED_POST_IMPLEMENTATION_FULL_REGRESSION=836`

exact test names:

1. `test_public_api_exact_four_symbols`
2. `test_builder_exact_signature_and_return_type`
3. `test_error_is_runtime_error`
4. `test_input_exact_fields_and_frozen`
5. `test_snapshot_exact_fields_and_frozen`
6. `test_snapshot_body_is_immutable`
7. `test_buy_limit_snapshot_exact`
8. `test_buy_market_snapshot_exact`
9. `test_api_id_method_and_path_exact`
10. `test_provider_body_key_set_exact`
11. `test_provider_body_values_are_strings`
12. `test_limit_provider_mapping_exact`
13. `test_market_provider_mapping_exact`
14. `test_provider_exchange_and_condition_price_exact`
15. `test_non_demo_environment_rejected`
16. `test_non_buy_side_rejected`
17. `test_non_krx_exchange_rejected`
18. `test_stock_code_blank_whitespace_control_rejected`
19. `test_stock_code_type_and_length_rejected`
20. `test_quantity_requires_exact_int_not_bool`
21. `test_quantity_positive_and_12_digit_limit`
22. `test_order_style_invalid_rejected`
23. `test_limit_price_required_exact_positive_int_and_12_digit_limit`
24. `test_market_price_must_be_none`
25. `test_source_attempt_ref_invalid_rejected`
26. `test_authorization_evidence_ref_invalid_rejected`
27. `test_provenance_references_preserved_exactly`
28. `test_phase29_submission_attempt_reference_contract_available`
29. `test_phase29_authorization_evidence_snapshot_id_contract_available`
30. `test_materializer_does_not_traverse_phase29_source_chain`
31. `test_fingerprint_repeat_stable`
32. `test_fingerprint_known_vector`
33. `test_fingerprint_changes_with_provider_request`
34. `test_fingerprint_changes_with_source_attempt_ref`
35. `test_fingerprint_changes_with_authorization_evidence_ref`
36. `test_fingerprint_is_lowercase_sha256_hex`
37. `test_builder_does_not_read_environment_credentials`
38. `test_builder_does_not_perform_network_io`
39. `test_builder_does_not_access_account`
40. `test_builder_does_not_submit_order_or_call_provider`
41. `test_transport_and_side_effect_flags_are_false`
42. `test_builder_does_not_use_file_io_retry_time_uuid_or_randomness`

exact test name count=42, unique name count=42, duplicate=0이어야 한다.

### Registration boundary

Phase 30 공식 계약 README 등록 자체는 Phase 30 source/test 구현 승인이 아니다.

README 등록 단계에서는 다음을 금지한다.

- Phase 30 source/test 생성 또는 수정
- 기존 Phase29/upstream source/test 수정
- `src/kiwoom_trading_system/brokers/kiwoom/rest/__init__.py` 변경
- dependency 변경
- credential/token/account/network/order 접근
- git add
- git commit
- git push
- Current Phase 변경

README 공식 계약 등록 이후에도 `Current Phase`는 별도 implementation/Closure 승인 전까지 `PHASE29`로 유지한다.

### Implementation allowed paths

Phase 30 implementation mutation allowlist는 exact 다음 2개 경로로 제한한다.

- `src/kiwoom_trading_system/brokers/kiwoom/rest/watchlist_order_send_request.py`
- `tests/test_watchlist_order_send_request.py`

Phase 30 implementation 단계에서는 위 두 경로만 생성 또는 수정할 수 있다.

`README.md`는 Phase 30 implementation mutation allowlist에 포함하지 않는다.
`src/kiwoom_trading_system/brokers/kiwoom/rest/__init__.py`도 implementation allowed path가 아니다.

Phase 30 implementation에서 기존 Phase29/upstream source/test, `README.md`, `rest/__init__.py`, `pyproject.toml`, `uv.lock`, `.env`, credential/token 관련 파일, Git index/commit/remote, Current Phase를 수정하지 않는다.

Future implementation commit path set과 git add/commit 권한은 별도 승인 대상이며, 본 README contract registration이 자동 승인하지 않는다.

## Phase 31 — demo Kiwoom Cash BUY-Order Authorization Consumption Claim & Replay-Guard Preparation Snapshot 기반선 v1.0

Order Submission: OUT OF SCOPE
Authorization Consumption Transaction: OUT OF SCOPE

`FROZEN_CONTRACT_IDENTITY_SHA256=D9BC9127B1BD90BC54049FA87F357C0DF94F6D82C2F9B89EB063542155B94CAA`

Phase 31은 Phase 30 `WatchlistOrderSendRequestSnapshot`의 이미 materialize된 demo/KRX/cash BUY request와 Phase 29 Future Submission boundary가 정의한 authorization provenance reference를 결합하여, future authoritative atomic check-and-consume transaction에 전달할 authorization claim identity와 replay guard를 immutable local snapshot으로 준비하는 pure local boundary이다.

Phase 31 자체에서는 authorization authority/controller 호출, authorization consumption, replay-ledger mutation, credential/token/.env 접근, account 접근, provider/client 호출, external network, 실제 `kt10000` POST, 주문 제출, response parsing, 주문번호 처리, retry/retransmission을 수행하지 않는다.

`CLAIM_PREPARED != SEND_AUTHORIZED`
`CLAIM_PREPARED != CURRENTLY_VALID_AT_POST_TIME`
`CLAIM_PREPARED != AUTHORIZATION_CONSUMED`
`CLAIM_PREPARED != POST_PERMITTED`
`CLAIM_PREPARED != ORDER_SUBMITTED`
`CLAIM_PREPARED != ORDER_ACCEPTED`

### Scope

Phase 31 exact scope:

- environment = `demo` only
- side = `BUY` only
- exchange = `KRX` only
- cash order only
- exact Phase 30 `WatchlistOrderSendRequestSnapshot` upstream
- Phase 29 Future Submission claim 4-tuple 의미 보존
- Phase 29 Future Submission replay-guard 2-tuple 의미 보존
- authorization claim identity preparation
- authorization replay guard preparation
- deterministic claim fingerprint
- immutable context/snapshot
- no authorization authority/controller call
- no authorization consumption
- no replay-ledger mutation
- no credential/token/account access
- no network
- no provider call
- no actual `kt10000` POST
- no order submission
- no response parsing
- no automatic retry

SELL, NXT, SOR, credit order, amend/cancel, 추가 주문유형, actual authorization check-and-consume, actual transport, provider response, order number, broker-side reconciliation mutation은 Phase 31 범위가 아니다.

### Public API

Phase 31 module-level public API는 exact 4개로 제한한다.

1. `WatchlistOrderAuthorizationConsumptionClaimError`
2. `KiwoomOrderAuthorizationConsumptionClaimContext`
3. `WatchlistOrderAuthorizationConsumptionClaimSnapshot`
4. `build_demo_watchlist_order_authorization_consumption_claim_snapshot`

`WatchlistOrderAuthorizationConsumptionClaimError`는 `RuntimeError`를 상속한다.

exact synchronous builder signature:

`build_demo_watchlist_order_authorization_consumption_claim_snapshot(`
`    source_snapshot: WatchlistOrderSendRequestSnapshot,`
`    context: KiwoomOrderAuthorizationConsumptionClaimContext,`
`) -> WatchlistOrderAuthorizationConsumptionClaimSnapshot`

defaults는 없다.

`src/kiwoom_trading_system/brokers/kiwoom/rest/__init__.py` package-level re-export는 Phase 31 계약에 포함하지 않는다.

### KiwoomOrderAuthorizationConsumptionClaimContext

`KiwoomOrderAuthorizationConsumptionClaimContext`는 frozen immutable dataclass이다.

exact field order는 다음 4개이다.

1. `authorization_authority_reference`
2. `authorization_evidence_snapshot_id`
3. `submission_attempt_reference`
4. `send_authorization_reference`

field contract:

- `authorization_authority_reference`는 Phase 29 계약을 좁히지 않으며 exact `str`, non-empty, non-whitespace opaque stable authority namespace identity이다.
- `send_authorization_reference`는 Phase 29 `AUTHORIZED_FOR_SEND` reference 계약을 좁히지 않으며 exact `str`, non-empty, non-whitespace opaque grant/reference이다.
- `authorization_evidence_snapshot_id`는 exact `str`이어야 하며 Phase 30 `authorization_evidence_ref`와 exact match해야 한다. Phase 30 upstream의 1..128/non-whitespace/control-character-free 계약을 그대로 승계한다.
- `submission_attempt_reference`는 exact `str`이어야 하며 Phase 30 `source_attempt_ref`와 exact match해야 한다. Phase 30 upstream의 1..128/non-whitespace/control-character-free 계약을 그대로 승계한다.

Phase 31은 `authorization_authority_reference` 또는 `send_authorization_reference`에 Phase 29보다 새로운 max-length/control-character 제한을 추가하지 않는다.

### Trusted provenance boundary

Phase 29 계약에서 `authorization_state`, `send_authorization_reference`, `authorization_authority_reference`, `authorization_evidence_snapshot_id`, `is_fresh`는 approved external authorization authority/controller/adapter가 제공하는 trusted provenance assertion으로 취급되지만, Phase 29 local validation 자체가 그 external-origin 사실을 독립적으로 입증하지는 않는다.

Phase 31도 같은 trust boundary를 좁히거나 확장하지 않는다.

caller/adapter는 동일한 approved Phase 29 authorization provenance assertion에서 다음 4개 reference를 공급해야 한다.

- `authorization_authority_reference`
- `authorization_evidence_snapshot_id`
- `submission_attempt_reference`
- `send_authorization_reference`

그러나 Phase 31 local builder가 독립적으로 증명하는 것은 다음뿐이다.

- exact local type/structure
- Phase 30 `source_attempt_ref`와 `submission_attempt_reference` exact binding
- Phase 30 `authorization_evidence_ref`와 `authorization_evidence_snapshot_id` exact binding
- Phase 30 request snapshot integrity
- deterministic claim/replay-guard materialization

Phase 31은 authority가 실제 승인 authority인지, grant가 실제 해당 authority에서 발행되었는지, grant가 해당 attempt에 귀속되는지, 현재 fresh/current-valid인지, consumed/revoked 상태인지에 대해 독립적으로 주장하지 않는다.

해당 검증은 future authoritative atomic check-and-consume boundary의 책임이다.

### Phase 30 upstream validation

`source_snapshot`은 exact `WatchlistOrderSendRequestSnapshot`이어야 한다.

Phase 31은 Phase 30 upstream을 신뢰만 하지 않고 등록된 immutable contract invariant를 local pure validation으로 재확인한다.

필수 invariant:

- `environment == "demo"`
- `side == "BUY"`
- `exchange == "KRX"`
- `api_id == "kt10000"`
- `http_method == "POST"`
- `api_path == "/api/dostk/ordr"`
- provider `body` exact key set = `dmst_stex_tp`, `stk_cd`, `ord_qty`, `ord_uv`, `trde_tp`, `cond_uv`
- provider `body` 모든 value는 exact `str`
- Phase 30 LIMIT/MARKET provider mapping invariant 유지
- `source_attempt_ref` exact Phase 30 contract 유지
- `authorization_evidence_ref` exact Phase 30 contract 유지
- `transport_allowed == False`
- `credential_accessed == False`
- `network_performed == False`
- `account_accessed == False`
- `order_submitted == False`
- `materialization_fingerprint` lowercase 64-hex

Phase 31은 Phase 30 request/body/provenance envelope에서 Phase 30 canonical algorithm을 사용하여 expected `materialization_fingerprint`를 pure local로 재계산하고 `source_snapshot.materialization_fingerprint`와 exact match해야 한다.

이 fingerprint integrity validation은 Phase 30 request를 remap/recalculate/replace/mutate/reorder하는 행위가 아니다.

Phase 31은 Phase 30 `source_snapshot`, body 및 provenance 값을 변경하지 않는다.

### Exact reference binding

`context.submission_attempt_reference == source_snapshot.source_attempt_ref`

`context.authorization_evidence_snapshot_id == source_snapshot.authorization_evidence_ref`

하나라도 다르면 fail closed한다.

### Authorization claim identity

Phase 29 Future Submission boundary의 exact 4-tuple 의미와 순서를 그대로 보존한다.

`authorization_claim_identity = (`
`    context.authorization_authority_reference,`
`    context.authorization_evidence_snapshot_id,`
`    context.submission_attempt_reference,`
`    context.send_authorization_reference,`
`)`

### Authorization replay guard

Phase 29 Future Submission boundary의 exact 2-tuple 의미와 순서를 그대로 보존한다.

`authorization_replay_guard = (`
`    context.authorization_authority_reference,`
`    context.send_authorization_reference,`
`)`

`send_authorization_reference` 단독은 claim identity가 아니다.

Phase 31은 claim identity/replay guard가 unconsumed인지, revoked인지, stale인지 또는 현재 authority에서 유효한지를 주장하지 않는다.

### WatchlistOrderAuthorizationConsumptionClaimSnapshot

`WatchlistOrderAuthorizationConsumptionClaimSnapshot`은 frozen immutable dataclass이다.

exact field order는 다음 11개이다.

1. `source_snapshot`
2. `context`
3. `authorization_claim_identity`
4. `authorization_replay_guard`
5. `claim_fingerprint`
6. `claim_prepared`
7. `authorization_consumption_committed`
8. `post_permitted`
9. `automatic_retry_permitted`
10. `network_performed`
11. `order_submitted`

builder 성공 시:

- `source_snapshot` identity exact preserve
- `context` identity exact preserve
- `claim_prepared == True`
- `authorization_consumption_committed == False`
- `post_permitted == False`
- `automatic_retry_permitted == False`
- `network_performed == False`
- `order_submitted == False`

Phase 30의 `transport_allowed == False`는 변경하지 않는다.

Phase 31 snapshot 생성만으로 transport permission, current authorization validity, authorization consumption 또는 order permission이 발생하지 않는다.

### Deterministic claim fingerprint

fingerprint field name은 exact `claim_fingerprint`이다.

fingerprint envelope exact key set:

- `materialization_fingerprint`
- `authorization_claim_identity`
- `authorization_replay_guard`

tuple은 canonical JSON에서 JSON array로 표현한다.

canonical JSON:

`json.dumps(`
`    envelope,`
`    sort_keys=True,`
`    separators=(",", ":"),`
`    ensure_ascii=True,`
`    allow_nan=False,`
`)`

canonical JSON을 UTF-8 bytes로 encode한 후:

`hashlib.sha256(canonical_bytes).hexdigest()`

를 사용한다.

`claim_fingerprint`는 lowercase 64-hex string이다.

known vector:

- `materialization_fingerprint = "95a9556fe973f96e40d664b3369d96366f6bc00fbc3ccd34cc14058925bebc69"`
- `authorization_authority_reference = "authority-1"`
- `authorization_evidence_snapshot_id = "snapshot-1"`
- `submission_attempt_reference = "attempt-1"`
- `send_authorization_reference = "grant-1"`

expected `claim_fingerprint`:

`6ecb23bec89d683c156299afc011b8eac1345e0d664de070b7a3dba427f3e7c4`

같은 exact input은 같은 fingerprint를 생성해야 하며 envelope element 하나라도 달라지면 fingerprint도 달라져야 한다.

### Validation order and first-error precedence

validation order와 first-error precedence는 exact 다음 순서로 고정한다.

1. `SOURCE_SNAPSHOT_TYPE_INVALID`
2. `SOURCE_SNAPSHOT_STRUCTURE_INVALID`
3. `SOURCE_SNAPSHOT_SAFETY_INVALID`
4. `SOURCE_MATERIALIZATION_FINGERPRINT_INVALID`
5. `CONTEXT_TYPE_INVALID`
6. `AUTHORIZATION_AUTHORITY_REFERENCE_INVALID`
7. `AUTHORIZATION_EVIDENCE_SNAPSHOT_ID_INVALID`
8. `SUBMISSION_ATTEMPT_REFERENCE_INVALID`
9. `SEND_AUTHORIZATION_REFERENCE_INVALID`
10. `SUBMISSION_ATTEMPT_REFERENCE_MISMATCH`
11. `AUTHORIZATION_EVIDENCE_REFERENCE_MISMATCH`

복수 오류가 존재해도 위 순서의 첫 오류 하나만 `WatchlistOrderAuthorizationConsumptionClaimError`로 raise한다.

validation failure에서는 partial claim identity, replay guard, fingerprint 또는 snapshot을 반환하지 않는다.

### State transition

Phase 31 state transition은 다음 세 단계뿐이다.

`MATERIALIZED -> CLAIM_BINDING_VALIDATED -> CLAIM_PREPARED`

failure는 fail closed이며 partial state를 외부에 반환하지 않는다.

`CLAIM_PREPARED` 이후에도:

- authorization consumption은 commit되지 않았다.
- `POST_PERMITTED`가 아니다.
- provider transport를 허용하지 않는다.
- automatic retry/reclaim/unconsume/reuse/retransmission을 허용하지 않는다.

### Future authoritative atomic-consumption boundary

향후 별도 공식 Phase에서만 authoritative atomic check-and-consume을 수행할 수 있다.

그 future boundary는 approved authorization authority/controller가 보장하는 하나의 authoritative atomic transaction 안에서 최소 다음을 검증해야 한다.

- claim identity unconsumed
- replay guard unconsumed
- exact authority namespace 동일
- exact immutable evidence snapshot identity 동일
- exact `submission_attempt_reference` 동일
- exact `send_authorization_reference` 동일
- grant가 해당 exact attempt에 귀속
- grant가 revoked/invalidated되지 않음
- evidence/grant가 transaction 시점에 authoritative하게 fresh/current-valid
- check와 consume이 하나의 atomic transaction임

위 조건이 모두 참일 때만 claim identity와 replay guard를 함께 consumed로 atomic commit할 수 있다.

partial consume 또는 one-key-only success는 허용하지 않는다.

atomicity를 보장할 수 없거나 결과가 already-consumed, duplicate, conflict, stale, revoked, invalid, timeout, cancellation, failure, unknown 또는 ambiguous이면 `POST_PERMITTED=NO`이며 `kt10000` POST를 시도하지 않는다.

automatic retry, automatic reclaim, automatic unconsume, authorization reuse, retransmission은 금지한다.

Phase 31은 이 future transaction을 구현하거나 승인하지 않는다.

### Forbidden side effects

Phase 31 module과 builder에서는 다음을 모두 금지한다.

- provider REST/WebSocket client call
- OAuth/token access
- `.env`/credential access
- environment credential lookup
- account access
- external network
- authorization authority/controller call
- authorization consumption
- consumption/replay-ledger mutation
- actual order action
- actual `kt10000` POST
- response parsing
- order-number handling
- Phase 29/30 source object mutation
- file I/O
- retry/backoff/retransmission
- wall-clock/time dependency
- UUID generation
- randomness

### Runtime targeted test manifest

Phase 31 future implementation targeted test total은 exact `42`개이다.

`EXPECTED_PRE_IMPLEMENTATION_FULL_REGRESSION=836`
`EXPECTED_NEW_TEST_DELTA=42`
`EXPECTED_POST_IMPLEMENTATION_FULL_REGRESSION=878`

exact test names:

1. `test_public_api_exact_four_symbols`
2. `test_error_is_runtime_error`
3. `test_context_exact_fields_and_frozen`
4. `test_snapshot_exact_fields_and_frozen`
5. `test_builder_exact_signature_and_return_type`
6. `test_builder_is_synchronous`
7. `test_rejects_nonexact_phase30_snapshot_type`
8. `test_preserves_phase30_snapshot_identity`
9. `test_requires_phase30_demo_environment`
10. `test_requires_phase30_buy_side`
11. `test_requires_phase30_krx_exchange`
12. `test_requires_phase30_kt10000_api_id`
13. `test_requires_phase30_post_method`
14. `test_requires_phase30_order_path`
15. `test_requires_phase30_exact_provider_body_key_set_and_string_values`
16. `test_requires_phase30_all_safety_flags_false`
17. `test_recomputes_and_requires_exact_phase30_materialization_fingerprint`
18. `test_does_not_remap_recalculate_replace_mutate_or_reorder_phase30_request`
19. `test_rejects_nonexact_context_type`
20. `test_authorization_authority_reference_preserves_phase29_exact_str_nonblank_contract`
21. `test_authorization_evidence_snapshot_id_binding_input_invalid_rejected`
22. `test_submission_attempt_reference_binding_input_invalid_rejected`
23. `test_send_authorization_reference_preserves_phase29_exact_str_nonblank_contract`
24. `test_submission_attempt_reference_binding_exact`
25. `test_authorization_evidence_reference_binding_exact`
26. `test_claim_identity_exact_four_tuple`
27. `test_replay_guard_exact_two_tuple`
28. `test_context_references_preserved_exactly_without_external_origin_claim`
29. `test_claim_fingerprint_repeat_stable`
30. `test_claim_fingerprint_known_vector`
31. `test_claim_fingerprint_changes_with_materialization_fingerprint`
32. `test_claim_fingerprint_changes_with_authority_reference`
33. `test_claim_fingerprint_changes_with_send_authorization_reference`
34. `test_claim_fingerprint_is_lowercase_sha256_hex`
35. `test_claim_prepared_true`
36. `test_authorization_consumption_committed_false`
37. `test_post_permitted_false`
38. `test_automatic_retry_permitted_false`
39. `test_builder_does_not_call_authorization_authority_or_mutate_ledger`
40. `test_builder_does_not_read_credentials_access_account_or_perform_network`
41. `test_builder_does_not_call_provider_parse_response_or_handle_order_number`
42. `test_builder_does_not_use_file_io_retry_time_uuid_or_randomness`

exact test name count=42, unique name count=42, duplicate=0이어야 한다.

### Registration boundary

Phase 31 공식 계약 README 등록 자체는 Phase 31 source/test 구현 승인이 아니다.

README 등록 단계에서는 다음을 금지한다.

- Phase 31 source/test 생성 또는 수정
- 기존 Phase29/Phase30/upstream source/test 수정
- `src/kiwoom_trading_system/brokers/kiwoom/rest/__init__.py` 변경
- dependency 변경
- credential/token/account/network/provider/order 접근
- authorization consumption 또는 replay-ledger mutation
- git add
- git commit
- git push
- Current Phase 변경

README 공식 계약 등록 이후에도 `Current Phase`는 별도 implementation/Closure 승인 전까지 `PHASE30`으로 유지한다.

### Future implementation allowed paths

Phase 31 future implementation mutation allowlist 후보는 exact 다음 2개 경로로 제한한다.

- `src/kiwoom_trading_system/brokers/kiwoom/rest/watchlist_order_authorization_consumption_claim.py`
- `tests/test_watchlist_order_authorization_consumption_claim.py`

DRAFT/README registration approval만으로 위 두 경로 생성 또는 수정은 승인되지 않는다.

`README.md`, `src/kiwoom_trading_system/brokers/kiwoom/rest/__init__.py`, 기존 Phase29/Phase30/upstream source/test, `pyproject.toml`, `uv.lock`, `.env`, credential/token 관련 파일, Git index/commit/remote, Current Phase는 future implementation allowlist에 포함하지 않는다.

future implementation commit path set과 git add/commit 권한은 별도 승인 대상이다.

### Closure conditions

Phase31은 다음 전체가 별도 승인 및 실제 검증되기 전 완료로 간주하지 않는다.

1. Final Contract Review 승인
2. README exact official contract registration 별도 승인 및 Actual 검증
3. frozen contract identity 확정
4. implementation 별도 승인
5. exact two-path implementation
6. targeted tests `42/42`
7. expected full regression `878/878`
8. failures=0
9. errors=0
10. 미승인 skipped=0
11. Phase29/Phase30 및 protected hashes 불변
12. dependency 변경 없음
13. package re-export 변경 없음
14. credential/token/account/network/provider/order 접근 없음
15. authorization consumption/replay-ledger mutation 없음
16. Git 변경 범위 승인 경로와 exact 일치
17. 별도 commit 승인 및 검증
18. 별도 Closure 승인 및 Current Phase alignment

Phase31 Closure 전까지 top-level `Current Phase`는 `PHASE30`으로 유지한다.

## Phase 32 — demo Kiwoom Cash BUY-Order Authority Adapter Check-and-Consume Result Evidence Snapshot 기반선 v1.0

Concrete Authority Backend: OUT OF SCOPE
Durable Ledger / Persistence: OUT OF SCOPE
Provider Transport / Order Submission: OUT OF SCOPE
Authority Adapter Lifecycle Ownership: ADAPTER / AUTHORITY
Phase32 Deferred-Object Lifecycle Ownership: NO

`FROZEN_CONTRACT_IDENTITY_SHA256=20C5E20145A05B349675CCE273AA5B2C4DB23F7FEDF62D1E9A74803CB135ACC4`

### Frozen contract identity rule

`FROZEN_CONTRACT_IDENTITY_SHA256`는 exact CRLF UTF-8 payload에서 다음 marker paragraph 하나만 완전히 제거한 bytes의 SHA-256 uppercase hex이다.

`FROZEN_CONTRACT_IDENTITY_SHA256=<64 uppercase hex>`

marker paragraph removal 대상은 marker line과 바로 뒤 exact `CRLF CRLF`까지이다.

전체 payload 자체의 raw SHA-256은 frozen identity와 별도로 관리한다.

Phase 32는 exact Phase 31 `WatchlistOrderAuthorizationConsumptionClaimSnapshot`을 upstream으로 받아 deterministic local validation을 수행하고, passive static surface inspection을 통과한 ordinary synchronous Python authority operation을 정확히 한 번 시도한 뒤 authority-reported result evidence를 immutable local snapshot으로 materialize하는 경계이다.

Phase 32는 concrete authority backend identity, durable atomic check-and-consume 구현, persistent replay ledger, 실제 approval/conformance provenance, provider send eligibility 또는 actual order submission을 독립적으로 증명하거나 승인하지 않는다.

`PROTOCOL_COMPATIBLE != APPROVED_AUTHORITY`
`ASSERTED_AUTHORITY_REFERENCE != VERIFIED_TRUST`
`AUTHORITY_REPORTED_CONSUMED != DURABLE_CONSUMPTION_PROVEN`
`CONSUMPTION_EVIDENCE_CANDIDATE_READY != TRANSPORT_PERMISSION`
`PHASE32_EVIDENCE != PROVIDER_SEND_ELIGIBILITY`
`INDETERMINATE != BLOCKED`
`INDETERMINATE => COMMIT_STATE_UNKNOWN`
`LOCAL_VALIDATION_FAILURE != INDETERMINATE`
`LOCAL_VALIDATION_FAILURE => AUTHORITY_INVOCATION_ATTEMPT_COUNT == 0`
`LOCAL_VALIDATION_SUCCESS => AUTHORITY_INVOCATION_ATTEMPT_COUNT == 1`
`SECOND_AUTHORITY_INVOCATION == PROHIBITED`
`AUTOMATIC_RETRY == PROHIBITED`

### Scope

Phase 32 exact scope:

- environment = `demo` only
- side = `BUY` only
- exchange = `KRX` only
- cash order only
- exact Phase 31 `WatchlistOrderAuthorizationConsumptionClaimSnapshot` upstream
- pure local validation of Phase 30/31 materialization and claim bindings
- caller-asserted authority approval/conformance references
- passive adapter surface inspection
- ordinary synchronous Python instance-method authority operation only
- exact one authority operation attempt after all local validation succeeds
- authority-reported result normalization
- immutable local evidence snapshot
- deterministic evidence fingerprint
- adapter/authority-owned async/background lifecycle
- no provider send permission creation
- no actual `kt10000` POST
- no credential/token/account access by Phase 32
- no automatic retry or second authority invocation

Concrete backend implementation, durable ledger/storage, actual atomic transaction implementation, production authority use, provider transport, response parsing, order number handling, SELL/NXT/SOR/credit/amend/cancel and actual order submission are outside Phase 32.

### Public API

Phase 32 module-level public API는 exact 5개로 제한한다.

1. `WatchlistOrderAuthorizationAdapterEvidenceError`
2. `KiwoomOrderAuthorizationAuthorityAdapter`
3. `KiwoomOrderAuthorizationAuthorityReportedResult`
4. `WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot`
5. `check_and_consume_demo_watchlist_order_authorization_adapter_evidence`

`WatchlistOrderAuthorizationAdapterEvidenceError`는 `RuntimeError`를 상속한다.

`src/kiwoom_trading_system/brokers/kiwoom/rest/__init__.py` package-level re-export는 Phase 32 계약에 포함하지 않는다.

### Builder signature

exact synchronous builder signature:

`check_and_consume_demo_watchlist_order_authorization_adapter_evidence(`
`    source_snapshot: WatchlistOrderAuthorizationConsumptionClaimSnapshot,`
`    authority: KiwoomOrderAuthorizationAuthorityAdapter,`
`    *,`
`    asserted_authority_approval_reference: str,`
`    asserted_authority_conformance_reference: str,`
`) -> WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot`

defaults는 없다.

### Authority Adapter Protocol

`KiwoomOrderAuthorizationAuthorityAdapter`는 typing contract이다. Protocol compatibility 자체는 authority approval/trust proof가 아니다.

exact method contract:

`check_and_consume(`
`    *,`
`    authorization_claim_identity: tuple[str, str, str, str],`
`    authorization_replay_guard: tuple[str, str],`
`    claim_fingerprint: str,`
`    asserted_authority_approval_reference: str,`
`    asserted_authority_conformance_reference: str,`
`) -> KiwoomOrderAuthorizationAuthorityReportedResult`

Phase 32 local validation은 runtime signature를 사전 실행으로 probe하지 않는다.

### Exact type contract

- exact `str`: `type(value) is str`
- exact `bool`: `type(value) is bool`
- exact `tuple`: `type(value) is tuple`
- exact Python function surface: `type(value) is types.FunctionType`
- exact result dataclass: `type(value) is KiwoomOrderAuthorizationAuthorityReportedResult`
- `None`: `value is None`

boolean field는 integer `0/1`을 허용하지 않는다.

### Phase 31 upstream contract

`source_snapshot`은 exact `WatchlistOrderAuthorizationConsumptionClaimSnapshot`이어야 한다.

Phase 32는 최소 다음 Phase 31 invariants를 local pure validation으로 재확인한다.

- `claim_prepared == True`
- `authorization_consumption_committed == False`
- `post_permitted == False`
- `automatic_retry_permitted == False`
- `network_performed == False`
- `order_submitted == False`
- `authorization_claim_identity` exact 4-tuple
- `authorization_replay_guard` exact 2-tuple
- `claim_fingerprint` lowercase 64-hex
- embedded Phase 30 source snapshot의 `transport_allowed == False`
- embedded Phase 30 source snapshot의 credential/network/account/order safety flags가 모두 False
- exact Phase 30 request/materialization binding 유지

Phase 31 claim identity exact meaning/order:

`authorization_claim_identity = (`
`    authorization_authority_reference,`
`    authorization_evidence_snapshot_id,`
`    submission_attempt_reference,`
`    send_authorization_reference,`
`)`

Phase 31 replay guard exact meaning/order:

`authorization_replay_guard = (`
`    authorization_authority_reference,`
`    send_authorization_reference,`
`)`

Phase 32는 Phase 30 canonical materialization fingerprint와 Phase 31 canonical claim fingerprint를 pure local로 재계산하여 exact match를 요구한다. upstream object를 remap, replace 또는 mutate하지 않는다.

Phase 31 claim fingerprint canonical envelope exact key set:

- `materialization_fingerprint`
- `authorization_claim_identity`
- `authorization_replay_guard`

canonical JSON:

`json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)`

UTF-8 encode 후:

`hashlib.sha256(canonical_bytes).hexdigest()`

를 사용한다.

### Asserted authority references

`asserted_authority_approval_reference`와 `asserted_authority_conformance_reference`는 exact opaque reference이다.

각 reference는:

- exact `str`
- length `1..128`
- non-empty
- `value == value.strip()`
- whitespace-only 금지
- U+0000..U+001F 금지
- U+007F 금지
- trim/normalization/case-fold/replacement 금지

이 asserted references는 caller assertion이며 Phase 32 local validation이 외부 approval/conformance 사실을 독립 증명하지 않는다.

### Local validation reasons

allowed deterministic local validation reason exact 7:

1. `SOURCE_SNAPSHOT_TYPE_INVALID`
2. `SOURCE_SNAPSHOT_STRUCTURE_OR_SAFETY_INVALID`
3. `PHASE30_REQUEST_OR_MATERIALIZATION_BINDING_INVALID`
4. `PHASE31_CLAIM_FINGERPRINT_INVALID`
5. `ASSERTED_AUTHORITY_APPROVAL_REFERENCE_INVALID`
6. `ASSERTED_AUTHORITY_CONFORMANCE_REFERENCE_INVALID`
7. `AUTHORITY_CHECK_AND_CONSUME_SURFACE_INVALID`

error string은 exact reason string이다.

### Validation order and first-error precedence

authority surface inspection이나 authority operation attempt보다 먼저 exact 다음 순서로 검증한다.

1. source snapshot exact type
2. Phase 31 source structure/safety
3. Phase 30 request/materialization binding
4. Phase 31 claim fingerprint
5. asserted authority approval reference
6. asserted authority conformance reference
7. passive `check_and_consume` surface and synchronous function-kind

복수 오류가 있어도 위 순서의 첫 오류 하나만 `WatchlistOrderAuthorizationAdapterEvidenceError`로 raise한다.

local validation failure에서는:

- authority operation attempt=`0`
- authority function body execution 없음
- authority result 없음
- evidence fingerprint 없음
- snapshot 없음
- partial result 없음
- INDETERMINATE normalization 없음
- automatic retry 없음

### Passive adapter surface inspection

unique sentinel `MISSING`을 사용한다.

`class_surface = inspect.getattr_static(type(authority), "check_and_consume", MISSING)`

`instance_surface = inspect.getattr_static(authority, "check_and_consume", MISSING)`

surface validation에서 일반 `getattr()`, `hasattr()`, `callable()`을 사용하지 않는다.

valid surface는 다음을 모두 만족해야 한다.

1. `class_surface is not MISSING`
2. `instance_surface is not MISSING`
3. `instance_surface is class_surface`
4. `type(class_surface) is types.FunctionType`
5. `inspect.iscoroutinefunction(class_surface) is False`
6. `inspect.isgeneratorfunction(class_surface) is False`
7. `inspect.isasyncgenfunction(class_surface) is False`

하나라도 실패하면 `AUTHORITY_CHECK_AND_CONSUME_SURFACE_INVALID`이다.

passive inspection은 다음을 실행하지 않아야 한다.

- property getter
- arbitrary descriptor `__get__`
- adapter `__getattr__`
- adapter custom `__getattribute__`
- adapter operation body

### Supported and unsupported surface

지원:

- class-defined ordinary synchronous Python instance method
- inherited ordinary synchronous Python instance method
- decorator 결과의 final stored class surface가 exact `types.FunctionType`이고 coroutine/generator/async-generator로 분류되지 않는 경우

지원하지 않음:

- missing surface
- instance-level shadow
- staticmethod
- classmethod
- property
- arbitrary custom descriptor
- callable object surface
- dynamic `__getattr__` only surface
- custom `__getattribute__`로만 노출되는 surface
- built-in/extension callable descriptor
- native `async def`
- generator function
- async-generator function
- `inspect.markcoroutinefunction()`으로 coroutine function으로 표시된 sync function
- `types.coroutine` 기반 generator function

decorator의 내부 의도나 wrapped target은 역추적하지 않는다. final stored static surface만 local gate의 판단 근거이다.

### Invocation binding

모든 local validation이 성공하면 passive inspection에서 검증한 exact `class_surface`를 사용한다.

`bound_operation = types.MethodType(class_surface, authority)`

일반 `getattr(authority, "check_and_consume")`로 method를 다시 resolve하지 않는다.

dynamic descriptor resolution, `__getattr__`, custom `__getattribute__`를 invocation binding에 사용하지 않는다.

### Invocation attempt boundary

`authority_invocation_attempted`는 exact bound operation call expression을 시작하기 직전에 True로 간주한다.

valid local gate 이후 actual authority operation attempt는 exact 1회이다.

- prefetch call 없음
- second check 없음
- second consume 없음
- repeated invocation 없음
- automatic retry 없음

runtime signature prevalidation은 하지 않는다. 실제 call에서 signature mismatch `TypeError` 또는 ordinary exception이 발생하면 post-attempt `AUTHORITY_EXCEPTION` INDETERMINATE로 처리한다.

### Decision model

exact decision values 3:

1. `AUTHORITY_REPORTED_CONSUMED`
2. `AUTHORITY_REPORTED_BLOCKED`
3. `INDETERMINATE`

reported decision은 adapter report evidence이며 durable backend truth가 아니다.

### Authority result schema

`KiwoomOrderAuthorizationAuthorityReportedResult`는 frozen immutable dataclass이다.

exact field order 13:

1. `authorization_claim_identity`
2. `authorization_replay_guard`
3. `claim_fingerprint`
4. `asserted_authority_approval_reference`
5. `asserted_authority_conformance_reference`
6. `authority_result_reference`
7. `decision`
8. `block_reason`
9. `indeterminate_reason`
10. `consumption_reference`
11. `authority_reported_authorization_consumption_committed`
12. `authority_reported_replay_guard_consumption_committed`
13. `commit_state_known`

`authorization_claim_identity`, `authorization_replay_guard`, `claim_fingerprint`, asserted references는 exact call input과 일치해야 한다.

### Authority result references

present `authority_result_reference`와 present `consumption_reference`는 exact opaque reference이다.

각 reference는:

- exact `str`
- length `1..128`
- non-empty
- `value == value.strip()`
- whitespace-only 금지
- U+0000..U+001F 금지
- U+007F 금지
- normalization/trim/case-fold/replacement 금지

### Block reasons

exact 10:

1. `CLAIM_ALREADY_CONSUMED`
2. `REPLAY_GUARD_ALREADY_CONSUMED`
3. `AUTHORITY_NAMESPACE_MISMATCH`
4. `EVIDENCE_SNAPSHOT_MISMATCH`
5. `SUBMISSION_ATTEMPT_MISMATCH`
6. `SEND_AUTHORIZATION_MISMATCH`
7. `GRANT_ATTEMPT_BINDING_INVALID`
8. `AUTHORIZATION_REVOKED`
9. `AUTHORIZATION_STALE`
10. `AUTHORIZATION_INVALID`

block-reason precedence는 concrete authoritative backend의 normative responsibility이며 Phase 32 local layer가 재유도하거나 독립 증명하지 않는다.

### Indeterminate reasons

exact 4:

1. `AUTHORITY_TIMEOUT`
2. `AUTHORITY_EXCEPTION`
3. `AUTHORITY_REPORTED_INDETERMINATE`
4. `AUTHORITY_RESULT_CONTRACT_VIOLATION`

### AUTHORITY_REPORTED_CONSUMED result

valid consumed result는 모두 만족해야 한다.

- exact input echoes
- valid `authority_result_reference`
- valid `consumption_reference`
- `decision == "AUTHORITY_REPORTED_CONSUMED"`
- `block_reason is None`
- `indeterminate_reason is None`
- `commit_state_known is True`
- both reported commit fields are exact True

snapshot normalized state:

- `consumption_evidence_candidate_ready=True`
- `authority_trust_independently_verified=False`
- `automatic_retry_permitted=False`
- `reconciliation_required=False`
- `authority_invocation_attempted=True`
- Phase32 direct safety flags=False

candidate-ready는 transport/post/send permission이 아니다.

### AUTHORITY_REPORTED_BLOCKED result

valid blocked result는 모두 만족해야 한다.

- exact input echoes
- valid `authority_result_reference`
- allowed block reason
- `decision == "AUTHORITY_REPORTED_BLOCKED"`
- `indeterminate_reason is None`
- `consumption_reference is None`
- `commit_state_known is True`
- both reported commit fields are exact False

snapshot normalized state:

- `consumption_evidence_candidate_ready=False`
- `authority_trust_independently_verified=False`
- `automatic_retry_permitted=False`
- `reconciliation_required=False`
- `authority_invocation_attempted=True`
- Phase32 direct safety flags=False

### Explicit authority-reported INDETERMINATE result

valid explicit INDETERMINATE result는 모두 만족해야 한다.

- exact input echoes
- valid `authority_result_reference`
- `decision == "INDETERMINATE"`
- `block_reason is None`
- `indeterminate_reason == "AUTHORITY_REPORTED_INDETERMINATE"`
- `consumption_reference is None`
- `commit_state_known is False`
- both reported commit fields are None

snapshot normalized state:

- `consumption_evidence_candidate_ready=False`
- `authority_trust_independently_verified=False`
- `automatic_retry_permitted=False`
- `reconciliation_required=True`
- `authority_invocation_attempted=True`
- Phase32 direct safety flags=False

### Post-attempt normalized INDETERMINATE

다음은 모두 fail-closed normalized INDETERMINATE 대상이다.

- `TimeoutError`
- ordinary `Exception`
- wrong returned exact type
- echo mismatch
- malformed reference
- unsupported decision/reason
- partial commit
- impossible state combination
- invalid exact type
- invalid deferred/awaitable/Future/Task return

`TimeoutError`는 `AUTHORITY_TIMEOUT`을 사용한다.

ordinary `Exception`은 `AUTHORITY_EXCEPTION`을 사용한다.

invalid/malformed returned result는 `AUTHORITY_RESULT_CONTRACT_VIOLATION`을 사용한다.

normalized state:

- `authority_result is None`
- `decision == "INDETERMINATE"`
- `block_reason is None`
- applicable exact indeterminate reason
- `authority_result_reference is None`
- `consumption_reference is None`
- reported commit fields=None/None
- `commit_state_known=False`
- `consumption_evidence_candidate_ready=False`
- `authority_trust_independently_verified=False`
- `automatic_retry_permitted=False`
- `reconciliation_required=True`
- `authority_invocation_attempted=True`
- Phase32 direct safety flags=False

### BaseException boundary

다음은 ordinary authority exception으로 normalize하지 않는다.

- `asyncio.CancelledError`
- `KeyboardInterrupt`
- `SystemExit`

필요한 local cleanup 이후 재전파하며 automatic retry하지 않는다.

### Adapter lifecycle ownership

conforming authority adapter가 자신의 async/background lifecycle을 전적으로 소유한다.

Conforming adapter는:

- 자신의 async/background work lifecycle을 소유한다.
- 필요한 strong reference를 자체 보존한다.
- 자신의 coroutine/generator/Task/Future cleanup 책임을 Phase 32에 이전하지 않는다.
- authority outcome을 adapter contract에 따라 settle한 뒤 Phase 32에 exact synchronous result dataclass를 반환한다.

Phase 32가 adapter 내부 async implementation 자체를 금지하는 것은 아니다. 다만 Phase 32로 deferred object를 넘기는 것은 adapter-contract violation이다.

### Invalid deferred returned objects

최소 다음은 모두 wrong exact result type이며 adapter-contract violation이다.

- bare coroutine object
- generator object
- async-generator object
- custom awaitable
- generator-based coroutine object
- `asyncio.Future`
- `asyncio.Task`
- Future-like / Task-like object
- exact result dataclass가 아닌 기타 object

runtime implementation은 위 종류별 semantic probing을 할 필요가 없다.

우선:

`type(result) is KiwoomOrderAuthorizationAuthorityReportedResult`

를 검사하고 False이면 `AUTHORITY_RESULT_CONTRACT_VIOLATION`으로 fail closed한다.

### Invalid deferred object non-operations

Phase 32는 invalid returned object에 대해 다음을 수행하지 않는다.

- `await`
- schedule / `create_task` / `ensure_future`
- synchronous iteration
- `next`
- `send`
- `throw`
- async iteration
- `anext`
- direct `__await__`
- `cancel`
- coroutine `close`
- generator `close`
- async-generator `aclose`
- Future/Task `result`
- Future/Task `exception`
- Future/Task `add_done_callback`
- completion까지 strong-reference retention
- semantic probing through execution
- second authority invocation
- automatic retry

이 non-interference rule은 unknown authority outcome을 Phase 32가 임의로 변경하지 않기 위한 것이다.

### Transient raw reference rule

invalid returned object는 exact result-type validation과 normalized state construction에 필요한 temporary local reference로만 취급한다.

invalid raw object는:

- snapshot에 저장하지 않는다.
- fingerprint에 포함하지 않는다.
- cache하지 않는다.
- module/global collection에 보존하지 않는다.
- completion까지 retain하지 않는다.

Phase 32 return 이후 invalid object lifetime을 보장하지 않는다.

### Bare coroutine warning boundary

bare coroutine을 await/schedule하지 않으면 Python runtime이 `coroutine was never awaited` RuntimeWarning을 발생시킬 수 있다.

Phase 32는 이 warning을:

- suppress하지 않는다.
- success evidence로 해석하지 않는다.
- reported consumption evidence로 해석하지 않는다.
- provider permission으로 해석하지 않는다.
- INDETERMINATE를 해제하는 근거로 사용하지 않는다.

Phase 32 implementation은 `warnings.filterwarnings`, `warnings.simplefilter` 등 global/process warning configuration을 변경하지 않는다.

### Generator / async-generator / custom-awaitable boundary

returned generator는 iterate/next/send/throw/close하지 않는다.

returned async-generator는 async iterate/anext/asend/athrow/aclose하지 않는다.

custom awaitable은 `__await__()`를 호출하거나 await하지 않는다.

해당 object의 lifecycle은 violating adapter/authority 책임이다.

### Future / Task boundary

returned Future 또는 Task는 pending 또는 done일 수 있고 Task는 이미 scheduled되어 있을 수 있다.

Phase 32는 Future/Task를:

- await하지 않는다.
- cancel하지 않는다.
- `result()` 호출하지 않는다.
- `exception()` 호출하지 않는다.
- done callback을 설치하지 않는다.
- completion까지 strong reference로 retain하지 않는다.

background Task는 Phase 32 builder return 이후에도 계속 실행될 수 있다.

event loop가 Task lifecycle을 strong-own한다고 가정하지 않는다. reliable background Task가 필요한 adapter는 필요한 strong-reference ownership을 자체적으로 가져야 한다.

Future/Task exception이 회수되지 않아 runtime/asyncio diagnostic이 발생할 수 있으며 Phase 32는 이를 suppress하거나 success/BLOCKED/CONSUMED evidence로 재분류하지 않는다.

### No retroactive mutation

background Task/Future가 Phase 32 return 이후 성공, 실패, cancellation 또는 garbage collection되더라도 이미 생성된 immutable Phase 32 snapshot을 변경하지 않는다.

후속 authoritative reconciliation은 별도 boundary의 책임이다.

### Direct safety flags

Phase 32 direct safety fields는 Phase 32 module 자체의 direct action만 의미한다.

다음 False 값은 adapter 내부 또는 adapter-created background activity의 부재를 독립 증명하지 않는다.

- `phase32_direct_credential_accessed`
- `phase32_direct_network_performed`
- `phase32_direct_account_accessed`
- `phase32_direct_order_submitted`

### Evidence snapshot

`WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot`은 frozen immutable dataclass이다.

exact field order 22:

1. `source_snapshot`
2. `asserted_authority_approval_reference`
3. `asserted_authority_conformance_reference`
4. `authority_result`
5. `decision`
6. `block_reason`
7. `indeterminate_reason`
8. `authority_result_reference`
9. `consumption_reference`
10. `evidence_fingerprint`
11. `authority_reported_authorization_consumption_committed`
12. `authority_reported_replay_guard_consumption_committed`
13. `commit_state_known`
14. `consumption_evidence_candidate_ready`
15. `authority_trust_independently_verified`
16. `automatic_retry_permitted`
17. `reconciliation_required`
18. `authority_invocation_attempted`
19. `phase32_direct_credential_accessed`
20. `phase32_direct_network_performed`
21. `phase32_direct_account_accessed`
22. `phase32_direct_order_submitted`

local validation failure에서는 snapshot이 없다.

### Evidence fingerprint

fingerprint field name은 exact `evidence_fingerprint`이다.

canonical envelope exact key set / logical field order 20:

1. `claim_fingerprint`
2. `asserted_authority_approval_reference`
3. `asserted_authority_conformance_reference`
4. `decision`
5. `block_reason`
6. `indeterminate_reason`
7. `authority_result_reference`
8. `consumption_reference`
9. `authority_reported_authorization_consumption_committed`
10. `authority_reported_replay_guard_consumption_committed`
11. `commit_state_known`
12. `consumption_evidence_candidate_ready`
13. `authority_trust_independently_verified`
14. `automatic_retry_permitted`
15. `reconciliation_required`
16. `authority_invocation_attempted`
17. `phase32_direct_credential_accessed`
18. `phase32_direct_network_performed`
19. `phase32_direct_account_accessed`
20. `phase32_direct_order_submitted`

canonical JSON:

`json.dumps(`
`    envelope,`
`    sort_keys=True,`
`    separators=(",", ":"),`
`    ensure_ascii=True,`
`    allow_nan=False,`
`)`

UTF-8 encode 후:

`hashlib.sha256(canonical_bytes).hexdigest()`

를 사용한다.

`evidence_fingerprint`는 lowercase 64-hex string이다.

raw authority result object 또는 invalid deferred object 자체는 fingerprint envelope에 포함하지 않는다.

### Permission isolation

Phase 30 `transport_allowed == False`를 exact preserve한다.

Phase 32 snapshot에는 `post_permitted`, `transport_allowed`, `send_permitted`, `provider_send_eligible` 같은 permission-grant field를 추가하지 않는다.

`consumption_evidence_candidate_ready=True`는 non-authoritative evidence candidate이며 provider/send/transport permission이 아니다.

`authority_trust_independently_verified`는 Phase 32에서 항상 False이다.

### Reported versus durable truth

`authority_reported_authorization_consumption_committed`와 `authority_reported_replay_guard_consumption_committed`는 adapter-reported fields이다.

두 값이 True라도:

- concrete backend identity
- durable atomic commit
- persistent ledger write
- authoritative current validity
- provider-send eligibility

를 Phase 32가 독립 증명하지 않는다.

### Forbidden side effects

Phase 32 module 자체에서 다음을 금지한다.

- provider REST/WebSocket call
- OAuth/token access
- `.env`/credential access
- account access
- actual network
- actual `kt10000` POST
- order submission
- response parsing
- order-number handling
- durable ledger/storage mutation
- upstream object mutation
- file I/O
- wall-clock/time dependency
- UUID generation
- randomness
- retry/backoff/retransmission
- dependency mutation
- Git mutation

authority adapter invocation 자체는 이 module boundary의 유일한 external operation이며 exact once-attempt contract를 따른다. adapter 내부 side-effect 부재를 Phase 32 direct flags가 독립 증명하지 않는다.

### Dependencies and export boundary

Phase 32 implementation은 Python standard library `inspect`, `types`, `json`, `hashlib`, `dataclasses`, `typing` 등 필요한 stdlib만 사용한다.

new third-party dependency는 추가하지 않는다.

다음은 변경하지 않는다.

- `src/kiwoom_trading_system/brokers/kiwoom/rest/__init__.py`
- `pyproject.toml`
- `uv.lock`

### Runtime targeted test manifest

Phase 32 future implementation targeted test total은 exact `190`개이다.

`EXPECTED_PRE_IMPLEMENTATION_FULL_REGRESSION=878`
`EXPECTED_NEW_TEST_DELTA=190`
`EXPECTED_POST_IMPLEMENTATION_FULL_REGRESSION=1068`

exact test names:
1. `test_public_api_exact_five_symbols`
2. `test_error_is_runtime_error`
3. `test_authority_adapter_protocol_is_typing_only_not_trust_proof`
4. `test_authority_result_exact_thirteen_fields_and_frozen`
5. `test_snapshot_exact_twenty_two_fields_and_frozen`
6. `test_builder_exact_signature_and_return_type`
7. `test_builder_is_synchronous`
8. `test_no_package_reexport`
9. `test_rejects_nonexact_phase31_snapshot_type`
10. `test_preserves_phase31_snapshot_identity`
11. `test_requires_phase31_claim_prepared_true`
12. `test_requires_phase31_authorization_consumption_committed_false`
13. `test_requires_phase31_post_permitted_false`
14. `test_requires_phase31_automatic_retry_permitted_false`
15. `test_requires_phase31_network_performed_false`
16. `test_requires_phase31_order_submitted_false`
17. `test_recomputes_and_requires_exact_phase31_claim_fingerprint`
18. `test_requires_phase31_claim_identity_exact_four_tuple`
19. `test_requires_phase31_replay_guard_exact_two_tuple`
20. `test_revalidates_phase30_request_materialization_and_reference_bindings`
21. `test_requires_phase30_transport_allowed_false_without_override`
22. `test_does_not_mutate_phase29_phase30_or_phase31_upstream_objects`
23. `test_accepts_valid_asserted_authority_approval_reference`
24. `test_rejects_invalid_asserted_authority_approval_reference_variants`
25. `test_accepts_valid_asserted_authority_conformance_reference`
26. `test_rejects_invalid_asserted_authority_conformance_reference_variants`
27. `test_passive_surface_accepts_class_defined_synchronous_python_instance_method`
28. `test_passive_surface_accepts_inherited_synchronous_python_instance_method`
29. `test_passive_surface_rejects_missing_surface`
30. `test_passive_surface_rejects_nonfunction_class_attribute`
31. `test_passive_surface_rejects_staticmethod`
32. `test_passive_surface_rejects_classmethod`
33. `test_passive_surface_rejects_property_without_executing_getter`
34. `test_passive_surface_rejects_custom_descriptor_without_executing_get`
35. `test_passive_surface_rejects_dynamic_getattr_without_executing_it`
36. `test_passive_surface_does_not_execute_custom_getattribute`
37. `test_passive_surface_rejects_instance_level_shadow`
38. `test_passive_surface_rejects_callable_object_surface`
39. `test_passive_surface_does_not_use_getattr_hasattr_or_callable`
40. `test_passive_surface_validation_is_not_authority_trust_proof`
41. `test_passive_surface_rejects_native_coroutine_function`
42. `test_passive_surface_rejects_native_generator_function`
43. `test_passive_surface_rejects_native_async_generator_function`
44. `test_passive_surface_rejects_markcoroutinefunction_sync_function`
45. `test_passive_surface_rejects_types_coroutine_generator_function`
46. `test_function_kind_rejection_executes_no_authority_body`
47. `test_function_kind_rejection_uses_surface_invalid_reason`
48. `test_function_kind_rejection_attempts_authority_zero_times`
49. `test_function_kind_rejection_returns_no_snapshot_fingerprint_or_partial_result`
50. `test_function_kind_rejection_is_not_normalized_to_indeterminate`
51. `test_ordinary_sync_decorator_wrapping_sync_target_is_accepted`
52. `test_decorated_final_coroutine_function_is_rejected_locally`
53. `test_unmarked_sync_wrapper_around_async_target_passes_local_surface_classification`
54. `test_unmarked_sync_wrapper_returning_generator_passes_local_surface_classification`
55. `test_unmarked_sync_wrapper_returning_async_generator_passes_local_surface_classification`
56. `test_unmarked_sync_wrapper_returning_generic_awaitable_passes_local_surface_classification`
57. `test_validated_function_is_bound_with_types_methodtype`
58. `test_invocation_binding_does_not_use_dynamic_attribute_resolution`
59. `test_custom_getattribute_not_executed_during_invocation_binding`
60. `test_dynamic_getattr_not_executed_during_invocation_binding`
61. `test_valid_local_gate_invokes_exact_validated_function_once`
62. `test_does_not_prefetch_second_check_or_retry_authority`
63. `test_passes_exact_claim_replay_and_claim_fingerprint`
64. `test_passes_exact_asserted_authority_references`
65. `test_sync_wrapper_returning_coroutine_becomes_contract_violation_indeterminate`
66. `test_returned_coroutine_is_not_awaited_or_driven_by_phase32`
67. `test_sync_wrapper_returning_generator_becomes_contract_violation_indeterminate`
68. `test_returned_generator_is_not_iterated_or_driven_by_phase32`
69. `test_sync_wrapper_returning_async_generator_becomes_contract_violation_indeterminate`
70. `test_returned_async_generator_is_not_iterated_or_driven_by_phase32`
71. `test_sync_wrapper_returning_generic_awaitable_becomes_contract_violation_indeterminate`
72. `test_returned_generic_awaitable_dunder_await_is_not_called_by_phase32`
73. `test_invalid_deferred_return_is_not_closed_awaited_iterated_or_driven_by_phase32`
74. `test_invalid_deferred_return_sets_authority_invocation_attempted_true`
75. `test_invalid_deferred_return_sets_authority_result_none`
76. `test_invalid_deferred_return_sets_result_and_consumption_references_none`
77. `test_invalid_deferred_return_sets_commit_state_unknown_and_reconciliation_required`
78. `test_invalid_deferred_return_never_sets_consumption_evidence_candidate_ready`
79. `test_invalid_deferred_return_never_grants_transport_or_provider_permission`
80. `test_invalid_deferred_return_is_never_retried`
81. `test_signature_mismatch_at_call_becomes_authority_exception_indeterminate`
82. `test_actual_call_runtime_error_becomes_authority_exception_indeterminate`
83. `test_actual_call_timeout_becomes_authority_timeout_indeterminate`
84. `test_actual_call_cancelled_error_is_reraised`
85. `test_actual_call_keyboard_interrupt_is_reraised`
86. `test_actual_call_system_exit_is_reraised`
87. `test_authority_invocation_attempted_is_true_when_call_expression_starts`
88. `test_authority_invocation_attempted_is_true_for_every_returned_snapshot`
89. `test_authority_reported_consumed_requires_exact_echo_bindings`
90. `test_authority_reported_consumed_requires_valid_authority_result_reference`
91. `test_malformed_consumed_authority_result_reference_becomes_contract_violation_indeterminate`
92. `test_authority_reported_consumed_requires_no_block_or_indeterminate_reason`
93. `test_authority_reported_consumed_accepts_valid_consumption_reference`
94. `test_blank_consumption_reference_becomes_contract_violation_indeterminate`
95. `test_whitespace_consumption_reference_becomes_contract_violation_indeterminate`
96. `test_control_character_consumption_reference_becomes_contract_violation_indeterminate`
97. `test_overlength_consumption_reference_becomes_contract_violation_indeterminate`
98. `test_authority_reported_consumed_requires_commit_state_known_exact_true`
99. `test_authority_reported_consumed_requires_both_reported_commit_flags_exact_true`
100. `test_authority_reported_consumed_sets_candidate_ready_true_without_permission`
101. `test_authority_reported_consumed_snapshot_matches_exact_state_matrix`
102. `test_authority_reported_blocked_requires_exact_echo_bindings`
103. `test_authority_reported_blocked_requires_valid_authority_result_reference`
104. `test_malformed_blocked_authority_result_reference_becomes_contract_violation_indeterminate`
105. `test_authority_reported_blocked_requires_allowed_block_reason`
106. `test_unsupported_block_reason_becomes_contract_violation_indeterminate`
107. `test_authority_reported_blocked_requires_indeterminate_reason_none`
108. `test_authority_reported_blocked_requires_consumption_reference_none`
109. `test_authority_reported_blocked_requires_commit_state_known_exact_true`
110. `test_authority_reported_blocked_requires_both_reported_commit_flags_exact_false`
111. `test_authority_reported_blocked_sets_candidate_ready_false_reconciliation_false_no_retry`
112. `test_authority_reported_blocked_snapshot_matches_exact_state_matrix`
113. `test_block_reason_precedence_is_backend_normative_not_locally_rederived`
114. `test_explicit_indeterminate_requires_exact_echo_bindings`
115. `test_explicit_indeterminate_requires_valid_authority_result_reference`
116. `test_malformed_explicit_indeterminate_authority_result_reference_becomes_contract_violation_indeterminate`
117. `test_explicit_indeterminate_requires_block_reason_none`
118. `test_explicit_indeterminate_requires_reason_authority_reported_indeterminate`
119. `test_explicit_indeterminate_requires_consumption_reference_none`
120. `test_explicit_indeterminate_requires_commit_state_known_exact_false`
121. `test_explicit_indeterminate_requires_both_reported_commit_flags_none`
122. `test_explicit_indeterminate_sets_candidate_false_reconciliation_true_no_retry`
123. `test_explicit_indeterminate_preserves_valid_authority_result`
124. `test_explicit_indeterminate_snapshot_matches_exact_state_matrix`
125. `test_wrong_authority_result_type_becomes_contract_violation_indeterminate`
126. `test_echo_mismatch_becomes_contract_violation_indeterminate`
127. `test_partial_true_false_commit_becomes_contract_violation_indeterminate`
128. `test_partial_false_true_commit_becomes_contract_violation_indeterminate`
129. `test_impossible_commit_state_combination_becomes_contract_violation_indeterminate`
130. `test_authority_result_reported_commit_fields_reject_int_zero_and_one`
131. `test_authority_result_commit_state_known_rejects_int_zero_and_one`
132. `test_snapshot_boolean_fields_reject_int_zero_and_one`
133. `test_exact_string_fields_reject_string_subclasses`
134. `test_identity_tuple_fields_reject_nonexact_tuple_shapes`
135. `test_local_validation_failure_raises_phase32_error`
136. `test_local_validation_failure_returns_no_snapshot_fingerprint_or_partial_result`
137. `test_local_validation_failure_is_not_normalized_to_indeterminate`
138. `test_local_validation_failure_attempts_authority_zero_times`
139. `test_local_validation_failure_raises_exact_allowed_reason`
140. `test_multiple_local_errors_obey_exact_first_error_precedence`
141. `test_local_validation_order_source_type_precedes_source_contract`
142. `test_local_validation_order_phase30_binding_precedes_claim_fingerprint`
143. `test_local_validation_order_asserted_references_precedes_surface_validation`
144. `test_evidence_fingerprint_envelope_has_exact_twenty_fields`
145. `test_evidence_fingerprint_repeat_stable_and_lowercase_sha256`
146. `test_evidence_fingerprint_changes_with_authority_result_reference`
147. `test_evidence_fingerprint_changes_with_consumption_reference`
148. `test_evidence_fingerprint_changes_with_reported_commit_state`
149. `test_evidence_fingerprint_changes_with_candidate_reconciliation_and_direct_safety_flags`
150. `test_evidence_fingerprint_changes_with_authority_invocation_attempted`
151. `test_snapshot_exposes_no_post_permitted_transport_allowed_or_send_permission_field`
152. `test_consumption_evidence_candidate_ready_never_grants_transport`
153. `test_authority_trust_independently_verified_is_always_false`
154. `test_phase32_direct_safety_flags_are_always_false`
155. `test_does_not_access_credentials_account_network_provider_or_order`
156. `test_does_not_use_file_io_wall_clock_uuid_randomness_retry_or_backoff`
157. `test_does_not_mutate_dependencies_git_or_upstream_contracts`
158. `test_bare_coroutine_invalid_return_is_adapter_contract_violation`
159. `test_bare_coroutine_invalid_return_may_emit_never_awaited_runtimewarning`
160. `test_phase32_does_not_await_returned_bare_coroutine`
161. `test_phase32_does_not_cancel_returned_bare_coroutine`
162. `test_phase32_does_not_close_returned_bare_coroutine`
163. `test_phase32_does_not_suppress_never_awaited_runtimewarning`
164. `test_phase32_does_not_mutate_global_warning_filters`
165. `test_returned_generator_is_not_closed_by_phase32`
166. `test_returned_async_generator_is_not_aclose_by_phase32`
167. `test_returned_custom_awaitable_is_not_closed_cancelled_or_driven_by_phase32`
168. `test_returned_future_is_not_awaited_cancelled_or_result_retrieved_by_phase32`
169. `test_returned_task_is_not_awaited_cancelled_or_result_retrieved_by_phase32`
170. `test_returned_task_may_already_be_scheduled_before_result_validation`
171. `test_scheduled_task_background_activity_may_continue_after_builder_returns`
172. `test_scheduled_task_background_activity_is_not_interpreted_as_success`
173. `test_scheduled_task_does_not_create_candidate_ready_or_permission`
174. `test_returned_future_and_task_remain_reconciliation_required`
175. `test_phase32_does_not_retain_invalid_task_or_future_to_completion`
176. `test_phase32_does_not_install_done_callback_on_invalid_task_or_future`
177. `test_invalid_deferred_object_lifecycle_remains_adapter_authority_responsibility`
178. `test_conforming_adapter_must_return_exact_synchronous_result_dataclass`
179. `test_conforming_adapter_must_own_and_settle_async_background_work_before_return`
180. `test_invalid_deferred_object_is_not_stored_in_snapshot`
181. `test_invalid_deferred_object_is_only_transiently_referenced_for_result_validation`
182. `test_invalid_deferred_return_never_triggers_second_authority_attempt`
183. `test_invalid_deferred_return_never_triggers_automatic_retry`
184. `test_task_exception_never_retrieved_diagnostic_is_not_suppressed_or_reclassified`
185. `test_future_exception_never_retrieved_diagnostic_is_not_suppressed_or_reclassified`
186. `test_background_task_completion_after_builder_return_does_not_retroactively_change_snapshot`
187. `test_background_task_failure_after_builder_return_does_not_retroactively_change_snapshot`
188. `test_direct_safety_flags_do_not_claim_adapter_background_work_absent`
189. `test_already_done_future_with_result_is_still_wrong_exact_type_contract_violation`
190. `test_phase32_does_not_call_future_result_exception_or_add_done_callback`

`TARGETED_TEST_COUNT=190`
`TARGETED_TEST_UNIQUE_COUNT=190`
`TARGETED_TEST_DUPLICATE_COUNT=0`

### Future implementation allowed paths

Phase 32 future implementation mutation allowlist 후보는 exact 다음 2개 경로로 제한한다.

- `src/kiwoom_trading_system/brokers/kiwoom/rest/watchlist_order_authorization_adapter_evidence.py`
- `tests/test_watchlist_order_authorization_adapter_evidence.py`

README registration approval만으로 위 source/test 경로 생성 또는 수정은 승인되지 않는다.

`README.md`, `src/kiwoom_trading_system/brokers/kiwoom/rest/__init__.py`, 기존 Phase29/Phase30/Phase31/upstream source/test, `pyproject.toml`, `uv.lock`, `.venv`, `.env`, credential 관련 파일, Git index/commit/remote 및 Current Phase는 implementation allowlist에 포함하지 않는다.

### README registration boundary

이 official contract candidate의 actual README registration 단계에서 허용 가능한 project write path 후보는 exact `README.md` 1개뿐이다.

actual registration 전까지:

- README mutation 금지
- source/test mutation 금지
- dependency mutation 금지
- credential/token/account/network/provider/order 접근 금지
- Git add/commit/push 금지
- Current Phase 변경 금지
- Phase 32 implementation 금지

actual README registration은 별도 명시승인 및 Actual Rerun 검증 대상이다.

### Acceptance / Closure conditions

Phase 32는 다음 전체가 별도 승인 및 실제 검증되기 전 완료로 간주하지 않는다.

1. Final Contract Review 승인
2. README exact official contract registration 별도 승인 및 Actual 검증
3. frozen contract identity exact match
4. implementation 별도 승인
5. exact two-path implementation
6. targeted tests `190/190`
7. expected full regression `1068/1068`
8. failures=0
9. errors=0
10. 미승인 skipped=0
11. expected failures=0
12. unexpected successes=0
13. passive surface semantics exact
14. local validation failure attempt=0
15. successful local validation authority attempt exact 1
16. second invocation/retry 없음
17. invalid deferred lifecycle adapter/authority-owned
18. Phase 32 await/cancel/close/aclose/retain-to-completion 없음
19. warning suppression/global warning mutation 없음
20. permission isolation 유지
21. authority-reported versus durable truth 분리
22. evidence fingerprint exact 20-field algorithm
23. Phase29/Phase30/Phase31 및 protected hashes 불변
24. dependency 변경 없음
25. package re-export 변경 없음
26. credential/token/account/provider/order direct action 없음
27. Git 변경 범위 승인 경로와 exact 일치
28. 별도 commit 승인 및 검증
29. 별도 Closure 승인 및 Current Phase alignment

### Concrete backend boundary

별도 concrete backend evidence 및 승인 전까지 exact 다음 상태를 유지한다.

`CONCRETE_AUTHORITY_BACKEND_PROVEN=NO`
`AUTHORITATIVE_CONSUMPTION_CAPABILITY_PROVEN=NO`
`PROVIDER_SEND_ELIGIBILITY_AUTHORIZED=NO`
`PRODUCTION_AUTHORITY_USE_AUTHORIZED=NO`

### Current Phase

Phase 32 official contract를 README에 등록하더라도 implementation, commit, Closure 및 Current Phase alignment가 별도 승인·검증되기 전까지 top-level `Current Phase`는 `PHASE31`로 유지한다.

## Phase 33 — demo Kiwoom Cash BUY-Order Concrete SQLite Authority Durable Check-and-Consume Ledger & Local Verification Evidence Snapshot 기반선 v1.0

Status: CONTRACT APPROVED FOR README REGISTRATION
Implementation: NOT YET APPROVED
Current Phase: PHASE32 UNTIL SEPARATE CLOSURE / CURRENT-PHASE ALIGNMENT
Provider Send Eligibility: NOT AUTHORIZED
Production Authority Use: NOT AUTHORIZED

Source Contract Artifact: `Phase33_New_Contract_DRAFT_A11_Independent_Revision_FINAL_REVIEW_PREPARATION_DESIGN_ONLY_NOT_APPROVED.txt`
Source Contract Bytes: `94998`
Source Contract SHA256: `16DD3E11560767B730F9B1ECD0EF623ABC34668906C7D13AA3D370F5F8338CF8`
Approved A11 Sections 1-33 CRLF Bytes: `93987`
Approved A11 Sections 1-33 CRLF SHA256: `90083F6C3F3CB926FB396F6AB0AA2C95623A4395FAE248E3E137268F774711AE`

### Approved-source body preservation rule

Sections 1 through 33 below preserve the approved DRAFT-A11 contract-body text exactly; the only representation change is canonical line-ending conversion from source LF to README CRLF.

The DRAFT-A11 front matter and DRAFT-A11 section 34 governance are not part of this official README payload. Section 34 below is the superseding official governance for README registration.

`FROZEN_CONTRACT_IDENTITY_SHA256=B628FE9DB2509DB31D8511E7A3FD296385B5B179C4902EAFEC49C973825A9C2C`

### Frozen contract identity rule

`FROZEN_CONTRACT_IDENTITY_SHA256` is the SHA-256 uppercase hex of this exact CRLF UTF-8 payload after removing exactly the marker line and its immediately following blank CRLF.

The complete payload raw SHA-256 is tracked separately from the frozen contract identity.

## 1. Official review basis

The A11 revision is based on a fresh current-request review of these official contracts:

1. Kiwoom REST API official portal:
   `https://openapi.kiwoom.com/guide/apiguide`
2. Kiwoom-Securities official REST API repository:
   `https://github.com/Kiwoom-Securities/Kiwoom-REST-API`
3. Python 3.13.15 `sqlite3` documentation:
   `https://docs.python.org/3.13/library/sqlite3.html`
4. SQLite transaction / PRAGMA / schema-table documentation:
   `https://sqlite.org/lang_transaction.html`
   `https://sqlite.org/pragma.html`
   `https://sqlite.org/schematab.html`
   `https://sqlite.org/lang_createtable.html`
5. Git status/diff documentation:
   `https://git-scm.com/docs/git-status`
   `https://git-scm.com/docs/git-diff`

Contract-relevant conclusions:

- Kiwoom demo and real environments remain distinct; Phase33 must not access credentials, tokens, accounts, provider transport, or order submission;
- Python 3.13 `Connection.autocommit=True` selects SQLite autocommit mode, and Python `Connection.commit()` / `Connection.rollback()` have no effect in that mode;
- `Connection.isolation_level` has no functional transaction-control effect when `autocommit=True`; A11 nevertheless freezes `isolation_level is None` as a redundant exact caller-visible surface invariant;
- Python `Connection.row_factory` controls the representation returned by newly created cursors and is `None` by default; A11 therefore freezes `connection.row_factory is None` so authoritative rows remain ordinary tuples;
- Python `Connection.text_factory` is invoked for SQLite TEXT values and is `str` by default; A11 freezes `connection.text_factory is str`;
- Python's process-global adapter/converter registry can transform DB-API-bound Python values and declared SQLite values; A11 therefore avoids authoritative DB-API parameter binding for persisted/lookup `str`/`int`, uses deterministic SQL BLOB/integer literal encoding, and keeps authoritative persisted-value reads converter-neutral instead of assuming `detect_types=0` or a pristine registry;
- A11 uses explicit SQL transaction control and `Connection.in_transaction` as the low-level transaction-state observation;
- `PRAGMA busy_timeout=0` is required so Phase33 does not create an SQLite busy-wait/retry window;
- SQLite WAL + synchronous FULL remains the single accepted local durability profile;
- `PRAGMA table_list` exposes ordinary-table/virtual-table, column-count, WITHOUT-ROWID, and STRICT state;
- `PRAGMA foreign_key_list` exposes REFERENCES constraints;
- `main.sqlite_schema.sql` stores normalized CREATE SQL capable of recreating the object and therefore can be frozen as an exact stored-DDL identity in addition to structural PRAGMA checks;
- an SQLite read transaction provides one read snapshot until transaction end, so the verifier must use one explicit read transaction for all authoritative verification reads;
- Git/project mutation remains outside this DRAFT preparation step.

---

## 2. Phase32 boundary and Phase33 A11 responsibility

Phase32 remains the official current boundary.

Phase32:

- accepts exact `WatchlistOrderAuthorizationConsumptionClaimSnapshot`;
- performs deterministic local validation;
- invokes one authority adapter operation at most once;
- normalizes authority-reported result evidence into exact `WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot`;
- does not prove concrete backend identity;
- does not independently prove durable local persistence;
- does not independently prove external approval/conformance provenance;
- does not authorize provider transport or production authority use.

Phase33 A11 candidate responsibility is limited to:

1. provide one concrete demo-only local SQLite authority implementation identity;
2. enforce exact caller-owned SQLite connection and exclusive-use preconditions;
3. freeze the Python DB-API result-conversion surface needed by Phase33 (`row_factory=None`, `text_factory=str`), use converter-neutral BLOB/INTEGER reads, and use deterministic SQL literal encoding with no authoritative DB-API parameter binding for persisted/lookup `str`/`int`;
4. perform authoritative persisted BLOB/INTEGER reads without relying on declared-type converters;
5. initialize and verify one exact `main` schema with frozen stored-DDL identity;
6. persist one replay-protected local consumption row under a fixed SQLite durability profile;
7. bind persistent claim identity and replay guard independently of `backend_instance_reference`;
8. derive deterministic domain-separated references and fingerprints;
9. eliminate pre-transaction schema/profile TOCTOU by authoritative in-transaction revalidation;
10. allow exact Phase32 consumed-candidate evidence to be rebound read-only to the durable row under one explicit SQLite read snapshot;
11. materialize immutable local verification evidence limited to observable identity/schema/connection-surface/durability/record bindings;
12. continue to withhold provider-send eligibility, production use, and external governance provenance.

A11 does not create or imply provider transport permission.

---

## 3. Scope

Phase33 A11 candidate exact scope:

- environment=`demo` only
- side=`BUY` only
- exchange=`KRX` only
- cash order only
- exact Phase32 `WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot` integration
- concrete backend=`sqlite3`
- exact caller-owned `sqlite3.Connection`
- caller-provided exclusive use of that connection for each Phase33 API invocation
- explicit connection surface precondition including `row_factory is None` and `text_factory is str`
- converter-neutral authoritative persisted BLOB/INTEGER reads
- deterministic UTF-8 BLOB / signed-64 integer SQL literal encoding with no authoritative DB-API placeholder binding
- caller/process stability contract prohibiting adapter/converter registry or connection conversion-surface mutation during an invocation
- explicit schema initialization
- exact `main` structural introspection
- exact frozen stored-DDL identity
- file-backed `main` database only
- exact declared authority transaction protocol
- exact local durability profile
- exact atomic check-and-consume algorithm
- authoritative schema/profile revalidation after successful `BEGIN IMMEDIATE`
- persistent claim identity uniqueness
- persistent replay-guard uniqueness
- deterministic authority-result reference
- deterministic consumption reference
- deterministic durable-record fingerprint
- read-only local durable-row verification under one explicit read transaction
- immutable Phase33 verification snapshot
- no provider REST/WebSocket call
- no credential/token/account access
- no `kt10000` POST
- no order submission
- no order-response parsing
- no order-number handling
- no provider-send permission
- no production-authority enablement
- no automatic retry
- no second consumption attempt
- no hidden thread/task/lock manager
- no third-party dependency
- no package-level re-export

Out of scope:

- real environment
- SELL
- NXT/SOR
- credit
- amend/cancel
- provider transport
- provider response
- provider order number
- external approval-governance proof
- cryptographic signing or tamper-proof storage
- remote database
- distributed consensus
- cross-database global uniqueness
- cross-process lease service
- automatic recovery/retry
- schema migration
- package-level re-export
- physical-storage durability proof beyond the declared SQLite contract profile
- concurrent use of the same caller-owned connection during a Phase33 invocation
- mutation of Python's global sqlite3 adapter/converter registries by Phase33

---

## 4. Safety invariants

`PHASE32_CONSUMPTION_EVIDENCE_CANDIDATE_READY != LOCAL_DURABLE_CONSUMPTION_RECORD_VERIFIED`

`LOCAL_DURABLE_CONSUMPTION_RECORD_VERIFIED != PROVIDER_SEND_ELIGIBILITY`

`CONCRETE_SQLITE_AUTHORITY_IDENTITY_VERIFIED != EXTERNAL_AUTHORITY_TRUST_VERIFIED`

`CONFIGURED_APPROVAL_REFERENCE != INDEPENDENT_APPROVAL_PROVENANCE`

`CONFIGURED_CONFORMANCE_REFERENCE != INDEPENDENT_CONFORMANCE_PROVENANCE`

`SQLITE_WAL_FULL_PROFILE_VERIFIED != CRYPTOGRAPHIC_TAMPER_PROOF`

`SQLITE_CONNECTION_SURFACE_VERIFIED != DECLARED_TRANSACTION_PROTOCOL_EXECUTION_PROVEN`

`DECLARED_TRANSACTION_PROFILE_ID_BOUND != HISTORICAL_TRANSACTION_EXECUTION_PROVEN`

`SINGLE_READ_SNAPSHOT_VERIFIED != HISTORICAL_WRITE_TRANSACTION_PROVEN`

`PROVIDER_SEND_ELIGIBILITY_AUTHORIZED == False`

`PRODUCTION_AUTHORITY_USE_AUTHORIZED == False`

`AUTOMATIC_RETRY == PROHIBITED`

`SECOND_AUTHORITY_CONSUMPTION_ATTEMPT == PROHIBITED`

`SQLITE_TRANSACTION_ROLLBACK != PROJECT_OR_GIT_ROLLBACK`

SQLite rollback is local database transaction cleanup only.

---

## 5. Candidate module-level public API

Candidate public API remains exact 7 symbols:

1. `WatchlistOrderAuthorizationDurableAuthorityError`
2. `KiwoomOrderAuthorizationDurableAuthorityConfig`
3. `KiwoomOrderAuthorizationDurableLedgerRecord`
4. `KiwoomOrderAuthorizationSQLiteAuthority`
5. `WatchlistOrderAuthorizationDurableVerificationSnapshot`
6. `initialize_demo_watchlist_order_authorization_durable_ledger`
7. `verify_demo_watchlist_order_authorization_durable_consumption`

`WatchlistOrderAuthorizationDurableAuthorityError` inherits `RuntimeError`.

No package-level re-export from `src/kiwoom_trading_system/brokers/kiwoom/rest/__init__.py`.

---

## 6. Future implementation paths

Candidate future implementation mutation allowlist remains exact 2 paths:

- `src/kiwoom_trading_system/brokers/kiwoom/rest/watchlist_order_authorization_durable_authority.py`
- `tests/test_watchlist_order_authorization_durable_authority.py`

Not included:

- `README.md`
- `src/kiwoom_trading_system/brokers/kiwoom/rest/__init__.py`
- any Phase29/30/31/32 source/test path
- `pyproject.toml`
- `uv.lock`
- `.venv`
- `.env`
- credential files
- Git index/commit/remote

DRAFT-A11 preparation does not authorize either future path to be created or modified in the project.

---

## 7. Durable authority config

`KiwoomOrderAuthorizationDurableAuthorityConfig` remains a frozen dataclass with exact field order 4:

1. `backend_instance_reference: str`
2. `authorization_authority_reference: str`
3. `authority_approval_reference: str`
4. `authority_conformance_reference: str`

Each reference:

- exact `str`
- length `1..128`
- non-empty
- `value == value.strip()`
- whitespace-only prohibited
- U+0000..U+001F prohibited
- U+007F prohibited
- no trim
- no case-fold
- no Unicode normalization
- no replacement

These are configured local bindings only.
They are not independent external approval or conformance proof.

---

## 8. Caller-owned SQLite connection and adapter/callback-independent SQL-value contract

`KiwoomOrderAuthorizationSQLiteAuthority` candidate constructor:

`KiwoomOrderAuthorizationSQLiteAuthority(`
`    connection: sqlite3.Connection,`
`    config: KiwoomOrderAuthorizationDurableAuthorityConfig,`
`)`

Exact preconditions:

1. `type(connection) is sqlite3.Connection`
2. caller owns connection lifecycle
3. Phase33 never closes the connection
4. connection must be open
5. `connection.in_transaction is False` before initializer, `check_and_consume`, or verifier transaction start
6. `connection.autocommit is True`
7. `connection.isolation_level is None`
8. `connection.row_factory is None`
9. `connection.text_factory is str`
10. `PRAGMA busy_timeout` result is exact integer `0`
11. no Python `Connection` context manager is used by Phase33
12. no `executescript()` is used by Phase33
13. transaction boundaries use explicit SQL only
14. `PRAGMA database_list` must show a non-empty file path for schema `main`
15. in-memory `main` databases are rejected
16. attached databases may exist but are never used as Phase33 storage
17. every Phase33 storage table/index/metadata SQL reference is explicitly `main.` qualified
18. no unqualified Phase33 storage table name is permitted
19. TEMP or attached objects with the same base names must not redirect Phase33 storage away from `main`
20. no hidden database open/path derivation/default path
21. no automatic connection-setting mutation
22. caller provides exclusive use of the same connection for the full Phase33 invocation
23. the same connection must not be concurrently used by another thread, task, callback, signal handler, or reentrant application path
24. caller must not mutate `connection.row_factory` or `connection.text_factory` during the invocation
25. Phase33 creates no background thread/task and no hidden lock manager
26. Phase33 does not register, remove, replace, restore, or otherwise mutate global sqlite3 adapters/converters or connection-local SQL callbacks/collations/authorizers

`connection.isolation_level is None` remains a redundant exact surface invariant while `autocommit=True`.

`row_factory=None` and `text_factory=str` remain exact observable surface invariants. A pre-transaction mismatch routes to `AUTHORITY_CONNECTION_TRANSACTION_MODE_INVALID`; no twelfth local reason is created.

### 8.1 Exact deterministic SQL literal encoding — no DB-API authoritative parameter binding

A11 removes A8's separate effective-binding probe model entirely.

Phase33 authoritative storage/schema lookup or mutation SQL MUST NOT bind Phase33 authority-critical `str` or `int` values through DB-API placeholders. Therefore registered Python adapters cannot transform the value between a probe and a later authoritative use because there is no such later parameter adaptation.

For every exact Python `str` used as persisted or lookup data:

1. require `type(value) is str`;
2. require the field-specific Phase33 validation rules first;
3. require `value.encode("utf-8", "strict")` to succeed;
4. let `raw = value.encode("utf-8", "strict")`;
5. let `hex_upper = raw.hex().upper()`;
6. the exact SQL value expression is `X'<HEX_UPPER>'`;
7. `<HEX_UPPER>` contains only `0-9A-F`, therefore no user-controlled quote/token can enter SQL syntax;
8. the resulting SQLite storage value is BLOB and exact byte equality is the authoritative persisted/lookup identity.

No `CAST(... AS TEXT)`, SQL collation, user-defined function, or Python adapter is used to construct an authority-critical bound value.

For every exact Python `int` used as persisted data:

1. require `type(value) is int` and not bool;
2. require signed 64-bit range `-9223372036854775808 <= value <= 9223372036854775807`;
3. canonical SQL decimal literal is Python `str(value)` with no leading plus and no redundant leading zero;
4. only ASCII `-0123456789` can occur;
5. the integer literal is embedded directly in the Phase33 SQL statement and is never passed through DB-API parameter adaptation.

Phase33 therefore performs **zero DB-API parameter binding for authority-critical Phase33 persisted/lookup values**.

Static table/schema identifiers are hard-coded constants. The only dynamically rendered PRAGMA object argument permitted is an SQLite-generated index name already obtained from verified structural metadata. The accepted exact internal autoindex-name set is frozen to:

- `sqlite_autoindex_kiwoom_order_authorization_meta_1`
- `sqlite_autoindex_kiwoom_order_authorization_consumption_1`
- `sqlite_autoindex_kiwoom_order_authorization_consumption_2`
- `sqlite_autoindex_kiwoom_order_authorization_consumption_3`
- `sqlite_autoindex_kiwoom_order_authorization_consumption_4`
- `sqlite_autoindex_kiwoom_order_authorization_consumption_5`

No other dynamic PRAGMA object name is accepted. Autoindex numeric suffixes are not treated as semantic proof of a particular UNIQUE key; semantic key-set/order/ascending/non-expression/non-partial verification continues to come from the corresponding `main.index_list` / `main.index_xinfo` rows. For `PRAGMA main.index_xinfo(...)`, the accepted name is rendered only after exact-set membership succeeds, by replacing each ASCII single quote `'` with two single quotes `''` and surrounding the resulting text with one SQL single-quoted string delimiter pair. The six accepted names contain no single quote, so their canonical rendered arguments are the same names surrounded by single quotes. No user-provided identifier is rendered into SQL.

### 8.2 Adapter/converter/callback independence

A11 does not infer `detect_types` and does not use direct declared-column conversion as authoritative data.

A11's authoritative path intentionally does not depend on:

- `sqlite3.register_adapter()` output;
- `sqlite3.register_converter()` output;
- caller-defined SQL scalar/aggregate/window functions, including a function named `typeof`;
- caller-defined text collations for authority-critical persistent identity;
- generic sentinel parameter probes.

Phase33 never calls authority-critical named SQL scalar functions such as `typeof()`, `hex()`, `length()`, or caller-defined equivalents.

Persistent identity/reference/fingerprint columns are exact BLOB columns in STRICT tables. Equality and UNIQUE enforcement for these values therefore use BLOB byte identity and do not depend on text collation behavior. A caller-defined collation named `BINARY` cannot redefine BLOB byte equality.

Connection-local authorizer/progress callbacks are not modified by Phase33. If they deny/ignore/abort an operation such that required structural/read/write invariants are not obtained exactly, the existing SQLite/read/schema failure path fails closed; Phase33 does not attempt to clear or restore those callbacks.

Global adapter/converter registry stability may still be required as ordinary process hygiene, but it is **not** evidence of adapter callable output determinism and is not part of the authoritative value proof.

### 8.3 Converter-neutral authoritative reads

Because the two Phase33 application tables are exact STRICT tables with BLOB identity/reference/fingerprint storage and INTEGER synchronous-level storage, their declared storage classes are enforced by SQLite schema semantics.

For an authoritative persisted BLOB-backed logical string:

1. select `CAST(column AS BLOB)` in an unannotated expression;
2. require exact Python `bytes`;
3. strict-decode UTF-8 using `bytes_value.decode("utf-8", "strict")`;
4. use only the decoded Python string as the logical contract value;
5. direct declared-column converter output is never authoritative.

For persisted INTEGER:

1. select `CAST(column AS INTEGER)` in an unannotated expression;
2. require `type(value) is int` and not bool;
3. require the field-specific exact numeric value/range.

No authority-critical persisted-value decision uses SQL `typeof()`.

For `main.sqlite_schema`, non-null `type`, `name`, `tbl_name`, and `sql` are read using `CAST(... AS BLOB)` and strict UTF-8 decode. Contractually null `sql` values require exact SQL/Python NULL semantics. Comparisons of `main.sqlite_schema` names required by Phase33 are made with `CAST(name AS BLOB)=X'<CONSTANT_HEX>'`, not text-collation equality.

PRAGMA result sets remain accepted only with `row_factory is None` and `text_factory is str`, plus exact primitive-type checks.

---

## 9. Exact SQLite transaction profile

Exact transaction profile ID:

`sqlite-autocommit-true-isolation-none-busy-zero-begin-immediate-v1`

Required exact surface/profile state:

- `connection.autocommit is True`
- `connection.isolation_level is None`
- `PRAGMA busy_timeout` result=`0`
- `connection.in_transaction is False` before transaction start
- transaction start SQL exact semantic operation=`BEGIN IMMEDIATE`
- transaction success finish SQL exact semantic operation=`COMMIT`
- failure cleanup SQL exact semantic operation=`ROLLBACK`
- no `Connection.commit()`
- no `Connection.rollback()`
- no `with connection:`
- no `executescript()`
- no nested transaction
- no SAVEPOINT
- no second transaction for retry
- no SQLite busy-wait/retry window; lock contention is a single failure path

`isolation_level=None` is a frozen surface invariant, not an independent transaction-control mechanism while `autocommit=True`.

After successful `BEGIN IMMEDIATE`, `connection.in_transaction` must be True.

After successful `COMMIT` or successful cleanup `ROLLBACK`, `connection.in_transaction` must be False.

---

## 10. Exact SQLite durability profile

Candidate durability profile reference:

`sqlite-main-wal-synchronous-full-v1`

Exact accepted profile:

- `PRAGMA main.journal_mode` result=`wal`
- `PRAGMA main.synchronous` result=`2` (`FULL`)

No alternate durability profile is accepted in A11.

Rejected:

- rollback-journal modes including `delete`, `truncate`, `persist`
- `memory`
- `off`
- synchronous=`0` / `OFF`
- synchronous=`1` / `NORMAL`
- synchronous=`3` / `EXTRA`

`EXTRA` is not rejected as unsafe; it is rejected because A11 freezes one exact profile and does not silently broaden the contract.

Phase33 does not silently change `journal_mode` or `synchronous`.
The caller must configure the connection/database before Phase33 initialization.

Durability statement is intentionally bounded:

`SQLITE_MAIN_WAL_FULL_CONTRACT_PROFILE_VERIFIED`

does not mean:

- cryptographic integrity;
- remote replication;
- distributed consensus;
- storage-device failure immunity;
- independent hardware durability attestation.

---

## 11. Explicit ledger initialization and exact schema verification

A11 adopts schema hardening: both Phase33 application tables are exact SQLite STRICT tables, and all logical string/reference/fingerprint storage columns are exact `BLOB` containing canonical UTF-8 bytes. `WITHOUT ROWID` remains prohibited.

The exact ledger schema reference remains:

`kiwoom-watchlist-order-authorization-durable-ledger-v1`

The exact schema metadata keys remain:

- `schema_id`
- `transaction_profile_id`
- `durability_profile_id`

The exact metadata values remain the existing Phase33 string constants but are persisted as canonical UTF-8 BLOB bytes.

### 11.1 Meta table exact logical schema

`main.kiwoom_order_authorization_meta`

exact columns/order:

1. `schema_key BLOB NOT NULL PRIMARY KEY`
2. `schema_value BLOB NOT NULL`

exact rows: three and only three logical keys encoded as UTF-8 BLOB:

- `schema_id`
- `transaction_profile_id`
- `durability_profile_id`

No extra metadata row is allowed.

### 11.2 Consumption table exact logical schema

`main.kiwoom_order_authorization_consumption`

exact columns/order:

1. `backend_instance_reference BLOB NOT NULL`
2. `authorization_authority_reference BLOB NOT NULL`
3. `authorization_evidence_snapshot_id BLOB NOT NULL`
4. `submission_attempt_reference BLOB NOT NULL`
5. `send_authorization_reference BLOB NOT NULL`
6. `claim_fingerprint BLOB NOT NULL`
7. `authority_approval_reference BLOB NOT NULL`
8. `authority_conformance_reference BLOB NOT NULL`
9. `authority_result_reference BLOB NOT NULL`
10. `consumption_reference BLOB NOT NULL`
11. `sqlite_journal_mode BLOB NOT NULL`
12. `sqlite_synchronous_level INTEGER NOT NULL`
13. `record_fingerprint BLOB NOT NULL`

Required exact UNIQUE key sets remain:

- claim identity: `(authorization_authority_reference, authorization_evidence_snapshot_id, submission_attempt_reference, send_authorization_reference)`
- replay guard: `(authorization_authority_reference, send_authorization_reference)`
- `authority_result_reference`
- `consumption_reference`
- `record_fingerprint`

`backend_instance_reference` remains provenance only and is excluded from persistent claim/replay uniqueness.

Because all unique identity terms are BLOB, their authority semantics are byte equality; text collations do not participate in identity or uniqueness.

### 11.3 Exact STRICT creation SQL and frozen stored-DDL identity

Exact initializer CREATE SQL:

`CREATE TABLE main.kiwoom_order_authorization_meta(schema_key BLOB NOT NULL PRIMARY KEY,schema_value BLOB NOT NULL) STRICT`

`CREATE TABLE main.kiwoom_order_authorization_consumption(backend_instance_reference BLOB NOT NULL,authorization_authority_reference BLOB NOT NULL,authorization_evidence_snapshot_id BLOB NOT NULL,submission_attempt_reference BLOB NOT NULL,send_authorization_reference BLOB NOT NULL,claim_fingerprint BLOB NOT NULL,authority_approval_reference BLOB NOT NULL,authority_conformance_reference BLOB NOT NULL,authority_result_reference BLOB NOT NULL,consumption_reference BLOB NOT NULL,sqlite_journal_mode BLOB NOT NULL,sqlite_synchronous_level INTEGER NOT NULL,record_fingerprint BLOB NOT NULL,UNIQUE(authorization_authority_reference,authorization_evidence_snapshot_id,submission_attempt_reference,send_authorization_reference),UNIQUE(authorization_authority_reference,send_authorization_reference),UNIQUE(authority_result_reference),UNIQUE(consumption_reference),UNIQUE(record_fingerprint)) STRICT`

SQLite-normalized exact stored DDL after creation:

Meta:

`CREATE TABLE kiwoom_order_authorization_meta(schema_key BLOB NOT NULL PRIMARY KEY,schema_value BLOB NOT NULL) STRICT`

- UTF-8 bytes=`116`
- SHA256=`55FDBAD5B3992B06F98D132FC881B7090E83E00E92CE20B5A05CD73B52F68AFE`

Consumption:

`CREATE TABLE kiwoom_order_authorization_consumption(backend_instance_reference BLOB NOT NULL,authorization_authority_reference BLOB NOT NULL,authorization_evidence_snapshot_id BLOB NOT NULL,submission_attempt_reference BLOB NOT NULL,send_authorization_reference BLOB NOT NULL,claim_fingerprint BLOB NOT NULL,authority_approval_reference BLOB NOT NULL,authority_conformance_reference BLOB NOT NULL,authority_result_reference BLOB NOT NULL,consumption_reference BLOB NOT NULL,sqlite_journal_mode BLOB NOT NULL,sqlite_synchronous_level INTEGER NOT NULL,record_fingerprint BLOB NOT NULL,UNIQUE(authorization_authority_reference,authorization_evidence_snapshot_id,submission_attempt_reference,send_authorization_reference),UNIQUE(authorization_authority_reference,send_authorization_reference),UNIQUE(authority_result_reference),UNIQUE(consumption_reference),UNIQUE(record_fingerprint)) STRICT`

- UTF-8 bytes=`888`
- SHA256=`52CE7F608809602658FAC025425BBBC6AB175586101898FB0AEA3C852C950FB8`

The stored strings above are compared as exact strict-UTF-8-decoded bytes from `CAST(main.sqlite_schema.sql AS BLOB)`; no direct declared TEXT conversion and no caller-overridable named SQL function is authoritative.

Any unapproved CHECK, REFERENCES, generated column, table constraint, non-STRICT form, WITHOUT ROWID, changed declared type, extra table option, or other stored-DDL difference is rejected.

### 11.4 Exact structural introspection

Required inspection remains:

- `PRAGMA main.table_list('kiwoom_order_authorization_meta')`
- `PRAGMA main.table_list('kiwoom_order_authorization_consumption')`
- `PRAGMA main.table_xinfo('kiwoom_order_authorization_meta')`
- `PRAGMA main.table_xinfo('kiwoom_order_authorization_consumption')`
- `PRAGMA main.index_list('<target>')`
- `PRAGMA main.index_xinfo('<verified-autoindex>')`
- `PRAGMA main.foreign_key_list('<target>')`
- converter-neutral reads from `main.sqlite_schema`

Exact `table_list` requirements for each target:

- schema=`main`
- type=`table`
- meta ncol=`2`; consumption ncol=`13`
- `wr=0`
- `strict=1`

Meta `table_xinfo` exact types/order:

- `schema_key`: type `BLOB`, notnull=1, pk=1, hidden=0, no default
- `schema_value`: type `BLOB`, notnull=1, pk=0, hidden=0, no default

Consumption `table_xinfo` exact types/order:

- the twelve logical string/reference/fingerprint/journal columns are exact `BLOB`
- `sqlite_synchronous_level` is exact `INTEGER`
- every column notnull=1, pk=0, hidden=0, no default

Exact index semantics remain five required UNIQUE constraints on the consumption table plus the metadata PK autoindex. No user-created (`origin='c'`) index may target either Phase33 table. Each index key must be the exact expected column set/order, ascending, non-expression, non-partial. `index_xinfo` may report collation metadata such as `BINARY`, but A11 persistent identity values are BLOB and authority semantics do not rely on a text-collation callback.

`foreign_key_list` must be empty for both tables.

No trigger may target either Phase33 table. No Phase33-namespaced view is allowed. TEMP/attached shadows do not redirect `main`-qualified access.

### 11.5 Initialization transaction

Initializer requires all section 8/9/10 connection preconditions, then uses exactly one `BEGIN IMMEDIATE` transaction to create missing exact tables and insert the exact three metadata rows using A11 deterministic BLOB SQL literals.

If tables already exist, initializer verifies exact STRICT/BLOB schema, exact frozen stored-DDL, exact metadata, and does not migrate or rewrite them.

No ALTER TABLE migration, no schema normalization, no retry, and no second transaction is permitted.

### 11.6 Initializer runtime failure lifecycle

Initializer runtime `sqlite3.Error` behavior remains fail-closed:

- inspect `connection.in_transaction`;
- if active, attempt cleanup-only explicit `ROLLBACK` exactly once;
- cleanup failure does not replace the original sqlite3.Error;
- re-raise the original sqlite3.Error;
- no retry/second initializer transaction;
- never infer successful initialization from an error path.

`KeyboardInterrupt`/`SystemExit` after transaction start receive the same at-most-one active cleanup rollback and the original BaseException is re-raised.

---

## 12. Durable ledger record

`KiwoomOrderAuthorizationDurableLedgerRecord` is a frozen dataclass with exact field order and exact annotations 13:

1. `backend_instance_reference: str`
2. `authorization_authority_reference: str`
3. `authorization_evidence_snapshot_id: str`
4. `submission_attempt_reference: str`
5. `send_authorization_reference: str`
6. `claim_fingerprint: str`
7. `authority_approval_reference: str`
8. `authority_conformance_reference: str`
9. `authority_result_reference: str`
10. `consumption_reference: str`
11. `sqlite_journal_mode: str`
12. `sqlite_synchronous_level: int`
13. `record_fingerprint: str`

No annotation may be widened to `Any`, `object`, an optional type, a union, or a subclass-specific type.

`record_fingerprint` is lowercase 64-hex SHA-256 over an exact 16-key canonical envelope:

1. `domain`
2. `schema_id`
3. `transaction_profile_id`
4. `durability_profile_id`
5. `backend_instance_reference`
6. `authorization_authority_reference`
7. `authorization_evidence_snapshot_id`
8. `submission_attempt_reference`
9. `send_authorization_reference`
10. `claim_fingerprint`
11. `authority_approval_reference`
12. `authority_conformance_reference`
13. `authority_result_reference`
14. `consumption_reference`
15. `sqlite_journal_mode`
16. `sqlite_synchronous_level`

Exact constants:

- `domain="phase33-durable-record-v1"`
- `schema_id="kiwoom-watchlist-order-authorization-durable-ledger-v1"`
- `transaction_profile_id="sqlite-autocommit-true-isolation-none-busy-zero-begin-immediate-v1"`
- `durability_profile_id="sqlite-main-wal-synchronous-full-v1"`

`record_fingerprint` itself is excluded from its source envelope.

Canonical serialization:

`json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)`

UTF-8 encode, then SHA-256 lowercase hex.

No rowid, timestamp, random value, UUID, PID, thread ID, process ID, machine name, raw connection identity, or filesystem path enters the fingerprint.

---

## 13. Concrete authority method

Exact Phase32-compatible synchronous method surface:

`check_and_consume(`
`    *,`
`    authorization_claim_identity: tuple[str, str, str, str],`
`    authorization_replay_guard: tuple[str, str],`
`    claim_fingerprint: str,`
`    asserted_authority_approval_reference: str,`
`    asserted_authority_conformance_reference: str,`
`) -> KiwoomOrderAuthorizationAuthorityReportedResult`

Exact return type remains Phase32 `KiwoomOrderAuthorizationAuthorityReportedResult`.

No coroutine, Future, Task, generator, async generator, callback, background worker, or deferred result is returned.

---

## 14. Pre-transaction validation

`check_and_consume` exact fail-fast order before `BEGIN IMMEDIATE`:

1. exact authority/config runtime types and frozen config-reference validation;
2. exact claim identity tuple and members;
3. exact replay guard tuple and members;
4. lowercase-64 claim fingerprint;
5. replay guard equals claim-derived guard;
6. configured authority reference / asserted approval / asserted conformance binding;
7. exact connection/open/file-backed-main validation;
8. `connection.in_transaction is False`;
9. exact connection surface: autocommit=True, isolation_level=None, busy_timeout=0, row_factory=None, text_factory=str;
10. every authority-critical string that can be needed before transaction is valid exact UTF-8 and can be deterministically encoded to the A11 BLOB SQL literal form; exact integers satisfy signed-64/canonical-decimal rules;
11. WAL/FULL profile;
12. exact Phase33 STRICT/BLOB structural schema, frozen stored-DDL, and exact metadata using converter-neutral reads.

No authority transaction or ledger mutation occurs until these pass.

A11 performs no preflight DB-API parameter-binding probe. The authoritative SQL itself uses the deterministic literal encoding defined in section 8, so there is no separate adapter invocation whose result must be trusted for a later statement.

---

## 15. Exact deterministic authority-result reference

Format:

`phase33-result-<64 lowercase hex>`

Exact canonical envelope key set 10:

1. `domain`
2. `schema_id`
3. `transaction_profile_id`
4. `durability_profile_id`
5. `backend_instance_reference`
6. `authorization_claim_identity`
7. `authorization_replay_guard`
8. `claim_fingerprint`
9. `authority_approval_reference`
10. `authority_conformance_reference`

Exact constants:

- `domain="phase33-authority-result-v1"`
- `schema_id="kiwoom-watchlist-order-authorization-durable-ledger-v1"`
- `transaction_profile_id="sqlite-autocommit-true-isolation-none-busy-zero-begin-immediate-v1"`
- `durability_profile_id="sqlite-main-wal-synchronous-full-v1"`

Tuple values are serialized by JSON as arrays without reordering member position.

Canonical JSON settings are identical to the durable record fingerprint.

No field may be added, removed, renamed, normalized, or substituted.

---

## 16. Exact deterministic consumption reference

Format:

`phase33-consume-<64 lowercase hex>`

Exact canonical envelope key set 11:

1. `domain`
2. `schema_id`
3. `transaction_profile_id`
4. `durability_profile_id`
5. `backend_instance_reference`
6. `authorization_claim_identity`
7. `authorization_replay_guard`
8. `claim_fingerprint`
9. `authority_approval_reference`
10. `authority_conformance_reference`
11. `authority_result_reference`

Exact constants:

- `domain="phase33-consumption-v1"`
- `schema_id="kiwoom-watchlist-order-authorization-durable-ledger-v1"`
- `transaction_profile_id="sqlite-autocommit-true-isolation-none-busy-zero-begin-immediate-v1"`
- `durability_profile_id="sqlite-main-wal-synchronous-full-v1"`

Canonical JSON settings are identical to the durable record fingerprint.

The distinct domain and inclusion of `authority_result_reference` provide exact domain separation from the authority-result reference.

No field may be added, removed, renamed, normalized, or substituted.

---

## 17. Atomic check-and-consume algorithm

After section 14 succeeds:

1. execute explicit SQL `BEGIN IMMEDIATE` exactly once;
2. require `connection.in_transaction is True`;
3. immediately re-check observable connection surface (`autocommit`, `isolation_level`, `row_factory`, `text_factory`, busy_timeout), WAL/FULL, exact STRICT/BLOB schema, exact frozen stored-DDL, and exact metadata inside that same transaction;
4. every authority-critical lookup value is rendered by the section 8 deterministic BLOB SQL literal encoder in the same SQL statement in which it is used; no DB-API parameter binding occurs;
5. claim lookup uses exact BLOB byte equality on the four claim columns;
6. replay lookup uses exact BLOB byte equality on the two replay columns;
7. authoritative persisted rows are reconstructed only from converter-neutral BLOB/INTEGER expressions;
8. no text collation or named SQL scalar function participates in claim/replay identity.

### 17.1 In-transaction authoritative revalidation failure

If the post-BEGIN connection/schema/metadata/durability revalidation fails semantically:

- do not return CONSUMED or BLOCKED;
- if active, attempt cleanup-only ROLLBACK exactly once;
- return Phase32-compatible INDETERMINATE with exact `indeterminate_reason="AUTHORITY_REPORTED_INDETERMINATE"`;
- `block_reason=None`;
- `consumption_reference=None`;
- reported commit fields=None;
- `commit_state_known=False`;
- no retry/second transaction.

SQLite read/runtime error follows section 18.

### 17.2 Existing claim row

If exact claim identity resolves a historical row:

1. normalize exact 13 fields from converter-neutral storage;
2. recompute exact 16-key record fingerprint and require equality;
3. recompute historical deterministic result/consumption references and require self-binding;
4. require historical durability/profile values;
5. require current `claim_fingerprint == historical claim_fingerprint` for exact `CLAIM_ALREADY_CONSUMED` semantics;
6. current/historical backend equality is not required;
7. current/historical approval/conformance equality is not required.

If fully self-consistent and claim fingerprint matches, explicit COMMIT then return BLOCKED `CLAIM_ALREADY_CONSUMED`.

If historical row is corrupt or same persistent claim identity has a conflicting claim fingerprint, never consume again and never return a normal BLOCKED proof; cleanup/finish as specified and return exact Phase32-compatible INDETERMINATE with `AUTHORITY_REPORTED_INDETERMINATE`.

### 17.3 Existing replay row

If replay guard resolves a historical row:

- historical row self-integrity/reference/durability validation is mandatory;
- historical snapshot/submission/claim fingerprint/backend/approval/conformance may differ from the current claim;
- such differences do not release the replay guard.

A valid historical replay row causes explicit COMMIT then BLOCKED `REPLAY_GUARD_ALREADY_CONSUMED`.

Corrupt historical replay row returns exact fail-closed INDETERMINATE and never permits a second consumption.

### 17.4 New consumption row

If neither claim nor replay row exists:

1. derive exact authority-result reference;
2. derive exact consumption reference;
3. derive exact 16-key record fingerprint;
4. validate each new exact string is strict UTF-8 encodable and construct its deterministic BLOB SQL literal;
5. build one exact `INSERT INTO main.kiwoom_order_authorization_consumption(...) VALUES(...)` statement using only BLOB literals for logical strings and canonical decimal INTEGER for synchronous level;
6. execute the INSERT exactly once;
7. execute explicit COMMIT exactly once;
8. only successful COMMIT allows CONSUMED.

No generated value is separately probed then rebound. Validation and authoritative use share the same deterministic literal representation, independent of registered Python adapters.

If post-BEGIN encoding/integrity construction fails before INSERT:

- decision=`INDETERMINATE`;
- `indeterminate_reason="AUTHORITY_REPORTED_INDETERMINATE"`;
- `block_reason=None`;
- `consumption_reference=None`;
- reported commit fields=None;
- `commit_state_known=False`;
- if active, cleanup ROLLBACK at most once;
- no retry;
- no second transaction.

SQLite UNIQUE constraints remain the authoritative race guard. Because key columns are BLOB, custom text collations cannot weaken byte-identity uniqueness.

---

## 18. `check_and_consume` failure, cleanup, and commit-state-unknown semantics

This entire section applies only to `KiwoomOrderAuthorizationSQLiteAuthority.check_and_consume`. Initializer runtime failures are governed by section 11.6. Verifier read-transaction failures are governed by section 20.

No automatic retry is permitted.
No failure branch may start a second authority transaction.

### 18.1 `BEGIN IMMEDIATE` raises `sqlite3.Error`

Immediately inspect `connection.in_transaction` without guessing whether SQLite established transaction state before raising.

If `connection.in_transaction is False`:

- issue no rollback;
- return Phase32-compatible `INDETERMINATE`;
- `indeterminate_reason="AUTHORITY_REPORTED_INDETERMINATE"`;
- reported commit fields=None;
- `commit_state_known=False`;
- no second transaction and no retry.

If `connection.in_transaction is True`:

- attempt exactly one explicit SQL cleanup `ROLLBACK`;
- whether cleanup succeeds or fails, return `INDETERMINATE`;
- reported commit fields=None;
- `commit_state_known=False`;
- no second cleanup attempt;
- no second transaction and no retry.

### 18.2 Expected SQLite failure after transaction start but before successful COMMIT

For expected `sqlite3.Error`, including authoritative schema/profile revalidation reads, claim lookup, replay lookup, fingerprint-row read, or INSERT:

1. preserve the original error state locally;
2. if `connection.in_transaction is True`, attempt exactly one explicit SQL `ROLLBACK`;
3. never start another transaction;
4. return `INDETERMINATE`;
5. reported commit fields=None;
6. `commit_state_known=False`;
7. no retry.

A successful cleanup rollback proves only that the currently open local transaction was rolled back. It does not convert the authority outcome to consumed or blocked.

### 18.3 COMMIT exception

If explicit SQL `COMMIT` raises `sqlite3.Error`:

- outcome is `INDETERMINATE`;
- consumed/blocked must not be guessed;
- `commit_state_known=False`;
- reported commit fields=None;
- inspect `connection.in_transaction`;
- if True, attempt exactly one cleanup `ROLLBACK`;
- cleanup success or failure does not upgrade the decision;
- no second cleanup attempt;
- no second transaction;
- no retry.

### 18.4 Cleanup ROLLBACK exception

If cleanup ROLLBACK itself fails:

- outcome remains `INDETERMINATE` for expected SQLite failure paths;
- no second cleanup attempt;
- no second transaction;
- no retry.

### 18.5 Unexpected Python exception

For an unexpected non-`sqlite3.Error` exception after `BEGIN IMMEDIATE` was attempted:

- inspect `connection.in_transaction`;
- if active, attempt one cleanup ROLLBACK;
- re-raise the original exception;
- cleanup failure must not replace the original exception as the primary exception;
- no retry and no second transaction.

### 18.6 `KeyboardInterrupt` / `SystemExit`

- inspect `connection.in_transaction`;
- if active, attempt exactly one cleanup ROLLBACK;
- always re-raise the original base exception;
- cleanup failure must not replace the original base exception;
- no retry;
- no second transaction.

---

## 19. Phase32 integration gate

Verifier input exact type:

`WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot`

Before any durable lookup, require:

- exact Phase32 snapshot type
- `decision == "AUTHORITY_REPORTED_CONSUMED"`
- `block_reason is None`
- `indeterminate_reason is None`
- valid exact Phase32 authority result
- valid `authority_result_reference`
- valid `consumption_reference`
- `commit_state_known is True`
- both authority-reported commit fields exact True
- `consumption_evidence_candidate_ready is True`
- `reconciliation_required is False`
- `automatic_retry_permitted is False`
- `authority_invocation_attempted is True`
- all Phase32 direct safety flags False
- exact recomputation of Phase32 evidence fingerprint
- exact embedded Phase31 claim fingerprint/binding
- exact embedded Phase30 request/materialization binding

Phase32 BLOCKED and INDETERMINATE evidence cannot be promoted.

---

## 20. Read-only local durable verification API, exact dual-reference lookup, and single-snapshot lifecycle

Exact verifier API remains:

`verify_demo_watchlist_order_authorization_durable_consumption(`
`    source_snapshot: WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot,`
`    authority: KiwoomOrderAuthorizationSQLiteAuthority,`
`) -> WatchlistOrderAuthorizationDurableVerificationSnapshot`

The verifier never calls `check_and_consume`, never INSERTs/UPDATEs/DELETEs/DDLs, never opens a write transaction, and never retries.

Local prerequisites are validated first, including exact connection surface and deterministic UTF-8/literal-encoding validity for source references. No DB-API parameter-binding probe is used.

Then verifier executes one explicit SQL `BEGIN` read transaction exactly once. Within that same snapshot it:

1. validates exact STRICT/BLOB structural schema and frozen stored-DDL;
2. validates exact metadata through converter-neutral BLOB reads;
3. validates WAL/FULL and observable connection surface;
4. independently resolves `source_snapshot.authority_result_reference` using a BLOB literal in the exact UNIQUE column lookup;
5. independently resolves `source_snapshot.consumption_reference` the same way;
6. reconstructs any returned durable row only from converter-neutral BLOB/INTEGER expressions;
7. applies the dual-reference cardinality/state routing below;
8. applies integrity-first verification precedence;
9. finishes the same read transaction with explicit COMMIT.

No caller-overridable named SQL scalar function is used for authority-critical storage or identity decisions. No text collation determines durable-row identity.

Dual-reference routing remains exact:

- both lookups absent -> `LEDGER_RECORD_NOT_FOUND`;
- exactly one resolves -> `LEDGER_RECORD_BINDING_MISMATCH`;
- both resolve but exact 13-field durable records differ -> `LEDGER_STATE_AMBIGUOUS`;
- both resolve to the same exact 13-field durable record -> continue verification.

Same-record equality uses only exact normalized 13-field values. rowid, cursor identity, Python object identity, raw connection identity, and path are excluded.

After same-row resolution exact precedence remains:

1. exact 13-field normalization;
2. exact 16-key record-fingerprint recomputation;
3. fingerprint mismatch -> `LEDGER_RECORD_FINGERPRINT_MISMATCH`;
4. historical deterministic result/consumption reference self-binding;
5. self-binding mismatch -> `LEDGER_RECORD_BINDING_MISMATCH`;
6. current authority backend identity comparison;
7. backend mismatch -> `BACKEND_IDENTITY_MISMATCH`;
8. remaining source/config/row semantic binding;
9. mismatch -> `LEDGER_RECORD_BINDING_MISMATCH`;
10. success.

Read/BEGIN/COMMIT SQLite error routes `LEDGER_READ_ERROR`; if transaction remains active, cleanup-only ROLLBACK is attempted at most once. No automatic retry or second read transaction.

Concurrent commits by other connections cannot create a mixed verifier view because all schema/metadata/row checks occur in the one explicit read transaction.

---

## 21. Verification snapshot

`WatchlistOrderAuthorizationDurableVerificationSnapshot` is a frozen dataclass with exact field order and exact annotations 19:

1. `source_snapshot: WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot`
2. `durable_record: KiwoomOrderAuthorizationDurableLedgerRecord | None`
3. `backend_instance_reference: str`
4. `ledger_schema_reference: str`
5. `verification_decision: str`
6. `indeterminate_reason: str | None`
7. `concrete_sqlite_authority_identity_verified: bool`
8. `ledger_schema_verified: bool`
9. `sqlite_connection_surface_verified: bool`
10. `sqlite_durability_profile_verified: bool`
11. `durable_record_present: bool`
12. `exact_binding_verified: bool`
13. `durable_consumption_record_verified: bool`
14. `authority_approval_provenance_verified: bool`
15. `authority_conformance_provenance_verified: bool`
16. `provider_send_eligibility_authorized: bool`
17. `production_authority_use_authorized: bool`
18. `reconciliation_required: bool`
19. `verification_fingerprint: str`

All boolean fields require exact `bool`; integer `0/1` is not accepted as a substitute by validation logic.

`ledger_schema_reference` exact successful/indeterminate contract value:

`kiwoom-watchlist-order-authorization-durable-ledger-v1`

`backend_instance_reference` exact value-source contract:

- for every successful verification snapshot, `backend_instance_reference == authority.config.backend_instance_reference`;
- for every verification INDETERMINATE snapshot, `backend_instance_reference == authority.config.backend_instance_reference`;
- the historical durable row's `backend_instance_reference` is a row-self-integrity value and a comparison input for `BACKEND_IDENTITY_MISMATCH`; it never replaces the verification snapshot identity field;
- local validation failure produces no verification snapshot, so this binding does not create a snapshot on local validation failure;
- no fallback, normalization, historical-row substitution, or null substitution is allowed for this field after local validation succeeds.

Successful local verification:

- `verification_decision="LOCAL_DURABLE_CONSUMPTION_RECORD_VERIFIED"`
- `indeterminate_reason is None`
- `durable_record` is exact `KiwoomOrderAuthorizationDurableLedgerRecord`
- `backend_instance_reference == authority.config.backend_instance_reference`
- `concrete_sqlite_authority_identity_verified=True`
- `ledger_schema_verified=True`
- `sqlite_connection_surface_verified=True`
- `sqlite_durability_profile_verified=True`
- `durable_record_present=True`
- `exact_binding_verified=True`
- `durable_consumption_record_verified=True`
- `authority_approval_provenance_verified=False`
- `authority_conformance_provenance_verified=False`
- `provider_send_eligibility_authorized=False`
- `production_authority_use_authorized=False`
- `reconciliation_required=False`

`concrete_sqlite_authority_identity_verified=True` means the verifier validated the exact authority runtime type, config identity bindings, backend-instance reference, connection object type, and exact Phase33 local storage identity requirements. It does not prove external governance trust or future execution capability.

`sqlite_connection_surface_verified=True` means only that the verifier observed the current caller connection surface matching the exact read-only-observable Phase33 requirements: exact `sqlite3.Connection`, open/file-backed `main`, `autocommit is True`, `isolation_level is None`, `busy_timeout=0`, `row_factory is None`, `text_factory is str`, and clean transaction entry state before the verifier begins its own read transaction. Deterministic SQL literal encoding is a Phase33 value-transport contract and is not part of this connection-surface proof.

It does not prove historical `BEGIN IMMEDIATE`, historical COMMIT/ROLLBACK execution, historical adapter/converter registry state, or the historical behavior represented by `transaction_profile_id`.

## 22. Verification decision model and exact reason precedence

Exact decision values remain:

1. `LOCAL_DURABLE_CONSUMPTION_RECORD_VERIFIED`
2. `INDETERMINATE`

No Phase33 verification `BLOCKED` decision exists.

Exact INDETERMINATE reasons remain 8:

1. `LEDGER_READ_ERROR`
2. `LEDGER_SCHEMA_MISMATCH`
3. `SQLITE_DURABILITY_PROFILE_MISMATCH`
4. `BACKEND_IDENTITY_MISMATCH`
5. `LEDGER_RECORD_NOT_FOUND`
6. `LEDGER_RECORD_BINDING_MISMATCH`
7. `LEDGER_RECORD_FINGERPRINT_MISMATCH`
8. `LEDGER_STATE_AMBIGUOUS`

For every INDETERMINATE verification snapshot:

- `durable_record is None`
- `ledger_schema_reference` remains the exact Phase33 schema-reference constant
- all local verification success flags=False
- approval/conformance provenance flags=False
- provider-send eligibility=False
- production-authority use=False
- `reconciliation_required=True`
- no reconciliation action is executed
- no second consume
- no automatic retry

For `BACKEND_IDENTITY_MISMATCH` specifically:

- current `authority.config.backend_instance_reference` and the self-integrity-valid historical row backend reference differ;
- `durable_record is None`;
- snapshot `backend_instance_reference` remains exact current `authority.config.backend_instance_reference`;
- historical row backend is not copied into the snapshot identity field;
- all local verification success flags remain False;
- approval/conformance provenance flags remain False;
- provider-send and production-use authorization flags remain False;
- `reconciliation_required=True`.

Exact post-local-precondition precedence, entirely within the one read transaction/snapshot:

1. any verifier BEGIN/read/finish SQLite error -> `LEDGER_READ_ERROR`;
2. schema introspection read error -> `LEDGER_READ_ERROR`; semantic/structural/stored-DDL mismatch -> `LEDGER_SCHEMA_MISMATCH`;
3. durability PRAGMA read error -> `LEDGER_READ_ERROR`; WAL/FULL mismatch -> `SQLITE_DURABILITY_PROFILE_MISMATCH`;
4. dual-reference cardinality/state:
   - both absent -> `LEDGER_RECORD_NOT_FOUND`;
   - exactly one resolves -> `LEDGER_RECORD_BINDING_MISMATCH`;
   - both resolve but exact normalized 13-field durable-record values differ -> `LEDGER_STATE_AMBIGUOUS`;
   - both resolve the same exact normalized 13-field record -> continue;
5. if the resolved row cannot satisfy exact 13-field durable-record type/normalization requirements -> `LEDGER_RECORD_BINDING_MISMATCH`;
6. recompute the exact 16-key historical `record_fingerprint` before trusting the row's current-backend or source/config semantic meaning; mismatch -> `LEDGER_RECORD_FINGERPRINT_MISMATCH`;
7. recompute the historical row's deterministic `authority_result_reference` and `consumption_reference` from that same historical row and exact constants; self-binding mismatch -> `LEDGER_RECORD_BINDING_MISMATCH`;
8. compare current authority `backend_instance_reference` to the now-self-consistent resolved historical row backend identity; mismatch -> `BACKEND_IDENTITY_MISMATCH`;
9. validate all remaining exact source/config/row semantic bindings; mismatch -> `LEDGER_RECORD_BINDING_MISMATCH`;
10. only after all above pass and verifier COMMIT succeeds -> `LOCAL_DURABLE_CONSUMPTION_RECORD_VERIFIED`.

Integrity precedence is mandatory. If a damaged durable row simultaneously creates a fingerprint mismatch and a backend or semantic-binding mismatch, `LEDGER_RECORD_FINGERPRINT_MISMATCH` wins. If the fingerprint is valid but deterministic historical reference self-binding fails, `LEDGER_RECORD_BINDING_MISMATCH` wins before current backend comparison.

Exact trigger definitions:

- `BACKEND_IDENTITY_MISMATCH`: only a self-integrity-valid row whose historical `backend_instance_reference` differs from the current verifier authority backend instance;
- `LEDGER_RECORD_NOT_FOUND`: both independent UNIQUE-reference lookups resolve zero rows;
- `LEDGER_RECORD_BINDING_MISMATCH`: one-sided reference resolution, invalid exact row normalization, historical deterministic-reference self-binding failure, or remaining source/config/row semantic mismatch after fingerprint integrity succeeds;
- `LEDGER_RECORD_FINGERPRINT_MISMATCH`: exact 16-key recomputation differs from the stored fingerprint, regardless of simultaneous backend/binding mismatch;
- `LEDGER_STATE_AMBIGUOUS`: both source references resolve rows, but the exact normalized 13-field durable-record values differ.

If any semantic INDETERMINATE result is determined before transaction end, the verifier still ends its read transaction exactly once before returning. A verifier COMMIT failure overrides any would-be semantic success and yields `INDETERMINATE / LEDGER_READ_ERROR`.

---

## 23. Deterministic local validation errors and exact routing

Allowed deterministic local validation reasons remain exact 11:

1. `SOURCE_SNAPSHOT_TYPE_INVALID`
2. `SOURCE_SNAPSHOT_NOT_CONSUMED_CANDIDATE`
3. `SOURCE_SNAPSHOT_BINDING_INVALID`
4. `AUTHORITY_BACKEND_TYPE_INVALID`
5. `AUTHORITY_CONFIG_INVALID`
6. `AUTHORITY_CONNECTION_INVALID`
7. `AUTHORITY_CONNECTION_TRANSACTION_ACTIVE`
8. `AUTHORITY_CONNECTION_TRANSACTION_MODE_INVALID`
9. `SQLITE_DURABILITY_PROFILE_INVALID`
10. `LEDGER_SCHEMA_INVALID`
11. `REFERENCE_OR_FINGERPRINT_INVALID`

No new reason is added for adapters, converters, named SQL functions, or collations because A11 removes those mechanisms from the authoritative value/identity proof rather than trying to introspect them.

`AUTHORITY_CONNECTION_TRANSACTION_MODE_INVALID` covers observable mismatch of autocommit/isolation/busy-timeout/row_factory/text_factory.

Invalid/non-UTF8-encodable authority/config/reference/fingerprint values route through the already applicable config/reference reason before transaction start.

### 23.1 Initializer routing

1. wrong/closed/non-file-backed connection -> `AUTHORITY_CONNECTION_INVALID`
2. active transaction -> `AUTHORITY_CONNECTION_TRANSACTION_ACTIVE`
3. observable exact connection-surface mismatch -> `AUTHORITY_CONNECTION_TRANSACTION_MODE_INVALID`
4. WAL/FULL mismatch -> `SQLITE_DURABILITY_PROFILE_INVALID`
5. existing STRICT/BLOB structural/stored-DDL/metadata mismatch -> `LEDGER_SCHEMA_INVALID`

Runtime SQLite errors after transaction start follow section 11.6.

### 23.2 `check_and_consume` routing

Exact pre-transaction precedence:

1. invalid config -> `AUTHORITY_CONFIG_INVALID`
2. malformed claim -> `REFERENCE_OR_FINGERPRINT_INVALID`
3. malformed replay guard -> `REFERENCE_OR_FINGERPRINT_INVALID`
4. malformed claim fingerprint -> `REFERENCE_OR_FINGERPRINT_INVALID`
5. replay guard/claim inconsistency -> `REFERENCE_OR_FINGERPRINT_INVALID`
6. authority/approval/conformance binding mismatch -> `REFERENCE_OR_FINGERPRINT_INVALID`
7. non-UTF8-encodable or non-canonical-literal-encodable authority-critical value -> `REFERENCE_OR_FINGERPRINT_INVALID`
8. wrong/closed/non-file connection -> `AUTHORITY_CONNECTION_INVALID`
9. active transaction -> `AUTHORITY_CONNECTION_TRANSACTION_ACTIVE`
10. observable connection-surface mismatch -> `AUTHORITY_CONNECTION_TRANSACTION_MODE_INVALID`
11. WAL/FULL mismatch -> `SQLITE_DURABILITY_PROFILE_INVALID`
12. STRICT/BLOB structural/stored-DDL/metadata mismatch -> `LEDGER_SCHEMA_INVALID`

No transaction starts before these pass.

After `BEGIN IMMEDIATE`, semantic revalidation or newly derived exact-value encoding/integrity failure returns exact Phase32-compatible INDETERMINATE with `indeterminate_reason="AUTHORITY_REPORTED_INDETERMINATE"`, cleanup at most once, no retry, no second transaction.

### 23.3 Verifier routing

Exact local-precondition precedence before verifier `BEGIN`:

1. source type invalid -> `SOURCE_SNAPSHOT_TYPE_INVALID`
2. source not eligible consumed candidate -> `SOURCE_SNAPSHOT_NOT_CONSUMED_CANDIDATE`
3. source fingerprint/Phase31/30 binding invalid -> `SOURCE_SNAPSHOT_BINDING_INVALID`
4. authority type invalid -> `AUTHORITY_BACKEND_TYPE_INVALID`
5. authority config invalid -> `AUTHORITY_CONFIG_INVALID`
6. wrong/closed/non-file connection -> `AUTHORITY_CONNECTION_INVALID`
7. active transaction -> `AUTHORITY_CONNECTION_TRANSACTION_ACTIVE`
8. observable connection-surface mismatch -> `AUTHORITY_CONNECTION_TRANSACTION_MODE_INVALID`
9. malformed/non-UTF8-encodable required source reference/fingerprint -> `REFERENCE_OR_FINGERPRINT_INVALID`

After explicit verifier `BEGIN`:

- schema/stored-DDL/metadata mismatch -> `INDETERMINATE / LEDGER_SCHEMA_MISMATCH`;
- durability mismatch -> `INDETERMINATE / SQLITE_DURABILITY_PROFILE_MISMATCH`;
- read/finish SQLite failure -> `INDETERMINATE / LEDGER_READ_ERROR`;
- durable-row BLOB/INTEGER normalization failure -> `INDETERMINATE / LEDGER_RECORD_BINDING_MISMATCH`;
- remaining identity/binding/fingerprint states follow section 22 exact precedence.

---

## 24. Verification fingerprint

`verification_fingerprint` is lowercase 64-hex SHA-256.

Exact canonical envelope key set remains 19:

1. `domain`
2. `source_evidence_fingerprint`
3. `durable_record_fingerprint`
4. `backend_instance_reference`
5. `ledger_schema_reference`
6. `verification_decision`
7. `indeterminate_reason`
8. `concrete_sqlite_authority_identity_verified`
9. `ledger_schema_verified`
10. `sqlite_connection_surface_verified`
11. `sqlite_durability_profile_verified`
12. `durable_record_present`
13. `exact_binding_verified`
14. `durable_consumption_record_verified`
15. `authority_approval_provenance_verified`
16. `authority_conformance_provenance_verified`
17. `provider_send_eligibility_authorized`
18. `production_authority_use_authorized`
19. `reconciliation_required`

The exact value source for every key is frozen:

1. `domain = "phase33-local-durable-verification-v1"`;
2. `source_evidence_fingerprint = source_snapshot.evidence_fingerprint` exactly; this is the exact Phase32 field after the Phase32 integration gate has independently recomputed and required its canonical fingerprint match;
3. successful verification: `durable_record_fingerprint = durable_record.record_fingerprint` exactly, after that exact durable record has passed row self-integrity validation;
4. every verification INDETERMINATE snapshot, regardless of reason: `durable_record_fingerprint = None` and canonical JSON therefore contains JSON `null`;
5. `backend_instance_reference = verification_snapshot.backend_instance_reference = authority.config.backend_instance_reference` exactly for success and every verification INDETERMINATE snapshot;
6. `ledger_schema_reference = "kiwoom-watchlist-order-authorization-durable-ledger-v1"`;
7. `verification_decision = verification_snapshot.verification_decision` exactly;
8. `indeterminate_reason = verification_snapshot.indeterminate_reason` exactly;
9. `concrete_sqlite_authority_identity_verified = verification_snapshot.concrete_sqlite_authority_identity_verified` exactly;
10. `ledger_schema_verified = verification_snapshot.ledger_schema_verified` exactly;
11. `sqlite_connection_surface_verified = verification_snapshot.sqlite_connection_surface_verified` exactly;
12. `sqlite_durability_profile_verified = verification_snapshot.sqlite_durability_profile_verified` exactly;
13. `durable_record_present = verification_snapshot.durable_record_present` exactly;
14. `exact_binding_verified = verification_snapshot.exact_binding_verified` exactly;
15. `durable_consumption_record_verified = verification_snapshot.durable_consumption_record_verified` exactly;
16. `authority_approval_provenance_verified = verification_snapshot.authority_approval_provenance_verified` exactly;
17. `authority_conformance_provenance_verified = verification_snapshot.authority_conformance_provenance_verified` exactly;
18. `provider_send_eligibility_authorized = verification_snapshot.provider_send_eligibility_authorized` exactly;
19. `production_authority_use_authorized = verification_snapshot.production_authority_use_authorized` exactly;
20. `reconciliation_required = verification_snapshot.reconciliation_required` exactly.

The list above has 20 mapping clauses because `durable_record_fingerprint` has mutually exclusive success and INDETERMINATE source rules while the canonical envelope itself remains exact 19 keys.

`source_evidence_fingerprint` must use only exact `source_snapshot.evidence_fingerprint`. A11 must not invent a differently named Phase32 fingerprint, fingerprint the complete source snapshot as a substitute, or copy a raw authority object into this field.

Successful `durable_record_fingerprint` must use only the already self-integrity-validated exact `durable_record.record_fingerprint`. A11 creates no second durable-record fingerprint field and does not recompute a differently named value for the verification envelope.

For every verification INDETERMINATE result, `durable_record is None` and `durable_record_fingerprint is None` even if a historical row was transiently read while determining the reason. The historical row fingerprint is not exposed as the verification snapshot durable-record fingerprint on an INDETERMINATE result.

`verification_fingerprint` itself is never a source key in its own envelope.

Canonical JSON:

`json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)`

UTF-8 encode, then SHA-256 lowercase hex.

Raw SQLite connection identity, cursor identity, database path, rowid, PID, machine name, clock, UUID, and randomness are excluded.

## 25. Permission isolation

Phase33 A11 must never expose True for:

- `provider_send_eligibility_authorized`
- `production_authority_use_authorized`
- `authority_approval_provenance_verified`
- `authority_conformance_provenance_verified`

Phase33 does not introduce:

- `transport_allowed=True`
- `post_permitted=True`
- `send_permitted=True`
- provider network permission
- actual order-submission permission

A future separate official contract is required before any such transition.

---

## 26. Allowed runtime side effects of a future implementation

Only:

- explicit creation/validation of Phase33 schema on caller-provided file-backed SQLite connection;
- exact SQLite reads/writes for `check_and_consume`;
- one explicit read transaction for verifier single-snapshot consistency;
- explicit SQL COMMIT when required;
- cleanup-only single ROLLBACK when required.

Still prohibited:

- provider network
- OAuth/token access
- account access
- actual order call
- provider response parsing
- order-number handling
- filesystem path auto-discovery
- hidden database creation
- `.env` access
- external credential access
- subprocess
- shell
- Git
- dependency mutation
- wall-clock dependency
- UUID/randomness
- automatic retry/backoff
- hidden background thread/task
- hidden lock manager
- same-connection concurrency initiated by Phase33

---

## 27. Dependencies

Candidate implementation dependencies remain Python standard library only:

- `sqlite3`
- `dataclasses`
- `hashlib`
- `json`
- `re`
- typing/collections helpers as needed

No new third-party dependency.

`pyproject.toml` unchanged.

`uv.lock` unchanged.

---

## 28. Exact targeted test expectation

DRAFT-A11 candidate targeted tests: exact `217`.

Category counts:

1. Public API / signatures / frozen dataclasses / annotations = `14`
2. Config/reference validation = `10`
3. STRICT-BLOB schema / stored-DDL / initializer / profile = `39`
4. Check-and-consume / prevalidation / TOCTOU = `36`
5. Replay / claim / corrupt-existing-row = `22`
6. Phase32 integration = `16`
7. Verification / dual-reference / integrity precedence / snapshot/fingerprint = `44`
8. SQLite failure / rollback cleanup = `13`
9. Safety / concurrency isolation = `8`
10. DB-API/callback-independent literal encoding / STRICT storage = `15`

Arithmetic:

`14 + 10 + 39 + 36 + 22 + 16 + 44 + 13 + 8 + 15 = 217`

Candidate regression arithmetic:

- `EXPECTED_PRE_IMPLEMENTATION_FULL_REGRESSION=1068`
- `EXPECTED_NEW_TEST_DELTA=217`
- `EXPECTED_POST_IMPLEMENTATION_FULL_REGRESSION=1285`

These are DRAFT-A11 candidate counts only, not execution results.

---

## 29. Exact named targeted test manifest

The exact candidate manifest is:

1. `test_public_api_symbol_set_exact_7`
2. `test_error_inherits_runtime_error`
3. `test_config_is_frozen_dataclass`
4. `test_config_field_order_exact_4`
5. `test_durable_record_is_frozen_dataclass`
6. `test_durable_record_field_order_exact_13`
7. `test_verification_snapshot_is_frozen_dataclass`
8. `test_verification_snapshot_field_order_exact_19`
9. `test_initializer_signature_exact`
10. `test_authority_constructor_signature_exact`
11. `test_check_and_consume_signature_exact_phase32_compatible`
12. `test_verifier_signature_exact`
13. `test_durable_record_field_annotations_exact_13`
14. `test_verification_snapshot_field_annotations_exact_19`
15. `test_config_accepts_minimum_length_references`
16. `test_config_accepts_maximum_length_references`
17. `test_config_rejects_empty_reference`
18. `test_config_rejects_whitespace_only_reference`
19. `test_config_rejects_leading_whitespace`
20. `test_config_rejects_trailing_whitespace`
21. `test_config_rejects_c0_control_character`
22. `test_config_rejects_delete_control_character`
23. `test_config_rejects_non_exact_str_subclass`
24. `test_config_does_not_trim_casefold_normalize_or_replace`
25. `test_initializer_requires_exact_sqlite_connection_type`
26. `test_initializer_rejects_closed_connection`
27. `test_initializer_rejects_active_transaction`
28. `test_initializer_requires_autocommit_true`
29. `test_initializer_requires_isolation_level_none_redundant_surface_invariant`
30. `test_initializer_rejects_memory_main_database`
31. `test_initializer_requires_file_backed_main_database`
32. `test_initializer_requires_main_journal_mode_wal`
33. `test_initializer_requires_main_synchronous_full_2`
34. `test_initializer_requires_busy_timeout_zero`
35. `test_initializer_rejects_synchronous_extra_3`
36. `test_initializer_rejects_synchronous_normal_1`
37. `test_initializer_rejects_synchronous_off_0`
38. `test_initializer_creates_exact_meta_table_in_main`
39. `test_initializer_creates_exact_consumption_table_in_main`
40. `test_initializer_records_exact_schema_id_metadata`
41. `test_initializer_records_exact_transaction_and_durability_profile_metadata`
42. `test_initializer_is_idempotent_for_exact_existing_schema`
43. `test_initializer_rejects_incompatible_existing_schema`
44. `test_temp_shadow_objects_do_not_override_main_schema`
45. `test_meta_table_xinfo_exact_structure`
46. `test_consumption_table_xinfo_exact_structure`
47. `test_phase33_autoindex_name_set_quoting_and_index_xinfo_exact_key_sets`
48. `test_phase33_unique_index_key_collations_are_binary`
49. `test_initializer_rejects_extra_user_created_index_on_phase33_table`
50. `test_initializer_rejects_trigger_on_phase33_table`
51. `test_initializer_rejects_phase33_namespaced_view`
52. `test_attached_schema_shadow_objects_do_not_override_main_schema`
53. `test_phase33_table_list_exact_type_ncol_wr_strict`
54. `test_initializer_requires_strict_phase33_tables`
55. `test_initializer_rejects_without_rowid_phase33_table`
56. `test_initializer_requires_zero_foreign_keys_for_phase33_tables`
57. `test_initializer_rejects_unapproved_check_constraint_via_stored_ddl`
58. `test_initializer_rejects_unapproved_collate_or_table_option_via_stored_ddl`
59. `test_initializer_requires_exact_canonical_stored_ddl_identity_and_hashes`
60. `test_initializer_begin_immediate_sqlite_error_cleanup_and_reraises_original`
61. `test_initializer_schema_ddl_or_metadata_sqlite_error_cleanup_and_reraises_original`
62. `test_initializer_commit_sqlite_error_cleanup_and_reraises_original`
63. `test_initializer_cleanup_rollback_error_does_not_replace_original_sqlite_error`
64. `test_check_and_consume_starts_begin_immediate_exactly_once`
65. `test_check_and_consume_reads_claim_key_inside_transaction`
66. `test_check_and_consume_reads_replay_key_inside_transaction`
67. `test_new_claim_inserts_exactly_one_row`
68. `test_success_commits_with_explicit_sql_commit_exactly_once`
69. `test_success_leaves_connection_not_in_transaction`
70. `test_success_returns_phase32_exact_reported_result_type`
71. `test_success_decision_is_authority_reported_consumed`
72. `test_success_commit_state_known_is_true`
73. `test_success_reported_commit_flags_are_true`
74. `test_authority_result_reference_prefix_exact`
75. `test_consumption_reference_prefix_exact`
76. `test_authority_result_reference_domain_separator_exact`
77. `test_consumption_reference_domain_separator_exact`
78. `test_authority_result_reference_envelope_key_set_and_profile_constants_exact`
79. `test_consumption_reference_envelope_key_set_and_profile_constants_exact`
80. `test_references_are_deterministic_for_same_inputs`
81. `test_record_fingerprint_envelope_key_set_exact_16_with_schema_and_durability_profiles`
82. `test_record_fingerprint_excludes_record_fingerprint_field`
83. `test_success_persists_wal_full_profile_fields`
84. `test_check_and_consume_rejects_invalid_config_before_transaction`
85. `test_check_and_consume_rejects_malformed_claim_identity_before_transaction`
86. `test_check_and_consume_rejects_malformed_replay_guard_before_transaction`
87. `test_check_and_consume_rejects_malformed_claim_fingerprint_before_transaction`
88. `test_check_and_consume_rejects_replay_guard_claim_mismatch_before_transaction`
89. `test_check_and_consume_rejects_asserted_binding_mismatch_before_transaction`
90. `test_check_and_consume_rejects_invalid_connection_before_transaction`
91. `test_check_and_consume_rejects_active_transaction_before_transaction`
92. `test_check_and_consume_rejects_connection_surface_mismatch_before_transaction`
93. `test_check_and_consume_rejects_durability_profile_mismatch_before_transaction`
94. `test_check_and_consume_rejects_schema_or_metadata_mismatch_before_transaction`
95. `test_check_and_consume_validation_precedence_config_before_reference_errors`
96. `test_check_and_consume_validation_precedence_connection_before_profile_and_schema`
97. `test_check_and_consume_local_validation_starts_no_transaction_and_mutates_no_ledger`
98. `test_check_and_consume_revalidates_schema_metadata_and_stored_ddl_inside_begin_before_lookup`
99. `test_check_and_consume_revalidates_wal_full_inside_begin_before_lookup_and_drift_is_indeterminate`
100. `test_claim_identity_unique_scope_ignores_backend_instance_reference`
101. `test_replay_guard_unique_scope_ignores_backend_instance_reference`
102. `test_same_claim_same_backend_is_blocked`
103. `test_same_claim_different_backend_is_blocked`
104. `test_same_replay_guard_same_backend_is_blocked`
105. `test_same_replay_guard_different_backend_is_blocked`
106. `test_claim_conflict_reason_is_claim_already_consumed`
107. `test_replay_conflict_reason_is_replay_guard_already_consumed`
108. `test_claim_conflict_performs_no_insert`
109. `test_replay_conflict_performs_no_insert`
110. `test_claim_conflict_commits_read_transaction_exactly_once`
111. `test_replay_conflict_commits_read_transaction_exactly_once`
112. `test_claim_conflict_leaves_connection_not_in_transaction`
113. `test_replay_conflict_leaves_connection_not_in_transaction`
114. `test_claim_conflict_does_not_modify_existing_row`
115. `test_replay_conflict_does_not_modify_existing_row`
116. `test_claim_unique_constraint_matches_exact_phase33_columns`
117. `test_replay_unique_constraint_matches_exact_phase33_columns`
118. `test_claim_conflict_does_not_start_second_transaction`
119. `test_replay_conflict_does_not_start_second_transaction`
120. `test_corrupt_existing_claim_row_returns_indeterminate_not_blocked_or_consumed`
121. `test_corrupt_existing_replay_row_returns_indeterminate_not_blocked_or_consumed`
122. `test_verifier_requires_exact_phase32_snapshot_type`
123. `test_verifier_rejects_phase32_blocked_snapshot`
124. `test_verifier_rejects_phase32_indeterminate_snapshot`
125. `test_verifier_requires_phase32_consumed_decision`
126. `test_verifier_requires_phase32_commit_state_known_true`
127. `test_verifier_requires_phase32_commit_flags_true`
128. `test_verifier_requires_consumption_evidence_candidate_ready_true`
129. `test_verifier_requires_phase32_reconciliation_required_false`
130. `test_verifier_requires_phase32_automatic_retry_false`
131. `test_verifier_requires_authority_invocation_attempted_true`
132. `test_verifier_requires_all_phase32_direct_safety_flags_false`
133. `test_verifier_recomputes_phase32_evidence_fingerprint_exactly`
134. `test_verifier_revalidates_embedded_phase31_claim_binding`
135. `test_verifier_revalidates_embedded_phase30_materialization_binding`
136. `test_verifier_requires_source_result_references_match_durable_row`
137. `test_verifier_never_calls_check_and_consume_again`
138. `test_success_verification_decision_is_local_durable_consumption_record_verified`
139. `test_success_concrete_sqlite_authority_identity_verified_true`
140. `test_success_ledger_schema_verified_true`
141. `test_success_sqlite_connection_surface_verified_true`
142. `test_success_sqlite_durability_profile_verified_true`
143. `test_success_durable_record_present_true`
144. `test_success_exact_binding_verified_true`
145. `test_success_durable_consumption_record_verified_true`
146. `test_success_approval_provenance_verified_false`
147. `test_success_conformance_provenance_verified_false`
148. `test_success_provider_send_eligibility_authorized_false`
149. `test_success_production_authority_use_authorized_false`
150. `test_success_reconciliation_required_false`
151. `test_verification_fingerprint_domain_exact`
152. `test_verification_fingerprint_envelope_key_set_exact_19_with_identity_and_connection_surface_fields`
153. `test_verification_fingerprint_deterministic_for_same_evidence`
154. `test_verification_fingerprint_changes_when_durable_record_changes`
155. `test_raw_connection_identity_never_enters_verification_fingerprint`
156. `test_ledger_schema_reference_exact_constant`
157. `test_verifier_schema_drift_routes_indeterminate_ledger_schema_mismatch`
158. `test_verifier_durability_drift_routes_indeterminate_sqlite_durability_profile_mismatch`
159. `test_verifier_rejects_invalid_authority_type_before_read_transaction`
160. `test_verifier_rejects_invalid_authority_config_before_read_transaction`
161. `test_verifier_rejects_invalid_connection_before_read_transaction`
162. `test_verifier_rejects_active_transaction_before_read_transaction`
163. `test_verifier_rejects_connection_surface_mismatch_before_read_transaction`
164. `test_verifier_rejects_malformed_local_reference_or_fingerprint_before_read_transaction`
165. `test_verifier_uses_single_explicit_read_transaction_from_begin_through_commit`
166. `test_verifier_single_read_transaction_prevents_mixed_snapshot_under_concurrent_row_or_schema_commit`
167. `test_verifier_read_or_commit_sqlite_error_routes_ledger_read_error_and_cleanup_once_without_retry`
168. `test_verifier_both_source_references_absent_routes_ledger_record_not_found`
169. `test_verifier_authority_result_reference_only_match_routes_ledger_record_binding_mismatch`
170. `test_verifier_consumption_reference_only_match_routes_ledger_record_binding_mismatch`
171. `test_verifier_source_references_resolve_different_rows_routes_ledger_state_ambiguous`
172. `test_verifier_current_backend_identity_mismatch_routes_backend_identity_mismatch`
173. `test_verifier_source_config_row_binding_mismatch_routes_ledger_record_binding_mismatch`
174. `test_verifier_record_fingerprint_mismatch_routes_ledger_record_fingerprint_mismatch`
175. `test_verifier_dual_reference_resolution_and_reason_precedence_exact`
176. `test_verifier_record_fingerprint_mismatch_precedes_backend_identity_mismatch`
177. `test_verifier_record_fingerprint_mismatch_precedes_record_binding_mismatch`
178. `test_verification_snapshot_backend_instance_reference_always_binds_current_authority_config`
179. `test_verification_fingerprint_source_evidence_fingerprint_binds_phase32_snapshot_evidence_fingerprint`
180. `test_verification_fingerprint_success_durable_record_fingerprint_binds_record_field_exactly`
181. `test_verification_fingerprint_indeterminate_uses_null_durable_record_fingerprint_and_current_backend_binding`
182. `test_begin_immediate_sqlite_error_without_active_transaction_returns_indeterminate_without_rollback_or_retry`
183. `test_begin_immediate_sqlite_error_with_active_transaction_attempts_cleanup_once_then_indeterminate`
184. `test_in_transaction_authoritative_revalidation_sqlite_error_attempts_cleanup_once`
185. `test_claim_lookup_sqlite_error_attempts_cleanup_once`
186. `test_replay_lookup_sqlite_error_attempts_cleanup_once`
187. `test_insert_sqlite_error_attempts_cleanup_once`
188. `test_commit_error_returns_indeterminate_commit_state_unknown_and_never_consumed_or_blocked`
189. `test_cleanup_rollback_failure_remains_indeterminate_without_second_cleanup`
190. `test_sqlite_failure_never_starts_second_transaction`
191. `test_unexpected_python_exception_cleans_up_then_reraises`
192. `test_keyboard_interrupt_cleans_up_then_reraises`
193. `test_system_exit_cleans_up_then_reraises`
194. `test_initializer_keyboard_interrupt_or_system_exit_cleans_up_then_reraises_original`
195. `test_phase33_performs_no_provider_network_call`
196. `test_phase33_performs_no_credential_token_or_account_access`
197. `test_phase33_performs_no_env_lookup`
198. `test_phase33_performs_no_subprocess_shell_or_git_action`
199. `test_phase33_uses_no_wall_clock_uuid_or_randomness`
200. `test_phase33_adds_no_third_party_dependency_and_no_package_level_reexport`
201. `test_phase33_never_authorizes_provider_send_or_production_use`
202. `test_phase33_requires_caller_exclusive_connection_use_and_creates_no_hidden_thread_task_or_lock_manager`
203. `test_initializer_rejects_non_none_connection_row_factory`
204. `test_initializer_rejects_non_str_connection_text_factory`
205. `test_check_and_consume_rejects_non_none_connection_row_factory_before_transaction`
206. `test_check_and_consume_rejects_non_str_connection_text_factory_before_transaction`
207. `test_verifier_rejects_non_none_connection_row_factory_before_read_transaction`
208. `test_verifier_rejects_non_str_connection_text_factory_before_read_transaction`
209. `test_authoritative_blob_backed_string_reads_decode_strict_utf8_without_typeof_dependency`
210. `test_authoritative_integer_reads_use_strict_integer_schema_and_converter_neutral_cast`
211. `test_authoritative_string_sql_blob_literal_encoding_bypasses_registered_adapter`
212. `test_authoritative_integer_sql_literal_encoding_bypasses_registered_adapter`
213. `test_stateful_str_adapter_cannot_pass_check_then_change_authoritative_binding`
214. `test_stateful_int_adapter_cannot_pass_check_then_change_authoritative_binding`
215. `test_connection_local_typeof_override_cannot_spoof_text_storage_contract`
216. `test_connection_local_typeof_override_cannot_spoof_integer_storage_contract`
217. `test_post_begin_binding_integrity_failure_reason_is_exact_authority_reported_indeterminate`

Manifest invariants:

- `TARGETED_TEST_COUNT=217`
- `TARGETED_TEST_UNIQUE_COUNT=217`
- `TARGETED_TEST_DUPLICATE_COUNT=0`
- exact numeric sequence=`1..217`

The A10 exact runtime test manifest is retained count-neutral in A11. A11 adds no runtime behavioral contract and therefore adds no new targeted test; tests 1-217 remain the exact candidate manifest. Three existing test names are count-neutral governance/exactness renames only: test 47 strengthens the previously required autoindex-name/quoting/index_xinfo exactness, and tests 116-117 replace stale A6-specific column wording with stable `phase33_columns` wording.

---

## 30. A10 -> A11 semantic diff

A11 is a governance/exactness consistency revision. It preserves A10's runtime behavior, public API, STRICT+BLOB/INTEGER storage model, deterministic SQL literal transport, Phase32 integration, transaction ownership, WAL/FULL profile, dual-reference routing, integrity-first precedence, claim/replay semantics, verification snapshot/fingerprint mapping, and permission isolation.

A11 changes only governance provenance and exactness wording that remained inconsistent in A10:

1. corrects the revision-chain status so A8, A9, and A10 Final Reviews are recorded as `STOP_HOLD`, while A11 is `DESIGN_ONLY` and not approved;
2. replaces the incorrect A7 source baseline with the exact A10 source artifact identity and declares that A10 artifact the sole Phase33 revision source of truth for A11;
3. renames targeted tests 116 and 117 from stale A6-specific column wording to exact stable `phase33_columns` wording without changing their behavior;
4. freezes the exact six-name SQLite internal autoindex set for the exact Phase33 DDL;
5. freezes the dynamic `PRAGMA main.index_xinfo(...)` object-name acceptance and exact SQL single-quote-doubling rendering rule;
6. explicitly states that SQLite autoindex numeric suffixes are not semantic proof of UNIQUE-key meaning and preserves `index_list` / `index_xinfo` key-set verification as normative;
7. renames/strengthens targeted test 47 count-neutrally to cover the accepted autoindex-name set, safe quoting, and exact `index_xinfo` key sets;
8. retains Candidate acceptance gates as exact unique contiguous `1..60`, while strengthening the structural-index gate to include the exact accepted autoindex-name set and quoting rule;
9. adds no new runtime behavioral contract, no new public API, no new field, no new reason, no new implementation path, and no new targeted test.

Exact historical count chain:

- A8 targeted tests=`212`
- A9 targeted tests=`217`
- A10 targeted tests=`217`
- A11 targeted tests=`217`
- A8 expected post-implementation regression=`1280`
- A9 expected post-implementation regression=`1285`
- A10 expected post-implementation regression=`1285`
- A11 expected post-implementation regression=`1285`

Frozen stored-DDL identities remain unchanged from A10:

- meta bytes=`116`, SHA256=`55FDBAD5B3992B06F98D132FC881B7090E83E00E92CE20B5A05CD73B52F68AFE`
- consumption bytes=`888`, SHA256=`52CE7F608809602658FAC025425BBBC6AB175586101898FB0AEA3C852C950FB8`

---

## 31. Phase32 compatibility analysis

A11 requires no modification to the Phase32 public API.

A11:

- consumes the exact Phase32 result snapshot;
- returns the exact Phase32 authority-reported result type from `check_and_consume`;
- does not invoke Phase32 authority twice;
- preserves Phase31/32 claim/replay identities while strengthening only the downstream concrete SQLite persistence layer;
- does not reinterpret Phase32 reported-consumed evidence as provider permission;
- uses Phase32-compatible INDETERMINATE rather than inventing a new Phase32 decision for in-transaction drift, corrupt existing rows, or post-BEGIN conversion-surface failure;
- does not change Phase29/30/31/32 source/test contracts;
- does not alter package exports;
- does not alter dependencies;
- does not grant transport permission;
- does not grant production authority;
- does not independently verify external approval/conformance provenance;
- consumes the exact Phase32 `evidence_fingerprint` field as the sole `source_evidence_fingerprint` value and does not modify the Phase32 fingerprint contract;
- treats Python sqlite3 row/text/adaptation/conversion behavior strictly as a downstream Phase33 concrete-backend execution boundary.

A11's exact-schema, converter-neutral-read, deterministic-literal-encoding/no-authoritative-DBAPI-binding, single-read-snapshot, initializer-error, and connection-exclusivity safeguards are downstream local persistence safeguards only. They do not add fields to Phase32 public dataclasses or change Phase32 decisions.

Therefore static contract analysis finds no intended Phase32 responsibility collision. Final compatibility still requires a separately approved read-only actual preflight against the current repository and approved `.venv`.

---

## 32. Candidate acceptance gates

A future official Phase33 contract cannot be considered complete until separately approved gates include at minimum the following exact `1..60` sequence:

1. DRAFT-A11 Final Contract Review / Approval Decision
2. exact README registration
3. frozen contract identity creation
4. separate implementation approval
5. exact two-path implementation
6. targeted tests `217/217` if this count survives final approval
7. full regression `1285/1285` if this count survives final approval
8. failures=0
9. errors=0
10. unapproved skipped=0
11. exact Python/sqlite runtime confirmation
12. exact caller connection surface confirmation including exact `sqlite3.Connection`, open/file-backed `main`, `autocommit=True`, `isolation_level=None`, `busy_timeout=0`, `row_factory is None`, `text_factory is str`, and clean transaction entry state
13. no authoritative DB-API placeholder binding for persisted/lookup Phase33 `str`/`int` values
14. deterministic UTF-8-to-BLOB SQL literal encoding and signed-64 canonical integer literal encoding verified
15. converter-neutral authoritative BLOB/INTEGER read contract verified
16. caller-exclusive-use and process adapter/converter registry-stability contracts preserved, without treating registry stability as proof of adapter-callable output determinism
17. exact WAL/FULL durability profile confirmation
18. exact `main` schema qualification
19. exact `table_list` / `table_xinfo` / foreign-key structural verification plus exact accepted six-name autoindex set, exact SQL single-quote-doubling for dynamic `main.index_xinfo(...)` arguments, and exact `index_list` / `index_xinfo` key-set semantics
20. exact frozen stored-DDL identity for both Phase33 tables
21. STRICT required; WITHOUT ROWID/FOREIGN KEY/unapproved CHECK/table options absent; authority identity uses BLOB byte semantics independent of text collations
22. exact metadata verification through converter-neutral BLOB/INTEGER reads
23. exact ledger schema reference binding
24. exact schema/transaction/durability profile binding in deterministic references/fingerprints
25. cross-backend-instance persistent replay protection
26. exact claim/replay UNIQUE semantics
27. deterministic domain-separated references
28. exact 16-key durable-record fingerprint
29. exact 19-key verification fingerprint
30. verification snapshot backend identity always binds exact current authority config backend identity
31. `source_evidence_fingerprint` binds exact Phase32 `source_snapshot.evidence_fingerprint` after Phase32 recomputation/match
32. successful `durable_record_fingerprint` binds exact self-integrity-validated durable record field
33. every verification INDETERMINATE uses null durable-record fingerprint and current-authority backend identity
34. authoritative schema/profile revalidation inside `BEGIN IMMEDIATE` before claim/replay lookup
35. corrupt existing claim/replay rows fail closed as INDETERMINATE
36. verifier uses one explicit read transaction and cannot observe a mixed snapshot
37. dual UNIQUE-reference cardinality and same-record equality follow section 20 exactly
38. durable-row fingerprint/self-integrity precedence occurs before current backend/source semantic interpretation
39. claim conflict requires current claim-fingerprint consistency while preserving backend/provenance independence
40. replay conflict remains blocked for a self-consistent historical replay row even when historical claim-specific fields differ
41. initializer runtime errors preserve and re-raise original exceptions after at most one cleanup rollback
42. no second authority consumption invocation
43. no automatic retry
44. fail-closed BEGIN/COMMIT/ROLLBACK exception handling
45. provider-send eligibility=False
46. production authority use=False
47. approval provenance=False
48. conformance provenance=False
49. protected Phase29-32 paths unchanged
50. dependency files unchanged
51. package re-export unchanged
52. no provider/account/order action
53. approved Git paths only
54. separate commit approval
55. separate Closure/Current Phase alignment
56. exact STRICT/BLOB storage for both Phase33 tables
57. no authority-critical reliance on caller-overridable named SQL scalar functions such as `typeof`
58. stateful adapter counterexamples cannot alter authoritative SQL values because those values are not DB-API parameter-bound
59. post-BEGIN encoding/integrity failure uses exact `AUTHORITY_REPORTED_INDETERMINATE`
60. Candidate acceptance-gate numbering itself is exact, unique, and contiguous `1..60`

---

## 33. Candidate boundary after eventual Phase33 completion

Only if all later official gates pass:

- `CONCRETE_SQLITE_AUTHORITY_IDENTITY_VERIFIED=YES_DEMO_LOCAL_IDENTITY_ONLY`
- `SQLITE_CONNECTION_SURFACE_VERIFIED=YES_CURRENT_CONNECTION_SURFACE_ONLY`
- `SQLITE_DBAPI_CONVERSION_SURFACE_VERIFIED=YES_CURRENT_INVOCATION_ONLY`
  - meaning is limited to exact `row_factory is None`, `text_factory is str`, and converter-neutral authoritative BLOB/INTEGER read boundaries; it does not prove Python adapter output determinism or historical registry state
- `CONVERTER_NEUTRAL_LEDGER_READS_VERIFIED=YES_LOCAL_READ_PATH_ONLY`
- `DETERMINISTIC_SQL_LITERAL_ENCODING_VERIFIED=YES_CURRENT_INVOCATION_VALUES_ONLY`
- `DECLARED_TRANSACTION_PROFILE_BOUND=YES_RECORD_REFERENCE_BINDING_ONLY`
- `SQLITE_DURABILITY_PROFILE_VERIFIED=YES_WAL_FULL_CONTRACT_PROFILE_ONLY`
- `SINGLE_VERIFIER_READ_SNAPSHOT_VERIFIED=YES_LOCAL_VERIFIER_INVOCATION_ONLY`
- `LOCAL_DURABLE_CONSUMPTION_RECORD_VERIFIED=YES`
- `VERIFICATION_BACKEND_REFERENCE_BOUND_TO_CURRENT_AUTHORITY_CONFIG=YES_LOCAL_EVIDENCE_IDENTITY_ONLY`
- `VERIFICATION_FINGERPRINT_VALUE_PROVENANCE_VERIFIED=YES_EXACT_LOCAL_MAPPING_ONLY`
- `AUTHORITY_APPROVAL_PROVENANCE_VERIFIED=NO`
- `AUTHORITY_CONFORMANCE_PROVENANCE_VERIFIED=NO`
- `PROVIDER_SEND_ELIGIBILITY_AUTHORIZED=NO`
- `PRODUCTION_AUTHORITY_USE_AUTHORIZED=NO`

A11 does not claim historical physical durability, historical `BEGIN IMMEDIATE`/COMMIT/ROLLBACK execution proof, historical process-global adapter/converter registry state, external authority trust, or provider-send permission.

A later separate contract is mandatory before provider send eligibility can even be considered.

---

## 34. Official governance

The status below is normative when this exact payload is present in `README.md`:

- `PHASE33_DRAFT_A11_FINAL_CONTRACT_REVIEW=PASS`
- `DRAFT_A11_OFFICIAL_CONTRACT_APPROVAL=PASS`
- `DRAFT_A11_APPROVED_AS_OFFICIAL=YES`
- `DRAFT_A11_CONTENT_REVISION_REQUIRED=NO`
- `DRAFT_A12_REQUIRED=NO`
- `PHASE33_OFFICIAL_CONTRACT_REGISTERED_IN_README=YES`
- `IMPLEMENTATION_AUTHORIZED=NO`
- `CURRENT_PHASE=PHASE32`
- `PROVIDER_SEND_ELIGIBILITY_AUTHORIZED=NO`
- `PRODUCTION_AUTHORITY_USE_AUTHORIZED=NO`
- `EXTERNAL_APPROVAL_PROVENANCE_VERIFIED=NO`
- `EXTERNAL_CONFORMANCE_PROVENANCE_VERIFIED=NO`

Exact README registration does not authorize Phase33 implementation, source/test mutation, dependency or environment mutation, Git mutation, credential/token/provider/account/order action, provider transport, production authority use, or Current Phase alignment.

Phase33 implementation remains a separately approved step after exact README registration.

## Phase 34 — demo Kiwoom Cash BUY-Order Provider Send Eligibility Candidate Snapshot 기반선 v1.0

Status: CLOSED
Implementation: COMPLETE
Current Phase: PHASE34
Provider Send Eligibility: NOT AUTHORIZED
Transport: NOT AUTHORIZED
Production Authority Use: NOT AUTHORIZED

Source Contract Artifact: `Phase34_New_Contract_DRAFT_A6_Independent_Revision_FINAL_REVIEW_PREPARATION_DESIGN_ONLY_NOT_APPROVED.txt`
Source Contract Bytes: `87987`
Source Contract SHA256: `2A6DE6DB1C8F84C5F62DBEDEA01CBC1CC2BAB22FC6A11B263EE27DE01BD6BB9E`
Preserved Approved DRAFT-A6 Full Source CRLF Bytes: `89292`
Preserved Approved DRAFT-A6 Full Source CRLF SHA256: `46EF353E6CDBF54392ACC51CA66B1A037AEDA72C74631A6C659212BCDE7A311B`

### Approved-source preservation and status-supersession rule

The complete approved DRAFT-A6 source payload below is preserved text-for-text; the only representation change is canonical line-ending conversion from source LF to README CRLF. No DRAFT-A6 source line is deleted, renumbered, rewritten, or normalized.

DRAFT-stage approval/authorization/governance statements inside that preserved source payload are historical provenance describing the source artifact before its separate Final Contract Review completed. They do not override the current official registration status. For current Phase34 approval/registration governance, `## 24. Official governance` below is the sole normative status authority. All technical contracts, algorithms, invariants, field/key cardinalities, validation precedence, acceptance criteria, safety boundaries, recovery rules, and future-boundary semantics in the preserved DRAFT-A6 source remain normative exactly as approved.

This status-supersession rule changes governance state only; it does not alter any technical requirement in the preserved DRAFT-A6 source.

`FROZEN_CONTRACT_IDENTITY_SHA256=425ABC17469812C772F6041C90B0BF76F445256E52547B9CC426FD5B23231026`

### Frozen contract identity rule

`FROZEN_CONTRACT_IDENTITY_SHA256` is the SHA-256 uppercase hex of this exact CRLF UTF-8 payload after removing exactly the marker line and its immediately following blank CRLF.

The complete payload raw SHA-256 is tracked separately from the frozen contract identity.

### Preserved approved DRAFT-A6 source payload

Phase34 — New Contract DRAFT-A6 Independent Revision / Final Contract Review Preparation
DESIGN_ONLY_NOT_APPROVED

PROPOSED CONTRACT NAME
Phase 34 — demo Kiwoom Cash BUY-Order Provider Send Eligibility Candidate Snapshot 기반선 v1.0

STATUS
- PHASE34_DRAFT_A6=DESIGN_ONLY_NOT_APPROVED
- PHASE34_DRAFT_A6_APPROVED_AS_OFFICIAL=NO
- PHASE34_DRAFT_A6_FINAL_CONTRACT_REVIEW=NOT_PERFORMED
- README_REGISTRATION_AUTHORIZED=NO
- IMPLEMENTATION_AUTHORIZED=NO
- CURRENT_PHASE=PHASE33
- PROVIDER_SEND_ELIGIBILITY_AUTHORIZED=NO
- TRANSPORT_ALLOWED=NO
- ACTUAL_ORDER_SUBMISSION_AUTHORIZED=NO
- PRODUCTION_AUTHORITY_USE_AUTHORIZED=NO
- GIT_ADD_COMMIT_PUSH_AUTHORIZED=NO

1. Revision basis / source-of-truth identity

DRAFT-A6 is an independent revision of exact DRAFT-A5 only.
No prior DRAFT-A6 artifact, prior-request search/review/analysis/validation count, or partial A6 judgment is reused.

Exact DRAFT-A5 source-of-truth identity supplied and independently byte-verified for this revision:
- filename=Phase34_New_Contract_DRAFT_A5_Independent_Revision_FINAL_REVIEW_PREPARATION_DESIGN_ONLY_NOT_APPROVED.txt
- bytes=86461
- SHA256=46CA4D006904BC810F1435D631E3D79E52F1D29490C9C1B58C75BF4186096F98
- encoding=UTF-8 without BOM
- EOL=LF-only

DRAFT-A5 official Final Contract Review disposition used as governance input:
- PHASE34_DRAFT_A5_FINAL_CONTRACT_REVIEW=STOP_HOLD
- PHASE34_DRAFT_A5_APPROVED_AS_OFFICIAL=NO
- DRAFT_A5_CONTENT_REVISION_REQUIRED=YES
- DRAFT_A6_REQUIRED=YES
- README_REGISTRATION_AUTHORIZED=NO
- IMPLEMENTATION_AUTHORIZED=NO
- CURRENT_PHASE=PHASE33

A5 Final Contract Review defect set carried into A6:
- A5_FCR_01_PHASE33_LEDGER_SCHEMA_REFERENCE_EXACT_RUNTIME_TYPE_GAP=VALID_DEFECT
- A5_FCR_02_PHASE33_VERIFICATION_FINGERPRINT_LEDGER_SCHEMA_VALUE_SOURCE_DRIFT=VALID_DEFECT
- A5_FCR_03_LEDGER_SCHEMA_ACCEPTANCE_COVERAGE_GAP=VALID_DEFECT

All earlier still-valid corrections remain preserved, including:
- A2_FCR_01_RETRACTED=YES;
- A2_FCR_01_OBJECT_GRAPH_DEFECT=NO;
- A2_EXISTING_PHASE30_REQUEST_PATH_PRESERVED=YES;
- A3_FCR_01_STALE_IMPLEMENTATION_APPROVAL_TARGET=REVISED_IN_A4_AND_PRESERVED_IN_A6;
- A3_FCR_02_DRAFT_STATUS_EXACT_VALUE_CONFLICT=REVISED_IN_A4_AND_PRESERVED_IN_A6;
- A3_FCR_03_DURABLE_RECORD_SELF_INTEGRITY_SOURCE_BINDING_GAP=REVISED_IN_A4_AND_PRESERVED_IN_A6;
- A3_FCR_04_SAFETY_STATE_PUBLIC_ERROR_REACHABILITY_GAP=REVISED_IN_A4_AND_PRESERVED_IN_A6.

FCR-01 object-graph correction remains frozen and is not reopened:
- local variable `source_snapshot` is the Phase33 verification snapshot;
- `phase32_snapshot = source_snapshot.source_snapshot`;
- `phase31_snapshot = phase32_snapshot.source_snapshot`;
- `request_snapshot = phase31_snapshot.source_snapshot`;
- equivalent direct Phase30 expression is exactly `source_snapshot.source_snapshot.source_snapshot.source_snapshot`;
- the leading token is the Phase33 local-variable name and there are exactly three `.source_snapshot` attribute traversals;
- `source_snapshot.source_snapshot.source_snapshot` stops at Phase31 and is never treated as Phase30.

Current official repository baseline carried into this DRAFT-A6 review preparation:
- Project=C:\Users\HP\Projects\kiwoom-trading-system
- Branch=main
- HEAD=4e9445fe85170461ecce0341e5b5862cb382b51d
- Parent=709b842b384835a0ae7c8d5a4b72c8a024df36ed
- Tree=e5acae8ad6d07f7bbcb24db91a5f240871d77931
- Commit subject=docs: align current phase with phase 33
- Repository=CLEAN as inherited evidence only; current-request PC Git state requires a separate Actual Rerun
- Current Phase=PHASE33
- Full Regression inherited baseline=1285/1285; not reused as a current-request Actual Rerun

This document is a candidate contract only. It is not an official Phase34 contract and does not authorize README registration, implementation, Git mutation, provider transport, credential/account access, or order action.

2. DRAFT-A5 Final Contract Review / A6 closure map

DRAFT-A6 preserves the A5 contract except for the exact `ledger_schema_reference` runtime-type/value-source and acceptance-coverage gaps found by the DRAFT-A5 Final Contract Review.

A5-FCR-01 — Phase33 `ledger_schema_reference` exact runtime-type gap
- CLOSED IN A6 CANDIDATE DESIGN by sections 9.1 and 9.3, section 15 step 7, and AC-125/AC-128.
- On both SUCCESS and Phase33 INDETERMINATE branches, `source_snapshot.ledger_schema_reference` must first satisfy `type(value) is str`.
- Only after the exact runtime-type gate passes may the field be compared to the exact literal `kiwoom-watchlist-order-authorization-durable-ledger-v1`.
- A Python `str` subclass is rejected even when equality to the literal is True and JSON serialization is byte-identical to the literal.
- Violation maps to existing step-7 `PHASE33_STATE_INVARIANT_INVALID`; no new public error code is introduced.

A5-FCR-02 — Phase33 verification-fingerprint `ledger_schema_reference` value-source drift
- CLOSED IN A6 CANDIDATE DESIGN by section 9.1 and AC-127.
- The Phase33 verification-fingerprint envelope source for key `ledger_schema_reference` is frozen to the exact literal constant `"kiwoom-watchlist-order-authorization-durable-ledger-v1"`, matching the official Phase33 contract.
- The snapshot field is validated separately by section 9.3 but is never used as the fingerprint envelope's source value for this key.

A5-FCR-03 — acceptance coverage gap
- CLOSED IN A6 CANDIDATE DESIGN by AC-125..AC-128.
- The acceptance set explicitly tests non-exact-str `ledger_schema_reference`, wrong exact-str literal, literal-source fingerprint mapping, and the str-subclass/equal-hash edge.

A4-FCR-01 and A4-FCR-02 remain closed exactly as in A5. A5 strict-UTF8 Phase33-verifier source-producibility hardening remains preserved for SUCCESS and INDETERMINATE branches.

No new public validation error code is required. The exact 24-code/24-step precedence is preserved.

No closure statement in this section is an approval decision. It means only that the A6 candidate text contains a proposed correction. A separate Final Contract Review / Approval Decision is mandatory.

3. Necessity / unresolved contract gap

The unresolved responsibility after Phase33 remains provider-send eligibility governance, not provider transmission.

Phase33 proves a local durable authorization-consumption record and local bindings, while successful Phase33 verification still requires:
- authority_approval_provenance_verified == False
- authority_conformance_provenance_verified == False
- provider_send_eligibility_authorized == False
- production_authority_use_authorized == False
- reconciliation_required == False

Phase33 does not grant:
- transport_allowed=True
- post_permitted=True
- send_permitted=True
- provider network permission
- actual order-submission permission

Phase34 DRAFT-A6 therefore remains a pure-local bridge. It can only materialize an immutable provider-send eligibility CANDIDATE snapshot after independently revalidating the already existing local object graph. It cannot create provider-send authority.

4. Exact scope

Phase34 DRAFT-A6 candidate exact scope:
- environment=`demo` only
- side=`BUY` only
- exchange=`KRX` only
- cash order only
- exact Phase33 `WatchlistOrderAuthorizationDurableVerificationSnapshot` upstream
- exact preservation of embedded Phase32 -> Phase31 -> Phase30 object identity graph
- exact extraction of embedded Phase30 `WatchlistOrderSendRequestSnapshot`; no copy/remap/rebuild
- independent pure-local validation of Phase33 success durable-record exact 13-field primitives/format
- independent recomputation/match of the exact Phase33 16-key durable-record `record_fingerprint`
- independent recomputation/match of Phase33 deterministic historical `authority_result_reference` and `consumption_reference`
- independent binding of the Phase33 durable record to validated Phase33/Phase32/Phase31 source semantics
- independent recomputation/match of Phase33 `verification_fingerprint` only after applicable durable-record gates
- independent recomputation/match of Phase32 `evidence_fingerprint`
- independent exact Phase31 claim/replay revalidation
- independent recomputation/match of Phase31 `claim_fingerprint`
- independent recomputation/match of Phase30 `materialization_fingerprint`
- exact static provider-request contract validation for `kt10000`
- deterministic frozen Phase34 eligibility-candidate snapshot
- deterministic Phase34 eligibility fingerprint
- no SQLite connection access
- no durable-ledger read/write
- no Phase33 verifier rerun or refresh
- no second authority consumption attempt
- no authority adapter/controller invocation
- no credential/token/.env access
- no account access
- no provider/client call
- no external network
- no actual `kt10000` POST
- no provider response parsing
- no order-number handling
- no retry/retransmission
- no broker-side reconciliation action or mutation
- no production authority permission
- no provider-send authorization

Out of scope:
- real environment
- SELL
- NXT/SOR
- credit
- amend/cancel
- token acquisition
- account selection
- account/buying-power refresh
- provider transport
- provider response
- order number
- fill/reject handling
- broker-side reconciliation mutation
- external authority approval provenance verification
- external authority conformance provenance verification
- production authority use
- automatic retry
- package-level re-export
- dependency changes

5. Safety invariants

The following are exact semantic invariants:

`LOCAL_DURABLE_CONSUMPTION_RECORD_VERIFIED != PROVIDER_SEND_ELIGIBILITY_AUTHORIZED`
`PROVIDER_SEND_ELIGIBILITY_CANDIDATE_READY != PROVIDER_SEND_ELIGIBILITY_AUTHORIZED`
`PROVIDER_SEND_ELIGIBILITY_CANDIDATE_READY != TRANSPORT_ALLOWED`
`PROVIDER_SEND_ELIGIBILITY_CANDIDATE_READY != POST_PERMITTED`
`PROVIDER_SEND_ELIGIBILITY_CANDIDATE_READY != ORDER_SUBMITTED`
`PROVIDER_SEND_ELIGIBILITY_CANDIDATE_READY != ORDER_ACCEPTED`

For every returned Phase34 snapshot:
- `authority_approval_provenance_verified is False`
- `authority_conformance_provenance_verified is False`
- `provider_send_eligibility_authorized is False`
- `production_authority_use_authorized is False`
- `transport_allowed is False`
- `credential_accessed is False`
- `network_performed is False`
- `account_accessed is False`
- `order_submitted is False`
- `automatic_retry_permitted is False`

Phase34 must never:
- convert a Phase33 INDETERMINATE into READY or AUTHORIZED;
- execute reconciliation merely because `reconciliation_required=True`;
- perform a second authorization-consumption attempt;
- refresh or rerun Phase33;
- access credentials/token/account/provider/network state;
- call `kt10000`;
- consume or interpret a provider response/order number.

6. Source of truth hierarchy

Candidate source-of-truth hierarchy:

1. current official repository README contracts for Phase27 through Phase33;
2. current official HEAD Phase30/31/32/33 implementation/test identities;
3. exact Phase33 public contract:
   - `WatchlistOrderAuthorizationDurableVerificationSnapshot`
   - `verify_demo_watchlist_order_authorization_durable_consumption`
4. exact Phase32 evidence contract embedded by Phase33:
   - `WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot`
   - canonical `evidence_fingerprint`
5. exact Phase31 claim contract embedded by Phase32:
   - `KiwoomOrderAuthorizationConsumptionClaimContext`
   - `WatchlistOrderAuthorizationConsumptionClaimSnapshot`
   - canonical `claim_fingerprint`
6. exact Phase30 provider request contract embedded by Phase31:
   - `WatchlistOrderSendRequestSnapshot`
   - canonical `materialization_fingerprint`
   - api_id=`kt10000`
   - http_method=`POST`
   - api_path=`/api/dostk/ordr`
   - body exact key set: `dmst_stex_tp`, `stk_cd`, `ord_qty`, `ord_uv`, `trde_tp`, `cond_uv`
7. current official Kiwoom REST API documentation/examples only as static corroboration of the already-materialized request shape; not as runtime permission;
8. Python 3.13 canonical JSON behavior only where the frozen fingerprint algorithms use it;
9. no new external-governance trust source is invented by Phase34.

Historical design drafts may explain intent but are not authority over current official Phase30-33 contracts.

7. Future implementation mutation allowlist candidate

Only after a separate Final Contract Review explicitly approves this exact DRAFT-A6 identity as the Phase34 official contract candidate, and implementation is separately approved after that review, the future implementation mutation allowlist candidate is exact two paths:

- `src/kiwoom_trading_system/brokers/kiwoom/rest/watchlist_order_provider_send_eligibility.py`
- `tests/test_watchlist_order_provider_send_eligibility.py`

A STOP-HOLD DRAFT-A2, DRAFT-A3, DRAFT-A4, or DRAFT-A5 artifact is never an implementation authorization prerequisite or substitute for DRAFT-A6 approval.

Explicitly excluded:
- `README.md`
- `src/kiwoom_trading_system/brokers/kiwoom/rest/__init__.py`
- every Phase27/28/29/30/31/32/33 source/test
- `pyproject.toml`
- `uv.lock`
- `.venv`
- `.env`
- credential/token files
- account/provider configuration files
- Git index/commit/remote

This DRAFT-A6 preparation authorizes no repository path mutation.

8. Candidate public API and exact enum member-name/value pairs

Candidate module-level public API is exact 5 symbols:

1. `WatchlistOrderProviderSendEligibilityError`
2. `KiwoomOrderProviderSendEligibilityDecision`
3. `KiwoomOrderProviderSendEligibilityIndeterminateReason`
4. `WatchlistOrderProviderSendEligibilityCandidateSnapshot`
5. `build_demo_watchlist_order_provider_send_eligibility_candidate_snapshot`

`WatchlistOrderProviderSendEligibilityError` inherits `RuntimeError`.
No package-level re-export from `src/kiwoom_trading_system/brokers/kiwoom/rest/__init__.py`.

Exact synchronous builder signature:

`build_demo_watchlist_order_provider_send_eligibility_candidate_snapshot(`
`    source_snapshot: WatchlistOrderAuthorizationDurableVerificationSnapshot,`
`) -> WatchlistOrderProviderSendEligibilityCandidateSnapshot`

No defaults. No context object. No authority object. No sqlite3.Connection. No client/provider/token/account argument.

8.1 Decision enum

`KiwoomOrderProviderSendEligibilityDecision` is exactly `class KiwoomOrderProviderSendEligibilityDecision(str, Enum)`.
Exact member order, member names, and values are:

1. member name `PROVIDER_SEND_ELIGIBILITY_CANDIDATE_READY`
   - value `"PROVIDER_SEND_ELIGIBILITY_CANDIDATE_READY"`
2. member name `INDETERMINATE`
   - value `"INDETERMINATE"`

No aliases. No additional members.

8.2 Indeterminate-reason enum

`KiwoomOrderProviderSendEligibilityIndeterminateReason` is exactly `class KiwoomOrderProviderSendEligibilityIndeterminateReason(str, Enum)`.
Exact member order, member name, and value are:

1. member name `SOURCE_DURABLE_VERIFICATION_INDETERMINATE`
   - value `"SOURCE_DURABLE_VERIFICATION_INDETERMINATE"`

No aliases. No additional members.

Malformed or contract-inconsistent input is not represented as a Phase34 INDETERMINATE business result. It raises `WatchlistOrderProviderSendEligibilityError` before a snapshot is returned.

9. Exact Phase33 upstream structural prerequisites, durable-record revalidation, and verification-fingerprint revalidation

`source_snapshot` must be exact type `WatchlistOrderAuthorizationDurableVerificationSnapshot`.

A6 separates SAFE PREREQUISITE VALIDATION, DURABLE-RECORD INTEGRITY/BINDING, and FINGERPRINT RECOMPUTATION. No fingerprint envelope is built until every object/type/state/primitive needed by that envelope has passed the earlier exact validation stages in sections 15 and 16.

Exact object-graph locals are frozen:
`phase32_snapshot = source_snapshot.source_snapshot`
`phase31_snapshot = phase32_snapshot.source_snapshot`
`request_snapshot = phase31_snapshot.source_snapshot`

These assignments are conceptually performed only after the immediately preceding exact-type gate has succeeded. An implementation may factor helpers but must preserve the same externally observable first-error precedence and must not dereference a deeper object before its exact parent/source type is validated.

9.1 Exact Phase33 verification-fingerprint envelope

Exact 19 keys:
1. `domain`
2. `source_evidence_fingerprint`
3. `durable_record_fingerprint`
4. `backend_instance_reference`
5. `ledger_schema_reference`
6. `verification_decision`
7. `indeterminate_reason`
8. `concrete_sqlite_authority_identity_verified`
9. `ledger_schema_verified`
10. `sqlite_connection_surface_verified`
11. `sqlite_durability_profile_verified`
12. `durable_record_present`
13. `exact_binding_verified`
14. `durable_consumption_record_verified`
15. `authority_approval_provenance_verified`
16. `authority_conformance_provenance_verified`
17. `provider_send_eligibility_authorized`
18. `production_authority_use_authorized`
19. `reconciliation_required`

Exact mapping is used only after the section 15 prerequisite sequence has completed through the applicable durable-record gates:
- `domain = "phase33-local-durable-verification-v1"`
- `source_evidence_fingerprint = phase32_snapshot.evidence_fingerprint`
- success only: `durable_record_fingerprint = source_snapshot.durable_record.record_fingerprint` after sections 9.4-9.7 pass
- Phase33 INDETERMINATE only: `durable_record_fingerprint = None`
- `backend_instance_reference = source_snapshot.backend_instance_reference`
- `ledger_schema_reference = "kiwoom-watchlist-order-authorization-durable-ledger-v1"` literal constant; the separately validated snapshot field is not the envelope value source
- remaining decision/reason/bool values = exact same-named Phase33 snapshot fields

Canonicalization is exact:
`json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)`
then UTF-8 encode and `hashlib.sha256(...).hexdigest()`.

The recomputed value must equal exact `source_snapshot.verification_fingerprint`, a lowercase 64-hex string.
Phase34 does not substitute a complete-object hash, object id, or differently named fingerprint.

9.2 Exact Phase33 decision prerequisite

Before decision-dependent state validation or fingerprint mapping:
- `verification_decision` must be exact `str`;
- exact allowed values are only `LOCAL_DURABLE_CONSUMPTION_RECORD_VERIFIED` and `INDETERMINATE`.

Any other type/value raises exact `PHASE33_DECISION_INVALID` before any use of durable-record fields and before Phase33 fingerprint recomputation.

9.3 Exact Phase33 branch-state invariants

For `verification_decision == "LOCAL_DURABLE_CONSUMPTION_RECORD_VERIFIED"`, before any durable-record field is trusted:
- `indeterminate_reason is None`;
- `durable_record` is exact `KiwoomOrderAuthorizationDurableLedgerRecord`;
- `backend_instance_reference` exact str satisfying the official Phase33 reference contract and strict UTF-8 encodability;
- `type(ledger_schema_reference) is str` (subclasses rejected);
- `ledger_schema_reference == "kiwoom-watchlist-order-authorization-durable-ledger-v1"`;
- `verification_fingerprint` exact lowercase 64-hex str;
- every Phase33 bool below is exact `bool`, not integer 0/1;
- `concrete_sqlite_authority_identity_verified is True`;
- `ledger_schema_verified is True`;
- `sqlite_connection_surface_verified is True`;
- `sqlite_durability_profile_verified is True`;
- `durable_record_present is True`;
- `exact_binding_verified is True`;
- `durable_consumption_record_verified is True`;
- `authority_approval_provenance_verified is False`;
- `authority_conformance_provenance_verified is False`;
- `provider_send_eligibility_authorized is False`;
- `production_authority_use_authorized is False`;
- `reconciliation_required is False`.

For `verification_decision == "INDETERMINATE"`:
- `indeterminate_reason` exact str and one of the exact official Phase33 8 reasons: `LEDGER_READ_ERROR`, `LEDGER_SCHEMA_MISMATCH`, `SQLITE_DURABILITY_PROFILE_MISMATCH`, `BACKEND_IDENTITY_MISMATCH`, `LEDGER_RECORD_NOT_FOUND`, `LEDGER_RECORD_BINDING_MISMATCH`, `LEDGER_RECORD_FINGERPRINT_MISMATCH`, `LEDGER_STATE_AMBIGUOUS`;
- `durable_record is None`;
- `backend_instance_reference` exact str satisfying the official Phase33 reference contract and strict UTF-8 encodability;
- `type(ledger_schema_reference) is str` (subclasses rejected);
- `ledger_schema_reference == "kiwoom-watchlist-order-authorization-durable-ledger-v1"`;
- `verification_fingerprint` exact lowercase 64-hex str;
- every Phase33 bool below is exact `bool`, not integer 0/1;
- every local verification success flag is exact False: `concrete_sqlite_authority_identity_verified`, `ledger_schema_verified`, `sqlite_connection_surface_verified`, `sqlite_durability_profile_verified`, `durable_record_present`, `exact_binding_verified`, `durable_consumption_record_verified`;
- `authority_approval_provenance_verified is False`;
- `authority_conformance_provenance_verified is False`;
- `provider_send_eligibility_authorized is False`;
- `production_authority_use_authorized is False`;
- `reconciliation_required is True`.

The exact `ledger_schema_reference` runtime-type gate always precedes the literal equality check and always precedes Phase33 verification-fingerprint recomputation. Equality, JSON serialization, or hash equality never substitutes for `type(value) is str`.
Any violation in this subsection raises exact `PHASE33_STATE_INVARIANT_INVALID`.
INDETERMINATE skips sections 9.4-9.7 durable-record gates because its exact durable-record value is None.

9.4 Exact Phase33 durable-record 13-field primitive/shape validation — success only

The exact success `durable_record` has the official 13 fields and no field is trusted merely because the outer dataclass type is exact.

Exact local primitive rules:
1. `backend_instance_reference`: exact `str`, valid official Phase33 reference contract;
2. `authorization_authority_reference`: exact `str`; first preserve the original Phase31 authorization-authority opaque-reference validity already required by section 11, and additionally require the exact Phase33 durable-authority config reference contract: length `1..128`, non-empty, `value == value.strip()`, whitespace-only prohibited, U+0000..U+001F prohibited, U+007F prohibited, strict UTF-8 encodable, with no trim, case-fold, Unicode normalization, or replacement; this value must later exactly equal the already validated Phase31 authorization authority reference in section 9.7;
3. `authorization_evidence_snapshot_id`: exact `str`, valid original Phase31 evidence-snapshot binding-reference contract;
4. `submission_attempt_reference`: exact `str`, valid original Phase31 submission-attempt binding-reference contract;
5. `send_authorization_reference`: exact `str`, valid original Phase31 send-authorization opaque-reference contract;
6. `claim_fingerprint`: exact lowercase 64-hex `str`;
7. `authority_approval_reference`: exact `str`, valid Phase32 asserted-authority reference contract;
8. `authority_conformance_reference`: exact `str`, valid Phase32 asserted-authority reference contract;
9. `authority_result_reference`: exact `str` matching `phase33-result-[0-9a-f]{64}`;
10. `consumption_reference`: exact `str` matching `phase33-consume-[0-9a-f]{64}`;
11. `sqlite_journal_mode`: exact `str` equal `"wal"`;
12. `sqlite_synchronous_level`: exact `int` equal `2`, with `bool` rejected;
13. `record_fingerprint`: exact lowercase 64-hex `str`.

In addition, every non-fixed arbitrary reference carried by the success durable record and needed by the Phase33 transaction/storage contract — fields 1 through 5 and fields 7 through 8 — must be strictly UTF-8 encodable with no surrogate-pass, replacement, normalization, or lossy fallback. This preserves Phase33's pre-transaction requirement that every authority-critical string used for deterministic BLOB SQL literal encoding be valid exact UTF-8. A Unicode encoding failure is a contract-validation failure at this same step, not a JSON/fingerprint exception.

Any failure raises exact `PHASE33_DURABLE_RECORD_STRUCTURE_INVALID` before record fingerprint, deterministic-reference, source-binding, or Phase33 verification-fingerprint recomputation.

9.5 Exact 16-key durable-record fingerprint recomputation — success only

Exact canonical envelope keys and value sources are:
1. `domain = "phase33-durable-record-v1"`
2. `schema_id = "kiwoom-watchlist-order-authorization-durable-ledger-v1"`
3. `transaction_profile_id = "sqlite-autocommit-true-isolation-none-busy-zero-begin-immediate-v1"`
4. `durability_profile_id = "sqlite-main-wal-synchronous-full-v1"`
5. `backend_instance_reference = durable_record.backend_instance_reference`
6. `authorization_authority_reference = durable_record.authorization_authority_reference`
7. `authorization_evidence_snapshot_id = durable_record.authorization_evidence_snapshot_id`
8. `submission_attempt_reference = durable_record.submission_attempt_reference`
9. `send_authorization_reference = durable_record.send_authorization_reference`
10. `claim_fingerprint = durable_record.claim_fingerprint`
11. `authority_approval_reference = durable_record.authority_approval_reference`
12. `authority_conformance_reference = durable_record.authority_conformance_reference`
13. `authority_result_reference = durable_record.authority_result_reference`
14. `consumption_reference = durable_record.consumption_reference`
15. `sqlite_journal_mode = durable_record.sqlite_journal_mode`
16. `sqlite_synchronous_level = durable_record.sqlite_synchronous_level`

Canonical JSON is exactly `json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)`, UTF-8 encoded, then lowercase SHA-256 hex.
The recomputed value must exactly equal `durable_record.record_fingerprint`; mismatch raises exact `PHASE33_DURABLE_RECORD_FINGERPRINT_INVALID`.

9.6 Exact Phase33 deterministic historical-reference self-binding — success only

Construct historical claim identity solely from the already structure-valid durable record in exact order:
`durable_claim_identity = (durable_record.authorization_authority_reference, durable_record.authorization_evidence_snapshot_id, durable_record.submission_attempt_reference, durable_record.send_authorization_reference)`

Construct historical replay guard solely from the durable record:
`durable_replay_guard = (durable_record.authorization_authority_reference, durable_record.send_authorization_reference)`

Expected authority-result reference is `"phase33-result-" + sha256(canonical_json).hexdigest()` over exact 10-key envelope:
- `domain="phase33-authority-result-v1"`
- `schema_id="kiwoom-watchlist-order-authorization-durable-ledger-v1"`
- `transaction_profile_id="sqlite-autocommit-true-isolation-none-busy-zero-begin-immediate-v1"`
- `durability_profile_id="sqlite-main-wal-synchronous-full-v1"`
- `backend_instance_reference=durable_record.backend_instance_reference`
- `authorization_claim_identity=durable_claim_identity`
- `authorization_replay_guard=durable_replay_guard`
- `claim_fingerprint=durable_record.claim_fingerprint`
- `authority_approval_reference=durable_record.authority_approval_reference`
- `authority_conformance_reference=durable_record.authority_conformance_reference`

Expected consumption reference is `"phase33-consume-" + sha256(canonical_json).hexdigest()` over exact 11-key envelope:
- `domain="phase33-consumption-v1"`
- `schema_id="kiwoom-watchlist-order-authorization-durable-ledger-v1"`
- `transaction_profile_id="sqlite-autocommit-true-isolation-none-busy-zero-begin-immediate-v1"`
- `durability_profile_id="sqlite-main-wal-synchronous-full-v1"`
- `backend_instance_reference=durable_record.backend_instance_reference`
- `authorization_claim_identity=durable_claim_identity`
- `authorization_replay_guard=durable_replay_guard`
- `claim_fingerprint=durable_record.claim_fingerprint`
- `authority_approval_reference=durable_record.authority_approval_reference`
- `authority_conformance_reference=durable_record.authority_conformance_reference`
- `authority_result_reference=durable_record.authority_result_reference`

Both references use exact canonical JSON `json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)`, then UTF-8 encode and lowercase SHA-256 hex.

Expected authority-result reference must equal `durable_record.authority_result_reference` and expected consumption reference must equal `durable_record.consumption_reference`.
Mismatch raises exact `PHASE33_DURABLE_RECORD_REFERENCE_SELF_BINDING_INVALID`.

9.7 Exact Phase33 durable-record -> validated source-graph binding — success only

Only after Phase30/31/32 validation and durable-record self-integrity succeed, require all exact bindings:
- `durable_record.backend_instance_reference == source_snapshot.backend_instance_reference`;
- `durable_record.authorization_authority_reference == phase31_snapshot.context.authorization_authority_reference`;
- `durable_record.authorization_evidence_snapshot_id == phase31_snapshot.context.authorization_evidence_snapshot_id`;
- `durable_record.submission_attempt_reference == phase31_snapshot.context.submission_attempt_reference`;
- `durable_record.send_authorization_reference == phase31_snapshot.context.send_authorization_reference`;
- `durable_record.claim_fingerprint == phase31_snapshot.claim_fingerprint`;
- `durable_record.authority_approval_reference == phase32_snapshot.asserted_authority_approval_reference`;
- `durable_record.authority_conformance_reference == phase32_snapshot.asserted_authority_conformance_reference`;
- `durable_record.authority_result_reference == phase32_snapshot.authority_result_reference`;
- `durable_record.consumption_reference == phase32_snapshot.consumption_reference`.

Any mismatch raises exact `PHASE33_DURABLE_RECORD_SOURCE_BINDING_INVALID`.
This gate is what forbids a cross-bound `Phase32 evidence A + self-integrity-valid durable record B` from being accepted merely because both fingerprints are independently well-formed.

After sections 9.4-9.7 applicable success gates pass, or after the exact INDETERMINATE branch has safely skipped them, section 9.1 Phase33 verification fingerprint is recomputed and matched. Phase34 performs no SQLite read, no Phase33 verifier rerun, and no authority invocation.

10. Exact Phase32 state/result prerequisites, authority-result binding, and evidence-fingerprint revalidation

Phase34 obtains the exact Phase32 object only after Phase33 source exact-type validation:
`phase32_snapshot = source_snapshot.source_snapshot`

Before any Phase32 field is used as a fingerprint source, `phase32_snapshot` must be exact type `WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot`; otherwise exact error `PHASE32_SOURCE_SNAPSHOT_TYPE_INVALID` is raised.

10.1 Phase32 state/result structural prerequisite

Before Phase32 evidence-fingerprint recomputation require:
- `evidence_fingerprint` exact lowercase 64-hex str;
- `decision` exact str equal only `AUTHORITY_REPORTED_CONSUMED`;
- `block_reason is None`;
- `indeterminate_reason is None`;
- `authority_result` exact `KiwoomOrderAuthorizationAuthorityReportedResult`;
- `asserted_authority_approval_reference` valid exact Phase32 opaque reference and strict UTF-8 encodable;
- `asserted_authority_conformance_reference` valid exact Phase32 opaque reference and strict UTF-8 encodable;
- `authority_result_reference` valid exact Phase32 opaque reference and strict UTF-8 encodable;
- `consumption_reference` valid exact Phase32 opaque reference and strict UTF-8 encodable;
- every bool field used below exact bool;
- `authority_reported_authorization_consumption_committed is True`;
- `authority_reported_replay_guard_consumption_committed is True`;
- `commit_state_known is True`;
- `consumption_evidence_candidate_ready is True`;
- `authority_trust_independently_verified is False`;
- `automatic_retry_permitted is False`;
- `reconciliation_required is False`;
- `authority_invocation_attempted is True`;
- `phase32_direct_credential_accessed is False`;
- `phase32_direct_network_performed is False`;
- `phase32_direct_account_accessed is False`;
- `phase32_direct_order_submitted is False`.

Violation of this structural/result state raises exact `PHASE32_STATE_OR_RESULT_INVALID`. Phase32 BLOCKED/INDETERMINATE evidence is invalid Phase34 input because Phase33 does not promote it into durable verification.

10.2 Phase32 authority-result exact binding prerequisite

This gate executes only after exact Phase31 type/state/claim/replay validation has made all referenced Phase31 values safe to read.

The exact `authority_result` must have:
- `authorization_claim_identity` exact tuple length 4 of exact str and exact equality to `phase31_snapshot.authorization_claim_identity`;
- `authorization_replay_guard` exact tuple length 2 of exact str and exact equality to `phase31_snapshot.authorization_replay_guard`;
- `claim_fingerprint` exact lowercase 64-hex str and exact equality to `phase31_snapshot.claim_fingerprint`;
- `asserted_authority_approval_reference` exact `str`, valid exact Phase32 opaque-reference contract, and exact equality to `phase32_snapshot.asserted_authority_approval_reference`;
- `asserted_authority_conformance_reference` exact `str`, valid exact Phase32 opaque-reference contract, and exact equality to `phase32_snapshot.asserted_authority_conformance_reference`;
- `decision` exact `str` equal to `"AUTHORITY_REPORTED_CONSUMED"`;
- `block_reason is None`;
- `indeterminate_reason is None`;
- `authority_result_reference` exact `str`, valid exact Phase32 opaque-reference contract, and exact equality to `phase32_snapshot.authority_result_reference`;
- `consumption_reference` exact `str`, valid exact Phase32 opaque-reference contract, and exact equality to `phase32_snapshot.consumption_reference`;
- both authority-reported commit fields exact True;
- `commit_state_known is True`.

For every exact-str requirement in this subsection, `type(value) is str` is mandatory. A subclass of `str` is invalid even when equality and JSON serialization would otherwise succeed. Equality checks occur only after exact runtime-type and, where applicable, exact opaque-reference validation.

Any mismatch in this subsection raises exact `PHASE32_AUTHORITY_RESULT_BINDING_INVALID`.

10.3 Exact Phase32 evidence-fingerprint recomputation

Exact evidence-fingerprint envelope keys are 20:
1. `claim_fingerprint`
2. `asserted_authority_approval_reference`
3. `asserted_authority_conformance_reference`
4. `decision`
5. `block_reason`
6. `indeterminate_reason`
7. `authority_result_reference`
8. `consumption_reference`
9. `authority_reported_authorization_consumption_committed`
10. `authority_reported_replay_guard_consumption_committed`
11. `commit_state_known`
12. `consumption_evidence_candidate_ready`
13. `authority_trust_independently_verified`
14. `automatic_retry_permitted`
15. `reconciliation_required`
16. `authority_invocation_attempted`
17. `phase32_direct_credential_accessed`
18. `phase32_direct_network_performed`
19. `phase32_direct_account_accessed`
20. `phase32_direct_order_submitted`

Exact value sources are the same-named Phase32 snapshot fields, except `claim_fingerprint = phase31_snapshot.claim_fingerprint` after Phase31 claim fingerprint validation.
Canonical JSON settings are exact:
`json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)`
then UTF-8 and lowercase SHA-256 hex.

The recomputed value must equal exact `phase32_snapshot.evidence_fingerprint`; otherwise exact `PHASE32_EVIDENCE_FINGERPRINT_INVALID`.

Phase34 does not call the Phase32 authority adapter and does not normalize malformed Phase32 evidence into a result snapshot.

11. Exact Phase31 claim/replay revalidation algorithm

Phase34 obtains the exact Phase31 object only after the Phase32 exact-type gate succeeds:
`phase31_snapshot = phase32_snapshot.source_snapshot`

It must be exact type `WatchlistOrderAuthorizationConsumptionClaimSnapshot`.
Its `context` must be exact type `KiwoomOrderAuthorizationConsumptionClaimContext`.

The revalidation is pure local. It must not invoke a builder, authority, database, provider, or network.

The exact algorithm is frozen in this order. No Phase31 nested field is dereferenced before exact Phase31 type, and no context field is dereferenced before exact context type:

11.1 Exact Phase31 state/type validation
1. require exact Phase31 snapshot type;
2. require exact Phase31 context type;
3. require `authorization_claim_identity` exact tuple, length 4, every item exact str;
4. require `authorization_replay_guard` exact tuple, length 2, every item exact str;
5. require `claim_fingerprint` exact str matching lowercase `[0-9a-f]{64}`;
6. require exact bool/value pairs:
   - `claim_prepared is True`
   - `authorization_consumption_committed is False`
   - `post_permitted is False`
   - `automatic_retry_permitted is False`
   - `network_performed is False`
   - `order_submitted is False`.

11.2 Exact Phase31 context-reference validation
The exact original Phase31 validators are preserved:
- `authorization_authority_reference`: exact str, non-empty, and `.strip()` truthy;
- `authorization_evidence_snapshot_id`: exact str, length 1..128, `.strip()` truthy, no codepoint <32 and no DEL 127;
- `submission_attempt_reference`: exact str, length 1..128, `.strip()` truthy, no codepoint <32 and no DEL 127;
- `send_authorization_reference`: exact str, non-empty, and `.strip()` truthy.

No stronger or weaker substitute validator may be silently used as the Phase31 contract itself.

Phase34 then applies a separate Phase33-verifier-producibility overlay because the containing object claims to be an actual Phase33 verification snapshot. This overlay does not redefine Phase31. Before a Phase34 result may be returned on either the Phase33 success or INDETERMINATE branch, require:
- `context.authorization_authority_reference` additionally satisfies the Phase33 durable-authority config exact-reference syntax: exact str already proven, length 1..128, `value == value.strip()`, whitespace-only prohibited, U+0000..U+001F prohibited, U+007F prohibited, no trim/case-fold/Unicode normalization/replacement, and strict UTF-8 encodable;
- `context.authorization_evidence_snapshot_id`, `context.submission_attempt_reference`, and `context.send_authorization_reference` are strict UTF-8 encodable without surrogate-pass/replacement;
- the same strict UTF-8 requirement applies to the already exact Phase32 top-level asserted approval/conformance references and authority-result/consumption references in section 10.1.

This overlay represents the Phase33 verifier's local precondition that malformed/non-UTF8-encodable required source references cannot produce any Phase33 verification snapshot. Failure of the Phase31-context portion is routed through existing step 9 `PHASE31_STATE_OR_REFERENCE_INVALID`; failure of the Phase32 top-level portion is routed through existing step 8 `PHASE32_STATE_OR_RESULT_INVALID`. No new public validation code is added.

11.3 Exact claim identity and replay guard reconstruction
Reconstruct only from exact Phase31 context fields:

`expected_claim_identity = (`
`    context.authorization_authority_reference,`
`    context.authorization_evidence_snapshot_id,`
`    context.submission_attempt_reference,`
`    context.send_authorization_reference,`
`)`

`expected_replay_guard = (`
`    context.authorization_authority_reference,`
`    context.send_authorization_reference,`
`)`

Require exact equality:
- `phase31_snapshot.authorization_claim_identity == expected_claim_identity`
- `phase31_snapshot.authorization_replay_guard == expected_replay_guard`

There is no sorting, normalization, lowercasing, whitespace trimming, tuple/list coercion, or reference substitution.

11.4 Exact Phase30 source/request binding as part of Phase31 revalidation
Set exactly:
`request_snapshot = phase31_snapshot.source_snapshot`

At global validation-precedence step 6, require only the exact type `WatchlistOrderSendRequestSnapshot` before any Phase30 field dereference. The remaining section 12 checks are deliberately staged only at their exact positions in section 15; they are not collapsed into this subsection and must not run early. In particular, Phase30 structural validation occurs at step 12, safety at step 13, context/reference binding at step 14, materialization-fingerprint validation at step 15, and provider-semantic validation at step 20.

At global precedence step 14, require exactly:
- `context.submission_attempt_reference == request_snapshot.source_attempt_ref`
- `context.authorization_evidence_snapshot_id == request_snapshot.authorization_evidence_ref`

11.5 Exact Phase31 claim-fingerprint recomputation
Exact envelope has 3 keys:
- `materialization_fingerprint = request_snapshot.materialization_fingerprint`
- `authorization_claim_identity = phase31_snapshot.authorization_claim_identity`
- `authorization_replay_guard = phase31_snapshot.authorization_replay_guard`

Tuple values serialize as JSON arrays by normal Python JSON serialization.
Canonical JSON exact settings:
`json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)`
then UTF-8 encode and lowercase SHA-256 hex.

Require recomputed fingerprint == exact `phase31_snapshot.claim_fingerprint`.

Phase34 never reconstructs a new Phase31 snapshot and never consumes the claim/replay guard.

12. Exact embedded Phase30 request binding and provider-contract validation

The exact `request_snapshot` obtained in section 11.4 is preserved by object identity in the Phase34 snapshot.
The named-local chain is exact:
`phase32_snapshot = source_snapshot.source_snapshot`
`phase31_snapshot = phase32_snapshot.source_snapshot`
`request_snapshot = phase31_snapshot.source_snapshot`
Equivalent direct expression from the Phase33 local variable is exactly `source_snapshot.source_snapshot.source_snapshot.source_snapshot`.
It must not be copied, remapped, normalized, replaced, or rebuilt.

12.1 Exact Phase30 request structural / primitive invariants
Require before canonicalization:
- `environment`, `side`, `exchange`, `api_id`, `http_method`, and `api_path` are each exact str; their provider-semantic values are checked separately in section 12.4 so `PROVIDER_REQUEST_CONTRACT_INVALID` has a distinct reachable meaning
- body is a Mapping; contract-controlled `AttributeError`, `KeyError`, or `TypeError` raised while interrogating this untrusted Mapping for keys/values/index access is normalized to exact `PHASE30_REQUEST_STRUCTURE_INVALID`, while `KeyboardInterrupt`/`SystemExit` and exceptions outside this defined malformed-input boundary propagate
- body exact key set is exactly:
  `dmst_stex_tp`, `stk_cd`, `ord_qty`, `ord_uv`, `trde_tp`, `cond_uv`
- every body key exact str
- every body value exact str
- `source_attempt_ref` passes exact Phase31 binding-reference validator
- `authorization_evidence_ref` passes exact Phase31 binding-reference validator
- `materialization_fingerprint` exact lowercase 64-hex str

Violations of this subsection raise exact `PHASE30_REQUEST_STRUCTURE_INVALID`. The exact provider-semantic values (`demo`, `BUY`, `KRX`, `kt10000`, `POST`, path, KRX body field, cond/order-type mapping) are intentionally not consumed by this error class; they are section 12.4 / `PROVIDER_REQUEST_CONTRACT_INVALID`.

12.2 Exact Phase30 safety invariants
Require exact False, not integer 0:
- `transport_allowed`
- `credential_accessed`
- `network_performed`
- `account_accessed`
- `order_submitted`

12.3 Exact Phase30 materialization-fingerprint recomputation
Exact envelope 9 keys:
1. `environment`
2. `side`
3. `exchange`
4. `api_id`
5. `http_method`
6. `api_path`
7. `body` as `dict(request_snapshot.body)`
8. `source_attempt_ref`
9. `authorization_evidence_ref`

Clarification: the semantic fields are 9 envelope keys because `body` is one key and both provenance references are separate keys. No field may be omitted despite historical shorthand descriptions.

Before `dict(request_snapshot.body)` or `json.dumps`, exact body key/value str validation and all primitive validations in sections 12.1-12.2 must already have succeeded. Thus malformed input cannot reach canonical JSON with an unsupported value type.

Canonical JSON exact settings:
`json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)`
then UTF-8 encode and lowercase SHA-256 hex.
Require exact equality with `request_snapshot.materialization_fingerprint`.

12.4 Provider request contract meaning and exact reachable validation

Only after sections 12.1-12.3 and the upstream fingerprint/binding prerequisites succeed, validate the frozen static Kiwoom provider semantics:
- `environment == "demo"`
- `side == "BUY"`
- `exchange == "KRX"`
- `api_id == "kt10000"`
- `http_method == "POST"`
- `api_path == "/api/dostk/ordr"`
- `body["dmst_stex_tp"] == "KRX"`
- `body["cond_uv"] == ""`
- exact order-type mapping:
  - `body["trde_tp"] == "0"` requires `body["ord_uv"] != ""`;
  - `body["trde_tp"] == "3"` requires `body["ord_uv"] == ""`;
  - any other `body["trde_tp"]` is invalid.

A mismatch in these static provider semantics raises exact `PROVIDER_REQUEST_CONTRACT_INVALID`. This distinct gate is intentionally reachable even when the internally self-consistent Phase30 snapshot and its materialization fingerprint were recomputed over a different string value.

`provider_request_contract_verified=True` means only that the already-materialized Phase30 request matches this frozen local shape corroborated against current official Kiwoom documentation. It does not prove:
- provider availability
- server acceptance
- token validity
- account validity or buying power
- execution-time authorization
- successful transport
- provider response semantics
- order acceptance or order number

13. Candidate snapshot — exact 21 fields and complete state matrix

`WatchlistOrderProviderSendEligibilityCandidateSnapshot` is `@dataclass(frozen=True)`.

13.1 Exact field order / annotations

1. `source_snapshot: WatchlistOrderAuthorizationDurableVerificationSnapshot`
2. `request_snapshot: WatchlistOrderSendRequestSnapshot`
3. `decision: KiwoomOrderProviderSendEligibilityDecision`
4. `indeterminate_reason: KiwoomOrderProviderSendEligibilityIndeterminateReason | None`
5. `request_materialization_verified: bool`
6. `authorization_claim_binding_verified: bool`
7. `durable_consumption_verified: bool`
8. `provider_request_contract_verified: bool`
9. `authority_approval_provenance_verified: bool`
10. `authority_conformance_provenance_verified: bool`
11. `provider_send_eligibility_candidate_ready: bool`
12. `provider_send_eligibility_authorized: bool`
13. `production_authority_use_authorized: bool`
14. `transport_allowed: bool`
15. `credential_accessed: bool`
16. `network_performed: bool`
17. `account_accessed: bool`
18. `order_submitted: bool`
19. `automatic_retry_permitted: bool`
20. `reconciliation_required: bool`
21. `eligibility_fingerprint: str`

Every bool field requires exact `bool`; integer `0/1` is invalid.
`eligibility_fingerprint` is exact lowercase 64-hex.

13.2 Complete returned-snapshot matrix

Field | SUCCESS | PHASE33 INDETERMINATE | exact source rule
source_snapshot | exact input object | exact input object | identity-preserved input
request_snapshot | exact embedded Phase30 object | exact embedded Phase30 object | `request_snapshot = phase31_snapshot.source_snapshot`; equivalent direct Phase33-local expression `source_snapshot.source_snapshot.source_snapshot.source_snapshot`
decision | `PROVIDER_SEND_ELIGIBILITY_CANDIDATE_READY` enum member | `INDETERMINATE` enum member | Phase34 builder result after all local revalidation
indeterminate_reason | None | `SOURCE_DURABLE_VERIFICATION_INDETERMINATE` enum member | Phase34 fixed mapping from validated Phase33 decision
request_materialization_verified | True | True | Phase30 canonical fingerprint + exact structure/safety validation succeeded
authorization_claim_binding_verified | True | True | Phase31 exact claim/replay/context/binding/fingerprint validation succeeded
durable_consumption_verified | True | False | exact copy of validated `source_snapshot.durable_consumption_record_verified`
provider_request_contract_verified | True | True | section 12 static local request-contract validation succeeded
authority_approval_provenance_verified | False | False | exact copy of validated `source_snapshot.authority_approval_provenance_verified`
authority_conformance_provenance_verified | False | False | exact copy of validated `source_snapshot.authority_conformance_provenance_verified`
provider_send_eligibility_candidate_ready | True | False | exact derived Phase34 candidate state
provider_send_eligibility_authorized | False | False | exact copy of validated `source_snapshot.provider_send_eligibility_authorized`; Phase34 cannot upgrade
production_authority_use_authorized | False | False | exact copy of validated `source_snapshot.production_authority_use_authorized`; Phase34 cannot upgrade
transport_allowed | False | False | Phase34-owned constant False
credential_accessed | False | False | Phase34-owned constant False
network_performed | False | False | Phase34-owned constant False
account_accessed | False | False | Phase34-owned constant False
order_submitted | False | False | Phase34-owned constant False
automatic_retry_permitted | False | False | Phase34-owned constant False
reconciliation_required | False | True | exact copy of validated `source_snapshot.reconciliation_required`
eligibility_fingerprint | computed exact A6 fingerprint | computed exact A6 fingerprint | section 14 only

A valid Phase33 INDETERMINATE may still have locally valid Phase30 request materialization, Phase31 claim/replay binding, and static provider request shape; therefore fields 5, 6, and 8 remain True after those independent local checks. The unresolved durable verification is represented exclusively by `durable_consumption_verified=False`, candidate-ready False, `reconciliation_required=True`, and the Phase34 INDETERMINATE decision/reason.

No snapshot is returned for malformed/inconsistent local input.

14. Deterministic eligibility fingerprint — exact 25-key safety-complete contract

`eligibility_fingerprint` is lowercase 64-hex SHA-256.

14.1 Exact canonical envelope key set

Exact 25 keys, no more and no fewer:
1. `domain`
2. `phase33_verification_fingerprint`
3. `phase32_evidence_fingerprint`
4. `phase31_claim_fingerprint`
5. `phase30_materialization_fingerprint`
6. `source_attempt_ref`
7. `authorization_evidence_ref`
8. `decision`
9. `indeterminate_reason`
10. `request_materialization_verified`
11. `authorization_claim_binding_verified`
12. `durable_consumption_verified`
13. `provider_request_contract_verified`
14. `authority_approval_provenance_verified`
15. `authority_conformance_provenance_verified`
16. `provider_send_eligibility_candidate_ready`
17. `provider_send_eligibility_authorized`
18. `production_authority_use_authorized`
19. `transport_allowed`
20. `credential_accessed`
21. `network_performed`
22. `account_accessed`
23. `order_submitted`
24. `automatic_retry_permitted`
25. `reconciliation_required`

Exact domain:
`phase34-provider-send-eligibility-candidate-v1`

14.2 Exact value-source mapping — every key frozen

1. `domain = "phase34-provider-send-eligibility-candidate-v1"` literal.
2. `phase33_verification_fingerprint = snapshot.source_snapshot.verification_fingerprint` exactly, after section 9 recomputation/match.
3. `phase32_evidence_fingerprint = snapshot.source_snapshot.source_snapshot.evidence_fingerprint` exactly, after section 10 recomputation/match.
4. `phase31_claim_fingerprint = snapshot.source_snapshot.source_snapshot.source_snapshot.claim_fingerprint` exactly, after section 11 recomputation/match.
5. `phase30_materialization_fingerprint = snapshot.request_snapshot.materialization_fingerprint` exactly, after section 12 recomputation/match.
6. `source_attempt_ref = snapshot.request_snapshot.source_attempt_ref` exactly.
7. `authorization_evidence_ref = snapshot.request_snapshot.authorization_evidence_ref` exactly.
8. `decision = snapshot.decision.value` exactly; JSON value is the frozen enum string value, never member repr/name derived dynamically.
9. `indeterminate_reason = None` if snapshot field is None; otherwise `snapshot.indeterminate_reason.value` exactly.
10. `request_materialization_verified = snapshot.request_materialization_verified` exactly.
11. `authorization_claim_binding_verified = snapshot.authorization_claim_binding_verified` exactly.
12. `durable_consumption_verified = snapshot.durable_consumption_verified` exactly.
13. `provider_request_contract_verified = snapshot.provider_request_contract_verified` exactly.
14. `authority_approval_provenance_verified = snapshot.authority_approval_provenance_verified` exactly.
15. `authority_conformance_provenance_verified = snapshot.authority_conformance_provenance_verified` exactly.
16. `provider_send_eligibility_candidate_ready = snapshot.provider_send_eligibility_candidate_ready` exactly.
17. `provider_send_eligibility_authorized = snapshot.provider_send_eligibility_authorized` exactly.
18. `production_authority_use_authorized = snapshot.production_authority_use_authorized` exactly.
19. `transport_allowed = snapshot.transport_allowed` exactly.
20. `credential_accessed = snapshot.credential_accessed` exactly.
21. `network_performed = snapshot.network_performed` exactly.
22. `account_accessed = snapshot.account_accessed` exactly.
23. `order_submitted = snapshot.order_submitted` exactly.
24. `automatic_retry_permitted = snapshot.automatic_retry_permitted` exactly.
25. `reconciliation_required = snapshot.reconciliation_required` exactly.

No fallback source, duplicated alias, implicit derivation at fingerprint time, source-object hash, Python object id, clock, UUID, PID, machine identity, SQLite path, credential/account value, provider-client state, or provider response may enter the envelope.

14.3 Canonicalization

Exact canonical JSON:
`json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)`

Encode UTF-8; then:
`hashlib.sha256(canonical_bytes).hexdigest()`.

The result must be lowercase 64-hex.

14.4 Safety-state coverage requirement

A change to any of these fields must change the canonical envelope input and therefore the expected fingerprint:
- decision/reason
- any four local verification summary bools
- both provenance bools
- candidate-ready
- send eligibility authorization
- production authority use
- transport
- credential/network/account/order state
- automatic retry state
- reconciliation state
- any upstream Phase33/32/31/30 fingerprint or exact request provenance reference

The fingerprint does not itself authorize any action.

15. Builder exact decision algorithm — traversal-safe and integrity-first prerequisite order

The builder executes the following exact externally observable validation order. A later step may not dereference or canonicalize a value whose prerequisite type/state gate is earlier and has not passed.

1. require exact Phase33 `source_snapshot` type; otherwise `SOURCE_SNAPSHOT_TYPE_INVALID`;
2. validate Phase33 decision exact type/value per 9.2; otherwise `PHASE33_DECISION_INVALID`;
3. set `phase32_snapshot = source_snapshot.source_snapshot`, then require exact Phase32 type; otherwise `PHASE32_SOURCE_SNAPSHOT_TYPE_INVALID`;
4. set `phase31_snapshot = phase32_snapshot.source_snapshot`, then require exact Phase31 type; otherwise `PHASE31_SOURCE_SNAPSHOT_TYPE_INVALID`;
5. require exact Phase31 context type before any context-field dereference; otherwise `PHASE31_CONTEXT_TYPE_INVALID`;
6. set `request_snapshot = phase31_snapshot.source_snapshot`, then require exact Phase30 request type; otherwise `PHASE30_REQUEST_SNAPSHOT_TYPE_INVALID`;
7. validate exact Phase33 success or INDETERMINATE branch-state invariants per 9.3, including success durable-record exact outer type but not yet trusting its fields; otherwise `PHASE33_STATE_INVARIANT_INVALID`;
8. validate Phase32 consumed-candidate structural/result state, every primitive needed later by the Phase32 envelope, and the section 10.1 Phase33-verifier strict-UTF8 source-reference overlay; otherwise `PHASE32_STATE_OR_RESULT_INVALID`;
9. validate Phase31 state/reference primitives plus the section 11.2 Phase33-verifier-producibility overlay for all branches; otherwise `PHASE31_STATE_OR_REFERENCE_INVALID`;
10. reconstruct/validate exact Phase31 claim identity; otherwise `PHASE31_CLAIM_IDENTITY_INVALID`;
11. reconstruct/validate exact replay guard; otherwise `PHASE31_REPLAY_GUARD_INVALID`;
12. validate Phase30 request structure/body/reference primitives with defined malformed Mapping exception normalization; otherwise `PHASE30_REQUEST_STRUCTURE_INVALID`;
13. validate Phase30 safety flags; otherwise `PHASE30_REQUEST_SAFETY_INVALID`;
14. validate Phase31 context -> Phase30 request reference bindings; otherwise `PHASE30_CONTEXT_BINDING_INVALID`;
15. recompute/match Phase30 materialization fingerprint; otherwise `PHASE30_MATERIALIZATION_FINGERPRINT_INVALID`;
16. recompute/match Phase31 claim fingerprint; otherwise `PHASE31_CLAIM_FINGERPRINT_INVALID`;
17. validate exact Phase32 authority-result echo/reference/commit binding against the now-validated Phase31 claim; otherwise `PHASE32_AUTHORITY_RESULT_BINDING_INVALID`;
18. recompute/match Phase32 evidence fingerprint; otherwise `PHASE32_EVIDENCE_FINGERPRINT_INVALID`;
19. success only: validate all 13 durable-record fields/primitives per 9.4; otherwise `PHASE33_DURABLE_RECORD_STRUCTURE_INVALID`; INDETERMINATE skips this step;
20. success only: independently recompute/match the exact 16-key durable-record fingerprint per 9.5; otherwise `PHASE33_DURABLE_RECORD_FINGERPRINT_INVALID`; INDETERMINATE skips this step;
21. success only: independently recompute/match exact Phase33 deterministic authority-result and consumption references per 9.6; otherwise `PHASE33_DURABLE_RECORD_REFERENCE_SELF_BINDING_INVALID`; INDETERMINATE skips this step;
22. success only: validate exact durable-record -> Phase33/32/31 source graph bindings per 9.7; otherwise `PHASE33_DURABLE_RECORD_SOURCE_BINDING_INVALID`; INDETERMINATE skips this step;
23. recompute/match Phase33 verification fingerprint using the already-validated Phase32 evidence fingerprint and, on success, the already self-integrity/source-bound durable record fingerprint; otherwise `PHASE33_VERIFICATION_FINGERPRINT_INVALID`;
24. validate the exact section 12.4 frozen provider-semantic values after self-consistent Phase30 materialization is proven; otherwise `PROVIDER_REQUEST_CONTRACT_INVALID`.

After all 24 applicable public validation gates pass, derive the exact section 13.2 Phase34 state matrix, build the exact 25-key section 14 envelope, compute `eligibility_fingerprint`, and return one frozen snapshot.

Phase34-owned result state is deterministic from validated input plus fixed False constants. There is no 25th caller-validation code for candidate-state construction. An impossible post-validation contradiction caused by an implementation defect must be detected by an explicit internal invariant check and raises exact `AssertionError("PHASE34_INTERNAL_SAFETY_STATE_DEFECT")`. This internal defect is not a `WatchlistOrderProviderSendEligibilityError`, is outside the public first-error precedence, is not an INDETERMINATE business result, and must never be caught and converted by the builder.

Branch result:
- validated Phase33 success -> `PROVIDER_SEND_ELIGIBILITY_CANDIDATE_READY`, candidate-ready=True;
- validated Phase33 INDETERMINATE -> Phase34 `INDETERMINATE / SOURCE_DURABLE_VERIFICATION_INDETERMINATE`, candidate-ready=False.

Both branches still require the same valid Phase32/31/30 embedded chain because Phase34 preserves and fingerprints the request/claim evidence rather than returning a partial result from malformed nested input.

16. Validation error / exception contract — exact 24-code public precedence

All contract-validation failures raise exact `WatchlistOrderProviderSendEligibilityError` with one exact code string.
Public validation code order is exactly:

1. `SOURCE_SNAPSHOT_TYPE_INVALID`
2. `PHASE33_DECISION_INVALID`
3. `PHASE32_SOURCE_SNAPSHOT_TYPE_INVALID`
4. `PHASE31_SOURCE_SNAPSHOT_TYPE_INVALID`
5. `PHASE31_CONTEXT_TYPE_INVALID`
6. `PHASE30_REQUEST_SNAPSHOT_TYPE_INVALID`
7. `PHASE33_STATE_INVARIANT_INVALID`
8. `PHASE32_STATE_OR_RESULT_INVALID`
9. `PHASE31_STATE_OR_REFERENCE_INVALID`
10. `PHASE31_CLAIM_IDENTITY_INVALID`
11. `PHASE31_REPLAY_GUARD_INVALID`
12. `PHASE30_REQUEST_STRUCTURE_INVALID`
13. `PHASE30_REQUEST_SAFETY_INVALID`
14. `PHASE30_CONTEXT_BINDING_INVALID`
15. `PHASE30_MATERIALIZATION_FINGERPRINT_INVALID`
16. `PHASE31_CLAIM_FINGERPRINT_INVALID`
17. `PHASE32_AUTHORITY_RESULT_BINDING_INVALID`
18. `PHASE32_EVIDENCE_FINGERPRINT_INVALID`
19. `PHASE33_DURABLE_RECORD_STRUCTURE_INVALID`
20. `PHASE33_DURABLE_RECORD_FINGERPRINT_INVALID`
21. `PHASE33_DURABLE_RECORD_REFERENCE_SELF_BINDING_INVALID`
22. `PHASE33_DURABLE_RECORD_SOURCE_BINDING_INVALID`
23. `PHASE33_VERIFICATION_FINGERPRINT_INVALID`
24. `PROVIDER_REQUEST_CONTRACT_INVALID`

A6 retains the 20 reachable A3 caller-validation code names other than the removed unreachable `PHASE34_SAFETY_STATE_CONSTRUCTION_INVALID`, and adds exactly four durable-record integrity/binding codes.

`PHASE34_SAFETY_STATE_CONSTRUCTION_INVALID` is not an A6 public validation code and must not appear in `WatchlistOrderProviderSendEligibilityError` precedence.

16.1 Contract-validation exception containment

The implementation must not use blanket `except Exception` around the whole builder.
Only explicitly defined interrogation boundaries may normalize malformed candidate input exceptions:
- after exact parent dataclass type validation, malformed child field/value types are routed by the active validation step;
- Phase30 `body` is required to satisfy exact Mapping/key/value prerequisites before indexed reads or canonicalization;
- defined `AttributeError`, `KeyError`, or `TypeError` arising solely while interrogating a contract-controlled malformed nested value at a stage whose error code is already frozen are converted to that stage's exact `WatchlistOrderProviderSendEligibilityError`;
- `json.dumps` is called only after all values entering the relevant envelope are validated as exact JSON-safe primitives/tuples/mapping copies, so malformed input must not escape as JSON serialization `TypeError`.

These conversions are validation-boundary normalization only. They must not catch exceptions from provider/network/SQLite because those operations are prohibited and absent.

16.2 Unexpected exception and internal-defect propagation

A genuinely unexpected Python implementation exception that is not an explicitly defined malformed-input validation failure propagates unchanged.
`KeyboardInterrupt` and `SystemExit` always propagate unchanged.
No unexpected exception is normalized into a Phase34 INDETERMINATE snapshot.

After all 24 public validation gates pass, any impossible contradiction among Phase34-owned fixed/copy/derived state is an implementation defect, not caller validation. Exact internal defect classification is explicit `AssertionError("PHASE34_INTERNAL_SAFETY_STATE_DEFECT")`. It is outside the 24-code public precedence, is not caught as `WatchlistOrderProviderSendEligibilityError`, and returns no snapshot.

17. State / transaction / side-effect contract

Phase34 is pure local and synchronous.

It must:
- create no SQLite transaction;
- access no `sqlite3.Connection`;
- read/write no durable ledger;
- invoke no authority;
- invoke no Phase33 verifier;
- invoke no provider/client;
- perform no network operation;
- read no credential/token/account state;
- mutate no upstream object;
- persist no new state;
- execute no reconciliation action.

There is no BEGIN/COMMIT/ROLLBACK lifecycle in Phase34.
`reconciliation_required=True` is evidence only; it grants no reconciliation permission.

A later provider-send phase must define its own execution-time freshness, external provenance, credentials/account ownership, transport, ambiguity, reconciliation, and no-retry contract. The Phase34 snapshot is not timeless send authority.

18. Demo / mock / live boundary

Phase34 candidate is demo-only but performs no demo provider call.

It must not:
- use `https://api.kiwoom.com`;
- use `https://mockapi.kiwoom.com`;
- acquire OAuth token;
- instantiate a provider client for sending;
- inspect a live or demo account;
- submit an order.

Official Kiwoom documentation is only a static contract-review source for the request shape already frozen by Phase30.

19. Public API / backward compatibility

If later separately implemented, Phase34 adds one isolated module only.
It must not change:
- Phase27 public API
- Phase28 public API
- Phase29 public API
- Phase30 public API
- Phase31 public API
- Phase32 public API
- Phase33 public API
- `rest/__init__.py` package exports
- dependency versions
- existing snapshot field order
- existing decision/reason values
- existing fingerprint algorithms

Phase34 accepts the official Phase33 snapshot as-is and requires no Phase30-33 code changes.

20. Acceptance criteria — exact AC-001 through AC-128

A later approved implementation must prove every applicable criterion below.

20.1 API / type surface
AC-001 exact module-level public symbol set is the section 8 five symbols only.
AC-002 error class inherits RuntimeError exactly.
AC-003 decision enum base is `(str, Enum)` with exact two-member order.
AC-004 decision enum exact member-name/value pairs match section 8.1 and contain no alias/additional member.
AC-005 indeterminate-reason enum exact member-name/value pair matches section 8.2 and contain no alias/additional member.
AC-006 frozen snapshot dataclass exact 21-field order/annotations match section 13.1.
AC-007 every snapshot bool field rejects integer 0/1 as substitute where validation applies.
AC-008 builder signature is exact and has no defaults/context/authority/sqlite/client/token/account parameters.

20.2 Phase33 exact upstream and durable-record validation
AC-009 exact Phase33 source type accepted; wrong type is rejected before any nested inspection.
AC-010 Phase33 supported decision exact type/value is validated before decision-dependent mapping.
AC-011 Phase33 exact success/INDETERMINATE branch-state matrix in section 9.3 is required before deeper trust.
AC-012 Phase33 INDETERMINATE exact 8-reason set and None durable-record branch are frozen.
AC-013 success durable record exact outer class is insufficient by itself; exact 13-field primitive/format contract in 9.4 is independently validated.
AC-014 success exact 16-key durable-record fingerprint is independently recomputed and matched before deterministic-reference/source binding and before Phase33 verification-fingerprint recomputation.
AC-015 success historical authority-result and consumption references are independently recomputed from durable-record values using exact Phase33 10-key/11-key algorithms and matched.
AC-016 success durable record is exactly bound to validated Phase33 backend identity, Phase31 claim/context, and Phase32 approval/conformance/result/consumption references.
AC-017 a cross-bound `Phase32 evidence A + self-integrity-valid durable record B` mismatch is rejected before Phase33 verification-fingerprint recomputation.
AC-018 exact Phase33 19-key verification envelope/canonical JSON/SHA-256 is independently reconstructed only after all applicable durable-record gates pass; unsupported decision or state contradiction is rejected earlier.

20.3 Phase32 evidence self-consistency
AC-019 embedded Phase32 exact type is required before any Phase32 field dereference.
AC-020 exact Phase32 consumed-candidate state/result primitives in section 10.1 are required; BLOCKED/INDETERMINATE cannot be promoted.
AC-021 exact Phase32 authority-result echo/reference/commit binding in section 10.2 is required against already-validated Phase31 values.
AC-022 exact Phase32 20-key evidence fingerprint envelope/canonical JSON/SHA-256 is independently reconstructed and matched only after AC-019..AC-021 prerequisites.

20.4 Phase31 exact claim/replay algorithm
AC-023 embedded Phase31 exact type is required before Phase31 field dereference.
AC-024 Phase31 context exact type is required before context field dereference.
AC-025 exact tuple type/length/exact-str checks for claim identity 4 and replay guard 2 are required.
AC-026 exact Phase31 bool state matrix in section 11.1 is required.
AC-027 exact original authorization-authority reference validator is preserved.
AC-028 exact original evidence-snapshot-id binding-reference validator is preserved.
AC-029 exact original submission-attempt binding-reference validator is preserved.
AC-030 exact original send-authorization reference validator is preserved.
AC-031 exact claim identity reconstruction/order and equality are required.
AC-032 exact replay guard reconstruction/order and equality are required.
AC-033 exact submission-attempt -> Phase30 source_attempt_ref binding is required.
AC-034 exact evidence-snapshot-id -> Phase30 authorization_evidence_ref binding is required.
AC-035 exact 3-key Phase31 claim-fingerprint envelope is independently recomputed and matched.
AC-036 no trimming/lowercasing/sorting/coercion/substitution of claim/replay identity values occurs.
AC-037 Phase31 malformed claim/replay/binding fails closed without consuming anything.

20.5 Phase30 request/materialization contract
AC-038 exact Phase30 request object identity is preserved in Phase34 snapshot.
AC-039 exact named-local graph is Phase33 -> Phase32 -> Phase31 -> Phase30 and exact Phase30 direct expression is the four-token `source_snapshot.source_snapshot.source_snapshot.source_snapshot` form.
AC-040 Phase30 top-level request fields are exact str primitives before fingerprint canonicalization; provider-semantic literal values are reserved for AC-048/AC-108.
AC-041 exact provider body key set is required.
AC-042 every provider body key/value exact str is required before indexed access/canonicalization.
AC-043 Phase30 body indexing/order-type inspection occurs only after exact Mapping key-set and exact-str key/value validation.
AC-044 Phase30 source/evidence reference validators are required.
AC-045 all Phase30 safety flags are exact False.
AC-046 exact Phase30 materialization envelope fields are independently reconstructed only after primitive validation.
AC-047 exact materialization canonical JSON/hash match is required.
AC-048 exact section 12.4 demo/BUY/KRX/kt10000/POST/path/KRX-body/cond/order-type provider semantics are required and mismatch is rejected without provider/client/network activity.

20.6 Complete Phase34 returned-state matrix / reconciliation source
AC-049 success snapshot matches every one of the 21 section 13.2 fields.
AC-050 Phase33 INDETERMINATE snapshot matches every one of the 21 section 13.2 fields.
AC-051 success `request_materialization_verified=True`.
AC-052 INDETERMINATE `request_materialization_verified=True` only after independent local Phase30 validation succeeds.
AC-053 success and INDETERMINATE `authorization_claim_binding_verified=True` only after exact section 11 succeeds.
AC-054 success `durable_consumption_verified=True` only after 9.4-9.7 durable-record validation and Phase33 verification fingerprint all succeed; INDETERMINATE durable-consumption flag is False.
AC-055 static provider request contract flag is True on either returned path only after exact section 12 validation.
AC-056 both provenance fields are False on every returned snapshot.
AC-057 candidate-ready is True only for fully validated Phase33 success and False for Phase33 INDETERMINATE.
AC-058 provider-send eligibility authorized is always False.
AC-059 production authority use authorized is always False.
AC-060 transport_allowed is always False.
AC-061 credential/network/account/order flags are always False.
AC-062 automatic_retry_permitted is always False.
AC-063 `reconciliation_required` is exact Phase34 snapshot field copied only from validated Phase33 source.
AC-064 success reconciliation_required=False and INDETERMINATE reconciliation_required=True.
AC-065 reconciliation_required=True performs no reconciliation action.
AC-066 malformed input returns no partial snapshot.

20.7 A6 eligibility fingerprint / safety-state coverage / exact mapping
AC-067 exact domain is `phase34-provider-send-eligibility-candidate-v1`.
AC-068 exact eligibility envelope key set is 25 keys, no more/no fewer.
AC-069 every one of the 25 keys uses only the exact section 14.2 value source.
AC-070 enum decision fingerprint value uses exact `.value`, not repr/object/member-name inference.
AC-071 indeterminate reason fingerprint value uses exact None or enum `.value`.
AC-072 same validated input/state yields the same fingerprint.
AC-073 changing Phase33 verification fingerprint changes expected Phase34 fingerprint.
AC-074 changing Phase32 evidence fingerprint changes expected Phase34 fingerprint.
AC-075 changing Phase31 claim fingerprint changes expected Phase34 fingerprint.
AC-076 changing Phase30 materialization fingerprint changes expected Phase34 fingerprint.
AC-077 changing either exact provenance request reference changes expected Phase34 fingerprint.
AC-078 changing any Phase34 local verification summary bool changes expected fingerprint.
AC-079 changing either provenance bool changes expected fingerprint.
AC-080 changing candidate-ready/send-authorization/production/transport state changes expected fingerprint.
AC-081 changing credential/network/account/order/retry/reconciliation state changes expected fingerprint.
AC-082 object id/clock/UUID/PID/machine/SQLite path/credential/account/provider-response state is excluded.

20.8 Isolation / compatibility / inherited defect traceability
AC-083 no SQLite/network/provider/client/credential/token/account/order/authority/retry/reconciliation side effect occurs; protected Phase27-33 APIs/files, package exports, and dependencies remain unchanged.
AC-084 inherited D1-D7 traceability is maintained: D1 -> AC-067..AC-082; D2 -> AC-068..AC-071; D3 -> AC-063..AC-065/AC-081; D4 -> AC-049..AC-066; D5 -> AC-023..AC-048; D6 -> AC-003..AC-005/AC-070..AC-071; D7 -> AC-001..AC-128.

20.9 A6 exact public validation-error / precedence criteria
AC-085 wrong outer source type raises exact `SOURCE_SNAPSHOT_TYPE_INVALID`.
AC-086 unsupported/non-str Phase33 decision raises exact `PHASE33_DECISION_INVALID`.
AC-087 wrong embedded Phase32 type raises exact `PHASE32_SOURCE_SNAPSHOT_TYPE_INVALID` before any Phase32 field dereference.
AC-088 wrong embedded Phase31 type raises exact `PHASE31_SOURCE_SNAPSHOT_TYPE_INVALID` before any Phase31 field dereference.
AC-089 wrong Phase31 context type raises exact `PHASE31_CONTEXT_TYPE_INVALID` before any context-field dereference.
AC-090 wrong Phase30 request type raises exact `PHASE30_REQUEST_SNAPSHOT_TYPE_INVALID` before any Phase30 request-field dereference.
AC-091 invalid Phase33 success/INDETERMINATE branch state raises exact `PHASE33_STATE_INVARIANT_INVALID`.
AC-092 invalid Phase32 consumed-candidate structural/result state, including non-UTF8-encodable required top-level Phase32 source references, raises exact `PHASE32_STATE_OR_RESULT_INVALID`.
AC-093 invalid Phase31 state/reference primitive or failure of the separate Phase33-verifier-producibility overlay in section 11.2 raises exact `PHASE31_STATE_OR_REFERENCE_INVALID`; this does not redefine the original Phase31 contract.
AC-094 invalid reconstructed Phase31 claim identity raises exact `PHASE31_CLAIM_IDENTITY_INVALID`.
AC-095 invalid reconstructed Phase31 replay guard raises exact `PHASE31_REPLAY_GUARD_INVALID`.
AC-096 malformed Phase30 request structure/body/mapping interrogation raises exact `PHASE30_REQUEST_STRUCTURE_INVALID`.
AC-097 invalid Phase30 safety state raises exact `PHASE30_REQUEST_SAFETY_INVALID`.
AC-098 invalid Phase31-context -> Phase30 reference binding raises exact `PHASE30_CONTEXT_BINDING_INVALID`.
AC-099 invalid Phase30 materialization fingerprint raises exact `PHASE30_MATERIALIZATION_FINGERPRINT_INVALID`.
AC-100 invalid Phase31 claim fingerprint raises exact `PHASE31_CLAIM_FINGERPRINT_INVALID`.
AC-101 invalid Phase32 authority-result exact runtime type, exact opaque-reference validity, echo/reference equality, or commit binding raises exact `PHASE32_AUTHORITY_RESULT_BINDING_INVALID`; equality never substitutes for exact `type(value) is str` where Phase32 requires exact str.
AC-102 invalid Phase32 evidence fingerprint raises exact `PHASE32_EVIDENCE_FINGERPRINT_INVALID`.
AC-103 malformed/invalid success durable-record 13-field primitive/format state raises exact `PHASE33_DURABLE_RECORD_STRUCTURE_INVALID`; `authorization_authority_reference` additionally satisfies the strict Phase33 durable-authority config exact-reference and strict UTF-8 contract before fingerprint recomputation.
AC-104 exact 16-key durable-record fingerprint mismatch raises exact `PHASE33_DURABLE_RECORD_FINGERPRINT_INVALID` before historical-reference/source binding checks.
AC-105 deterministic historical authority-result or consumption reference self-binding mismatch raises exact `PHASE33_DURABLE_RECORD_REFERENCE_SELF_BINDING_INVALID`.
AC-106 self-integrity-valid durable record that does not exactly bind to validated Phase33/32/31 source graph raises exact `PHASE33_DURABLE_RECORD_SOURCE_BINDING_INVALID`.
AC-107 invalid Phase33 verification fingerprint after all applicable durable-record gates raises exact `PHASE33_VERIFICATION_FINGERPRINT_INVALID`.
AC-108 any section 12.4 provider-semantic mismatch after otherwise self-consistent Phase30 structure/materialization raises exact `PROVIDER_REQUEST_CONTRACT_INVALID`.

20.10 Precedence / exception / graph / governance / Final-Review-defect traceability
AC-109 if multiple defects coexist, the first public validation error is determined only by the 24-step ordering in sections 15 and 16; helpers/refactoring may not change this observable precedence.
AC-110 malformed nested dataclass values/body mappings cannot expose raw `AttributeError`, `KeyError`, or JSON-serialization `TypeError`; they map only to the exact active contract error defined by sections 15-16.
AC-111 unexpected Python exceptions outside the explicitly defined malformed-input validation boundary propagate unchanged; `KeyboardInterrupt`/`SystemExit` propagate; explicit `AssertionError("PHASE34_INTERNAL_SAFETY_STATE_DEFECT")` is an internal implementation defect outside the public error set and is never converted into a snapshot.
AC-112 FCR-01 correction is exact: `phase32_snapshot = source_snapshot.source_snapshot`; `phase31_snapshot = phase32_snapshot.source_snapshot`; `request_snapshot = phase31_snapshot.source_snapshot`; equivalent direct Phase30 expression is `source_snapshot.source_snapshot.source_snapshot.source_snapshot`.
AC-113 success durable-record verification is integrity-first: 13-field structure -> 16-key record fingerprint -> deterministic-reference self-binding -> source-graph binding -> Phase33 verification fingerprint; cross-bound evidence/record construction is rejected.
AC-114 A3-FCR-04 is closed: `PHASE34_SAFETY_STATE_CONSTRUCTION_INVALID` is absent from the public validation set, no caller-controlled trigger is claimed, and impossible post-validation Phase34-state contradiction is classified only as the internal defect in AC-111.
AC-115 prior governance fixes remain exact: future implementation gate refers to approval of this exact DRAFT-A6 identity, and the only exact `PHASE34_DRAFT_A6` draft-status value is `DESIGN_ONLY_NOT_APPROVED`.
AC-116 prior Final-Review-defect traceability is maintained: A3-FCR-01 -> section 7/AC-115; A3-FCR-02 -> header/section 23/AC-115; A3-FCR-03 -> sections 9.4-9.7, 15-16, AC-013..AC-018/AC-103..AC-113; A3-FCR-04 -> sections 15-16, AC-111/AC-114; A2 FCR-01 correction -> sections 1-2/AC-039/AC-112; A4-FCR-01 -> section 9.4/step 19/AC-103/AC-117..AC-119; A4-FCR-02 -> section 10.2/step 17/AC-101/AC-120..AC-122; A5 strict-UTF8/source-producibility hardening -> sections 9.3-9.4/10.1/11.2, steps 7-9 and 19, AC-123..AC-124; A5-FCR-01 -> section 9.3/step 7/AC-125/AC-126/AC-128; A5-FCR-02 -> section 9.1/AC-127/AC-128; A5-FCR-03 -> AC-125..AC-128.

20.11 A4 Final-Review exactness-edge closure criteria
AC-117 with an otherwise valid upstream source graph whose Phase31 authority reference is `"authority-1"`, mutating only the success durable-record `authorization_authority_reference` to `" authority-1 "` is rejected at step 19 with exact `PHASE33_DURABLE_RECORD_STRUCTURE_INVALID` even if all durable-record-dependent fingerprints/references are recomputed consistently.
AC-118 success durable-record authorization-authority reference length 129 is rejected at step 19 with exact `PHASE33_DURABLE_RECORD_STRUCTURE_INVALID` before durable-record fingerprint recomputation.
AC-119 success durable-record authorization-authority reference containing U+0000..U+001F or U+007F is rejected at step 19 with exact `PHASE33_DURABLE_RECORD_STRUCTURE_INVALID` before durable-record fingerprint recomputation.
AC-120 any nested Phase32 `authority_result` asserted approval/conformance reference that is a `str` subclass rather than exact `str` is rejected at step 17 with exact `PHASE32_AUTHORITY_RESULT_BINDING_INVALID` even when equality to the outer snapshot value is True.
AC-121 any nested Phase32 `authority_result.decision` that is a `str` subclass or other non-exact-str value is rejected at step 17 with exact `PHASE32_AUTHORITY_RESULT_BINDING_INVALID` before equality to `AUTHORITY_REPORTED_CONSUMED` is accepted.
AC-122 nested Phase32 `authority_result_reference` or `consumption_reference` must be exact `str`, satisfy the exact Phase32 opaque-reference contract, and exactly equal the same-named outer Phase32 snapshot field; `str` subclasses, whitespace-padded, overlength, control-character, or mismatched values are rejected at step 17 with exact `PHASE32_AUTHORITY_RESULT_BINDING_INVALID`.
AC-123 every Phase33-success authority-critical arbitrary reference that Phase33 had to encode for its durable transaction is strict UTF-8 encodable without surrogate-pass/replacement: a non-UTF8-encodable outer Phase33 `backend_instance_reference` is rejected at step 7 with exact `PHASE33_STATE_INVARIANT_INVALID`, and a non-UTF8-encodable success durable-record field among fields 1..5 or 7..8 is rejected at step 19 with exact `PHASE33_DURABLE_RECORD_STRUCTURE_INVALID` before record-fingerprint recomputation.
AC-124 Phase33 verifier-producibility is branch-complete: on both success and INDETERMINATE inputs, a whitespace-padded/overlength/control-character Phase31 authorization-authority reference that cannot satisfy the Phase33 config-reference syntax, or any required embedded Phase31/Phase32 source reference that is not strict UTF-8 encodable, is rejected before snapshot construction through step 9 `PHASE31_STATE_OR_REFERENCE_INVALID` or step 8 `PHASE32_STATE_OR_RESULT_INVALID` as applicable; no synthetic Phase33 INDETERMINATE snapshot may bypass these local preconditions.
AC-125 on both SUCCESS and Phase33 INDETERMINATE inputs, a `ledger_schema_reference` that is a `str` subclass rather than exact `str` is rejected at step 7 with exact `PHASE33_STATE_INVARIANT_INVALID` before any Phase33 verification-fingerprint recomputation.
AC-126 on both SUCCESS and Phase33 INDETERMINATE inputs, an exact `str` `ledger_schema_reference` whose value differs from `kiwoom-watchlist-order-authorization-durable-ledger-v1` is rejected at step 7 with exact `PHASE33_STATE_INVARIANT_INVALID`.
AC-127 the Phase33 verification-fingerprint envelope key `ledger_schema_reference` uses only the exact literal constant `"kiwoom-watchlist-order-authorization-durable-ledger-v1"`; the snapshot field is separately validated but is not the envelope value source.
AC-128 a synthetic `str` subclass ledger-schema field that is equal to the literal and serializes to the same canonical JSON/hash is still rejected by the step-7 exact-runtime-type gate before fingerprint recomputation; hash equality cannot bypass type validation.

Future implementation full regression must use the then-current exact expected count with failures=0, errors=0, unauthorized skipped=0. This DRAFT-A6 does not invent a post-implementation test total. Current inherited baseline remains 1285/1285 and is not a current-request Actual Rerun.

21. Recovery / rollback contract

Design/review stage:
- no repository mutation
- no rollback required

Future implementation, only if separately approved:
- only exact approved implementation/test paths may change
- existing user changes must be preserved
- no automatic reset/restore/clean/revert
- failure preserves current state for evidence
- any correction resets validation 1..5 and reruns from the beginning
- Git add/commit/push require separate approval

Runtime Phase34:
- no transaction/resource owned
- no automatic retry
- no rollback side effect
- no second authority attempt
- malformed local input returns no snapshot
- validated Phase33 INDETERMINATE remains Phase34 INDETERMINATE

22. Future boundary after eventual Phase34 completion

Only if separate official review, README registration, implementation, testing, commit, and closure gates later pass may Phase34 establish:
- `PHASE33_DURABLE_VERIFICATION_BOUND=YES`
- `PHASE32_EVIDENCE_FINGERPRINT_REVALIDATED=YES`
- `PHASE31_CLAIM_REPLAY_BINDING_REVALIDATED=YES`
- `PHASE30_PROVIDER_REQUEST_BINDING_VERIFIED=YES`
- `LOCAL_PROVIDER_CONTRACT_VERIFIED=YES`
- `PROVIDER_SEND_ELIGIBILITY_CANDIDATE_READY=YES` only on the success path
- `AUTHORITY_APPROVAL_PROVENANCE_VERIFIED=NO`
- `AUTHORITY_CONFORMANCE_PROVENANCE_VERIFIED=NO`
- `PROVIDER_SEND_ELIGIBILITY_AUTHORIZED=NO`
- `TRANSPORT_ALLOWED=NO`
- `PRODUCTION_AUTHORITY_USE_AUTHORIZED=NO`

A separate later contract remains mandatory before provider-send permission or any actual `kt10000` POST.
The Phase34 candidate snapshot alone must never be treated as sufficient authorization.

23. DRAFT-A6 governance

Exact status:
- `PHASE34_DRAFT_A6=DESIGN_ONLY_NOT_APPROVED`
- `PHASE34_DRAFT_A6_APPROVED_AS_OFFICIAL=NO`
- `PHASE34_DRAFT_A6_FINAL_CONTRACT_REVIEW=NOT_PERFORMED`
- `A2_FCR_01_RETRACTED=YES`
- `A2_FCR_01_OBJECT_GRAPH_DEFECT=NO`
- `A2_EXISTING_PHASE30_REQUEST_PATH_PRESERVED=YES`
- `A3_FCR_01_STALE_IMPLEMENTATION_APPROVAL_TARGET=REVISED_IN_A4_CANDIDATE`
- `A3_FCR_02_DRAFT_STATUS_EXACT_VALUE_CONFLICT=REVISED_IN_A4_CANDIDATE`
- `A3_FCR_03_DURABLE_RECORD_SELF_INTEGRITY_SOURCE_BINDING_GAP=REVISED_IN_A4_CANDIDATE`
- `A3_FCR_04_SAFETY_STATE_PUBLIC_ERROR_REACHABILITY_GAP=REVISED_IN_A4_CANDIDATE`
- `A4_FCR_01_PHASE33_DURABLE_AUTHORITY_REFERENCE_EXACTNESS_GAP=REVISED_IN_A5_CANDIDATE`
- `A4_FCR_02_PHASE32_NESTED_AUTHORITY_RESULT_EXACT_RUNTIME_TYPE_GAP=REVISED_IN_A5_CANDIDATE`
- `A5_FCR_01_PHASE33_LEDGER_SCHEMA_REFERENCE_EXACT_RUNTIME_TYPE_GAP=REVISED_IN_A6_CANDIDATE`
- `A5_FCR_02_PHASE33_VERIFICATION_FINGERPRINT_LEDGER_SCHEMA_VALUE_SOURCE_DRIFT=REVISED_IN_A6_CANDIDATE`
- `A5_FCR_03_LEDGER_SCHEMA_ACCEPTANCE_COVERAGE_GAP=REVISED_IN_A6_CANDIDATE`
- `README_REGISTRATION_AUTHORIZED=NO`
- `IMPLEMENTATION_AUTHORIZED=NO`
- `CURRENT_PHASE=PHASE33`
- `GIT_ADD_COMMIT_PUSH_AUTHORIZED=NO`
- `PROVIDER_SEND_ELIGIBILITY_AUTHORIZED=NO`
- `TRANSPORT_ALLOWED=NO`
- `ORDER_SUBMISSION_AUTHORIZED=NO`
- `PRODUCTION_AUTHORITY_USE_AUTHORIZED=NO`

This artifact itself does not modify README, repository source/test files, dependencies, Git state, credentials, provider/network/account/order state, or Current Phase.

The only permitted next governance action after this preparation is a separate fresh:
`Phase34 — New Contract DRAFT-A6 Final Contract Review / Approval Decision`

That separate review must perform its own current-request search/review/analysis/validation gates. This Preparation result, its searches, and its validation 1..4 must not be reused as that future review's required fresh counts.
DRAFT-A6 must not be treated as approved merely because this artifact exists.

---

## 24. Official governance

The status below is normative when this exact payload is present in `README.md`:

- `PHASE34_DRAFT_A6_FINAL_CONTRACT_REVIEW=PASS`
- `DRAFT_A6_OFFICIAL_CONTRACT_APPROVAL=PASS`
- `PHASE34_DRAFT_A6_APPROVED_AS_OFFICIAL=YES`
- `DRAFT_A6_CONTENT_REVISION_REQUIRED=NO`
- `DRAFT_A7_REQUIRED=NO`
- `PHASE34_README_OFFICIAL_CONTRACT_REGISTERED=YES`
- `PHASE34_IMPLEMENTATION_APPROVED=YES`
- `CURRENT_PHASE=PHASE34`
- `PROVIDER_SEND_ELIGIBILITY_AUTHORIZED=NO`
- `TRANSPORT_ALLOWED=NO`
- `PRODUCTION_AUTHORITY_USE_AUTHORIZED=NO`
- `CREDENTIAL_TOKEN_ACCOUNT_PROVIDER_NETWORK_ORDER_ACTION_AUTHORIZED=NO`
- `GIT_ADD_COMMIT_PUSH_APPROVED=NO`

Exact README registration does not authorize Phase34 implementation, source/test mutation, dependency or environment mutation, Git mutation, credential/token/provider/account/order action, provider transport, production authority use, or Current Phase alignment.

Phase34 implementation remains a separately approved step after exact README registration.

## 25. Phase34 Closure / Current Phase alignment

Closure status:

- `PHASE34_IMPLEMENTATION=COMPLETE`
- `PHASE34_TESTING=PASS`
- `PHASE34_CLOSURE=PASS`
- `CURRENT_PHASE=PHASE34`
- `PHASE34_IMPLEMENTATION_COMMIT=6ea5b9edf153c1a2869da280ca0aeacd5408746f`
- `PHASE34_FULL_REGRESSION_BASELINE_TEST_COUNT=1413`
- `PHASE34_FULL_REGRESSION_V5_TEST_COUNT=1413`
- `PHASE34_FULL_REGRESSION_FAILURES=0`
- `PHASE34_FULL_REGRESSION_ERRORS=0`
- `PHASE34_FULL_REGRESSION_SKIPPED=0`
- `PHASE34_FULL_REGRESSION_EXIT_CODE=0`
- `PHASE33_DURABLE_VERIFICATION_BOUND=YES`
- `PHASE32_EVIDENCE_FINGERPRINT_REVALIDATED=YES`
- `PHASE31_CLAIM_REPLAY_BINDING_REVALIDATED=YES`
- `PHASE30_PROVIDER_REQUEST_BINDING_VERIFIED=YES`
- `LOCAL_PROVIDER_CONTRACT_VERIFIED=YES`
- `AUTHORITY_APPROVAL_PROVENANCE_VERIFIED=NO`
- `AUTHORITY_CONFORMANCE_PROVENANCE_VERIFIED=NO`
- `PROVIDER_SEND_ELIGIBILITY_AUTHORIZED=NO`
- `TRANSPORT_ALLOWED=NO`
- `PRODUCTION_AUTHORITY_USE_AUTHORIZED=NO`
- `CREDENTIAL_TOKEN_ACCOUNT_PROVIDER_NETWORK_ORDER_ACTION_AUTHORIZED=NO`
- `GIT_ADD_COMMIT_PUSH_APPROVED=NO`
- `GIT_PUSH=NOT_PERFORMED`

Phase34 closure establishes only the validated local provider-send eligibility candidate boundary.
It does not authorize provider transport, credential/account access, order action, production authority use, or an actual kt10000 POST.

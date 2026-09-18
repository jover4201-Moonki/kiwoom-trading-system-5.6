# Kiwoom Trading System

키움증권 REST API와 WebSocket을 기반으로 구축하는
한국 주식 단기매매 지원 시스템입니다.

## Current Phase

Phase 31 — demo Kiwoom Cash BUY-Order Authorization Consumption Claim & Replay-Guard Preparation Snapshot 기반선 v1.0

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

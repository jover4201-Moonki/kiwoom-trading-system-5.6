# Kiwoom Trading System

키움증권 REST API와 WebSocket을 기반으로 구축하는
한국 주식 단기매매 지원 시스템입니다.

## Current Phase

Phase 22 — demo Risk Check 통과 후보 Order Permission 평가 스냅샷 기반선 v1.0

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

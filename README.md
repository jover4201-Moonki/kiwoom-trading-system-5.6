# Kiwoom Trading System

키움증권 REST API와 WebSocket을 기반으로 구축하는
한국 주식 단기매매 지원 시스템입니다.

## Current Phase

Phase 5 - Kiwoom WebSocket Demo Baseline

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
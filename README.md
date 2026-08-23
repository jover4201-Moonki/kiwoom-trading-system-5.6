# Kiwoom Trading System

키움증권 REST API와 WebSocket을 기반으로 구축하는
한국 주식 단기매매 지원 시스템입니다.

## Current Phase

Phase 2 - Project Structure

## Safety Principle

Signal -> Risk Check -> Order Permission -> Order

신호엔진과 주문엔진은 직접 연결하지 않습니다.

API Key, App Secret, 계좌 비밀정보는 소스코드와 Git에 저장하지 않습니다.

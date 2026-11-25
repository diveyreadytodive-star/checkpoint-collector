# CHECKPOINT 11팀 데이터 수집 (GitHub Actions)

## 1회 설정 (10분)
1. 공공데이터포털(data.go.kr)에서 아래 4개를 활용신청(자동승인) → 마이페이지 **일반 인증키(Decoding)** 복사
   - 경기도_버스도착정보 조회(15080346), 버스위치정보 조회(15080648), 버스노선 조회(15080662), 정류소 조회(15080666)
2. (선택) 서울 열린데이터광장 인증키 → 따릉이 재고도 같이 수집
3. GitHub에서 **private 저장소** 새로 만들고 이 폴더 파일 전부 업로드 (`.github/workflows/collect.yml` 경로 그대로)
4. 저장소 Settings → Secrets and variables → Actions → New repository secret
   - `GG_KEY` = 공공데이터포털 Decoding 키
5. Actions 탭 → collect → **Run workflow** (until_hour에 지금+1 정도) 로 테스트
   - 로그에서 `[ok] 8800 ...`, `[info] 위치정보 응답 필드: ...`, `data.go.kr HTTP 200` 확인

이후 평일 출근(06~10시)·퇴근(16~21시)마다 자동 실행되고, `data/` 폴더에 CSV가 커밋됩니다.

## 수집 노선
| 노선 | 기준 정류장 | 시간대 |
|---|---|---|
| 8800 | 순천향대학병원(한남동) 102000070 | 출퇴근 |
| 1112 | 잠실역.잠실대교남단(중) 123000001 | 출퇴근 |
| 7770 | 사당역(중) 121001315 | 퇴근 |

예비(꺼 둠): M5443 홈플러스서수원점(출근), M5107 노선 전체(퇴근) — `course_collect.py`의 TARGETS에서 주석 해제

## 주의
- GitHub 서버는 해외에 있어서 일부 국내 API가 막힐 수 있음 → 테스트 로그의 HTTP 코드가 200이 아니면
  팀원 PC에서 `python3 course_collect.py` 로 직접 돌리거나 self-hosted runner로 전환.
- GitHub 예약 실행은 5~20분 늦게 시작될 수 있음 (그래서 10분 일찍 예약).

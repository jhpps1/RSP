#!/bin/bash

echo "==========================================="
echo "    논문 검색 데모 시작"
echo "==========================================="
echo

echo "[1/4] Docker 컨테이너 시작 중..."
docker-compose up -d --build

echo
echo "[2/4] 서비스 준비 완료 대기 중..."
sleep 30

echo
echo "[3/4] 샘플 데이터 및 임베딩 생성 중..."
docker-compose exec api python create_embeddings.py

echo
echo "[4/4] 데모 환경 준비 완료!"
echo
echo "==========================================="
echo "    접속 정보"
echo "==========================================="
echo "웹 UI:        http://localhost:3000"
echo "API 문서:     http://localhost:8000/docs"  
echo "API 상태:     http://localhost:8000/health"
echo "==========================================="
echo
echo "브라우저에서 http://localhost:3000 으로 접속하세요!"
echo
echo "종료하려면 Ctrl+C 를 누르고 다음 명령어를 실행하세요:"
echo "docker-compose down"
echo
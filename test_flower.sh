#!/bin/bash

################################################################################
# TEST_FLOWER.SH - Validación automática de Flower (Celery Monitor)
# Red Team SaaS Professional - QA Automation
################################################################################

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

FLOWER_URL="http://localhost:5555"
REPORT_FILE="test_flower_report.txt"

TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

print_header() {
    echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC} $1"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"
}

print_test() { echo -e "${YELLOW}→${NC} $1"; }
print_pass() { echo -e "${GREEN}✓${NC} $1"; TESTS_PASSED=$((TESTS_PASSED + 1)); }
print_fail() { echo -e "${RED}✗${NC} $1"; TESTS_FAILED=$((TESTS_FAILED + 1)); }
log_result() { echo "$1" >> "$REPORT_FILE"; }
increment_test() { TESTS_TOTAL=$((TESTS_TOTAL + 1)); }

test_flower_accessible() {
    print_header "TEST 1: Flower Accessible"
    increment_test
    
    print_test "GET $FLOWER_URL"
    
    local response=$(curl -s -w "\n%{http_code}" "$FLOWER_URL")
    local http_code=$(echo "$response" | tail -n 1)
    
    if [ "$http_code" = "200" ]; then
        print_pass "Flower accesible (HTTP $http_code)"
        log_result "✓ Flower accesible"
    else
        print_fail "HTTP $http_code"
        log_result "✗ Flower: HTTP $http_code"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

test_flower_api() {
    print_header "TEST 2: Flower API"
    increment_test
    
    print_test "GET $FLOWER_URL/api/workers"
    
    local response=$(curl -s -w "\n%{http_code}" "$FLOWER_URL/api/workers")
    local http_code=$(echo "$response" | tail -n 1)
    local body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        if echo "$body" | grep -q "{"; then
            print_pass "Flower API funciona"
            log_result "✓ API: OK"
        else
            print_fail "Response inválida"
            log_result "✗ API: Response inválida"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
    else
        print_fail "HTTP $http_code"
        log_result "✗ API: HTTP $http_code"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

test_flower_workers() {
    print_header "TEST 3: Workers Status"
    increment_test
    
    print_test "Verificar workers conectados"
    
    local response=$(curl -s "$FLOWER_URL/api/workers")
    
    # Contar workers
    local worker_count=$(echo "$response" | grep -o '"[^"]*":' | wc -l)
    
    if [ "$worker_count" -gt 0 ]; then
        echo "  Workers encontrados: $worker_count"
        print_pass "Workers disponibles"
        log_result "✓ Workers: $worker_count detectados"
    else
        print_fail "Sin workers conectados"
        log_result "⚠ Workers: Ninguno conectado"
        # No es un fallo crítico, solo warning
    fi
}

test_flower_tasks_api() {
    print_header "TEST 4: Tasks API"
    increment_test
    
    print_test "GET $FLOWER_URL/api/tasks"
    
    local response=$(curl -s -w "\n%{http_code}" "$FLOWER_URL/api/tasks")
    local http_code=$(echo "$response" | tail -n 1)
    
    if [ "$http_code" = "200" ]; then
        print_pass "Tasks API funciona"
        log_result "✓ Tasks API: OK"
    else
        print_fail "HTTP $http_code"
        log_result "✗ Tasks API: HTTP $http_code"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

test_flower_stats() {
    print_header "TEST 5: Statistics"
    increment_test
    
    print_test "GET $FLOWER_URL/api/queues/length"

    local response=$(curl -s -w "\n%{http_code}" "$FLOWER_URL/api/queues/length")
    local http_code=$(echo "$response" | tail -n 1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "405" ] || [ "$http_code" = "204" ]; then
        print_pass "Endpoints de estadísticas disponibles"
        log_result "✓ Stats: OK"
    else
        print_fail "HTTP $http_code"
        log_result "✗ Stats: HTTP $http_code"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

test_flower_performance() {
    print_header "TEST 6: Performance"
    increment_test
    
    print_test "Medir tiempo de respuesta"
    
    local time=$(curl -s -o /dev/null -w "%{time_total}" "$FLOWER_URL")
    
    echo "  Response time: ${time}s"
    
    if awk "BEGIN {exit !($time < 2)}"; then
        print_pass "Rendimiento aceptable: ${time}s"
        log_result "✓ Performance: OK"
    else
        print_fail "Rendimiento bajo: ${time}s"
        log_result "✗ Performance: Lento"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║      TEST FLOWER - Red Team SaaS Professional             ║"
    echo "║      Validación de Celery Task Monitor                     ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    > "$REPORT_FILE"
    log_result "Flower Tests - $(date)"
    log_result "========================================"
    
    # Verificar conectividad
    print_test "Verificando conectividad a $FLOWER_URL..."
    if ! curl -s "$FLOWER_URL" > /dev/null 2>&1; then
        echo -e "${RED}✗ Flower no está disponible${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Flower disponible${NC}\n"
    
    # Tests
    test_flower_accessible
    test_flower_api
    test_flower_workers
    test_flower_tasks_api
    test_flower_stats
    test_flower_performance
    
    # Reporte
    print_header "REPORTE FINAL"
    
    echo "Total Tests:     $TESTS_TOTAL"
    echo "Passed:          $TESTS_PASSED"
    echo "Failed:          $TESTS_FAILED"
    
    local percentage=$((TESTS_PASSED * 100 / TESTS_TOTAL))
    echo "Success Rate:    ${percentage}%"
    
    log_result ""
    log_result "SUMMARY: $TESTS_PASSED/$TESTS_TOTAL passed"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "\n${GREEN}✓ TODOS LOS TESTS PASARON${NC}"
        exit 0
    else
        echo -e "\n${YELLOW}⚠ ALGUNOS TESTS FALLARON${NC}"
        exit 1
    fi
}

main "$@"

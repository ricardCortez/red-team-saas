#!/bin/bash

################################################################################
# TEST_PROMETHEUS.SH - Validación automática de Prometheus
# Red Team SaaS Professional - QA Automation
################################################################################

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROMETHEUS_URL="http://localhost:9090"
REPORT_FILE="test_prometheus_report.txt"

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

test_prometheus_accessible() {
    print_header "TEST 1: Prometheus Accessible"
    increment_test
    
    print_test "GET $PROMETHEUS_URL"
    
    local response=$(curl -s -w "\n%{http_code}" "$PROMETHEUS_URL")
    local http_code=$(echo "$response" | tail -n 1)
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "302" ]; then
        print_pass "Prometheus accesible (HTTP $http_code)"
        log_result "✓ Prometheus accesible"
    else
        print_fail "HTTP $http_code"
        log_result "✗ Prometheus: HTTP $http_code"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

test_prometheus_api() {
    print_header "TEST 2: Prometheus API"
    increment_test
    
    print_test "GET $PROMETHEUS_URL/api/v1/query?query=up"
    
    local response=$(curl -s "$PROMETHEUS_URL/api/v1/query?query=up")
    
    if echo "$response" | grep -q '"status":"success"'; then
        print_pass "Prometheus API funciona"
        log_result "✓ API: OK"
    else
        print_fail "API no responde correctamente"
        log_result "✗ API: Error"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

test_metrics_up() {
    print_header "TEST 3: Métricas Disponibles"
    increment_test
    
    print_test "Query: up (verificar si targets están UP)"
    
    local response=$(curl -s "$PROMETHEUS_URL/api/v1/query?query=up")
    
    if echo "$response" | grep -q '"value"'; then
        print_pass "Métricas disponibles"
        log_result "✓ Métricas: OK"
        
        # Extraer valor
        local value=$(echo "$response" | grep -o '"value":\["[^"]*","[^"]*' | tail -1 | cut -d'"' -f4)
        echo "  Valor: $value"
    else
        print_fail "Sin métricas"
        log_result "✗ Métricas: No disponibles"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

test_prometheus_targets() {
    print_header "TEST 4: Targets Status"
    increment_test
    
    print_test "GET $PROMETHEUS_URL/api/v1/targets"
    
    local response=$(curl -s "$PROMETHEUS_URL/api/v1/targets")
    
    if echo "$response" | grep -q '"status":"success"'; then
        # Contar targets UP
        local active=$(echo "$response" | grep -o '"health":"up"' | wc -l)
        
        if [ "$active" -gt 0 ]; then
            print_pass "Targets encontrados: $active"
            log_result "✓ Targets: $active activos"
        else
            print_fail "Sin targets activos"
            log_result "✗ Targets: Ninguno activo"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
    else
        print_fail "No se pueden obtener targets"
        log_result "✗ Targets: Error"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

test_http_requests_metric() {
    print_header "TEST 5: HTTP Requests Metric"
    increment_test
    
    print_test "Query: http_requests_total"
    
    local response=$(curl -s "$PROMETHEUS_URL/api/v1/query?query=http_requests_total")
    
    if echo "$response" | grep -q '"value"'; then
        print_pass "Métrica de requests registrada"
        log_result "✓ HTTP Requests: OK"
    else
        print_fail "Métrica no disponible aún"
        log_result "⚠ HTTP Requests: No disponible"
    fi
}

test_prometheus_performance() {
    print_header "TEST 6: Performance"
    increment_test
    
    local time=$(curl -s -o /dev/null -w "%{time_total}" "$PROMETHEUS_URL")
    
    echo "  Response time: ${time}s"
    
    if awk "BEGIN {exit !($time < 1)}"; then
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
    echo "║      TEST PROMETHEUS - Red Team SaaS Professional          ║"
    echo "║      Validación de Métricas y Monitoring                   ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    > "$REPORT_FILE"
    log_result "Prometheus Tests - $(date)"
    log_result "========================================"
    
    # Verificar conectividad
    print_test "Verificando conectividad a $PROMETHEUS_URL..."
    if ! curl -s "$PROMETHEUS_URL" > /dev/null 2>&1; then
        echo -e "${RED}✗ Prometheus no está disponible${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Prometheus disponible${NC}\n"
    
    # Tests
    test_prometheus_accessible
    test_prometheus_api
    test_metrics_up
    test_prometheus_targets
    test_http_requests_metric
    test_prometheus_performance
    
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

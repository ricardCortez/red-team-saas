#!/bin/bash

################################################################################
# TEST_SWAGGER.SH - Validación automática de Swagger UI
# Red Team SaaS Professional - QA Automation
################################################################################

set -e

# COLORES
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# VARIABLES
SWAGGER_URL="http://localhost:8000/api/docs"
REDOC_URL="http://localhost:8000/api/redoc"
OPENAPI_URL="http://localhost:8000/api/openapi.json"

REPORT_FILE="test_swagger_report.txt"

TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

################################################################################
# FUNCIONES
################################################################################

print_header() {
    echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC} $1"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"
}

print_test() {
    echo -e "${YELLOW}→${NC} $1"
}

print_pass() {
    echo -e "${GREEN}✓${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

print_fail() {
    echo -e "${RED}✗${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

log_result() {
    echo "$1" >> "$REPORT_FILE"
}

increment_test() {
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
}

################################################################################
# TESTS
################################################################################

test_swagger_accessible() {
    print_header "TEST 1: Swagger UI Accessible"
    increment_test
    
    print_test "GET $SWAGGER_URL"
    
    local response=$(curl -s -w "\n%{http_code}" "$SWAGGER_URL")
    local http_code=$(echo "$response" | tail -n 1)
    local body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        print_pass "Swagger UI accesible (HTTP $http_code)"
        log_result "✓ Swagger UI accesible"
    else
        print_fail "HTTP $http_code (esperado 200)"
        log_result "✗ Swagger UI: HTTP $http_code"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

test_swagger_html() {
    print_header "TEST 2: Swagger HTML Content"
    increment_test
    
    print_test "Verificar contenido HTML"
    
    local response=$(curl -s "$SWAGGER_URL")
    
    if echo "$response" | grep -q "swagger-ui"; then
        print_pass "Contenido Swagger UI detectado"
        log_result "✓ Swagger HTML válido"
    else
        print_fail "No contiene swagger-ui"
        log_result "✗ Swagger HTML inválido"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

test_openapi_json() {
    print_header "TEST 3: OpenAPI JSON Schema"
    increment_test
    
    print_test "GET $OPENAPI_URL"
    
    local response=$(curl -s -w "\n%{http_code}" "$OPENAPI_URL")
    local http_code=$(echo "$response" | tail -n 1)
    local body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        # Validar JSON
        if echo "$body" | grep -q '"openapi"'; then
            print_pass "OpenAPI JSON válido"
            log_result "✓ OpenAPI JSON: OK"
        else
            print_fail "JSON inválido"
            log_result "✗ OpenAPI JSON: Inválido"
            TESTS_FAILED=$((TESTS_FAILED + 1))
            return 1
        fi
    else
        print_fail "HTTP $http_code"
        log_result "✗ OpenAPI JSON: HTTP $http_code"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

test_endpoints_documented() {
    print_header "TEST 4: Endpoints Documented"
    increment_test
    
    print_test "Verificar endpoints en OpenAPI"
    
    local endpoints=(
        "/health"
        "/api/v1/auth/register"
        "/api/v1/auth/login"
        "/api/v1/auth/refresh"
        "/api/v1/auth/me"
    )
    
    local response=$(curl -s "$OPENAPI_URL")
    local missing=0
    
    for endpoint in "${endpoints[@]}"; do
        if echo "$response" | grep -q "\"$endpoint\""; then
            echo "  ✓ $endpoint"
        else
            echo "  ✗ $endpoint"
            ((missing++))
        fi
    done
    
    if [ $missing -eq 0 ]; then
        print_pass "Todos los endpoints documentados"
        log_result "✓ Endpoints documentados"
    else
        print_fail "$missing endpoints faltantes"
        log_result "✗ Faltan $missing endpoints"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

test_schemas_documented() {
    print_header "TEST 5: Pydantic Schemas"
    increment_test
    
    print_test "Verificar modelos/schemas"
    
    local response=$(curl -s "$OPENAPI_URL")
    
    local schemas=(
        "UserCreate"
        "UserResponse"
        "Token"
    )
    
    local missing=0
    
    for schema in "${schemas[@]}"; do
        if echo "$response" | grep -q "\"$schema\""; then
            echo "  ✓ $schema"
        else
            echo "  ✗ $schema"
            ((missing++))
        fi
    done
    
    if [ $missing -eq 0 ]; then
        print_pass "Todos los schemas documentados"
        log_result "✓ Schemas: OK"
    else
        print_fail "$missing schemas faltantes"
        log_result "✗ Faltan schemas"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

test_redoc_accessible() {
    print_header "TEST 6: ReDoc Accessible"
    increment_test
    
    print_test "GET $REDOC_URL"
    
    local response=$(curl -s -w "\n%{http_code}" "$REDOC_URL")
    local http_code=$(echo "$response" | tail -n 1)
    
    if [ "$http_code" = "200" ]; then
        print_pass "ReDoc accesible (HTTP $http_code)"
        log_result "✓ ReDoc accesible"
    else
        print_fail "HTTP $http_code"
        log_result "✗ ReDoc: HTTP $http_code"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

test_response_headers() {
    print_header "TEST 7: Response Headers"
    increment_test
    
    print_test "Verificar headers de respuesta"
    
    local response=$(curl -s -i "$SWAGGER_URL" 2>&1)
    
    local has_content_type=$(echo "$response" | grep -i "content-type" | head -1)
    
    if [ -n "$has_content_type" ]; then
        print_pass "Content-Type header presente"
        log_result "✓ Headers correctos"
    else
        print_fail "Content-Type no presente"
        log_result "✗ Headers incompletos"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

test_swagger_performance() {
    print_header "TEST 8: Performance"
    increment_test
    
    print_test "Medir tiempo de carga de Swagger"
    
    local time=$(curl -s -o /dev/null -w "%{time_total}" "$SWAGGER_URL")
    
    echo "  Tiempo de carga: ${time}s"
    log_result "Swagger load time: ${time}s"
    
    local time_ms=$(awk "BEGIN {printf \"%d\", $time * 1000}")

    if awk "BEGIN {exit !($time_ms < 2000)}"; then
        print_pass "Tiempo de carga aceptable: ${time_ms}ms"
        log_result "✓ Rendimiento OK"
    else
        print_fail "Tiempo de carga alto: ${time_ms}ms"
        log_result "✗ Rendimiento bajo"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

################################################################################
# MAIN
################################################################################

main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║      TEST SWAGGER - Red Team SaaS Professional             ║"
    echo "║      Validación de Swagger UI y ReDoc                      ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    > "$REPORT_FILE"
    log_result "Swagger UI Tests - $(date)"
    log_result "========================================"
    
    # Verificar conectividad
    print_test "Verificando conectividad a http://localhost:8000..."
    if ! curl -s "http://localhost:8000/health" > /dev/null 2>&1; then
        echo -e "${RED}✗ API no está disponible${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ API disponible${NC}\n"
    
    # Tests
    test_swagger_accessible
    test_swagger_html
    test_openapi_json
    test_endpoints_documented
    test_schemas_documented
    test_redoc_accessible
    test_response_headers
    test_swagger_performance
    
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
        log_result "✓ STATUS: PASS"
        exit 0
    else
        echo -e "\n${RED}✗ ALGUNOS TESTS FALLARON${NC}"
        log_result "✗ STATUS: FAIL"
        exit 1
    fi
}

main "$@"

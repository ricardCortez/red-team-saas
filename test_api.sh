#!/bin/bash

################################################################################
# TEST_API.SH - Validación automática del API Backend
# Red Team SaaS Professional - QA Automation
################################################################################

set -e

# COLORES
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# VARIABLES
API_URL="http://localhost:8000"
HEALTH_ENDPOINT="$API_URL/health"
AUTH_REGISTER="$API_URL/api/v1/auth/register"
AUTH_LOGIN="$API_URL/api/v1/auth/login"
AUTH_ME="$API_URL/api/v1/auth/me"
AUTH_REFRESH="$API_URL/api/v1/auth/refresh"

REPORT_FILE="test_api_report.txt"
TEST_EMAIL="qa_test_$(date +%s)@example.com"
TEST_USERNAME="qa_user_$(date +%s)"
TEST_PASSWORD="TestPass123!"
TEST_FULLNAME="QA Test User"

# Contadores
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

################################################################################
# FUNCIONES AUXILIARES
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

save_token() {
    local token=$1
    echo "$token" > /tmp/access_token.txt
}

get_saved_token() {
    cat /tmp/access_token.txt 2>/dev/null || echo ""
}

save_refresh_token() {
    local token=$1
    echo "$token" > /tmp/refresh_token.txt
}

get_saved_refresh_token() {
    cat /tmp/refresh_token.txt 2>/dev/null || echo ""
}

################################################################################
# TESTS
################################################################################

test_api_health() {
    print_header "TEST 1: API HEALTH CHECK"
    increment_test
    
    print_test "GET $HEALTH_ENDPOINT"
    
    local response=$(curl -s -w "\n%{http_code}" "$HEALTH_ENDPOINT")
    local http_code=$(echo "$response" | tail -n 1)
    local body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        if echo "$body" | grep -q '"status":"ok"'; then
            print_pass "API Health check: OK (HTTP $http_code)"
            log_result "✓ API Health check: OK"
        else
            print_fail "API Health check: Respuesta inválida"
            log_result "✗ API Health check: Respuesta inválida"
            TESTS_FAILED=$((TESTS_FAILED + 1))
            return 1
        fi
    else
        print_fail "API Health check: HTTP $http_code (esperado 200)"
        log_result "✗ API Health check: HTTP $http_code"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

test_api_root() {
    print_header "TEST 2: ROOT ENDPOINT"
    increment_test
    
    print_test "GET $API_URL/"
    
    local response=$(curl -s -w "\n%{http_code}" "$API_URL/")
    local http_code=$(echo "$response" | tail -n 1)
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "404" ] || [ "$http_code" = "307" ]; then
        print_pass "Root endpoint accesible (HTTP $http_code)"
        log_result "✓ Root endpoint accesible"
    else
        print_fail "Root endpoint: HTTP $http_code"
        log_result "✗ Root endpoint: HTTP $http_code"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

test_auth_register() {
    print_header "TEST 3: POST /api/v1/auth/register"
    increment_test
    
    print_test "Registrar usuario: $TEST_EMAIL"
    
    local payload=$(cat <<EOF
{
    "email":"$TEST_EMAIL",
    "username":"$TEST_USERNAME",
    "password":"$TEST_PASSWORD",
    "full_name":"$TEST_FULLNAME"
}
EOF
)
    
    local response=$(curl -s -w "\n%{http_code}" -X POST "$AUTH_REGISTER" \
        -H "Content-Type: application/json" \
        -d "$payload")
    
    local http_code=$(echo "$response" | tail -n 1)
    local body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "201" ]; then
        if echo "$body" | grep -q '"email"'; then
            print_pass "POST /auth/register: OK (HTTP $http_code)"
            log_result "✓ POST /auth/register: OK"
            # Validar que no contiene password
            if ! echo "$body" | grep -q '"password_hash"'; then
                print_pass "Password no expuesto en response"
                log_result "✓ Password no expuesto"
            else
                print_fail "Password expuesto en response"
                log_result "✗ Password expuesto en response"
            fi
        else
            print_fail "POST /auth/register: Response inválida"
            log_result "✗ POST /auth/register: Response inválida"
            TESTS_FAILED=$((TESTS_FAILED + 1))
            return 1
        fi
    else
        print_fail "POST /auth/register: HTTP $http_code (esperado 201)"
        log_result "✗ POST /auth/register: HTTP $http_code"
        echo "Response: $body"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

test_auth_login() {
    print_header "TEST 4: POST /api/v1/auth/login"
    increment_test
    
    print_test "Login con: $TEST_EMAIL"

    local response=$(curl -s -w "\n%{http_code}" -X POST "$AUTH_LOGIN?email=${TEST_EMAIL}&password=${TEST_PASSWORD}")
    
    local http_code=$(echo "$response" | tail -n 1)
    local body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        if echo "$body" | grep -q '"access_token"'; then
            print_pass "POST /auth/login: OK (HTTP $http_code)"
            log_result "✓ POST /auth/login: OK"
            
            # Extraer y guardar tokens
            local access_token=$(echo "$body" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
            local refresh_token=$(echo "$body" | grep -o '"refresh_token":"[^"]*' | cut -d'"' -f4)
            
            if [ -n "$access_token" ]; then
                save_token "$access_token"
                print_pass "Access token obtenido y guardado"
                log_result "✓ Access token obtenido"
            fi
            
            if [ -n "$refresh_token" ]; then
                save_refresh_token "$refresh_token"
                print_pass "Refresh token obtenido y guardado"
                log_result "✓ Refresh token obtenido"
            fi
        else
            print_fail "POST /auth/login: No contiene access_token"
            log_result "✗ POST /auth/login: No contiene tokens"
            TESTS_FAILED=$((TESTS_FAILED + 1))
            return 1
        fi
    else
        print_fail "POST /auth/login: HTTP $http_code (esperado 200)"
        log_result "✗ POST /auth/login: HTTP $http_code"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

test_auth_me() {
    print_header "TEST 5: GET /api/v1/auth/me (PROTECTED)"
    increment_test
    
    print_test "GET /api/v1/auth/me con token válido"
    
    local token=$(get_saved_token)
    
    if [ -z "$token" ]; then
        print_fail "No hay token disponible (ejecutar login primero)"
        log_result "✗ GET /auth/me: Sin token"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
    
    local response=$(curl -s -w "\n%{http_code}" -X GET "$AUTH_ME?token=${token}")
    
    local http_code=$(echo "$response" | tail -n 1)
    local body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        if echo "$body" | grep -q '"email"'; then
            print_pass "GET /auth/me: OK (HTTP $http_code)"
            log_result "✓ GET /auth/me: OK"
        else
            print_fail "GET /auth/me: Response inválida"
            log_result "✗ GET /auth/me: Response inválida"
            TESTS_FAILED=$((TESTS_FAILED + 1))
            return 1
        fi
    else
        print_fail "GET /auth/me: HTTP $http_code (esperado 200)"
        log_result "✗ GET /auth/me: HTTP $http_code"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

test_auth_me_no_token() {
    print_header "TEST 6: GET /api/v1/auth/me (SIN TOKEN)"
    increment_test
    
    print_test "GET /api/v1/auth/me sin token (debe retornar 401)"
    
    local response=$(curl -s -w "\n%{http_code}" -X GET "$AUTH_ME")
    
    local http_code=$(echo "$response" | tail -n 1)
    
    if [ "$http_code" = "401" ] || [ "$http_code" = "403" ]; then
        print_pass "Autenticación requerida: HTTP $http_code"
        log_result "✓ Autenticación requerida"
    else
        print_fail "Debería retornar 401/403, retornó: $http_code"
        log_result "✗ Autenticación no requerida: HTTP $http_code"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

test_auth_refresh() {
    print_header "TEST 7: POST /api/v1/auth/refresh"
    increment_test
    
    print_test "Refresh token"
    
    local refresh_token=$(get_saved_refresh_token)
    
    if [ -z "$refresh_token" ]; then
        print_fail "No hay refresh token disponible"
        log_result "✗ POST /auth/refresh: Sin refresh token"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
    
    local response=$(curl -s -w "\n%{http_code}" -X POST "$AUTH_REFRESH?refresh_token=${refresh_token}")
    
    local http_code=$(echo "$response" | tail -n 1)
    local body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        if echo "$body" | grep -q '"access_token"'; then
            print_pass "POST /auth/refresh: OK (HTTP $http_code)"
            log_result "✓ POST /auth/refresh: OK"
        else
            print_fail "POST /auth/refresh: No contiene access_token"
            log_result "✗ POST /auth/refresh: Response inválida"
            TESTS_FAILED=$((TESTS_FAILED + 1))
            return 1
        fi
    else
        print_fail "POST /auth/refresh: HTTP $http_code (esperado 200)"
        log_result "✗ POST /auth/refresh: HTTP $http_code"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

test_error_invalid_email() {
    print_header "TEST 8: ERROR HANDLING - Invalid Email"
    increment_test
    
    print_test "Register con email inválido (debe retornar 422)"
    
    local payload='{"email":"invalid-email"}'
    
    local response=$(curl -s -w "\n%{http_code}" -X POST "$AUTH_REGISTER" \
        -H "Content-Type: application/json" \
        -d "$payload")
    
    local http_code=$(echo "$response" | tail -n 1)
    
    if [ "$http_code" = "422" ] || [ "$http_code" = "400" ]; then
        print_pass "Validación de email: HTTP $http_code"
        log_result "✓ Validación de email: OK"
    else
        print_fail "Debería retornar 422/400, retornó: $http_code"
        log_result "✗ Validación de email: Falla"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

test_response_content_type() {
    print_header "TEST 9: CONTENT-TYPE"
    increment_test
    
    print_test "Verificar Content-Type: application/json"
    
    local response=$(curl -s -i "$HEALTH_ENDPOINT" 2>&1 | grep -i "content-type")
    
    if echo "$response" | grep -q "application/json"; then
        print_pass "Content-Type correcto: application/json"
        log_result "✓ Content-Type: application/json"
    else
        print_fail "Content-Type incorrecto: $response"
        log_result "✗ Content-Type incorrecto"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

test_performance() {
    print_header "TEST 10: PERFORMANCE - Response Times"
    increment_test
    
    print_test "Medir tiempo de respuesta"
    
    local time_health=$(curl -s -o /dev/null -w "%{time_total}" "$HEALTH_ENDPOINT")
    
    echo "  /health: ${time_health}s"
    log_result "Response time /health: ${time_health}s"
    
    # Convertir a milisegundos
    local time_ms=$(awk "BEGIN {printf \"%d\", $time_health * 1000}")

    if awk "BEGIN {exit !($time_ms < 1000)}"; then
        print_pass "Latencia aceptable: ${time_ms}ms"
        log_result "✓ Latencia aceptable"
    else
        print_fail "Latencia alta: ${time_ms}ms"
        log_result "✗ Latencia alta"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

################################################################################
# MAIN
################################################################################

main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║      TEST API - Red Team SaaS Professional                 ║"
    echo "║      Validación Automática del Backend                     ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Limpiar reporte anterior
    > "$REPORT_FILE"
    log_result "API Backend Tests - $(date)"
    log_result "========================================"
    
    # Verificar conectividad
    print_test "Verificando conectividad a $API_URL..."
    if ! curl -s "$API_URL/health" > /dev/null 2>&1; then
        echo -e "${RED}✗ No se puede conectar a $API_URL${NC}"
        echo "  Asegúrate de que el API está corriendo"
        echo "  docker-compose up -d"
        exit 1
    fi
    echo -e "${GREEN}✓ Conectado a $API_URL${NC}\n"
    
    # Ejecutar tests
    test_api_health
    test_api_root
    test_auth_register
    test_auth_login
    test_auth_me
    test_auth_me_no_token
    test_auth_refresh
    test_error_invalid_email
    test_response_content_type
    test_performance
    
    # Reporte final
    print_header "REPORTE FINAL"
    
    echo "Total Tests:     $TESTS_TOTAL"
    echo "Passed:          $TESTS_PASSED"
    echo "Failed:          $TESTS_FAILED"
    
    local percentage=$((TESTS_PASSED * 100 / TESTS_TOTAL))
    echo "Success Rate:    ${percentage}%"
    
    log_result ""
    log_result "SUMMARY:"
    log_result "Total: $TESTS_TOTAL"
    log_result "Passed: $TESTS_PASSED"
    log_result "Failed: $TESTS_FAILED"
    log_result "Success Rate: ${percentage}%"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "\n${GREEN}✓ TODOS LOS TESTS PASARON${NC}"
        log_result ""
        log_result "✓ STATUS: PASS"
        exit 0
    else
        echo -e "\n${RED}✗ ALGUNOS TESTS FALLARON${NC}"
        log_result ""
        log_result "✗ STATUS: FAIL"
        exit 1
    fi
}

# Ejecutar
main "$@"

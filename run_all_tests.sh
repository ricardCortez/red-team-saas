#!/bin/bash

################################################################################
# RUN_ALL_TESTS.SH - Orquestador de tests QA
# Red Team SaaS Professional - Ejecuta todos los tests modulares
################################################################################

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# VARIABLES
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
RESULTS_DIR="qa_results_$TIMESTAMP"
CONSOLIDATED_REPORT="CONSOLIDATED_QA_REPORT.txt"

# Crear directorio de resultados
mkdir -p "$RESULTS_DIR"
cd "$RESULTS_DIR"

# Array de tests
TESTS=(
    "Health Check|$SCRIPT_DIR/test_health_check.sh"
    "API Backend|$SCRIPT_DIR/test_api.sh"
    "Swagger UI|$SCRIPT_DIR/test_swagger.sh"
    "Prometheus|$SCRIPT_DIR/test_prometheus.sh"
    "Flower|$SCRIPT_DIR/test_flower.sh"
)

# Contadores
TOTAL_SUITES=0
PASSED_SUITES=0
FAILED_SUITES=0

################################################################################
# FUNCIONES
################################################################################

print_banner() {
    echo ""
    echo "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo "${CYAN}║${NC}      RED TEAM SaaS - QA AUTOMATION SUITE                 ${CYAN}║${NC}"
    echo "${CYAN}║${NC}      Validación de Ambiente Completo                     ${CYAN}║${NC}"
    echo "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_header() {
    echo ""
    echo "${BLUE}┌────────────────────────────────────────────────────────────┐${NC}"
    echo "${BLUE}│${NC} $1"
    echo "${BLUE}└────────────────────────────────────────────────────────────┘${NC}"
    echo ""
}

print_test_start() {
    echo -e "${YELLOW}→${NC} Ejecutando: $1..."
}

print_test_pass() {
    echo -e "${GREEN}✓${NC} $1 - PASSED"
}

print_test_fail() {
    echo -e "${RED}✗${NC} $1 - FAILED"
}

run_test() {
    local test_name="$1"
    local test_script="$2"
    
    print_header "SUITE: $test_name"
    
    if [ ! -f "$test_script" ]; then
        print_test_fail "$test_name (script no encontrado)"
        ((FAILED_SUITES++))
        return 1
    fi
    
    # Hacer el script ejecutable
    chmod +x "$test_script"
    
    print_test_start "$test_name"
    
    # Ejecutar test y capturar resultado
    if bash "$test_script" 2>&1; then
        print_test_pass "$test_name"
        ((PASSED_SUITES++))
        return 0
    else
        print_test_fail "$test_name"
        ((FAILED_SUITES++))
        return 1
    fi
}

generate_report() {
    print_header "CONSOLIDANDO RESULTADOS"
    
    echo "Consolidating test reports..."
    
    # Crear reporte consolidado
    {
        echo "╔════════════════════════════════════════════════════════════╗"
        echo "║         QA VALIDATION CONSOLIDATED REPORT                 ║"
        echo "║         Red Team SaaS Professional                         ║"
        echo "║         Timestamp: $(date)                            ║"
        echo "╚════════════════════════════════════════════════════════════╝"
        echo ""
        echo "SUMMARY:"
        echo "────────────────────────────────────────────────────────────"
        echo "Total Test Suites:    $TOTAL_SUITES"
        echo "Passed Suites:        $PASSED_SUITES"
        echo "Failed Suites:        $FAILED_SUITES"
        echo ""
        
        local percentage=$((PASSED_SUITES * 100 / TOTAL_SUITES))
        echo "Overall Success Rate: ${percentage}%"
        echo ""
        
        echo "DETAILED RESULTS:"
        echo "────────────────────────────────────────────────────────────"
        
        # Incluir reportes individuales
        for report_file in test_*_report.txt; do
            if [ -f "$report_file" ]; then
                echo ""
                echo "▼ $report_file"
                echo "─────────────────"
                cat "$report_file"
            fi
        done
        
        echo ""
        echo "════════════════════════════════════════════════════════════"
        
        if [ $FAILED_SUITES -eq 0 ]; then
            echo "STATUS: ✓ ALL TESTS PASSED"
            echo "READY FOR NEXT PHASE: YES"
        else
            echo "STATUS: ✗ SOME TESTS FAILED"
            echo "READY FOR NEXT PHASE: NO"
        fi
        
        echo "════════════════════════════════════════════════════════════"
    } > "$CONSOLIDATED_REPORT"
    
    cat "$CONSOLIDATED_REPORT"
}

create_summary_html() {
    local html_file="QA_REPORT.html"
    
    {
        echo "<!DOCTYPE html>"
        echo "<html>"
        echo "<head>"
        echo "    <title>QA Report - Red Team SaaS</title>"
        echo "    <style>"
        echo "        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }"
        echo "        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }"
        echo "        .summary { background: white; padding: 15px; margin: 20px 0; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }"
        echo "        .pass { color: #27ae60; font-weight: bold; }"
        echo "        .fail { color: #e74c3c; font-weight: bold; }"
        echo "        table { width: 100%; border-collapse: collapse; }"
        echo "        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }"
        echo "        th { background: #34495e; color: white; }"
        echo "        .metric { display: inline-block; margin: 10px 20px; }"
        echo "    </style>"
        echo "</head>"
        echo "<body>"
        echo "    <div class='header'>"
        echo "        <h1>Red Team SaaS - QA Validation Report</h1>"
        echo "        <p>Generated: $(date)</p>"
        echo "    </div>"
        echo ""
        echo "    <div class='summary'>"
        echo "        <h2>Summary</h2>"
        echo "        <div class='metric'><span class='pass'>✓ Passed:</span> $PASSED_SUITES</div>"
        echo "        <div class='metric'><span class='fail'>✗ Failed:</span> $FAILED_SUITES</div>"
        echo "        <div class='metric'>Total: $TOTAL_SUITES</div>"
        echo "        <div class='metric'>Success Rate: $((PASSED_SUITES * 100 / TOTAL_SUITES))%</div>"
        echo "    </div>"
        echo ""
        echo "</body>"
        echo "</html>"
    } > "$html_file"
    
    echo ""
    echo "HTML Report created: $html_file"
}

################################################################################
# MAIN
################################################################################

main() {
    print_banner
    
    echo "Results Directory: $RESULTS_DIR"
    echo "Starting QA validation..."
    echo ""
    
    # Contar total de suites
    TOTAL_SUITES=${#TESTS[@]}
    
    # Ejecutar cada test
    for test in "${TESTS[@]}"; do
        IFS='|' read -r name script <<< "$test"
        
        if run_test "$name" "$script"; then
            echo ""
        else
            echo ""
        fi
    done
    
    # Generar reporte consolidado
    print_header "FINAL REPORT"
    generate_report
    
    # Crear HTML report
    create_summary_html
    
    # Mostrar resumen final
    echo ""
    echo "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo "${CYAN}║${NC}                   EXECUTION COMPLETE"
    echo "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Results saved in: $(pwd)"
    echo "Consolidated report: $CONSOLIDATED_REPORT"
    echo ""
    
    if [ $FAILED_SUITES -eq 0 ]; then
        echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
        echo -e "${GREEN}✓ READY FOR NEXT PHASE${NC}"
        exit 0
    else
        echo -e "${RED}✗ $FAILED_SUITES TEST(S) FAILED${NC}"
        echo -e "${RED}✗ FIX ISSUES BEFORE CONTINUING${NC}"
        exit 1
    fi
}

# Ejecutar main
main "$@"

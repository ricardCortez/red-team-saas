#!/bin/bash

################################################################################
# TEST_HEALTH_CHECK.SH - Quick Health Check de todos los servicios
# Red Team SaaS Professional - QA Automation
################################################################################

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║      HEALTH CHECK - Red Team SaaS Professional             ║"
echo "║      Verificación rápida de servicios                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

SERVICES=(
    "API|http://localhost:8000/health"
    "Swagger UI|http://localhost:8000/api/docs"
    "ReDoc|http://localhost:8000/api/redoc"
    "Prometheus|http://localhost:9090"
    "Grafana|http://localhost:3000"
    "Flower|http://localhost:5555"
)

UP=0
DOWN=0

for service in "${SERVICES[@]}"; do
    IFS='|' read -r name url <<< "$service"
    
    print_test="${YELLOW}→${NC}"
    
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200\|404\|302"; then
        echo -e "${GREEN}✓${NC} $name"
        ((UP++))
    else
        echo -e "${RED}✗${NC} $name"
        ((DOWN++))
    fi
done

echo ""
echo "Servicios UP:   $UP"
echo "Servicios DOWN: $DOWN"

if [ $DOWN -eq 0 ]; then
    echo -e "\n${GREEN}✓ TODOS LOS SERVICIOS ESTÁN FUNCIONANDO${NC}"
    exit 0
else
    echo -e "\n${RED}✗ ALGUNOS SERVICIOS NO ESTÁN DISPONIBLES${NC}"
    exit 1
fi

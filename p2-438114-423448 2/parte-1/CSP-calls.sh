#!/bin/bash


echo "---------------------------"
echo "Ejecutando Test"
echo "---------------------------"
echo ""

echo "Ejecutando ./CSP-tests/maintenance01"
python3 CSPMaintenance.py \ CSP-tests/maintenance01.txt


echo "---------------------------"
echo ""

echo "Ejecutando ./CSP-tests/maintenance02"
python3 CSPMaintenance.py \ CSP-tests/maintenance02.txt

echo "---------------------------"
echo ""

echo "Ejecutando ./CSP-tests/maintenance03"
python3 CSPMaintenance.py \ CSP-tests/maintenance03.txt

echo ""
echo "---------------------------"
echo "Completado"
echo "---------------------------"

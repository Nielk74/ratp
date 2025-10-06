#!/bin/bash

echo "=== RATP Live Tracker - Quick Endpoint Tests ==="
echo ""

# Test 1: Health
echo "1. Health Check:"
timeout 3 curl -s http://localhost:8000/health && echo " ✓" || echo " ✗"
echo ""

# Test 2: Root
echo "2. Root Info:"
timeout 3 curl -s http://localhost:8000/ | head -c 100 && echo "... ✓" || echo " ✗"
echo ""

# Test 3: Lines
echo "3. Get Lines:"
timeout 3 curl -s http://localhost:8000/api/lines/ | head -c 200 && echo "... ✓" || echo " ✗"
echo ""

# Test 4: Geolocation
echo "4. Nearest Stations (Châtelet):"
timeout 3 curl -s "http://localhost:8000/api/geo/nearest?lat=48.8584&lon=2.3470" | head -c 200 && echo "... ✓" || echo " ✗"
echo ""

# Test 5: Traffic (with timeout since it may be slow)
echo "5. Traffic Status (may timeout if external API is slow):"
timeout 3 curl -s http://localhost:8000/api/traffic/ | head -c 200 && echo "... ✓" || echo " ⚠ (timeout/unavailable)"
echo ""

# Test 6: Webhooks list
echo "6. List Webhooks:"
timeout 3 curl -s http://localhost:8000/api/webhooks/ && echo " ✓" || echo " ✗"
echo ""

echo "=== Tests Complete ==="
